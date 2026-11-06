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
