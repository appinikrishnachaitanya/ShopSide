"""Consent, tenant isolation, pricing authority and room offer lifecycle."""
import json, time, uuid
from fastapi.testclient import TestClient
import app.main as main
from app.merchant import identity, merchant, put

TEST_CATEGORY='desk'
PRODUCT={'id':'channel3:desk-1','provider_id':'desk-1','name':'Studio desk','retrieved_at':time.time(),
         'offers':[{'retailer':'sandbox.example','price_cents':15000,'currency':'USD','availability':'InStock','url':'https://sandbox.example/desk'}]}

def setup(monkeypatch):
    global TEST_CATEGORY
    TEST_CATEGORY='desk-'+uuid.uuid4().hex[:8]
    for row in main.db.execute('SELECT state FROM merchant_jobs').fetchall():
        job=json.loads(row[0]);job['status']='done';put(main.db,'merchant_jobs',job['id'],job)
    monkeypatch.setattr(main,'product_details',lambda _id:PRODUCT)
    monkeypatch.setattr(main.merchant_service,'product_details',lambda _id:PRODUCT)
    ids=[]
    for index in (1,2,3,4):
        mid='test-tenant-'+uuid.uuid4().hex[:10]
        m={'id':mid,'name':'Sandbox '+str(index),'sandbox':True,'verified_domain':'sandbox.example','agent_name':'Seller '+str(index),
           'opt_in':True,'active':True,'mode':'manual','policy':{'max_discount_bps':1000,'minimum_price_cents':12000,'max_counteroffers':3,'offer_lifetime_seconds':600,'review_policy':'out_of_policy'},'activity':[]}
        put(main.db,'merchants',mid,m)
        token='test-'+uuid.uuid4().hex
        main.db.execute('INSERT INTO merchant_users VALUES(?,?,?)',(identity(token),mid,'Operator'))
        mapping={'merchant_id':mid,'product_id':'shopside:desk-1','source':'SHOPSIDE_SANDBOX','sku':'desk-1',
                 'title':'Studio desk','category':TEST_CATEGORY,'price_cents':15000+index*10,'currency':'USD',
                 'stock_quantity':8,'active':True,'status':'current',
                 'observed':{'name':'Studio desk','price_cents':15000+index*10,'currency':'USD','availability':'InStock','retrieved_at':int(time.time()),'url':None}}
        main.db.execute('INSERT INTO merchant_products VALUES(?,?,?)',(mid,'shopside:desk-1',json.dumps(mapping)))
        main.db.execute('INSERT INTO merchant_inventory VALUES(?,?,?,?)',(mid,'shopside:desk-1',8,0))
        main.db.commit();ids.append((mid,token))
    return ids

def room():
    buyer=TestClient(main.app);other=TestClient(main.app)
    response=buyer.post('/api/rooms',json={'name':'Owner','initial_request':'A desk under $200'}).json()
    rid=response['room']['id'];other.post('/api/join/'+response['invite'],json={'name':'Friend'})
    state=main.load(rid);state['shopping_intent']={'product_requirements':[TEST_CATEGORY],'constraints':[]};main.save(rid,state)
    return buyer,other,rid

def test_dual_opt_in_matching_bound_and_isolation(monkeypatch):
    ids=setup(monkeypatch);buyer,other,rid=room();base='/api/rooms/'+rid
    assert buyer.post(base+'/seller-offers/request').status_code==409
    merchant_client=TestClient(main.app)
    assert merchant_client.get('/api/merchant/me',headers={'X-ShopSide-Merchant-Token':ids[0][1]}).json()['metrics']['new_opportunities']==0
    assert other.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-0001'}).status_code==403
    assert buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-0001'}).status_code==200
    result=buyer.post(base+'/seller-offers/request').json();assert result['opportunity_count']==3
    assert buyer.post(base+'/seller-offers/request').json()['opportunity_count']==3
    first=merchant_client.get('/api/merchant/me',headers={'Authorization':'Bearer '+ids[0][1]}).json()['opportunities']
    assert len(first)==1
    other_tenant=TestClient(main.app)
    assert other_tenant.post('/api/merchant/opportunities/'+first[0]['id']+'/action',json={'action':'decline','command_id':'different-tenant'},headers={'Authorization':'Bearer '+ids[1][1]}).status_code==404
    assert buyer.post(base+'/seller-offers/consent',json={'enabled':False,'command_id':'consent-0002'}).status_code==200
    assert buyer.post(base+'/seller-offers/request').status_code==409

