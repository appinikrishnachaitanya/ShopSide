import os, tempfile
os.environ['SHOPSIDE_DB']=tempfile.mktemp()
from fastapi.testclient import TestClient
from app.main import app

def test_shared_room():
    a,b,c=TestClient(app),TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'Krishna'}).json(); r=result['room']['id']
    assert b.get('/api/rooms/'+r).status_code==403
    assert b.post('/api/join/'+result['invite'],json={'name':'Priya'}).status_code==200
    assert c.post('/api/join/'+result['invite'],json={'name':'Third'}).status_code==409
    cmd={'command_id':'one','revision':1,'kind':'focus','value':'2'}
    assert a.post('/api/rooms/'+r+'/commands',json=cmd).status_code==200
    assert b.get('/api/rooms/'+r).json()['focus']=='2'
    assert a.post('/api/rooms/'+r+'/commands',json=cmd).status_code==200
    assert b.post('/api/rooms/'+r+'/commands',json={**cmd,'command_id':'two'}).status_code==409
    assert b.post('/api/rooms/'+r+'/commands',json={'command_id':'three','revision':2,'kind':'reaction','value':'2'}).status_code==200
    assert a.get('/api/rooms/'+r).json()['reactions']['2']==['Priya']

def test_cart_quote_authority_and_freeze():
    a,b=TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'Payer'}).json(); r=result['room']['id']; base='/api/rooms/'+r
    b.post('/api/join/'+result['invite'],json={'name':'Friend'})
    assert a.post(base+'/commands',json={'command_id':'cart','revision':1,'kind':'cart','value':'0'}).status_code==200
    assert b.post(base+'/quote').status_code==403
    q=a.post(base+'/quote').json()
    assert q['total']==8900 and q['items'][0]['quantity']==1
    assert a.post(base+'/quote').status_code==409
    assert a.post(base+'/commands',json={'command_id':'edit','revision':3,'kind':'cart','value':'1'}).status_code==409
    assert b.post(base+'/payments/'+q['id']+'/cancel').status_code==403
    assert a.post(base+'/payments/'+q['id']+'/cancel').status_code==200
    assert a.get(base).json()['checkout'] is None

def test_websocket_membership_and_origin():
    a=TestClient(app); result=a.post('/api/rooms',json={'name':'A'}).json(); r=result['room']['id']
    with a.websocket_connect('/api/rooms/'+r+'/live',headers={'origin':'http://localhost:3000'}) as ws:
        assert ws.receive_json()['people']==['A']
        assert a.post('/api/rooms/'+r+'/commands',json={'command_id':'ws','revision':0,'kind':'focus','value':'3'}).status_code==200
        assert ws.receive_json()['focus']=='3'

def test_verified_capture_and_pending_recovery(monkeypatch):
    import app.main as main
    monkeypatch.setenv('PAYPAL_MERCHANT_ID','merchant')
    a=TestClient(app); result=a.post('/api/rooms',json={'name':'Payer'}).json(); base='/api/rooms/'+result['room']['id']
    a.post(base+'/commands',json={'command_id':'cart','revision':0,'kind':'cart','value':'0'})
    quote=a.post(base+'/quote').json(); url=base+'/payments/'+quote['id']
    calls=[]
    async def fake(method,path,payload=None,operation=None):
        calls.append((method,path,operation))
        if path=='/v2/checkout/orders': return {'id':'provider-order'}
        if path.endswith('/capture'): return {'status':'COMPLETED'}
        return {'status':'COMPLETED','purchase_units':[{'payee':{'merchant_id':'merchant'},'payments':{'captures':[{'id':'verified-capture','status':'COMPLETED','amount':{'currency_code':'USD','value':'89.00'}}]}}]}
    monkeypatch.setattr(main,'paypal',fake)
    assert a.post(url+'/create').json()['order_id']=='provider-order'
    assert a.post(url+'/capture').json()['status']=='paid'
    assert a.post(url+'/capture').json()['status']=='paid'
    assert len([c for c in calls if c[1].endswith('/capture')])==1
    assert a.get(base).json()['checkout']['status']=='paid'

