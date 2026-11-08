import os
from fastapi.testclient import TestClient
from app.main import app

def test_shared_room():
    a,b,c=TestClient(app),TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'Krishna'}).json(); r=result['room']['id']
    assert b.get('/api/rooms/'+r).status_code==403
    assert b.post('/api/join/'+result['invite'],json={'name':'Priya'}).status_code==200
    cmd={'command_id':'one','revision':1,'kind':'focus','value':'2'}
    assert a.post('/api/rooms/'+r+'/commands',json=cmd).status_code==200
    assert b.get('/api/rooms/'+r).json()['focus']=='2'
    assert a.post('/api/rooms/'+r+'/commands',json=cmd).status_code==200
    assert b.post('/api/rooms/'+r+'/commands',json={**cmd,'command_id':'two'}).status_code==409
    assert b.post('/api/rooms/'+r+'/commands',json={'command_id':'three','revision':2,'kind':'reaction','value':'2'}).status_code==200
    assert a.get('/api/rooms/'+r).json()['reactions']['2']==['Priya']

def test_cart_quote_authority_and_freeze():
    a,b=TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'Payer'}).json(); r=result['room']['id']; base='/api/rooms/'+r
    b.post('/api/join/'+result['invite'],json={'name':'Friend'})
    assert a.post(base+'/commands',json={'command_id':'cart','revision':1,'kind':'cart','value':'0'}).status_code==200
    assert b.post(base+'/quote').status_code==403
    q=a.post(base+'/quote').json()
    assert q['total']==8900 and q['items'][0]['quantity']==1
    assert a.post(base+'/quote').status_code==409
    assert a.post(base+'/commands',json={'command_id':'edit','revision':3,'kind':'cart','value':'1'}).status_code==409
    assert b.post(base+'/payments/'+q['id']+'/cancel').status_code==403
    assert a.post(base+'/payments/'+q['id']+'/cancel').status_code==200
    assert a.get(base).json()['checkout'] is None

def test_websocket_membership_and_origin():
    with TestClient(app) as a:
        result=a.post('/api/rooms',json={'name':'A'}).json(); r=result['room']['id']
        with a.websocket_connect('/api/rooms/'+r+'/live',headers={'origin':'http://localhost:3000'}) as ws:
            assert ws.receive_json()['people']==['A']
            assert a.post('/api/rooms/'+r+'/commands',json={'command_id':'ws','revision':0,'kind':'focus','value':'3'}).status_code==200
            assert ws.receive_json()['focus']=='3'

def test_verified_capture_and_pending_recovery(monkeypatch):
    import app.main as main
    monkeypatch.setenv('PAYPAL_MERCHANT_ID','merchant')
    a=TestClient(app); result=a.post('/api/rooms',json={'name':'Payer'}).json(); base='/api/rooms/'+result['room']['id']
    a.post(base+'/commands',json={'command_id':'cart','revision':0,'kind':'cart','value':'0'})
    quote=a.post(base+'/quote').json(); url=base+'/payments/'+quote['id']
    calls=[]
    async def fake(method,path,payload=None,operation=None):
        calls.append((method,path,operation))
        if path=='/v2/checkout/orders': return {'id':'provider-order'}
        if path.endswith('/capture'): return {'status':'COMPLETED'}
        return {'status':'COMPLETED','purchase_units':[{'payee':{'merchant_id':'merchant'},'payments':{'captures':[{'id':'verified-capture','status':'COMPLETED','amount':{'currency_code':'USD','value':'89.00'}}]}}]}
    monkeypatch.setattr(main,'paypal',fake)
    assert a.post(url+'/create').json()['order_id']=='provider-order'
    assert a.post(url+'/capture').json()['status']=='paid'
    assert a.post(url+'/capture').json()['status']=='paid'
    assert len([c for c in calls if c[1].endswith('/capture')])==1
    assert a.get(base).json()['checkout']['status']=='paid'

