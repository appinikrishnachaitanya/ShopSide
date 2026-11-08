import json
import uuid
from fastapi.testclient import TestClient
import app.main as main
from test_merchant_checkout import accepted_offer


def test_verified_capture_event_reconciles_merchant_order(monkeypatch):
    client,room,offer,_=accepted_offer()
    payment=client.post(f'/api/rooms/{room}/seller-offers/{offer["id"]}/checkout').json()
    payment.update(status='pending',provider_id='ORDER-'+uuid.uuid4().hex)
    main.payment_save(payment)
    event_id='event-'+uuid.uuid4().hex
    main.db.execute('INSERT INTO paypal_webhook_payloads VALUES(?,?)',(event_id,json.dumps({
        'event_type':'PAYMENT.CAPTURE.COMPLETED','order_id':payment['provider_id'],
        'capture_id':'CAPTURE-'+event_id,'status':'pending'})))
    main.db.commit()
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    monkeypatch.setenv('PAYPAL_MERCHANT_ID','sandbox-payee')
    async def provider(method,path,payload=None,operation=None):
        assert method=='GET' and path.endswith(payment['provider_id'])
        return {'status':'COMPLETED','purchase_units':[{'payee':{'merchant_id':'sandbox-payee'},
            'payments':{'captures':[{'id':'CAPTURE-'+event_id,'status':'COMPLETED',
                'amount':{'currency_code':'USD','value':'270.00','breakdown':{}}}]}}]}
    monkeypatch.setattr(main,'paypal',provider)
    result=client.post(f'/api/internal/paypal-events/{event_id}/process')
    assert result.status_code==200,result.text
    assert main.payment_load(payment['id'],room)['status']=='paid'
    assert main.load(room)['checkout']['status']=='paid'
    assert client.post(f'/api/internal/paypal-events/{event_id}/process').json()['status']=='processed'


def test_authorization_webhook_reads_back_provider_before_marking_authorized(monkeypatch):
    client,room,offer,_=accepted_offer()
    payment=client.post(f'/api/rooms/{room}/seller-offers/{offer["id"]}/checkout').json()
    payment.update(status='authorizing',authorization_mode='PREAUTHORIZED',provider_id='AUTH-ORDER',
        payee='sandbox-payee',authorization_expires=main.time.time()+3600)
    main.payment_save(payment)
    event_id='event-'+uuid.uuid4().hex
    main.db.execute('INSERT INTO paypal_webhook_payloads VALUES(?,?)',(event_id,json.dumps({
        'event_type':'PAYMENT.AUTHORIZATION.CREATED','order_id':'AUTH-ORDER',
        'authorization_id':'AUTH-ID','status':'pending'})))
    main.db.commit()
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    monkeypatch.setattr(main.merchant_tasks,'configured',lambda:False)
    async def provider(method,path,payload=None,operation=None):
        assert method=='GET' and path=='/v2/checkout/orders/AUTH-ORDER'
        return {'purchase_units':[{'payee':{'merchant_id':'sandbox-payee'},
            'amount':{'currency_code':'USD','value':'270.00','breakdown':{}},
            'payments':{'authorizations':[{'id':'AUTH-ID','status':'CREATED',
                'amount':{'currency_code':'USD','value':'270.00'}}]}}]}
    monkeypatch.setattr(main,'paypal',provider)
    response=client.post(f'/api/internal/paypal-events/{event_id}/process')
    assert response.status_code==200,response.text
    assert main.payment_load(payment['id'],room)['authorization_id']=='AUTH-ID'
    assert main.payment_load(payment['id'],room)['status']=='authorized'