def test_quote_review_accept_counter_dismiss_and_invitation(monkeypatch):
    ids=setup(monkeypatch);buyer,friend,rid=room();base='/api/rooms/'+rid
    client=TestClient(main.app);headers={'Authorization':'Bearer '+ids[0][1]}
    buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-0003'});buyer.post(base+'/seller-offers/request')
    op=client.get('/api/merchant/me',headers=headers).json()['opportunities'][0];endpoint='/api/merchant/opportunities/'+op['id']+'/action'
    review=client.post(endpoint,json={'action':'generate','price_cents':11000,'command_id':'generate-review'},headers=headers).json()
    assert review['review_required']
    approved=client.post(endpoint,json={'action':'approve','command_id':'approve-review'},headers=headers)
    assert approved.status_code==422 # below the merchant's absolute floor
    client.post(endpoint,json={'action':'reject','command_id':'reject-review'},headers=headers)
    published=client.post(endpoint,json={'action':'generate','price_cents':14000,'command_id':'generate-good'},headers=headers)
    assert published.status_code==200
    quote=published.json()['quote'];assert quote['price_cents']==14000
    assert friend.post(base+'/seller-offers/action',json={'action':'invite','offer_id':quote['id'],'command_id':'friend-invite'}).status_code==403
    assert buyer.post(base+'/seller-offers/action',json={'action':'invite','offer_id':quote['id'],'command_id':'owner-invite'}).status_code==200
    assert friend.get(base).json()['seller_agent']['merchant_id']==ids[0][0]
    assert buyer.post(base+'/seller-offers/action',json={'action':'remove','offer_id':quote['id'],'command_id':'owner-remove'}).status_code==200
    assert 'seller_agent' not in friend.get(base).json()
    over_budget=friend.post(base+'/seller-offers/action',json={'action':'counter','offer_id':quote['id'],'price_cents':20001,'command_id':'over-budget-counter'})
    assert over_budget.status_code==422
    assert friend.get(base).json()['flash_offers'][0]['status']=='OFFER_PUBLISHED'
    assert friend.post(base+'/seller-offers/action',json={'action':'counter','offer_id':quote['id'],'price_cents':13000,'command_id':'friend-counter'}).status_code==200
    assert buyer.post(base+'/seller-offers/action',json={'action':'accept','offer_id':quote['id'],'command_id':'owner-accept'}).status_code==200
    assert client.get('/api/merchant/me',headers=headers).json()['metrics']['accepted_deals']==1
    assert friend.get(base).json()['flash_offers'][0]['status']=='ACCEPTED'
    assert friend.get(base).json().get('checkout') is None

def test_seller_consent_policy_records_changes_without_payment_authority():
    buyer,_,rid=room();base='/api/rooms/'+rid
    enabled=buyer.post(base+'/seller-offers/consent',json={'enabled':True,'auto_accept_limit_cents':10000,'command_id':'policy-enable'}).json()
    assert enabled['seller_policy_history'][-1]['auto_accept_limit_cents']==10000
    assert enabled['seller_policy_history'][-1]['payment_authorized'] is False
    updated=buyer.post(base+'/seller-offers/consent',json={'enabled':True,'auto_accept_limit_cents':9000,'command_id':'policy-update'}).json()
    assert updated['seller_offers']['policy_version']==2
    assert updated['seller_policy_history'][0]['auto_accept_limit_cents']==10000
    revoked=buyer.post(base+'/seller-offers/consent',json={'enabled':False,'command_id':'policy-revoke'}).json()
    assert revoked['seller_policy_history'][-1]['enabled'] is False
    assert revoked['seller_offers']['enabled'] is False

def test_seller_negotiation_window_is_bounded_and_not_payment_approval():
    buyer,_,rid=room();base='/api/rooms/'+rid
    assert buyer.post(base+'/seller-offers/consent',json={'enabled':True,'duration_seconds':172801,'command_id':'window-invalid'}).status_code==422
    before=int(time.time())
    response=buyer.post(base+'/seller-offers/consent',json={'enabled':True,'duration_seconds':86400,'command_id':'window-valid'})
    assert response.status_code==200
    state=response.json()
    assert before+86400<=state['seller_offers']['expires_at']<=int(time.time())+86400
    assert state['seller_policy_history'][-1]['payment_authorized'] is False

def test_deal_rescue_does_not_treat_foreign_currency_budget_as_usd():
    from app.merchant import demand_from_room
    assert demand_from_room({'budget':10000,'shopping_intent':{'product_requirements':['desk'],'currency':'GBP'}}) is None
    assert demand_from_room({'budget':10000,'shopping_intent':{'product_requirements':['desk'],'currency':'USD'}})['currency']=='USD'