def test_direct_sandbox_order_receipt_uses_verified_capture_and_variant(monkeypatch):
    import app.main as main
    import pytest
    from starlette.requests import Request
    payment={'id':'local-order','room':'room','payer':'A','status':'paid','capture':'capture-1','provider_id':'paypal-order',
             'verified_at':'2026-11-08T12:00:00+00:00','total':7800,'currency':'USD',
             'items':[{'product':'11','name':'Lamp','variant':'midnight','quantity':2,'price':3900}]}
    monkeypatch.setattr(main,'auth',lambda *_:'A')
    monkeypatch.setattr(main,'load',lambda _:{'people':['A','B']})
    monkeypatch.setattr(main,'payment_load',lambda *_:payment)
    monkeypatch.setattr(main.db,'execute',lambda *_:type('Rows',(),{'fetchall':lambda self:[]})())
    request=Request({'type':'http','method':'GET','path':'/','headers':[], 'query_string':b'', 'server':('test',80), 'client':('test',1), 'scheme':'http'})
    receipt=main.merchant_order_receipt('room','local-order',request)
    assert receipt['merchant_name']=='ShopSide sandbox catalog'
    assert receipt['total_cents']==receipt['reference_total_cents']==7800 and receipt['savings_cents']==0
    assert receipt['items'][0]['variant']=='midnight' and receipt['paypal_sandbox_capture_id']=='capture-1'
    assert receipt['paid_at']==payment['verified_at']
    payment['status']='approval'
    with pytest.raises(main.HTTPException):main.merchant_order_receipt('room','local-order',request)

def test_discovery_shared_and_external_offer_cannot_charge(monkeypatch):
    import app.main as main
    from app.discovery import normalize
    item=normalize({'id':'real-product','title':'Provider headphones','offers':[{'url':'https://retailer.example/item','domain':'retailer.example','price':{'price':99.99,'currency':'USD'}}]})
    assert item['offers'][0]['price_cents']==9999
    assert item['merchant_offer'] is None
    monkeypatch.setattr(main,'search_products',lambda q,max_price=None:[item])
    a,b=TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'A'}).json(); base='/api/rooms/'+result['room']['id']
    b.post('/api/join/'+result['invite'],json={'name':'B'})
    assert a.post(base+'/discovery',json={'query':'headphones'}).status_code==200
    assert b.get(base).json()['discovery'][0]['provenance']=='channel3'
    rev=b.get(base).json()['revision']
    assert a.post(base+'/commands',json={'command_id':'external','revision':rev,'kind':'cart','value':item['id']}).status_code==422
    assert a.post(base+'/commands',json={'command_id':'spotlight','revision':rev,'kind':'focus','value':item['id']}).status_code==200
    assert b.get(base).json()['focus']==item['id']

def test_saved_channel3_products_survive_a_new_market_discovery(monkeypatch):
    import app.main as main
    saved=[
        {'id':'channel3:chair-one','provider_id':'chair-one','name':'Chair One','provenance':'channel3','offers':[]},
        {'id':'channel3:chair-two','provider_id':'chair-two','name':'Chair Two','provenance':'channel3','offers':[]},
    ]
    newer={'id':'channel3:uk-chair','provider_id':'uk-chair','name':'UK Chair','provenance':'channel3','offers':[]}
    monkeypatch.setattr(main,'search_products',lambda query,max_price=None: saved if query=='chairs' else [newer])
    client=TestClient(app)
    created=client.post('/api/rooms',json={'name':'A'}).json();base='/api/rooms/'+created['room']['id']
    assert client.post(base+'/discovery',json={'query':'chairs'}).status_code==200
    for product in saved:
        state=client.get(base).json()
        assert client.post(base+'/commands',json={'kind':'shortlist','value':product['id'],'revision':state['revision'],'command_id':'save-'+product['id']}).status_code==200
    # Emulate a room created before product snapshots were persisted.
    with main.lock:
        legacy=main.load(created['room']['id']);legacy.pop('shortlisted_products',None);main.save(created['room']['id'],legacy)
    assert client.post(base+'/discovery',json={'query':'UK chairs'}).status_code==200
    state=client.get(base).json()
    assert state['shortlist']==[product['id'] for product in saved]
    assert [state['shortlisted_products'][product['id']]['name'] for product in saved]==['Chair One','Chair Two']
    compare=','.join(state['shortlist'])
    assert client.post(base+'/commands',json={'kind':'compare','value':compare,'revision':state['revision'],'command_id':'compare-old-market'}).status_code==200
    state=client.get(base).json()
    assert state['comparison']==[product['id'] for product in saved]
    assert client.post(base+'/commands',json={'kind':'shortlist','value':saved[0]['id'],'revision':state['revision'],'command_id':'remove-old-market'}).status_code==200
    state=client.get(base).json()
    assert state['shortlist']==[saved[1]['id']]
    assert saved[0]['id'] not in state['shortlisted_products']

