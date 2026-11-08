import json
import uuid
from fastapi.testclient import TestClient
import app.main as main
from test_merchant_checkout import accepted_offer


def test_sandbox_authorize_and_offline_settlement(monkeypatch):
    client,room_id,offer,_=accepted_offer()
    monkeypatch.setenv('PAYPAL_MERCHANT_IDS_JSON',json.dumps({offer['merchant_id']:'mapped-sandbox-payee'}))
    monkeypatch.setattr(main.merchant_tasks,'configured',lambda:True)
    queued=[]
    monkeypatch.setattr(main.merchant_tasks,'enqueue',lambda id,path=None:queued.append((id,path)))
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    calls=[]
    async def provider(method,path,payload=None,operation=None):
        calls.append((method,path,payload,operation))
        if path=='/v2/checkout/orders' and method=='POST':
            assert payload['intent']=='AUTHORIZE'
            assert payload['purchase_units'][0]['payee']['merchant_id']=='mapped-sandbox-payee'
            return {'id':'PAYPAL-AUTH-ORDER'}
        if path.endswith('/authorize') and method=='POST':return {}
        if path.endswith('/capture') and method=='POST':return {'id':'PAYPAL-AUTH-CAPTURE'}
        if path=='/v2/payments/captures/PAYPAL-AUTH-CAPTURE':
            return {'status':'COMPLETED','amount':{'currency_code':'USD','value':'270.00'}}
        if path=='/v2/checkout/orders/PAYPAL-AUTH-ORDER':
            return {'purchase_units':[{'payee':{'merchant_id':'mapped-sandbox-payee'},
                'amount':{'currency_code':'USD','value':'270.00'},
                'payments':{'authorizations':[{'id':'PAYPAL-AUTH-ID','status':'CREATED',
                    'amount':{'currency_code':'USD','value':'270.00'}}]}}]}
        raise AssertionError((method,path))
    monkeypatch.setattr(main,'paypal',provider)
    payment=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').json()
    assert payment['preauthorization_available']
    base=f'/api/rooms/{room_id}/payments/{payment["id"]}'
    assert client.post(base+'/preauthorize/create').json()['status']=='approval'
    assert client.post(base+'/capture').status_code==409
    authorized=client.post(base+'/preauthorize/authorize')
    assert authorized.status_code==200,authorized.text
    assert authorized.json()['authorization_id']=='PAYPAL-AUTH-ID'
    assert queued and queued[0][1].endswith('/process')
    result=client.post(f'/api/internal/paypal-settlements/{payment["id"]}/process')
    assert result.status_code==200,result.text
    assert result.json()=={'status':'paid','capture_id':'PAYPAL-AUTH-CAPTURE'}
    assert client.post(f'/api/internal/paypal-settlements/{payment["id"]}/process').json()['status']=='paid'
    assert len([call for call in calls if call[1].endswith('/capture')])==1
    receipt=client.get(f'/api/rooms/{room_id}/merchant-orders/{payment["id"]}/receipt')
    assert receipt.status_code==200,receipt.text


def test_unmapped_merchant_cannot_preauthorize(monkeypatch):
    client,room_id,offer,_=accepted_offer()
    monkeypatch.delenv('PAYPAL_MERCHANT_IDS_JSON',raising=False)
    payment=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').json()
    assert payment['preauthorization_available'] is False
    assert client.post(f'/api/rooms/{room_id}/payments/{payment["id"]}/preauthorize/create').status_code==503


def test_settlement_rejects_revoked_consent_without_capture(monkeypatch):
    client,room_id,offer,_=accepted_offer()
    monkeypatch.setenv('PAYPAL_MERCHANT_IDS_JSON',json.dumps({offer['merchant_id']:'mapped-sandbox-payee'}))
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    payment=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').json()
    payment.update(authorization_mode='PREAUTHORIZED',payee='mapped-sandbox-payee',
        status='authorized',provider_id='PAYPAL-ORDER',authorization_id='PAYPAL-AUTH',
        authorization_expires=main.time.time()+3600)
    main.payment_save(payment)
    room=main.load(room_id);room['seller_offers']['enabled']=False;main.save(room_id,room)
    async def forbidden(*args,**kwargs):raise AssertionError('PayPal capture must not be attempted')
    monkeypatch.setattr(main,'paypal',forbidden)
    response=client.post(f'/api/internal/paypal-settlements/{payment["id"]}/process')
    assert response.status_code==409