def test_discovery_shared_and_external_offer_cannot_charge(monkeypatch):
    import app.main as main
    from app.discovery import normalize
    item=normalize({'id':'real-product','title':'Provider headphones','offers':[{'url':'https://retailer.example/item','domain':'retailer.example','price':{'price':99.99,'currency':'USD'}}]})
    assert item['offers'][0]['price_cents']==9999
    assert item['merchant_offer'] is None
    monkeypatch.setattr(main,'search_products',lambda q,max_price=None:[item])
    a,b=TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'A'}).json(); base='/api/rooms/'+result['room']['id']
    b.post('/api/join/'+result['invite'],json={'name':'B'})
    assert a.post(base+'/discovery',json={'query':'headphones'}).status_code==200
    assert b.get(base).json()['discovery'][0]['provenance']=='channel3'
    rev=b.get(base).json()['revision']
    assert a.post(base+'/commands',json={'command_id':'external','revision':rev,'kind':'cart','value':item['id']}).status_code==422
    assert a.post(base+'/commands',json={'command_id':'spotlight','revision':rev,'kind':'focus','value':item['id']}).status_code==200
    assert b.get(base).json()['focus']==item['id']

def test_missing_discovery_key_is_explicit(monkeypatch):
    monkeypatch.delenv('CHANNEL3_API_KEY',raising=False)
    a=TestClient(app); result=a.post('/api/rooms',json={'name':'A'}).json()
    assert a.post('/api/rooms/'+result['room']['id']+'/discovery',json={'query':'headphones'}).status_code==503

def test_variant_quantity_reservation_cancel_and_replay():
    import app.main as main
    a=TestClient(app); r=a.post('/api/rooms',json={'name':'Payer'}).json()['room']['id']; base='/api/rooms/'+r
    import json
    before=main.stock('7','midnight')
    line={'product':'7','variant':'midnight','quantity':2}
    assert a.post(base+'/commands',json={'command_id':'variant','revision':0,'kind':'cart_line','value':json.dumps(line)}).status_code==200
    q=a.post(base+'/quote').json()
    assert q['total']==17000 and q['items'][0]['variant']=='midnight'
    assert main.stock('7','midnight')==before-2
    assert a.post(base+'/payments/'+q['id']+'/cancel').status_code==200
    assert main.stock('7','midnight')==before
    assert a.post(base+'/payments/'+q['id']+'/create').status_code==409
    assert a.post(base+'/payments/'+q['id']+'/cancel').status_code==409

def test_lost_capture_response_reconciles_without_second_charge(monkeypatch):
    import app.main as main
    import httpx
    monkeypatch.setenv('PAYPAL_MERCHANT_ID','merchant')
    a=TestClient(app); r=a.post('/api/rooms',json={'name':'Payer'}).json()['room']['id']; base='/api/rooms/'+r
    a.post(base+'/commands',json={'command_id':'cart','revision':0,'kind':'cart','value':'6'})
    q=a.post(base+'/quote').json(); url=base+'/payments/'+q['id']; captures=[]
    async def fake(method,path,payload=None,operation=None):
        if path=='/v2/checkout/orders': return {'id':'lost-response-order'}
        if path.endswith('/capture'):
            captures.append(operation); raise httpx.ReadTimeout('lost response')
        return {'status':'COMPLETED','purchase_units':[{'payee':{'merchant_id':'merchant'},'payments':{'captures':[{'id':'reconciled','status':'COMPLETED','amount':{'currency_code':'USD','value':'49.00'}}]}}]}
    monkeypatch.setattr(main,'paypal',fake)
    assert a.post(url+'/create').status_code==200
    assert a.post(url+'/capture').status_code==502
    assert a.post(url+'/capture').json()['status']=='paid'
    assert len(captures)==1
    assert a.get(base+'/checkout').json()['capture']=='reconciled'