def test_legacy_shortlist_is_snapshotted_before_discovery_is_replaced():
    import app.main as main
    product={'id':'channel3:legacy-chair','name':'Saved chair'}
    state={'shortlist':[product['id']],'discovery':[product]}
    main.preserve_shortlisted_products(state)
    assert state['shortlisted_products']=={product['id']:product}

def test_legacy_shortlist_recovers_channel3_products_after_the_old_search_is_gone(monkeypatch):
    import app.main as main
    old={'id':'channel3:chair-one','provider_id':'chair-one','name':'Saved chair','provenance':'channel3','offers':[]}
    room={'id':'room','people':['A'],'payer':'A','revision':0,'shortlist':[old['id']],
          'discovery':[{'id':'channel3:uk-chair','name':'Current UK result'}],'commands':[]}
    monkeypatch.setattr(main,'auth',lambda *_:'A')
    monkeypatch.setattr(main,'load',lambda _r:room)
    monkeypatch.setattr(main,'product_details',lambda provider_id:old if provider_id=='chair-one' else None)
    monkeypatch.setattr(main,'save',lambda _r,state:room.update(state))
    from starlette.requests import Request
    request=Request({'type':'http','method':'POST','path':'/','headers':[], 'query_string':b'', 'server':('test',80), 'client':('test',1), 'scheme':'http'})
    result=main.restore_shortlist('room',request)
    assert result['shortlisted_products'][old['id']]['name']=='Saved chair'

def test_product_detail_enrichment_preserves_the_selected_listing_and_offer():
    import app.main as main
    import pytest
    selected={'id':'channel3:chair','provider_id':'chair','name':'Debenhams chair','provenance':'channel3',
        'offers':[{'retailer':'Debenhams','price_cents':8742,'currency':'GBP','url':'https://debenhams.example/chair'}],
        'attributes':{},'key_features':[]}
    fresh={'id':'channel3:chair','name':'Alternate title','offers':[{'retailer':'Best Buy','price_cents':13499,'currency':'USD'}],
        'attributes':{'material':'mesh'},'key_features':['Adjustable lumbar']}
    result=main.enrich_selected_listing(selected,fresh)
    assert result['name']=='Debenhams chair'
    assert result['offers']==selected['offers']
    assert result['attributes']=={'material':'mesh'}
    assert main.offers_in_selected_market(selected,[{'currency':'USD','price_cents':100},{'currency':'GBP','price_cents':8742}])==[{'currency':'GBP','price_cents':8742}]
    with pytest.raises(main.HTTPException):main.enrich_selected_listing(selected,{**fresh,'id':'channel3:other-chair'})

def test_missing_discovery_key_is_explicit(monkeypatch):
    monkeypatch.delenv('CHANNEL3_API_KEY',raising=False)
    a=TestClient(app); result=a.post('/api/rooms',json={'name':'A'}).json()
    assert a.post('/api/rooms/'+result['room']['id']+'/discovery',json={'query':'headphones'}).status_code==503

def test_variant_quantity_reservation_cancel_and_replay():
    import app.main as main
    a=TestClient(app); r=a.post('/api/rooms',json={'name':'Payer'}).json()['room']['id']; base='/api/rooms/'+r
    import json
    before=main.stock('7','midnight')
    line={'product':'7','variant':'midnight','quantity':2}
    assert a.post(base+'/commands',json={'command_id':'variant','revision':0,'kind':'cart_line','value':json.dumps(line)}).status_code==200
    q=a.post(base+'/quote').json()
    assert q['total']==17000 and q['items'][0]['variant']=='midnight'
    assert main.stock('7','midnight')==before-2
    assert a.post(base+'/payments/'+q['id']+'/cancel').status_code==200
    assert main.stock('7','midnight')==before
    assert a.post(base+'/payments/'+q['id']+'/create').status_code==409
    assert a.post(base+'/payments/'+q['id']+'/cancel').status_code==409

