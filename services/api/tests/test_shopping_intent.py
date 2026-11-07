import json
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app


def test_apparel_sizes_are_constraints_not_bundle_categories():
    from app.shopping_intent import ShoppingIntent
    intent=ShoppingIntent.model_validate({'product_requirements':['shirt','chinos','size M','size 32'],
        'bundle_requested':True,'constraints':[]})
    assert intent.product_requirements==['shirt','chinos']
    assert intent.constraints==['size M','size 32']
    assert intent.bundle_requested is True


def test_size_words_inside_product_names_are_preserved():
    from app.shopping_intent import ShoppingIntent
    intent=ShoppingIntent.model_validate({'product_requirements':['shirt size M','chinos size 32','size 9'],
        'constraints':['black color']})
    assert intent.product_requirements==['shirt size M','chinos size 32']
    assert intent.constraints==['black color','size 9']


def test_outfit_follow_up_creates_real_bundle_without_guessing_before_answer():
    from app.shopping_intent import ShoppingIntent, complete_outfit_intent
    goal='Plan a super stylish outfit for my sister wedding under $300'
    vague=ShoppingIntent(shopping_goal='Wedding outfit',product_requirements=['outfit'],budget_cents=30000,currency='USD',follow_up='Dress or suit?')
    assert complete_outfit_intent(vague,goal).product_requirements==['outfit']
    clarified=complete_outfit_intent(vague,goal,'A tailored suit')
    assert clarified.product_requirements==['suit','dress shoes']
    assert clarified.bundle_requested is True
    assert clarified.follow_up==''
    assert clarified.budget_cents==30000


def test_outfit_answer_updates_shared_room_and_preserves_budget(monkeypatch):
    import app.main as main
    from app.shopping_intent import ShoppingIntent
    async def interpret(text,schema):
        if 'Shopper answered:' in text:
            return ShoppingIntent(shopping_goal='Wedding outfit',product_requirements=['outfit'],budget_cents=None,follow_up='')
        return ShoppingIntent(shopping_goal='Wedding outfit',product_requirements=['outfit'],follow_up='Dress or suit?')
    monkeypatch.setattr(main,'interpret_with_adk',interpret)
    a,b=TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'Alex','initial_request':'Plan a super stylish outfit for my sister wedding under $300'}).json()
    base='/api/rooms/'+created['room']['id']
    assert b.post('/api/join/'+created['invite'],json={'name':'Sam'}).status_code==200
    assert a.post(base+'/intent').status_code==200
    before=a.get(base).json()
    payload={'text':'A tailored suit','revision':before['revision'],'command_id':'outfit-answer-1'}
    assert b.post(base+'/intent/answer',json=payload).status_code==200
    after=a.get(base).json()
    assert after['shopping_intent']['product_requirements']==['suit','dress shoes']
    assert after['shopping_intent']['bundle_requested'] is True
    assert after['shopping_intent']['studio_requested'] is False
    assert after['shopping_intent']['budget_cents']==30000
    assert after['budget']==30000
    assert a.post(base+'/intent/answer',json=payload).status_code==200
    assert a.post(base+'/intent/answer',json={**payload,'command_id':'different'}).status_code==409


def test_ai_interpretation_is_shared_without_automatic_studio(monkeypatch):
    import app.main as main
    output={'shopping_goal':'Furnish bedroom','product_requirements':['bed','lamp'],'budget_cents':100000,'currency':'USD','style':'minimalist','constraints':['small room'],'shopping_context':'move_in','participant_count':2,'bundle_requested':True,'follow_up':'What bed size?'}
    from app.shopping_intent import ShoppingIntent
    async def interpret(_text,schema):return ShoppingIntent.model_validate(output)
    monkeypatch.setattr(main,'interpret_with_adk',interpret)
    a,b=TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'Alex','initial_request':'We are moving and need a bed and lamp under $1000'}).json()
    base='/api/rooms/'+created['room']['id']
    assert b.post('/api/join/'+created['invite'],json={'name':'Sam'}).status_code==200
    assert b.post(base+'/intent').status_code==403
    assert a.post(base+'/intent').status_code==200
    shared=b.get(base).json()
    assert shared['mode']=='general' and shared['shopping_intent']['bundle_requested'] is True
    assert shared['shopping_intent']['shopping_mode']=='SPATIAL_ELIGIBLE'
    assert shared['shopping_intent']['studio_requested'] is False
    assert shared['shopping_intent']['budget_cents']==100000


def test_bundle_uses_real_observed_prices_and_total_budget(monkeypatch,mock_bundle_runner):
    import app.main as main
    import time
    client=TestClient(app)
    created=client.post('/api/rooms',json={'name':'Alex'}).json();r=created['room']['id'];base='/api/rooms/'+r
    with main.lock:
        room=main.load(r);room['shopping_intent']={'product_requirements':['desk','chair'],'budget_cents':30000,'currency':'USD'};main.save(r,room)
    def search(term, _max=None):
        return [{'id':'channel3:'+term,'name':term,'provenance':'channel3','retrieved_at':time.time(),'offers':[{'url':'https://retailer.example/p','retailer':'retailer.example','price_cents':10000 if term=='desk' else 12000,'currency':'USD','availability':'InStock'}]}]
    monkeypatch.setattr(main,'search_products',search)
    assert client.post(base+'/bundle/search').json()=={'count':1}
    room=client.get(base).json()
    assert room['bundle_options'][0]['total_cents']==22000
    assert len(room['discovery'])==2
    assert client.post(base+'/commands',json={'kind':'budget','value':'20000','revision':room['revision'],'command_id':'new-budget'}).status_code==200
    assert 'bundle_options' not in client.get(base).json()
    assert client.post(base+'/bundle/search').json()=={'count':0}

def test_home_planning_can_be_enabled_without_ai():
    client=TestClient(app)
    room=client.post('/api/rooms',json={'name':'Alex','initial_request':'A room under $700'}).json()['room']
    base='/api/rooms/'+room['id']
    assert client.post(base+'/home-plan').status_code==200
    updated=client.get(base).json()
    assert updated['mode']=='move_in'
    assert updated['move_in']['mission']['budget_cents']==70000
