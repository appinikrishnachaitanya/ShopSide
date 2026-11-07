"""Owned sandbox offers retain their exact amount through PayPal verification."""
import uuid

from fastapi.testclient import TestClient

import app.main as main
from app.merchant import identity, match, merchant, publish, put, read
from app.merchant_agent import OfferProposal


def accepted_offer():
    client=TestClient(main.app)
    response=client.post('/api/rooms',json={'name':'Buyer'}).json()
    room_id=response['room']['id']
    state=main.load(room_id)
    state['budget']=50000
    state['shopping_intent']={'product_requirements':['compact desk','ergonomic chair']}
    state['seller_offers']={'enabled':True,'demand_key':uuid.uuid4().hex,'expires_at':main.merchant_service.now()+3600}
    m=merchant(main.db,'sandbox-merchant-1')
    m.update(opt_in=True,active=True,mode='manual')
    m['policy'].update(minimum_price_cents=20000,max_discount_bps=1000)
    put(main.db,'merchants',m['id'],m)
    token='merchant-test-'+uuid.uuid4().hex
    main.db.execute('INSERT INTO merchant_users(token_hash,merchant_id,name) VALUES(?,?,?)',(identity(token),m['id'],'Operator'))
    main.db.commit()
    op_id=next(op_id for op_id in match(main.db,room_id,state,main.notify)
               if read(main.db.execute('SELECT state FROM merchant_opportunities WHERE id=?',(op_id,)).fetchone())['merchant_id']==m['id'])
    op=read(main.db.execute('SELECT state FROM merchant_opportunities WHERE id=?',(op_id,)).fetchone())
    offer=publish(main.db,state,op,m,OfferProposal(product_id=op['product_id'],price_cents=27000,
        explanation='A desk and chair for your workspace.'),'operator',main.notify)['quote']
    state['revision']+=1;main.save(room_id,state)
    accepted=client.post(f'/api/rooms/{room_id}/seller-offers/action',json={
        'action':'accept','offer_id':offer['id'],'command_id':uuid.uuid4().hex})
    assert accepted.status_code==200,accepted.text
    return client,room_id,offer,token


def test_accepted_offer_paypal_capture_and_merchant_order(monkeypatch):
    client,room_id,offer,token=accepted_offer()
    before={line['product_id']:main.db.execute('SELECT stock_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
        (offer['merchant_id'],line['product_id'])).fetchone()[0] for line in offer['items']}
    async def no_receipt(*_args):pass
    monkeypatch.setattr(main,'auto_memory_receipts',no_receipt)
    async def provider(method,path,payload=None,operation=None):
        if method=='POST' and path=='/v2/checkout/orders':
            assert payload['purchase_units'][0]['amount']=={'currency_code':'USD','value':'270.00'}
            return {'id':'PAYPAL-SANDBOX-ORDER'}
        if method=='POST' and path.endswith('/capture'):return {}
        if method=='GET':return {'status':'COMPLETED','purchase_units':[{'payee':{'merchant_id':'sandbox-payee'},
            'payments':{'captures':[{'id':'SANDBOX-CAPTURE','status':'COMPLETED',
                'amount':{'currency_code':'USD','value':'270.00'}}]}}]}
        raise AssertionError((method,path))
    monkeypatch.setattr(main,'paypal',provider)
    monkeypatch.setenv('PAYPAL_MERCHANT_ID','sandbox-payee')
    response=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout')
    assert response.status_code==200,response.text
    payment=response.json()
    assert payment['total']==27000 and payment['merchant_id']=='sandbox-merchant-1'
    for line in payment['items']:
        stock=main.db.execute('SELECT stock_quantity,reserved_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
            (payment['merchant_id'],line['product'])).fetchone()
        assert stock[1]==1
    base=f'/api/rooms/{room_id}/payments/{payment["id"]}'
    assert client.post(base+'/create').json()['order_id']=='PAYPAL-SANDBOX-ORDER'
    result=client.post(base+'/capture')
    assert result.status_code==200,result.text
    assert result.json()['local_order_id']==payment['id']
    assert result.json()['capture']=='SANDBOX-CAPTURE'
    assert client.post(base+'/capture').json()['status']=='paid'
    receipt=client.get(f'/api/rooms/{room_id}/merchant-orders/{payment["id"]}/receipt').json()
    assert receipt['order_id']==payment['id'] and receipt['total_cents']==27000
    assert receipt['paypal_sandbox_capture_id']=='SANDBOX-CAPTURE'
    assert len(receipt['items'])==2
    assert receipt['payer'] and receipt['room_members']
    assert [event['event'] for event in receipt['decision_trail']][-1]=='payment_captured'
    assert TestClient(main.app).get(f'/api/rooms/{room_id}/merchant-orders/{payment["id"]}/receipt').status_code==403
    for line in payment['items']:
        stock=main.db.execute('SELECT stock_quantity,reserved_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
            (payment['merchant_id'],line['product'])).fetchone()
        assert stock==(before[line['product']]-1,0)
    portal=client.get('/api/merchant/me',headers={'X-ShopSide-Merchant-Token':token})
    assert portal.status_code==200
    assert portal.json()['metrics']['confirmed_orders']>=1
    assert any(order['id']==payment['id'] and order['paypal_capture_id']=='SANDBOX-CAPTURE' for order in portal.json()['orders'])


