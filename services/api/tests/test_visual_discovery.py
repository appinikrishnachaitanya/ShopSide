from fastapi.testclient import TestClient
import app.main as main
from app import discovery


def test_channel3_image_and_product_url_search_share_room(monkeypatch):
    calls=[]
    def provider(path,payload):
        calls.append((path,payload))
        product={'id':'visual-1','title':'Verified watch','offers':[]}
        return {'products':[product]} if path=='/v1/search' else {'product':product}
    monkeypatch.setattr(discovery,'request',provider)
    client=TestClient(main.app)
    room=client.post('/api/rooms',json={'name':'Buyer'}).json()['room']['id']
    base=f'/api/rooms/{room}/discovery/visual'
    image=client.post(base,json={'url':'https://images.example/watch.jpg','kind':'image','revision':0,'command_id':'image-1'})
    assert image.status_code==200,image.text
    assert calls[-1]==('/v1/search',{'image_url':'https://images.example/watch.jpg','limit':12})
    lookup=client.post(base,json={'url':'https://retailer.example/watch','kind':'product','revision':1,'command_id':'lookup-1'})
    assert lookup.status_code==200,lookup.text
    assert calls[-1]==('/v1/lookup',{'url':'https://retailer.example/watch'})
    assert main.load(room)['discovery'][0]['id']=='channel3:visual-1'
    rejected=client.post(base,json={'url':'http://localhost/watch','kind':'product','revision':2,'command_id':'bad-1'})
    assert rejected.status_code==422