def test_buyer_can_scope_negotiation_to_one_participating_merchant(monkeypatch):
    ids=setup(monkeypatch);buyer,_,rid=room();base='/api/rooms/'+rid
    assert TestClient(main.app).get(base+'/deal-rescue/merchants').status_code==403
    choices=buyer.get(base+'/deal-rescue/merchants').json()['merchants']
    assert any(item['id']==ids[0][0] for item in choices)
    enabled=buyer.post(base+'/seller-offers/consent',json={'enabled':True,'merchant_id':ids[0][0],'command_id':'scoped-consent'})
    assert enabled.status_code==200
    assert enabled.json()['seller_policy_history'][-1]['merchant_id']==ids[0][0]
    assert buyer.post(base+'/seller-offers/request').json()['opportunity_count']==1
    opportunities=buyer.get(base+'/deal-rescue').json()['opportunities']
    assert len(opportunities)==1 and opportunities[0]['merchant_name']=='Sandbox 1'
    changed=buyer.post(base+'/seller-offers/consent',json={'enabled':True,'merchant_id':ids[1][0],'command_id':'scope-change'})
    assert changed.status_code==409

def test_deal_rescue_progress_is_room_scoped_and_hides_merchant_policy(monkeypatch):
    setup(monkeypatch)
    buyer,friend,rid=room();base='/api/rooms/'+rid
    assert TestClient(main.app).get(base+'/deal-rescue').status_code==403
    assert buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'progress-consent'}).status_code==200
    assert buyer.post(base+'/seller-offers/request').status_code==200
    result=friend.get(base+'/deal-rescue').json()
    assert result['payment_mode']=='NEGOTIATE_FIRST'
    assert len(result['opportunities'])==3
    assert all(item['label']=='Awaiting merchant' for item in result['opportunities'])
    assert all(set(item)=={'id','merchant_name','status','label','created_at','expires_at'} for item in result['opportunities'])
    first=result['opportunities'][0]
    row=main.db.execute('SELECT state FROM merchant_opportunities WHERE id=?',(first['id'],)).fetchone()
    opportunity=json.loads(row[0]);opportunity['status']='ACCEPTED';opportunity['offer']={'expires_at':int(time.time())-1}
    main.merchant_service.save_op(main.db,opportunity)
    updated=friend.get(base+'/deal-rescue').json()
    assert next(item for item in updated['opportunities'] if item['id']==first['id'])['label']=='Expired'

def test_expired_quote_and_merchant_optout(monkeypatch):
    ids=setup(monkeypatch);buyer,_,rid=room();base='/api/rooms/'+rid
    m=merchant(main.db,ids[0][0]);m['opt_in']=False;put(main.db,'merchants',ids[0][0],m)
    buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-0004'})
    assert buyer.post(base+'/seller-offers/request').json()['opportunity_count']<=3
    assert TestClient(main.app).get('/api/merchant/me',headers={'Authorization':'Bearer '+ids[0][1]}).json()['opportunities']==[]
    quote={'id':'expired-'+uuid.uuid4().hex,'opportunity_id':'nope','merchant_id':ids[0][0],'expires_at':int(time.time())-1,'status':'OFFER_PUBLISHED'}
    state=main.load(rid);state['flash_offers']=[quote];main.save(rid,state)
    assert buyer.post(base+'/seller-offers/action',json={'action':'accept','offer_id':quote['id'],'command_id':'expired-offer'}).status_code in (404,409)

def test_durable_automatic_job_and_room_fanout(monkeypatch):
    from app.merchant_agent import OfferProposal
    ids=setup(monkeypatch);buyer,_,rid=room();base='/api/rooms/'+rid
    m=merchant(main.db,ids[0][0]);m['mode']='automatic';put(main.db,'merchants',ids[0][0],m)
    async def fake_agent(_merchant,_opportunity,_products,_market):
        return OfferProposal(product_id='shopside:desk-1',price_cents=14000,explanation='A desk within your budget.'),{'model_calls':1,'tools':['get_merchant_policy','get_eligible_products','get_market_price_context','get_buyer_opportunity'],'outcome':'proposed'}
    monkeypatch.setattr(main.merchant_service,'propose',fake_agent)
    monkeypatch.setenv('MERCHANT_JOB_TOKEN','scheduler-test-secret')
    with buyer.websocket_connect(base+'/live',headers={'origin':'http://localhost:3000'}) as ws:
        ws.receive_json()
        buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-job'});ws.receive_json()
        matched=buyer.post(base+'/seller-offers/request').json();assert matched['opportunity_count']==3,matched
        # Local task fallback runs immediately after the request and fans the offer out.
        message=ws.receive_json()
        if not message.get('flash_offers'):message=ws.receive_json()
        assert message['flash_offers'][0]['merchant_id']==ids[0][0]
    op=TestClient(main.app).get('/api/merchant/me',headers={'Authorization':'Bearer '+ids[0][1]}).json()['opportunities'][0]
    assert op['agent_trace']['tools'][0]=='get_merchant_policy'
    second=TestClient(main.app).post('/api/internal/merchant-jobs/process',headers={'x-merchant-job-token':'scheduler-test-secret'})
    assert not any(r['id']==op['id'] for r in second.json()['results'])
    first_quote=buyer.get(base).json()['flash_offers'][0]
    assert buyer.post(base+'/seller-offers/action',json={'action':'counter','offer_id':first_quote['id'],'price_cents':13000,'command_id':'counter-auto'}).status_code==200
    quotes=buyer.get(base).json()['flash_offers']
    assert len(quotes)==2 and quotes[0]['status']=='CANCELLED' and quotes[1]['status']=='OFFER_PUBLISHED'
    history=TestClient(main.app).get('/api/merchant/me',headers={'Authorization':'Bearer '+ids[0][1]}).json()['opportunities'][0]['agent_traces']
    assert len(history)==2 and all(entry['model_calls']==1 for entry in history)

