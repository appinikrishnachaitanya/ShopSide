from types import SimpleNamespace
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from app.main import app
from app.move_in import Allocation, Mission, PercentageAllocation, allocate_percentages

def test_new_room_retains_the_selected_shopping_mode():
    client=TestClient(app)
    created=client.post('/api/rooms',json={'name':'A','mode':'move_in','initial_request':'Sofa under $700'}).json()['room']
    assert created['mode']=='move_in'
    assert created['move_in']['mission']['budget_cents']==70000

def test_mission_validation_and_exact_cents():
    with pytest.raises(ValidationError): Mission(budget_cents=-1)
    with pytest.raises(ValidationError): Mission(currency='usd')
    with pytest.raises(ValidationError): Allocation(total_cents=100,currency='USD',shares={'A':50,'B':49},revision=0,command_id='x')
    assert allocate_percentages(101,{'A':5000,'B':5000})=={'A':51,'B':50}
    with pytest.raises(ValidationError): PercentageAllocation(total_cents=1,currency='USD',basis_points={'A':9999},revision=0,command_id='x')
    assert Allocation(total_cents=101,currency='USD',shares={'A':50,'B':51},revision=0,command_id='x').total_cents==101

def test_shared_mission_approvals_and_shares():
    a,b,c=TestClient(app),TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'A','mode':'move_in','initial_request':'Our first home'}).json()
    base='/api/rooms/'+created['room']['id']; assert c.get(base).status_code==403
    assert b.post('/api/join/'+created['invite'],json={'name':'B'}).status_code==200
    mission=created['room']['move_in']['mission'];mission['budget_cents']=50000
    update={'mission':mission,'revision':1,'command_id':'mission'}
    assert a.post(base+'/move-in/mission',json=update).status_code==200
    assert a.post(base+'/move-in/mission',json=update).status_code==200
    assert b.post(base+'/move-in/mission',json={**update,'command_id':'stale'}).status_code==409
    assert b.get(base).json()['move_in']['mission']['budget_cents']==50000
    assert a.post(base+'/move-in/item',json={'product_id':'11','status':'proposed','revision':2,'command_id':'item'}).status_code==200
    assert a.post(base+'/move-in/item',json={'product_id':'11','approve':True,'revision':3,'command_id':'a'}).status_code==200
    assert b.get(base).json()['move_in']['items']['11']['status']=='proposed'
    assert b.post(base+'/move-in/item',json={'product_id':'11','approve':True,'revision':4,'command_id':'b'}).status_code==200
    assert a.get(base).json()['move_in']['items']['11']['status']=='agreed'
    assert b.post(base+'/move-in/allocation',json={'total_cents':101,'currency':'USD','shares':{'A':50,'B':51},'revision':5,'command_id':'share'}).status_code==200
    assert a.get(base).json()['move_in']['allocation']['shares']=={'A':50,'B':51}
    assert c.post(base+'/move-in/item',json={'product_id':'11','approve':True,'revision':6,'command_id':'unauth'}).status_code==403

def test_question_limit_is_server_enforced(monkeypatch):
    import app.main as main
    import json
    mission=Mission().model_dump(mode='json')
    class Models:
        def generate_content(self,**kwargs):return SimpleNamespace(text=json.dumps({'mission':mission,'question':'What room? And which color?'}))
    monkeypatch.setenv('GEMINI_MODEL','test');monkeypatch.setattr(main,'configured_client',lambda:SimpleNamespace(models=Models(),close=lambda:None))
    a=TestClient(app);r=a.post('/api/rooms',json={'name':'A','mode':'move_in'}).json()['room']['id'];base='/api/rooms/'+r
    for n in range(6):
        state=a.get(base).json()
        assert a.post(base+'/move-in/turn',json={'text':f'answer {n}','revision':state['revision'],'command_id':f't{n}'}).status_code==200
    state=a.get(base).json()['move_in']
    assert state['question_count']<=4
    assert all(h['text'].count('?')<=1 for h in state['history'] if h['actor']=='ShopSide')

