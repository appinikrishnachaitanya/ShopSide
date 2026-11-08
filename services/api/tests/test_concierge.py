from fastapi.testclient import TestClient
from app.main import app


def test_concierge_removes_unverified_dimension_and_load_claims():
    from app.concierge import grounded_spec_text
    product={'name':'Compact desk','offers':[{'price_cents':47200,'currency':'USD','dimensions':None}],
             'attributes':{},'description':'A compact desk.','key_features':['Adjustable height']}
    result=grounded_spec_text('The desk is 48 inches wide and supports 200 lb. Listed price: $472.',[product])
    assert '48 inches wide' not in result
    assert 'supports 200 lb' not in result
    assert 'Listed price: $472.' in result
    assert 'Check the retailer listing' in result


def test_concierge_keeps_dimension_claims_when_matching_channel3_evidence_exists():
    from app.concierge import grounded_spec_text
    product={'name':'Compact desk','offers':[{'dimensions':{'width':{'number':48,'unit':'in'},
             'depth':{'number':24,'unit':'in'},'height':{'number':30,'unit':'in'}}}],
             'attributes':{},'description':'','key_features':[]}
    result=grounded_spec_text('The desk measures 48 × 24 × 30 in.',[product])
    assert result=='The desk measures 48 × 24 × 30 in.'
    assert '48 feet' not in grounded_spec_text('The Compact desk is 48 feet wide.',[product])

def test_provider_conversation_continues_and_persists(monkeypatch):
    import app.concierge as concierge
    calls=[]
    async def provider(text,conversation_id):
        calls.append((text,conversation_id))
        return {'conversation_id':'channel-thread','text':'How long is your trip?' if not conversation_id else 'What is your budget?','suggestions':['Weekend','10 days'],'products':[]}
    monkeypatch.setattr(concierge,'conversation_turn',provider)
    a,b=TestClient(app),TestClient(app);created=a.post('/api/rooms',json={'name':'A'}).json();base='/api/rooms/'+created['room']['id']
    assert b.post('/api/join/'+created['invite'],json={'name':'B'}).status_code==200
    assert a.post(base+'/concierge',json={'text':'I need luggage','revision':1,'command_id':'c1'}).status_code==200
    state=b.get(base).json();assert state['shopping_journey']['conversation_id']=='channel-thread';assert state['shopping_journey']['question']['choices']==['Weekend','10 days']
    assert b.post(base+'/concierge',json={'text':'10 days','revision':state['revision'],'command_id':'c2'}).status_code==200
    assert calls[-1]==('10 days','channel-thread')
    assert a.get(base).json()['shopping_journey']['question_count']==2

def test_question_cap_falls_back_to_real_search(monkeypatch):
    import app.concierge as concierge
    import app.main as main
    calls=[];queries=[]
    async def provider(text,conversation_id):
        calls.append(text);return {'conversation_id':'thread','text':'What else matters '+str(len(calls))+'?','suggestions':[],'products':[]}
    monkeypatch.setattr(concierge,'conversation_turn',provider)
    monkeypatch.setattr(main,'search_products',lambda q,max_price=None:(queries.append(q) or []))
    a=TestClient(app);r=a.post('/api/rooms',json={'name':'A'}).json()['room']['id'];base='/api/rooms/'+r
    for i in range(6):
        state=a.get(base).json();payload={'text':'luggage answer '+str(i),'revision':state['revision'],'command_id':'id'+str(i)}
        assert a.post(base+'/concierge',json=payload).status_code==200
    state=a.get(base).json();assert state['shopping_journey']['status']=='results';assert state['shopping_journey']['question_count']==5
    assert len(calls)==5 and 'luggage answer 0' in queries[0]
    assert a.post(base+'/concierge',json=payload).status_code==200
    assert a.get(base).json()['revision']==state['revision']

def test_show_now_and_provider_failure(monkeypatch):
    import app.concierge as concierge
    import app.main as main
    async def fail(*args):raise RuntimeError('provider unavailable')
    monkeypatch.setattr(concierge,'conversation_turn',fail)
    a=TestClient(app);r=a.post('/api/rooms',json={'name':'A'}).json()['room']['id'];base='/api/rooms/'+r
    assert a.post(base+'/concierge',json={'text':'luggage','revision':0,'command_id':'c'}).status_code==502
    assert a.get(base).json().get('shopping_journey') is None
    monkeypatch.setattr(main,'search_products',lambda q,max_price=None:[])
    assert a.post(base+'/concierge',json={'text':'','action':'show','revision':0,'command_id':'s'}).status_code==422
    assert a.get(base).json().get('discovery') is None