def test_real_quote_expiry_and_product_ownership(monkeypatch):
    from app.merchant_agent import OfferProposal
    ids=setup(monkeypatch);buyer,_,rid=room();base='/api/rooms/'+rid
    buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-expiry'})
    buyer.post(base+'/seller-offers/request')
    merchant_id,token=ids[0]
    client=TestClient(main.app);headers={'Authorization':'Bearer '+token}
    op=client.get('/api/merchant/me',headers=headers).json()['opportunities'][0]
    state=main.load(rid)
    bad=OfferProposal(product_id='channel3:other',price_cents=14000,explanation='Other item')
    from fastapi import HTTPException
    import pytest
    with pytest.raises(HTTPException):
        main.merchant_service.publish(main.db,state,main.merchant_service.scoped_opportunity(main.db,merchant_id,op['id']),merchant(main.db,merchant_id),bad,'operator',main.notify)
    endpoint='/api/merchant/opportunities/'+op['id']+'/action'
    good=client.post(endpoint,json={'action':'generate','price_cents':14000,'command_id':'generate-expiring'},headers=headers).json()['quote']
    state=main.load(rid);state['flash_offers'][0]['expires_at']=int(time.time())-1;main.save(rid,state)
    response=buyer.post(base+'/seller-offers/action',json={'action':'accept','offer_id':good['id'],'command_id':'accept-expired'})
    assert response.status_code==409
    assert buyer.get(base).json()['flash_offers'][0]['status']=='EXPIRED'

def test_budget_edit_revokes_old_seller_demand(monkeypatch):
    ids=setup(monkeypatch);buyer,friend,rid=room();base='/api/rooms/'+rid
    buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-budget-change'})
    assert buyer.post(base+'/seller-offers/request').json()['opportunity_count']==3
    before=buyer.get(base).json();old_key=before['seller_offers']['demand_key']
    result=buyer.post(base+'/plan/budget',json={'amount_cents':25000,'currency':'USD','revision':before['revision'],'command_id':'budget-change'})
    assert result.status_code==200
    after=friend.get(base).json()
    assert after['seller_offers']['demand_key']!=old_key and after['seller_offers']['match_count']==0
    assert after['budget']==25000
    first=TestClient(main.app).get('/api/merchant/me',headers={'Authorization':'Bearer '+ids[0][1]}).json()['opportunities'][0]
    assert first['status']=='CANCELLED'
    assert buyer.post(base+'/seller-offers/request').json()['opportunity_count']==3


def test_failed_merchant_ai_job_is_durable_and_bounded(monkeypatch):
    ids=setup(monkeypatch);buyer,_,rid=room();base='/api/rooms/'+rid
    m=merchant(main.db,ids[0][0]);m['mode']='automatic';put(main.db,'merchants',ids[0][0],m)
    async def unavailable(*_args):raise RuntimeError('model unavailable')
    monkeypatch.setattr(main.merchant_service,'propose',unavailable)
    monkeypatch.setenv('MERCHANT_JOB_TOKEN','job-retry-test')
    buyer.post(base+'/seller-offers/consent',json={'enabled':True,'command_id':'consent-retry-test'})
    assert buyer.post(base+'/seller-offers/request').json()['opportunity_count']==3
    op=TestClient(main.app).get('/api/merchant/me',headers={'Authorization':'Bearer '+ids[0][1]}).json()['opportunities'][0]
    for attempt in (2,3):
        job=main.merchant_service.read(main.db.execute('SELECT state FROM merchant_jobs WHERE id=?',(op['id'],)).fetchone())
        assert job['status']=='pending' and job['attempts']==attempt-1
        job['next_at']=main.merchant_service.now()-1
        main.merchant_service.put(main.db,'merchant_jobs',job['id'],job)
        response=TestClient(main.app).post('/api/internal/merchant-jobs/process',headers={'x-merchant-job-token':'job-retry-test'})
        assert response.status_code==200
    final=main.merchant_service.read(main.db.execute('SELECT state FROM merchant_jobs WHERE id=?',(op['id'],)).fetchone())
    assert final['status']=='failed' and final['attempts']==3
