from fastapi.testclient import TestClient
import app.main as main
import pytest
import json


def test_watch_reuses_subscription_and_cancels_after_last_listener(monkeypatch):
    from app import discovery
    calls=[]
    monkeypatch.setattr(discovery,'request',lambda path,body: calls.append(('create',path,body)) or {'subscription_id':'sub-1'})
    monkeypatch.setattr(discovery,'cancel_subscription',lambda id: calls.append(('cancel',id)))
    first=TestClient(main.app); second=TestClient(main.app)
    room=first.post('/api/rooms',json={'name':'Alice'}).json()['room']['id']
    invite=main.load(room)['invite']
    assert second.post(f'/api/join/{invite}',json={'name':'Bob'}).status_code==200
    state=main.load(room);state['discovery']=[{'id':'channel3:item-123','provider_id':'item-123','name':'Chair','source':'CHANNEL3_LIVE','offers':[{'retailer':'store.example','currency':'USD','price_cents':10000}]}];main.save(room,state)
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
    state=main.load(room);state['discovery']=[{'id':'channel3:item-123','provider_id':'item-123','name':'Shoe','source':'CHANNEL3_LIVE','offers':[{'retailer':'store.example','currency':'USD','price_cents':10000}]}];main.save(room,state)
    monkeypatch.setattr(main,'product_details',lambda id,selected_options: (_ for _ in ()).throw(main.HTTPException(409,'Requested variation is unavailable')))
    response=client.post(f'/api/rooms/{room}/price-watches',json={
        'product_id':'channel3:item-123','threshold_cents':10000,'selected_options':{'Size':'9'}})
    assert response.status_code==409


def test_cancelled_channel3_subscription_can_be_recreated(monkeypatch):
    from app import discovery
    monkeypatch.setenv('CHANNEL3_API_KEY','test-key')
    calls=[]
    class Response:
        status_code=200
        def raise_for_status(self):pass
        def json(self):return {'subscription_id':'sub-'+str(len(calls))}
    class Client:
        def __init__(self,**kwargs):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def request(self,*args,**kwargs):calls.append((args,kwargs));return Response()
    monkeypatch.setattr(discovery.httpx,'Client',Client)
    first=discovery.request('/v1/product-subscriptions',{'product_id':'one','events':['offer.price.changed']})
    second=discovery.request('/v1/product-subscriptions',{'product_id':'one','events':['offer.price.changed']})
    assert first['subscription_id']!=second['subscription_id']
    assert len(calls)==2

def test_watch_currency_is_validated_and_filters_webhook_offers():
    from pydantic import ValidationError
    watch=main.WatchRequest(product_id='channel3:chair',threshold_cents=9000,currency='GBP')
    assert watch.currency=='GBP'
    with pytest.raises(ValidationError):main.WatchRequest(product_id='channel3:chair',threshold_cents=9000,currency='gbp')
    offers=[{'currency':'USD','price_cents':13000},{'currency':'GBP','price_cents':8742}]
    assert main.offers_in_watch_currency(offers,{'currency':'GBP'})==[offers[1]]
    assert main.offers_in_watch_currency(offers,{})==[offers[0]]

def test_gbp_watch_is_bound_to_a_matching_saved_market_offer(monkeypatch):
    from starlette.requests import Request
    from app import discovery
    selected={'id':'channel3:chair','provider_id':'chair','offers':[{'retailer':'debenhams.example','currency':'GBP','price_cents':8742}]}
    monkeypatch.setattr(main,'room_channel3_product',lambda *_:selected)
    monkeypatch.setattr(main,'auth',lambda *_:'Alice')
    calls=[]
    monkeypatch.setattr(discovery,'request',lambda path,payload:(calls.append((path,payload)) or {'subscription_id':'gbp-sub'}))
    request=Request({'type':'http','method':'POST','path':'/','headers':[], 'query_string':b'', 'server':('test',80), 'client':('test',1), 'scheme':'http'})
    watch=main.create_price_watch('gbp-room',main.WatchRequest(product_id='channel3:chair',threshold_cents=9000,currency='GBP',retailer_domain='debenhams.example'),request)
    assert watch['currency']=='GBP'
    assert json.loads(watch['scope'])['currency']=='GBP'
    assert calls[0][1]['domains']==['debenhams.example']
    with pytest.raises(main.HTTPException):
        main.create_price_watch('gbp-room',main.WatchRequest(product_id='channel3:chair',threshold_cents=9000,currency='USD'),request)