def test_malformed_paypal_readback_returns_reconcilable_error(monkeypatch):
    client,room_id,offer,_=accepted_offer()
    payment=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').json()
    async def provider(method,path,payload=None,operation=None):
        if method=='POST':return {'id':'PAYPAL-SANDBOX-ORDER'}
        return {'status':'COMPLETED','purchase_units':[]}
    monkeypatch.setattr(main,'paypal',provider)
    base=f'/api/rooms/{room_id}/payments/{payment["id"]}'
    assert client.post(base+'/create').status_code==200
    result=client.post(base+'/status')
    assert result.status_code==502
    assert 'check payment status' in result.json()['detail'].lower()
    with main.lock:
        pending=main.payment_load(payment['id'],room_id)
        main.release_merchant_reservations(pending)
        main.payment_save(pending)


def test_unaccepted_or_external_offer_cannot_checkout():
    client,room_id,offer,_=accepted_offer()
    assert client.post(f'/api/rooms/{room_id}/seller-offers/channel3:external/checkout').status_code==409
    state=main.load(room_id)
    next(o for o in state['flash_offers'] if o['id']==offer['id'])['status']='DECLINED'
    main.save(room_id,state)
    assert client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').status_code==409


def test_cancel_unused_merchant_quote_releases_stock():
    client,room_id,offer,_=accepted_offer()
    before={line['product_id']:main.db.execute('SELECT stock_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
        (offer['merchant_id'],line['product_id'])).fetchone()[0] for line in offer['items']}
    payment=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').json()
    assert client.post(f'/api/rooms/{room_id}/payments/{payment["id"]}/cancel').json()['status']=='cancelled'
    for line in payment['items']:
        assert main.db.execute('SELECT stock_quantity,reserved_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
            (payment['merchant_id'],line['product'])).fetchone()==(before[line['product']],0)
    assert client.post(f'/api/rooms/{room_id}/payments/{payment["id"]}/capture').status_code==409


def test_paypal_amount_mismatch_never_completes_merchant_order(monkeypatch):
    client,room_id,offer,token=accepted_offer()
    before=main.db.execute('SELECT stock_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
        (offer['merchant_id'],offer['items'][0]['product_id'])).fetchone()[0]
    payment=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').json()
    monkeypatch.setenv('PAYPAL_MERCHANT_ID','sandbox-payee')
    async def provider(method,path,payload=None,operation=None):
        if method=='POST' and path=='/v2/checkout/orders':return {'id':'MISMATCH-ORDER'}
        if method=='POST':return {}
        return {'status':'COMPLETED','purchase_units':[{'payee':{'merchant_id':'sandbox-payee'},
            'payments':{'captures':[{'id':'BAD-CAPTURE','status':'COMPLETED',
                'amount':{'currency_code':'USD','value':'1.00'}}]}}]}
    monkeypatch.setattr(main,'paypal',provider)
    base=f'/api/rooms/{room_id}/payments/{payment["id"]}'
    assert client.post(base+'/create').status_code==200
    assert client.post(base+'/capture').status_code==409
    assert main.db.execute('SELECT stock_quantity,reserved_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
        (payment['merchant_id'],payment['items'][0]['product'])).fetchone()==(before,1)
    portal=client.get('/api/merchant/me',headers={'X-ShopSide-Merchant-Token':token}).json()
    assert not any(order['id']==payment['id'] and order['status']=='paid' for order in portal['orders'])


def test_webhook_requires_verified_signature_and_deduplicates(monkeypatch):
    client=TestClient(main.app)
    monkeypatch.setenv('PAYPAL_WEBHOOK_ID','sandbox-webhook')
    headers={name:'test-value' for name in ('paypal-auth-algo','paypal-cert-url','paypal-transmission-id',
        'paypal-transmission-sig','paypal-transmission-time')}
    event={'id':'event-'+uuid.uuid4().hex,'event_type':'PAYMENT.CAPTURE.COMPLETED'}
    async def invalid(*_args,**_kwargs):return {'verification_status':'FAILURE'}
    monkeypatch.setattr(main,'paypal',invalid)
    assert client.post('/api/paypal/webhook',json=event,headers=headers).status_code==403
    async def valid(*_args,**_kwargs):return {'verification_status':'SUCCESS'}
    monkeypatch.setattr(main,'paypal',valid)
    assert client.post('/api/paypal/webhook',json=event,headers=headers).status_code==200
    assert client.post('/api/paypal/webhook',json=event,headers=headers).status_code==200
    assert main.db.execute('SELECT COUNT(*) FROM paypal_webhook_events WHERE id=?',(event['id'],)).fetchone()[0]==1
