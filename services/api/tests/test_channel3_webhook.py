import base64
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from svix.webhooks import Webhook
import app.main as main


def test_signed_channel3_webhook_is_durable_and_deduplicated(monkeypatch):
    secret='whsec_'+base64.b64encode(b'channel3-local-test-secret').decode()
    monkeypatch.setenv('CHANNEL3_WEBHOOK_SECRET',secret)
    monkeypatch.setattr(main.merchant_tasks,'configured',lambda:False)
    body=json.dumps({'type':'offer.price.changed','data':{'subscription_id':'sub-test'}})
    event_id='msg-channel3-local-test'
    timestamp=datetime.now(timezone.utc)
    headers={'svix-id':event_id,'svix-timestamp':str(int(timestamp.timestamp())),
             'svix-signature':Webhook(secret).sign(event_id,timestamp,body)}
    client=TestClient(main.app)
    assert client.post('/api/channel3/webhooks',content=body,headers=headers).status_code==200
    assert client.post('/api/channel3/webhooks',content=body,headers=headers).status_code==200
    assert main.db.execute('SELECT COUNT(*) FROM channel3_webhook_events WHERE id=?',(event_id,)).fetchone()[0]==1
    assert client.post('/api/channel3/webhooks',content=body+' ',headers=headers).status_code==403


def test_channel3_webhook_requires_secret(monkeypatch):
    monkeypatch.delenv('CHANNEL3_WEBHOOK_SECRET',raising=False)
    assert TestClient(main.app).post('/api/channel3/webhooks',json={}).status_code==503


def test_webhook_worker_refreshes_offer_and_alerts_watch_owner(monkeypatch):
    from app import discovery
    monkeypatch.setattr(discovery,'request',lambda path,body:{'subscription_id':'worker-sub'})
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    monkeypatch.setattr(discovery,'product_details',lambda id,options=None:{'offers':[{'retailer':'store.example','price_cents':8000,'currency':'USD'}]})
    client=TestClient(main.app)
    room=client.post('/api/rooms',json={'name':'Alice'}).json()['room']['id']
    watch=client.post(f'/api/rooms/{room}/price-watches',json={'product_id':'channel3:worker-product','threshold_cents':9000}).json()
    event_id='msg-worker-local'
    main.db.execute('INSERT INTO channel3_webhook_events VALUES(?,?,?,?)',(event_id,'offer.price.changed',
        datetime.now(timezone.utc).isoformat(),json.dumps({'type':'offer.price.changed','data':{'subscription_id':'worker-sub'},'status':'pending'})))
    main.db.commit()
    path=f'/api/internal/channel3-events/{event_id}/process'
    response=client.post(path)
    assert response.status_code==200,response.text
    assert response.json()['status']=='processed'
    assert client.post(path).json()['status']=='processed'
    alerts=main.load(room)['price_watch_alerts']
    assert len(alerts)==1 and alerts[0]['participant']=='Alice' and alerts[0]['price_cents']==8000


def test_availability_event_alerts_without_a_price(monkeypatch):
    from app import discovery
    monkeypatch.setattr(discovery,'request',lambda path,body:{'subscription_id':'availability-sub'})
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    monkeypatch.setattr(discovery,'product_details',lambda id,options=None:{'offers':[{'retailer':'store.example','price_cents':None,'currency':'USD','availability':'InStock'}]})
    client=TestClient(main.app)
    room=client.post('/api/rooms',json={'name':'Alice'}).json()['room']['id']
    assert client.post(f'/api/rooms/{room}/price-watches',json={'product_id':'channel3:available-product','threshold_cents':9000}).status_code==200
    event_id='msg-availability-local'
    main.db.execute('INSERT INTO channel3_webhook_events VALUES(?,?,?,?)',(event_id,'offer.availability.changed',
        datetime.now(timezone.utc).isoformat(),json.dumps({'type':'offer.availability.changed','data':{'subscription_id':'availability-sub'},'status':'pending'})))
    main.db.commit()
    assert client.post(f'/api/internal/channel3-events/{event_id}/process').status_code==200
    alert=main.load(room)['price_watch_alerts'][0]
    assert alert['kind']=='availability' and alert['price_cents'] is None