def test_lost_capture_response_reconciles_without_second_charge(monkeypatch):
    import app.main as main
    import httpx
    monkeypatch.setenv('PAYPAL_MERCHANT_ID','merchant')
    a=TestClient(app); r=a.post('/api/rooms',json={'name':'Payer'}).json()['room']['id']; base='/api/rooms/'+r
    a.post(base+'/commands',json={'command_id':'cart','revision':0,'kind':'cart','value':'6'})
    q=a.post(base+'/quote').json(); url=base+'/payments/'+q['id']; captures=[]
    async def fake(method,path,payload=None,operation=None):
        if path=='/v2/checkout/orders': return {'id':'lost-response-order'}
        if path.endswith('/capture'):
            captures.append(operation); raise httpx.ReadTimeout('lost response')
        return {'status':'COMPLETED','purchase_units':[{'payee':{'merchant_id':'merchant'},'payments':{'captures':[{'id':'reconciled','status':'COMPLETED','amount':{'currency_code':'USD','value':'49.00'}}]}}]}
    monkeypatch.setattr(main,'paypal',fake)
    assert a.post(url+'/create').status_code==200
    assert a.post(url+'/capture').status_code==502
    assert a.post(url+'/capture').json()['status']=='paid'
    assert len(captures)==1
    assert a.get(base+'/checkout').json()['capture']=='reconciled'

def test_foreign_origin_and_friend_receipt_access():
    a,b=TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'Payer'}).json(); base='/api/rooms/'+result['room']['id']
    b.post('/api/join/'+result['invite'],json={'name':'Friend'})
    assert b.get(base+'/checkout').status_code==403
    assert b.get(base+'/me').json()['is_payer'] is False
    assert a.post(base+'/commands',headers={'origin':'https://foreign.example'},json={'command_id':'csrf','revision':1,'kind':'chat','value':'bad'}).status_code==403

def test_adk_coordinates_real_room_tool_with_test_runner(monkeypatch):
    """Explicitly fake model runner; validates ADK wiring and persisted tool outcomes."""
    import google.adk.runners
    from types import SimpleNamespace
    import app.main as main
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    monkeypatch.setattr(main,'configured_client',lambda:object())
    import google.adk.models.google_llm
    monkeypatch.setattr(google.adk.models.google_llm,'Gemini',lambda **kwargs:'mock-gemini')
    seen={}
    class Sessions:
        async def create_session(self,**kwargs): return SimpleNamespace(id='test-session')
    class Runner:
        def __init__(self,agent,**kwargs): self.agent=agent; self.session_service=Sessions(); seen['agent']=agent
        async def run_async(self,**kwargs):
            tool=next(t for t in self.agent.tools if getattr(t,'__name__','')=='search_catalog')
            assert tool(query='Quiet')[0]['name']=='Quiet Hours'
            yield SimpleNamespace(is_final_response=lambda:True,content=SimpleNamespace(parts=[SimpleNamespace(text='Test runner response',thought=False)]))
    monkeypatch.setattr(google.adk.runners,'InMemoryRunner',Runner)
    a=TestClient(app);r=a.post('/api/rooms',json={'name':'A'}).json()['room']['id'];base='/api/rooms/'+r
    assert a.post(base+'/agent',json={'text':'Find Quiet Hours','revision':0}).status_code==200
    s=a.get(base).json()
    assert s['activity'][-1]['tool']=='search_catalog'
    assert s['messages'][-1]['actor']=='ShopSide'
    names=[getattr(t,'__name__','') for t in seen['agent'].tools]
    assert 'paypal_order_status' in names
    assert not any(name in names for name in ['create_order','pay_order','capture_order'])

