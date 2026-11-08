import json
import uuid
from fastapi.testclient import TestClient
import app.main as main
from test_merchant_checkout import accepted_offer
from app.merchant import identity, match, merchant, put, read


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
                'amount':{'currency_code':'USD','value':'270.00','breakdown':{}},
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


def test_buyer_authorizes_before_merchant_offer_and_settles_lower_amount(monkeypatch):
    client=TestClient(main.app)
    room_id=client.post('/api/rooms',json={'name':'Buyer'}).json()['room']['id']
    seller=merchant(main.db,'sandbox-merchant-1')
    seller.update(opt_in=True,active=True,mode='manual')
    seller['policy'].update(minimum_price_cents=20000,max_discount_bps=1000)
    put(main.db,'merchants',seller['id'],seller)
    token='merchant-test-'+uuid.uuid4().hex
    main.db.execute('INSERT INTO merchant_users(token_hash,merchant_id,name) VALUES(?,?,?)',
        (identity(token),seller['id'],'Operator'));main.db.commit()
    room=main.load(room_id)
    room['budget']=30000;room['shopping_intent']={'product_requirements':['compact desk','ergonomic chair']}
    room['seller_offers']={'enabled':True,'merchant_id':seller['id'],'auto_accept_limit_cents':28000,
        'policy_version':1,'demand_key':uuid.uuid4().hex,'expires_at':main.time.time()+3600}
    main.save(room_id,room)
    opportunity_id=match(main.db,room_id,room,main.notify)[0]
    monkeypatch.setenv('PAYPAL_MERCHANT_IDS_JSON',json.dumps({seller['id']:'mapped-sandbox-payee'}))
    monkeypatch.setenv('PAYPAL_PARTIAL_CAPTURE_MERCHANT_IDS_JSON',json.dumps([seller['id']]))
    monkeypatch.setattr(main.merchant_tasks,'configured',lambda:True)
    queued=[];monkeypatch.setattr(main.merchant_tasks,'enqueue',lambda id,path=None:queued.append((id,path)))
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    payment_response=client.post(f'/api/rooms/{room_id}/deal-rescue/{opportunity_id}/provisional-authorization',json={'maximum_cents':28000})
    assert payment_response.status_code==200,payment_response.text
    payment=payment_response.json();assert payment['quote_id'] is None and payment['total']==28000
    calls=[]
    async def provider(method,path,payload=None,operation=None):
        calls.append((method,path,payload))
        if path=='/v2/checkout/orders' and method=='POST':return {'id':'PRE-OFFER-ORDER'}
        if path.endswith('/authorize') and method=='POST':return {}
        if path.endswith('/capture') and method=='POST':
            assert payload['amount']=={'currency_code':'USD','value':'270.00'}
            return {'id':'LOWER-CAPTURE'}
        if path=='/v2/payments/captures/LOWER-CAPTURE':return {'status':'COMPLETED','amount':{'currency_code':'USD','value':'270.00'}}
        if path=='/v2/checkout/orders/PRE-OFFER-ORDER':return {'purchase_units':[{'payee':{'merchant_id':'mapped-sandbox-payee'},
            'amount':{'currency_code':'USD','value':'280.00','breakdown':{}},'payments':{'authorizations':[{'id':'PRE-OFFER-AUTH',
                'status':'CREATED','amount':{'currency_code':'USD','value':'280.00'}}]}}]}
        raise AssertionError((method,path))
    monkeypatch.setattr(main,'paypal',provider)
    base=f'/api/rooms/{room_id}/payments/{payment["id"]}'
    assert client.post(base+'/preauthorize/create').json()['status']=='approval'
    assert client.post(base+'/preauthorize/authorize').json()['status']=='authorized'
    assert not queued  # No merchant offer exists yet.
    merchant_headers={'X-ShopSide-Merchant-Token':token}
    proposed=client.post(f'/api/merchant/opportunities/{opportunity_id}/action',headers=merchant_headers,json={
        'command_id':uuid.uuid4().hex,'action':'generate','price_cents':27000,'explanation':'Approved workspace bundle.'})
    assert proposed.status_code==200,proposed.text
    assert queued  # Accepted within the buyer's recorded limit after seller approval.
    settled=client.post(f'/api/internal/paypal-settlements/{payment["id"]}/process')
    assert settled.status_code==200,settled.text
    assert settled.json()['capture_id']=='LOWER-CAPTURE'
    receipt=client.get(f'/api/rooms/{room_id}/merchant-orders/{payment["id"]}/receipt').json()
    assert receipt['total_cents']==27000 and receipt['paypal_sandbox_authorization_id']=='PRE-OFFER-AUTH'


def test_lower_capture_without_capability_voids_hold_and_requests_buyer_checkout(monkeypatch):
    client,room_id,offer,_=accepted_offer()
    monkeypatch.setenv('PAYPAL_MERCHANT_IDS_JSON',json.dumps({offer['merchant_id']:'mapped-sandbox-payee'}))
    monkeypatch.delenv('PAYPAL_PARTIAL_CAPTURE_MERCHANT_IDS_JSON',raising=False)
    monkeypatch.setattr(main.merchant_tasks,'verify',lambda request:True)
    payment=client.post(f'/api/rooms/{room_id}/seller-offers/{offer["id"]}/checkout').json()
    payment.update(authorization_mode='PREAUTHORIZED',payee='mapped-sandbox-payee',status='authorized',
        provider_id='PAYPAL-ORDER',authorization_id='PAYPAL-AUTH',authorization_void_id='VOID-ID',
        authorization_expires=main.time.time()+3600,total=28000)
    main.payment_save(payment)
    calls=[]
    async def provider(method,path,payload=None,operation=None):
        calls.append(path)
        if method=='POST' and path.endswith('/void'):return {}
        if method=='GET' and path.endswith('/PAYPAL-AUTH'):return {'status':'VOIDED'}
        raise AssertionError('No capture may occur without lower-amount capture capability')
    monkeypatch.setattr(main,'paypal',provider)
    result=client.post(f'/api/internal/paypal-settlements/{payment["id"]}/process')
    assert result.status_code==200,result.text
    assert result.json()['status']=='buyer_approval_required'
    assert main.load(room_id)['checkout'] is None
    assert not any(path.endswith('/capture') for path in calls)
