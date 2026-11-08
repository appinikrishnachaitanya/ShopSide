from fastapi.testclient import TestClient
import app.main as main


def test_watch_reuses_subscription_and_cancels_after_last_listener(monkeypatch):
    from app import discovery
    calls=[]
    monkeypatch.setattr(discovery,'request',lambda path,body: calls.append(('create',path,body)) or {'subscription_id':'sub-1'})
    monkeypatch.setattr(discovery,'cancel_subscription',lambda id: calls.append(('cancel',id)))
    first=TestClient(main.app); second=TestClient(main.app)
    room=first.post('/api/rooms',json={'name':'Alice'}).json()['room']['id']
    invite=main.load(room)['invite']
    assert second.post(f'/api/join/{invite}',json={'name':'Bob'}).status_code==200
    path=f'/api/rooms/{room}/price-watches'
    payload={'product_id':'channel3:item-123','threshold_cents':10000}
    a=first.post(path,json=payload); b=second.post(path,json=payload)
    assert a.status_code==200,a.text
    assert b.status_code==200,b.text
    assert len([x for x in calls if x[0]=='create'])==1
    assert len(first.get(path).json())==1
    assert first.post(path+'/'+a.json()['id']+'/cancel').status_code==200
    assert not any(x[0]=='cancel' for x in calls)
    assert second.post(path+'/'+b.json()['id']+'/cancel').status_code==200
    assert ('cancel','sub-1') in calls


def test_watch_requires_verified_variant(monkeypatch):
    from app import discovery
    client=TestClient(main.app)
    room=client.post('/api/rooms',json={'name':'Alice'}).json()['room']['id']
    monkeypatch.setattr(main,'product_details',lambda id,selected_options: (_ for _ in ()).throw(main.HTTPException(409,'Requested variation is unavailable')))
    response=client.post(f'/api/rooms/{room}/price-watches',json={
        'product_id':'channel3:item-123','threshold_cents':10000,'selected_options':{'Size':'9'}})
    assert response.status_code==409
