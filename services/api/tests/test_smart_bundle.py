from fastapi.testclient import TestClient
import pytest
import app.main as main
from app.smart_bundle import normalized_candidates, build_bundles


def product(name, price, retailer='store.example', **changes):
    value={'id':'channel3:'+name.replace(' ','-'),'name':name,'retrieved_at':123,'offers':[{'url':'https://'+retailer+'/item','retailer':retailer,'price_cents':price,'currency':'USD','availability':'InStock'}]}
    value.update(changes);return value


def test_budget_saver_and_best_match_are_distinct_and_single_seller_uses_other_offers():
    desk=product('plain desk',8000,'cheap.example');desk['offers'].append({'url':'https://same.example/desk','retailer':'same.example','price_cents':9000,'currency':'USD'})
    ergonomic=product('ergonomic chair',11000,'same.example')
    cheap=product('basic chair',7000,'other.example')
    slots=normalized_candidates(['desk','ergonomic chair'],[[desk],[ergonomic,cheap]],'USD')
    bundles,has_one=build_bundles(slots,30000,'USD','workspace')
    assert has_one
    kinds={b['kind']:b for b in bundles}
    assert kinds['budget_saver']['subtotal_cents']==15000
    assert kinds['best_match']['subtotal_cents']==19000
    assert kinds['one_seller']['subtotal_cents']==20000
    assert {i['offer']['retailer'] for i in kinds['one_seller']['items']}=={'same.example'}


def test_rejects_bad_offers_and_avoids_duplicate_products():
    wrong=product('desk',1000,offers=[{'url':'javascript:alert(1)','retailer':'bad','price_cents':1000,'currency':'USD'}])
    out=product('chair',1000,offers=[{'url':'https://shop.example/p','retailer':'shop.example','price_cents':1000,'currency':'USD','availability':'OutOfStock'}])
    slots=normalized_candidates(['desk','chair'],[[wrong],[out]],'USD')
    assert build_bundles(slots,30000,'USD','')[0]==[]
    combo=product('desk chair',1000)
    slots=normalized_candidates(['desk','chair'],[[combo],[combo]],'USD')
    assert build_bundles(slots,30000,'USD','')[0]==[]

@pytest.mark.parametrize('offer',[
    {'url':'https://shop.example/p','retailer':'shop.example','currency':'USD'},
    {'url':'https://shop.example/p','retailer':'shop.example','price_cents':1000,'currency':'EUR'},
    {'url':'http://shop.example/p','retailer':'shop.example','price_cents':1000,'currency':'USD'},
    {'url':'https://shop.example/p','retailer':'shop.example','price_cents':None,'currency':'USD'},
])
def test_missing_price_wrong_currency_and_unsafe_offers_are_excluded(offer):
    slots=normalized_candidates(['desk','chair'],[[product('desk',1000,offers=[offer])],[product('chair',1000)]],'USD')
    assert slots[0]['products']==[]

def test_no_single_retailer_is_not_invented():
    slots=normalized_candidates(['desk','chair'],[[product('desk',1000,'a.example')],[product('chair',1000,'b.example')]],'USD')
    bundles,one_seller=build_bundles(slots,3000,'USD','')
    assert not one_seller and all(b['kind']!='one_seller' for b in bundles)


def test_four_categories_and_missing_budget():
    terms=['desk','chair','lamp','table'];slots=normalized_candidates(terms,[[product(term,1000)] for term in terms],'USD')
    assert build_bundles(slots,3999,'USD','')[0]==[]
    assert build_bundles(slots,None,'USD','')[0]==[]
    assert build_bundles(slots,4000,'USD','')[0][0]['subtotal_cents']==4000


def test_shared_selection_swap_approvals_and_save(monkeypatch,mock_bundle_runner):
    a,b,outsider=TestClient(main.app),TestClient(main.app),TestClient(main.app)
    created=a.post('/api/rooms',json={'name':'Alex'}).json();r=created['room']['id'];base='/api/rooms/'+r
    b.post('/api/join/'+created['invite'],json={'name':'Sam'})
    with main.lock:
        state=main.load(r);state['shopping_intent']={'shopping_goal':'workspace','product_requirements':['desk','chair'],'budget_cents':30000,'currency':'USD','bundle_requested':True};main.save(r,state)
    monkeypatch.setattr(main,'search_products',lambda term,_max=None: [product('desk',10000)] if term=='desk' else [product('chair',10000),product('comfy chair',12000),product('expensive chair',25000)])
    assert outsider.post(base+'/bundle/search').status_code==403
    assert a.post(base+'/bundle/search').status_code==200
    initial=a.get(base).json()['smart_bundle'];option=initial['options'][0]
    def act(client,kind,version,id,**kw):return client.post(base+'/bundle/action',json={'action':kind,'expected_version':version,'command_id':id,**kw})
    assert act(a,'select',initial['version'],'select',bundle_id=option['id']).status_code==200
    selected=b.get(base).json()['smart_bundle'];version=selected['version']
    current=a.get(base).json()
    assert a.post(base+'/commands',json={'kind':'chat','value':'Looks good','revision':current['revision'],'command_id':'chat'}).status_code==200
    assert act(a,'approve',version,'a').status_code==200
    assert act(b,'approve',version,'b').status_code==200
    assert act(a,'save',version,'save').status_code==200
    async def alternative_search(requirement,intent,currency,search,max_model_calls,max_http_calls):
        raw=[product('new chair',11000)]
        slot=normalized_candidates([requirement],[raw],currency)[0]
        return {'raw':raw,'products':slot['products'],'scores':{raw[0]['id']:88},'activity':{'model_calls':2,'channel3_http_calls':1,'tools':[{'tool':'search_alternatives','outcome':'completed'}]}}
    monkeypatch.setattr(main,'run_alternative_agent',alternative_search)
    request={'expected_version':version,'command_id':'find-more'}
    assert b.post(base+'/bundle/alternatives/1/search',json=request).status_code==200
    assert b.post(base+'/bundle/alternatives/1/search',json=request).status_code==200
    assert a.get(base).json()['smart_bundle']['version']==version
    alternatives=b.get(base+'/bundle/alternatives/1').json()['alternatives']
    assert any(x['product']['name']=='new chair' and x['product']['alternative_fit_score']==88 for x in alternatives)
    chair=next(x for x in alternatives if x['product']['name']=='comfy chair')
    assert act(b,'swap',version,'swap',slot_id='1',product_id=chair['product']['id'],offer_id=chair['offer']['id']).status_code==200
    updated=a.get(base).json()['smart_bundle']
    assert updated['version']==version+1 and updated['approvals']=={}
    assert updated['selected']['subtotal_cents']==22000
    assert updated['selected']['items'][0]['product']['name']=='desk'
    assert updated['saved']['subtotal_cents']==20000
    assert act(b,'swap',version,'swap',slot_id='1',product_id=chair['product']['id'],offer_id=chair['offer']['id']).status_code==200
    assert act(a,'approve',version,'stale').status_code==409
    expensive=next(x for x in alternatives if x['product']['name']=='expensive chair')
    assert act(a,'swap',version+1,'expensive',slot_id='1',product_id=expensive['product']['id'],offer_id=expensive['offer']['id']).status_code==422
    assert outsider.post(base+'/bundle/action',json={'action':'approve','expected_version':version+1,'command_id':'bad'}).status_code==403
    assert act(a,'approve',version+1,'again').status_code==200
    c=TestClient(main.app);assert c.post('/api/join/'+created['invite'],json={'name':'Chris'}).status_code==200
    assert a.get(base).json()['smart_bundle']['approvals']=={}