def test_vertex_auth_modes_do_not_mix_api_key_and_adc(monkeypatch):
    import app.ai_config as config
    monkeypatch.setenv('AI_PROVIDER','vertex')
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT','test-project')
    monkeypatch.setenv('GOOGLE_CLOUD_LOCATION','global')
    monkeypatch.setenv('GEMINI_API_KEY','test-key')
    monkeypatch.setattr(config.genai,'Client',lambda **kwargs:kwargs)
    assert config.configured_client()=={'vertexai':True,'project':'test-project','location':'global'}
    monkeypatch.delenv('GOOGLE_CLOUD_PROJECT')
    monkeypatch.delenv('VERTEX_API_KEY',raising=False)
    assert config.configured_client()=={'vertexai':True,'api_key':'test-key'}


def test_express_mode_ignores_ambient_project(monkeypatch):
    import app.ai_config as config
    monkeypatch.setenv('AI_PROVIDER','vertex-express')
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT','ambient-project')
    monkeypatch.setenv('GEMINI_API_KEY','test-express-key')
    monkeypatch.delenv('VERTEX_API_KEY',raising=False)
    monkeypatch.setattr(config.genai,'Client',lambda **kwargs:kwargs)
    assert config.configured_client()=={'vertexai':True,'api_key':'test-express-key'}

def test_quote_rolls_back_stock_and_payment_when_save_fails(monkeypatch):
    import app.main as main
    a=TestClient(app,raise_server_exceptions=False)
    r=a.post('/api/rooms',json={'name':'Payer'}).json()['room']['id'];base='/api/rooms/'+r
    assert a.post(base+'/commands',json={'command_id':'cart','revision':0,'kind':'cart','value':'4'}).status_code==200
    before=main.stock('4','standard')
    def fail(*args,**kwargs): raise RuntimeError('simulated storage failure')
    monkeypatch.setattr(main,'payment_save',fail)
    assert a.post(base+'/quote').status_code==500
    assert main.stock('4','standard')==before
    assert a.get(base).json()['checkout'] is None

def test_postgres_connection_recovers_after_server_disconnect():
    import pytest
    import psycopg
    import app.main as main
    if not main.db.postgres:
        pytest.skip('PostgreSQL-only disconnect recovery')
    pid=main.db.execute('SELECT pg_backend_pid()').fetchone()[0]
    with psycopg.connect(os.environ['SHOPSIDE_TEST_DATABASE_URL'],autocommit=True) as connection:
        assert connection.execute('SELECT pg_terminate_backend(%s)',(pid,)).fetchone()[0]
    with pytest.raises(psycopg.Error): main.db.execute('SELECT 1')
    assert main.db.execute('SELECT 1').fetchone()[0]==1


def test_external_cart_is_shared_persisted_and_never_charged(monkeypatch):
    import app.main as main
    from app.discovery import normalize
    item=normalize({'id':'external-1','title':'Retail headphones','offers':[{'url':'https://retailer.example/p','domain':'retailer.example','price':{'price':75,'currency':'USD'}}]})
    monkeypatch.setattr(main,'search_products',lambda q,max_price=None:[item])
    a,b=TestClient(app),TestClient(app)
    result=a.post('/api/rooms',json={'name':'Payer'}).json();base='/api/rooms/'+result['room']['id']
    b.post('/api/join/'+result['invite'],json={'name':'Friend'})
    a.post(base+'/discovery',json={'query':'headphones'})
    rev=a.get(base).json()['revision']
    assert a.post(base+'/commands',json={'command_id':'add-retailer','revision':rev,'kind':'external_cart_add','value':item['id']}).status_code==200
    state=b.get(base).json()
    assert state['external_cart'][0]['id']==item['id']
    assert state['cart']==[]
    assert a.post(base+'/quote').status_code==422
    assert b.post(base+'/commands',json={'command_id':'remove-retailer','revision':state['revision'],'kind':'external_cart_remove','value':item['id']}).status_code==200
    assert a.get(base).json()['external_cart']==[]


