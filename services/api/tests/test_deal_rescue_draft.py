from fastapi.testclient import TestClient
import app.main as main
from app.merchant import merchant,put,demand_from_room


def test_price_watch_alert_creates_owned_alternative_draft_without_payment(monkeypatch):
    from app import discovery
    monkeypatch.setattr(discovery,'request',lambda path,payload:{'subscription_id':'draft-sub'})
    seller=merchant(main.db,'sandbox-merchant-1');seller.update(active=True,opt_in=True)
    put(main.db,'merchants',seller['id'],seller)
    client=TestClient(main.app)
    room=client.post('/api/rooms',json={'name':'Buyer','initial_request':'Desk under $300'}).json()['room']['id']
    state=main.load(room)
    state['discovery']=[{'id':'channel3:real-desk','provider_id':'real-desk','source':'CHANNEL3_LIVE',
        'name':'Compact desk','category':'Desks','offers':[{'retailer':'shop.example','url':'https://shop.example/desk','currency':'USD','price_cents':10000}],'retrieved_at':main.time.time()}]
    state['budget']=30000;main.save(room,state)
    watch=client.post(f'/api/rooms/{room}/price-watches',json={'product_id':'channel3:real-desk','threshold_cents':10000}).json()
    alert_id='event-1:'+watch['id']
    state=main.load(room);state['price_watch_alerts']=[{'id':alert_id,'participant':'Buyer','product_id':'channel3:real-desk',
        'price_cents':9000,'currency':'USD','kind':'price'}];main.save(room,state)
    result=client.post(f'/api/rooms/{room}/price-watch-alerts/{alert_id}/deal-rescue-draft')
    assert result.status_code==200,result.text
    assert result.json()['owned_alternative_category']=='desk'
    assert demand_from_room(main.load(room))['categories']==['desk']
    assert main.load(room)['checkout'] is None
    assert client.post(f'/api/rooms/{room}/deal-rescue/draft/clear').json()['cleared']
    assert 'deal_rescue_draft' not in main.load(room)