def test_cheaper_similar_uses_matching_currency(monkeypatch):
    import app.main as main
    source={'id':'channel3:original','provider_id':'original','name':'Chair','provenance':'channel3','offers':[{'currency':'USD','price_cents':10000}]}
    options=[{'id':'channel3:cheap','name':'Cheaper','offers':[{'currency':'USD','price_cents':8000}]}, {'id':'channel3:other','name':'Different currency','offers':[{'currency':'EUR','price_cents':100}]}]
    monkeypatch.setattr(main,'search_products',lambda *args:[source])
    monkeypatch.setattr(main,'product_details',lambda *args:source)
    monkeypatch.setattr(main,'similar_products',lambda *args:options)
    c=TestClient(app);room=c.post('/api/rooms',json={'name':'A','mode':'move_in'}).json()['room'];base='/api/rooms/'+room['id']
    assert c.post(base+'/discovery',json={'query':'chair'}).status_code==200
    result=c.post(base+'/product/cheaper',json={'provider_id':'original','revision':1,'command_id':'cheap'})
    assert result.status_code==200 and result.json()['count']==1
    ids={p['id'] for p in c.get(base).json()['discovery']};assert 'channel3:cheap' in ids and 'channel3:other' not in ids

def test_shared_room_placements_validate_and_sync():
    import json
    a,b,c=TestClient(app),TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'A','mode':'move_in'}).json();base='/api/rooms/'+created['room']['id']
    assert b.post('/api/join/'+created['invite'],json={'name':'B'}).status_code==200
    value=json.dumps({'product_id':'11','x':1.2,'z':-0.5})
    command={'kind':'placement_upsert','value':value,'revision':1,'command_id':'p1'}
    assert c.post(base+'/commands',json=command).status_code==403
    assert a.post(base+'/commands',json=command).status_code==200
    assert b.get(base).json()['room_placements'][0]['x']==1.2
    assert a.post(base+'/commands',json=command).status_code==200
    assert b.post(base+'/commands',json={**command,'command_id':'stale'}).status_code==409
    assert b.post(base+'/commands',json={'kind':'placement_upsert','value':json.dumps({'product_id':'11','x':9,'z':0}),'revision':2,'command_id':'bad'}).status_code==422
    assert b.post(base+'/commands',json={'kind':'placement_remove','value':'11','revision':2,'command_id':'remove'}).status_code==200
    assert a.get(base).json()['room_placements']==[]

def test_marker_reactions_are_independent_validated_and_shared():
    import json
    a,b,outsider=TestClient(app),TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'A','mode':'move_in'}).json();base='/api/rooms/'+created['room']['id']
    assert b.post('/api/join/'+created['invite'],json={'name':'B'}).status_code==200
    def cmd(client,kind,value,revision,id):return client.post(base+'/commands',json={'kind':kind,'value':json.dumps(value),'revision':revision,'command_id':id})
    assert cmd(a,'marker_reaction',{'product_id':'11','reaction':'love'},1,'missing').status_code==422
    assert cmd(a,'placement_upsert',{'product_id':'11','x':0,'z':0},1,'place').status_code==200
    assert cmd(outsider,'marker_reaction',{'product_id':'11','reaction':'love'},2,'denied').status_code==403
    assert cmd(a,'marker_reaction',{'product_id':'11','reaction':'bad'},2,'bad').status_code==422
    assert cmd(a,'marker_reaction',{'product_id':'11','reaction':'love'},2,'love').status_code==200
    assert cmd(a,'marker_reaction',{'product_id':'11','reaction':'love'},2,'love').status_code==200
    assert cmd(b,'marker_reaction',{'product_id':'11','reaction':'price'},2,'stale').status_code==409
    assert cmd(b,'marker_reaction',{'product_id':'11','reaction':'price'},3,'price').status_code==200
    assert a.get(base).json()['marker_reactions']['11']=={'A':'love','B':'price'}
    assert cmd(a,'marker_reaction',{'product_id':'11','reaction':'love'},4,'remove').status_code==200
    assert b.get(base).json()['marker_reactions']['11']=={'B':'price'}
    assert b.get(base).json().get('agreed_product') is None