def test_retailer_cart_survives_new_search_and_sample_quote_excludes_it(monkeypatch):
    import app.main as main
    from app.discovery import normalize
    item=normalize({'id':'retailer-1','title':'Retail item','offers':[{'url':'https://retailer.example/p','domain':'retailer.example','price':{'price':250,'currency':'USD'}}]})
    monkeypatch.setattr(main,'search_products',lambda q,max_price=None:[item] if q=='first' else [])
    a=TestClient(app);r=a.post('/api/rooms',json={'name':'Payer'}).json()['room']['id'];base='/api/rooms/'+r
    a.post(base+'/discovery',json={'query':'first'})
    assert a.post(base+'/commands',json={'command_id':'retailer','revision':1,'kind':'external_cart_add','value':item['id']}).status_code==200
    assert a.post(base+'/discovery',json={'query':'second'}).status_code==200
    state=a.get(base).json()
    assert state['external_cart'][0]['id']==item['id']
    assert a.post(base+'/commands',json={'command_id':'sample','revision':state['revision'],'kind':'cart','value':'0'}).status_code==200
    quote=a.post(base+'/quote').json()
    assert quote['total']==8900
    assert len(quote['items'])==1 and quote['items'][0]['product']=='0'

def test_tab_scoped_memberships_survive_shared_browser_cookies():
    client=TestClient(app)
    first='a'*32;second='b'*32
    one={'X-ShopSide-Session':first};two={'X-ShopSide-Session':second}
    created=client.post('/api/rooms',json={'name':'A'},headers=one).json();base='/api/rooms/'+created['room']['id']
    assert client.post('/api/join/'+created['invite'],json={'name':'B'},headers=two).status_code==200
    assert client.get(base+'/me',headers=one).json()=={'name':'A','is_payer':True}
    assert client.get(base+'/me',headers=two).json()=={'name':'B','is_payer':False}
    assert client.get(base+'/me').json()['name']=='B'  # Existing legacy client.
    state=client.get(base,headers=one).json()
    assert client.post(base+'/commands',headers=one,json={'kind':'chat','value':'Hello from A','revision':state['revision'],'command_id':'chat-a'}).status_code==200
    state=client.get(base,headers=two).json()
    assert client.post(base+'/commands',headers=two,json={'kind':'chat','value':'Hello from B','revision':state['revision'],'command_id':'chat-b'}).status_code==200
    assert client.get(base,headers=one).json()['messages']==[{'actor':'A','text':'Hello from A'},{'actor':'B','text':'Hello from B'}]
    assert client.get(base+'/me',headers={'X-ShopSide-Session':'c'*32}).status_code==403
    assert client.get(base+'/me',headers={'X-ShopSide-Session':'invalid'}).status_code==400
    assert client.post(base+'/session',headers=one).status_code==200
    assert client.get(base+'/me',headers=one).json()['name']=='A'

def test_legacy_membership_can_upgrade_to_a_tab_session():
    client=TestClient(app)
    created=client.post('/api/rooms',json={'name':'Legacy'}).json();base='/api/rooms/'+created['room']['id']
    headers={'X-ShopSide-Session':'d'*32}
    assert client.get(base+'/me',headers=headers).status_code==403
    assert client.post(base+'/session',headers=headers).status_code==200
    assert client.get(base+'/me',headers=headers).json()['name']=='Legacy'

def test_duplicate_names_ignore_case_and_whitespace():
    a,b=TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'  Alice  '}).json()
    assert created['room']['people']==['Alice']
    assert b.post('/api/join/'+created['invite'],json={'name':' ALICE '}).status_code==409

def test_websocket_observes_commit_without_local_notification():
    """Simulate a second Cloud Run instance writing the same database."""
    import json
    import app.main as main
    with TestClient(main.app) as client:
        room=client.post('/api/rooms',json={'name':'Alex'}).json()['room'];rid=room['id']
        with client.websocket_connect('/api/rooms/'+rid+'/live',headers={'origin':'http://localhost:3000'}) as ws:
            assert ws.receive_json()['revision']==0
            state=main.load(rid)
            state['messages'].append({'actor':'Sam','text':'Cross-instance message'})
            state['revision']+=1
            main.db.execute('UPDATE rooms SET state=? WHERE id=?',(json.dumps(state),rid))
            main.db.commit()  # No notify(rid): the other instance has no subscriber handle.
            incoming=ws.receive_json()
            assert incoming['messages'][-1]['text']=='Cross-instance message'