def test_explicit_agreement_requires_both_members():
    a,b=TestClient(app),TestClient(app);created=a.post('/api/rooms',json={'name':'A'}).json();base='/api/rooms/'+created['room']['id']
    b.post('/api/join/'+created['invite'],json={'name':'B'})
    assert a.post(base+'/commands',json={'kind':'agreement','value':'0','revision':1,'command_id':'a'}).status_code==200
    assert a.get(base).json()['agreed_product'] is None
    assert b.post(base+'/commands',json={'kind':'agreement','value':'0','revision':2,'command_id':'b'}).status_code==200
    assert a.get(base).json()['agreed_product']=='0'
    assert b.post(base+'/commands',json={'kind':'agreement','value':'1','revision':3,'command_id':'c'}).status_code==200
    assert a.get(base).json()['agreed_product'] is None

def test_variant_resolution_and_similar_are_shared_and_validated(monkeypatch):
    import app.main as main
    source={'id':'channel3:original','provider_id':'original','name':'Travel bag','provenance':'channel3','offers':[]}
    variant={'id':'channel3:blue','provider_id':'blue','name':'Blue bag','provenance':'channel3','offers':[]}
    monkeypatch.setattr(main,'search_products',lambda *args:[source])
    def details(product,options=None):
        if product=='original':return {**source,'variants':{'options':[{'name':'Color','values':[{'label':'Blue','product_id':'blue','exists':True}]}]}}
        assert product=='blue' and options=={'Color':'Blue'}
        return variant
    monkeypatch.setattr(main,'product_details',details)
    monkeypatch.setattr(main,'similar_products',lambda product:[{'id':'channel3:similar','provider_id':'similar','name':'Other','provenance':'channel3','offers':[]}])
    a,b=TestClient(app),TestClient(app);created=a.post('/api/rooms',json={'name':'A'}).json();base='/api/rooms/'+created['room']['id']
    b.post('/api/join/'+created['invite'],json={'name':'B'});a.post(base+'/discovery',json={'query':'bag'})
    payload={'provider_id':'original','selected_options':{'Color':'Blue'},'variant_product_id':'unknown','revision':2,'command_id':'bad'}
    assert a.post(base+'/product/resolve',json=payload).status_code==422
    payload.update(variant_product_id='blue',command_id='ok')
    assert a.post(base+'/product/resolve',json=payload).status_code==200
    state=b.get(base).json();assert state['focus']=='channel3:blue'
    assert a.post(base+'/product/similar',json={'provider_id':'blue','revision':state['revision'],'command_id':'similar'}).status_code==200
    assert any(p['id']=='channel3:similar' for p in b.get(base).json()['discovery'])


def test_initial_request_survives_provider_failure(monkeypatch):
    import app.concierge as concierge
    async def fail(*args):raise RuntimeError('offline')
    monkeypatch.setattr(concierge,'conversation_turn',fail)
    client=TestClient(app)
    room=client.post('/api/rooms',json={'name':'A','initial_request':'Luggage for a trip'}).json()['room']
    base='/api/rooms/'+room['id']
    assert client.post(base+'/concierge',json={'text':'Luggage for a trip','revision':0,'command_id':'c'}).status_code==502
    assert client.get(base).json()['shopping_journey']['history']==[{'actor':'A','text':'Luggage for a trip'}]

def test_refined_search_shares_pagination_and_filters(monkeypatch):
    import app.discovery as discovery
    calls=[]
    monkeypatch.setattr(discovery,'request',lambda path,payload:(calls.append((path,payload)) or {'products':[],'next_page_token':'next'}))
    a,b=TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'A'}).json();base='/api/rooms/'+created['room']['id']
    b.post('/api/join/'+created['invite'],json={'name':'B'})
    payload={'query':'luggage','min_price':50,'max_price':200,'availability':['InStock'],'mode':'agentic','currency':'USD','revision':1,'command_id':'s'}
    assert a.post(base+'/search',json=payload).status_code==200
    assert calls[0][1]['config']=={'mode':'agentic','currency':'USD'}
    assert calls[0][1]['filters']=={'price':{'min_price':50,'max_price':200},'availability':['InStock']}
    assert b.get(base).json()['search_page_token']=='next'
    assert a.post(base+'/search',json={**payload,'command_id':'invalid','revision':2,'min_price':300}).status_code==422