def test_four_member_room_requires_every_member_to_approve():
    members=[TestClient(app) for _ in range(5)]
    created=members[0].post('/api/rooms',json={'name':'A','mode':'move_in'}).json();base='/api/rooms/'+created['room']['id']
    assert members[1].post('/api/join/'+created['invite'],json={'name':'B'}).status_code==200
    def action(client,value):
        state=client.get(base).json()
        return client.post(base+'/move-in/item',json={'product_id':'11','approve':True,'revision':state['revision'],'command_id':value})
    assert action(members[0],'a').status_code==200 and action(members[1],'b').status_code==200
    assert members[0].get(base).json()['move_in']['items']['11']['status']=='agreed'
    assert members[2].post('/api/join/'+created['invite'],json={'name':'C'}).status_code==200
    assert members[3].post('/api/join/'+created['invite'],json={'name':'D'}).status_code==200
    assert members[4].post('/api/join/'+created['invite'],json={'name':'E'}).status_code==409
    assert members[0].get(base).json()['move_in']['items']['11']['status']=='proposed'
    assert action(members[2],'c').status_code==200
    assert members[0].get(base).json()['move_in']['items']['11']['status']=='proposed'
    assert action(members[3],'d').status_code==200
    state=members[0].get(base).json()
    assert state['people']==['A','B','C','D'] and state['move_in']['items']['11']['status']=='agreed'

@pytest.mark.parametrize(('text','expected'),[
    ('We need a home office under $700.',70000),
    ('Our budget is $1,200.50 for the apartment',120050),
    ('We can spend up to USD 700',70000),
    ('A budget between $500 and $700',None),
    ('Our budget is under £700',None),
    ('A desk under $700 each',None),
    ('Under $700 for each item',None),
    ('Rent under $700',None),
    ('Not under $700',None),
    ('A $700 desk',None),
])
def test_explicit_initial_budget_is_conservative(text,expected):
    from app.move_in import explicit_initial_usd_budget
    assert explicit_initial_usd_budget(text)==expected

def test_initial_budget_survives_model_omission_and_failure(monkeypatch):
    import app.main as main
    import json
    request='We need a home office and kitchen under $700.'
    client=TestClient(app)
    room=client.post('/api/rooms',json={'name':'A','mode':'move_in','initial_request':request}).json()['room']
    base='/api/rooms/'+room['id']
    assert room['move_in']['mission']['budget_cents']==70000
    class Models:
        def generate_content(self,**kwargs):return SimpleNamespace(text=json.dumps({'mission':Mission().model_dump(mode='json'),'question':'What is most important?'}))
    monkeypatch.setenv('GEMINI_MODEL','test')
    monkeypatch.setattr(main,'configured_client',lambda:SimpleNamespace(models=Models(),close=lambda:None))
    assert client.post(base+'/move-in/turn',json={'text':request,'revision':0,'command_id':'turn'}).status_code==200
    assert client.get(base).json()['move_in']['mission']['budget_cents']==70000
    other=client.post('/api/rooms',json={'name':'B','mode':'move_in','initial_request':request}).json()['room'];other_base='/api/rooms/'+other['id']
    def fail():raise RuntimeError('provider offline')
    monkeypatch.setattr(main,'configured_client',fail)
    assert client.post(other_base+'/move-in/turn',json={'text':request,'revision':0,'command_id':'turn'}).status_code==502
    assert client.get(other_base).json()['move_in']['mission']['budget_cents']==70000
