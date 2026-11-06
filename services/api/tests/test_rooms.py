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