def test_agent_cannot_return_a_bundle_without_tool_results(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    import app.smart_bundle_agent as module
    class Sessions:
        async def create_session(self,**kwargs):return SimpleNamespace(id='test')
    class Runner:
        def __init__(self,agent,app_name):self.session_service=Sessions()
        async def run_async(self,**kwargs):
            yield SimpleNamespace()
    class Client:
        def close(self):pass
    async def progress(*args):pass
    monkeypatch.setattr(module,'InMemoryRunner',Runner);monkeypatch.setattr(module,'Gemini',lambda **kwargs:'test')
    monkeypatch.setattr(module,'configured_client',lambda:Client());monkeypatch.setenv('GEMINI_MODEL','test')
    with pytest.raises(RuntimeError,match='required search'):
        asyncio.run(module.run_bundle_agent({'product_requirements':['desk','chair']},30000,'USD',lambda *_:[],progress))

def test_budget_is_required_and_budget_updates_are_idempotent():
    client=TestClient(main.app)
    room=client.post('/api/rooms',json={'name':'Alex'}).json()['room'];base='/api/rooms/'+room['id']
    with main.lock:
        state=main.load(room['id']);state['shopping_intent']={'product_requirements':['desk','chair'],'bundle_requested':True,'currency':None,'budget_cents':None};main.save(room['id'],state)
    assert client.post(base+'/bundle/search').status_code==422
    data={'amount_cents':30000,'currency':'USD','expected_version':0,'command_id':'budget'}
    assert client.post(base+'/bundle/budget',json=data).status_code==200
    version=client.get(base).json()['smart_bundle']['version']
    assert client.post(base+'/bundle/budget',json=data).status_code==200
    assert client.get(base).json()['smart_bundle']['version']==version


def test_provider_failure_does_not_invent_a_bundle(monkeypatch,mock_bundle_runner):
    monkeypatch.setenv('SHOPSIDE_BUNDLE_TRACE','true')
    client=TestClient(main.app)
    room=client.post('/api/rooms',json={'name':'Alex'}).json()['room'];base='/api/rooms/'+room['id']
    with main.lock:
        state=main.load(room['id']);state['shopping_intent']={'product_requirements':['desk','chair'],'bundle_requested':True,'currency':'USD','budget_cents':30000};main.save(room['id'],state)
    def fail(*args):raise RuntimeError('provider unavailable')
    monkeypatch.setattr(main,'search_products',fail)
    assert client.post(base+'/bundle/search').status_code==502
    bundle=client.get(base).json()['smart_bundle']
    assert bundle.get('options') is None and bundle['agent_activity']['status']=='error'

def test_single_product_request_does_not_create_a_bundle(monkeypatch):
    client=TestClient(main.app);room=client.post('/api/rooms',json={'name':'Alex'}).json()['room'];base='/api/rooms/'+room['id']
    with main.lock:
        state=main.load(room['id']);state['shopping_intent']={'product_requirements':['chair'],'bundle_requested':False,'currency':'USD','budget_cents':10000};main.save(room['id'],state)
    assert client.post(base+'/bundle/search').status_code==422
    assert 'smart_bundle' not in client.get(base).json()

def test_same_best_and_cheapest_adds_distinct_product_option():
    desks=[product('desk basic',8000),product('desk studio',11000)]
    chairs=[product('chair basic',7000),product('chair studio',10000)]
    slots=normalized_candidates(['desk','chair'],[desks,chairs],'USD')
    bundles,_=build_bundles(slots,30000,'USD','workspace')
    primary=bundles[0]
    assert primary['kind']=='best_match' and 'budget_saver' in primary['also_qualifies']
    alternative=next(b for b in bundles if b['kind']=='alternative')
    assert alternative['id']!=primary['id']
    assert any(a['product']['id']!=b['product']['id'] for a,b in zip(primary['items'],alternative['items']))
    assert alternative['subtotal_cents']<=30000
