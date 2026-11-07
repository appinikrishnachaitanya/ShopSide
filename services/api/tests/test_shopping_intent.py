import json
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app


def test_ai_interpretation_is_shared_and_creates_move_in_context(monkeypatch):
    import app.main as main
    output={'shopping_goal':'Furnish bedroom','product_requirements':['bed','lamp'],'budget_cents':100000,'currency':'USD','style':'minimalist','constraints':['small room'],'shopping_context':'move_in','participant_count':2,'bundle_requested':True,'follow_up':'What bed size?'}
    class Models:
        def generate_content(self,**kwargs):return SimpleNamespace(text=json.dumps(output))
    class Client:
        models=Models()
        def close(self):pass
    monkeypatch.setattr(main,'configured_client',lambda:Client())
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    a,b=TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'Alex','initial_request':'We are moving and need a bed and lamp under $1000'}).json()
    base='/api/rooms/'+created['room']['id']
    assert b.post('/api/join/'+created['invite'],json={'name':'Sam'}).status_code==200
    assert b.post(base+'/intent').status_code==403
    assert a.post(base+'/intent').status_code==200
    shared=b.get(base).json()
    assert shared['mode']=='move_in' and shared['shopping_intent']['bundle_requested'] is True
    assert shared['move_in']['mission']['budget_cents']==100000
    assert shared['move_in']['question']=='What bed size?'


def test_bundle_uses_real_observed_prices_and_total_budget(monkeypatch):
    import app.main as main
    import time
    client=TestClient(app)
    created=client.post('/api/rooms',json={'name':'Alex'}).json();r=created['room']['id'];base='/api/rooms/'+r
    with main.lock:
        room=main.load(r);room['shopping_intent']={'product_requirements':['desk','chair'],'budget_cents':30000,'currency':'USD'};main.save(r,room)
    def search(term, _max=None):
        return [{'id':'channel3:'+term,'name':term,'provenance':'channel3','retrieved_at':time.time(),'offers':[{'url':'https://retailer.example/p','retailer':'retailer.example','price_cents':10000 if term=='desk' else 12000,'currency':'USD','availability':'InStock'}]}]
    monkeypatch.setattr(main,'search_products',search)
    assert client.post(base+'/bundle/search').json()=={'count':1}
    room=client.get(base).json()
    assert room['bundle_options'][0]['total_cents']==22000
    assert len(room['discovery'])==2
    assert client.post(base+'/commands',json={'kind':'budget','value':'20000','revision':room['revision'],'command_id':'new-budget'}).status_code==200
    assert 'bundle_options' not in client.get(base).json()
    assert client.post(base+'/bundle/search').json()=={'count':0}

def test_home_planning_can_be_enabled_without_ai():
    client=TestClient(app)
    room=client.post('/api/rooms',json={'name':'Alex','initial_request':'A room under $700'}).json()['room']
    base='/api/rooms/'+room['id']
    assert client.post(base+'/home-plan').status_code==200
    updated=client.get(base).json()
    assert updated['mode']=='move_in'
    assert updated['move_in']['mission']['budget_cents']==70000