def test_foreign_origin_and_friend_receipt_access():
    a,b=TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'Payer'}).json(); base='/api/rooms/'+result['room']['id']
    b.post('/api/join/'+result['invite'],json={'name':'Friend'})
    assert b.get(base+'/checkout').status_code==403
    assert b.get(base+'/me').json()['is_payer'] is False
    assert a.post(base+'/commands',headers={'origin':'https://foreign.example'},json={'command_id':'csrf','revision':1,'kind':'chat','value':'bad'}).status_code==403

def test_adk_coordinates_real_room_tool_with_test_runner(monkeypatch):
    """Explicitly fake model runner; validates ADK wiring and persisted tool outcomes."""
    import google.adk.runners
    from types import SimpleNamespace
    import app.main as main
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    seen={}
    class Sessions:
        async def create_session(self,**kwargs): return SimpleNamespace(id='test-session')
    class Runner:
        def __init__(self,agent,**kwargs): self.agent=agent; self.session_service=Sessions(); seen['agent']=agent
        async def run_async(self,**kwargs):
            tool=next(t for t in self.agent.tools if getattr(t,'__name__','')=='search_catalog')
            assert tool(query='Quiet')[0]['name']=='Quiet Hours'
            yield SimpleNamespace(is_final_response=lambda:True,content=SimpleNamespace(parts=[SimpleNamespace(text='Test runner response',thought=False)]))
    monkeypatch.setattr(google.adk.runners,'InMemoryRunner',Runner)
    a=TestClient(app);r=a.post('/api/rooms',json={'name':'A'}).json()['room']['id'];base='/api/rooms/'+r
    assert a.post(base+'/agent',json={'text':'Find Quiet Hours','revision':0}).status_code==200
    s=a.get(base).json()
    assert s['activity'][-1]['tool']=='search_catalog'
    assert s['messages'][-1]['actor']=='ShopSide'
    names=[getattr(t,'__name__','') for t in seen['agent'].tools]
    assert 'paypal_order_status' in names
    assert not any(name in names for name in ['create_order','pay_order','capture_order'])

def test_vertex_auth_modes_do_not_mix_api_key_and_adc(monkeypatch):
    import app.ai_config as config
    monkeypatch.setenv('AI_PROVIDER','vertex')
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT','test-project')
    monkeypatch.setenv('GOOGLE_CLOUD_LOCATION','global')
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setattr(config.genai,'Client',lambda **kwargs:kwargs)
    assert config.configured_client()=={'vertexai':True,'project':'test-project','location':'global'}
    monkeypatch.delenv('GOOGLE_CLOUD_PROJECT')
    monkeypatch.delenv('VERTEX_API_KEY',raising=False)
    assert config.configured_client()=={'vertexai':True,'api_key':'test-key'}


def test_express_mode_ignores_ambient_project(monkeypatch):
    import app.ai_config as config
    monkeypatch.setenv('AI_PROVIDER','vertex-express')
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT','ambient-project')
    monkeypatch.setenv('GEMINI_API_KEY','test-express-key')
    monkeypatch.delenv('VERTEX_API_KEY',raising=False)
    monkeypatch.setattr(config.genai,'Client',lambda **kwargs:kwargs)
    assert config.configured_client()=={'vertexai':True,'api_key':'test-express-key'}

def test_voice_signaling_only_between_authorized_room_members():
    from starlette.websockets import WebSocketDisconnect
    a,b,c=TestClient(app),TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'A'}).json();r=result['room']['id'];b.post('/api/join/'+result['invite'],json={'name':'B'})
    import pytest
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect('/api/rooms/'+r+'/call',headers={'origin':'http://localhost:3000'}):pass
    with a.websocket_connect('/api/rooms/'+r+'/call',headers={'origin':'http://localhost:3000'}) as first:
        with b.websocket_connect('/api/rooms/'+r+'/call',headers={'origin':'http://localhost:3000'}) as second:
            assert first.receive_json()['type']=='peer_ready'
            first.send_json({'type':'offer','payload':{'sdp':'test'}})
            assert second.receive_json()=={'type':'offer','payload':{'sdp':'test'}}
            second.send_json({'type':'answer','payload':{'sdp':'reply'}})
            assert first.receive_json()=={'type':'answer','payload':{'sdp':'reply'}}
