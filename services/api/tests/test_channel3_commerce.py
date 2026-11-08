import pytest
from fastapi import HTTPException

from app import discovery


def test_provider_fields_are_mapped_without_invented_ratings():
    product=discovery.normalize({'id':'x','title':'Compact Desk','category':{'title':'Office Furniture'},
        'brands':[{'id':'b','name':'Studio'}],
        'offers':[{'url':'https://store.example/item','domain':'store.example',
                   'price':{'price':180,'currency':'USD'},'availability':'InStock'}]})
    assert product['source']=='CHANNEL3_LIVE' and product['brand']=='Studio'
    assert product['spatial_eligible'] is True
    assert product['ratings'] is None
    assert product['offers'][0]['price_cents']==18000


def test_variant_relaxation_is_rejected(monkeypatch):
    import channel3_sdk
    monkeypatch.setenv('CHANNEL3_API_KEY','test-key')
    raw={'id':'shoe','title':'Running Shoe','variants':{'options':[{'name':'Size','values':[
        {'label':'9','exists':True},{'label':'10','exists':True}]}],
        'selected':[{'name':'Size','label':'10'}]},'offers':[]}
    class Product:
        def model_dump(self,**_kwargs):return raw
    class Products:
        def retrieve(self,*_args,**_kwargs):return Product()
    class Client:
        def __init__(self,**_kwargs):self.products=Products()
    monkeypatch.setattr(channel3_sdk,'Channel3',Client)
    with pytest.raises(HTTPException) as exc:
        discovery.product_details('shoe',{'Size':'9'})
    assert exc.value.status_code==409
    assert 'unavailable' in exc.value.detail


def test_price_history_unavailable_is_honest(monkeypatch):
    import channel3_sdk
    monkeypatch.setenv('CHANNEL3_API_KEY','test-key')
    class PriceTracking:
        def retrieve_history(self,*_args,**_kwargs):raise RuntimeError('not enabled')
    class Client:
        def __init__(self,**_kwargs):self.price_tracking=PriceTracking()
    monkeypatch.setattr(channel3_sdk,'Channel3',Client)
    result=discovery.price_history('shoe')
    assert result['available'] is False
    assert 'unavailable' in result['reason']


def test_malformed_price_statistics_degrade_to_unavailable(monkeypatch):
    import channel3_sdk
    from types import SimpleNamespace
    from datetime import datetime,timezone
    monkeypatch.setenv('CHANNEL3_API_KEY','test-key')
    class PriceTracking:
        def retrieve_history(self,*_args,**_kwargs):
            return SimpleNamespace(statistics=SimpleNamespace(min_price=None),
                history=[SimpleNamespace(timestamp=datetime.now(timezone.utc),price=20,currency='USD')])
    class Client:
        def __init__(self,**_kwargs):self.price_tracking=PriceTracking()
    monkeypatch.setattr(channel3_sdk,'Channel3',Client)
    result=discovery.price_history('shirt')
    assert result['available'] is False
def test_structured_brand_and_retailer_search_filters(monkeypatch):
    from app import discovery
    calls=[]
    def fake_request(path,payload=None):
        calls.append((path,payload))
        if path.startswith('/v1/brands/search?'):return {'brands':[{'id':'nike-id','name':'Nike'}]}
        return {'products':[]}
    monkeypatch.setattr(discovery,'request',fake_request)
    body=discovery.AdvancedSearch(query='running shoes',revision=0,command_id='test',brand='Nike',retailer_domain='nike.com',max_price=150,availability=['InStock'],country='GB',currency='GBP',language='en')
    discovery.advanced_search(body)
    assert calls[1][1]['filters']=={'price':{'max_price':150},'availability':['InStock'],'brand_ids':['nike-id'],'website_ids':['nike.com']}
    assert calls[1][1]['config']=={'mode':'default','country':'GB','currency':'GBP','language':'en'}


def test_unknown_brand_does_not_silently_broaden_search(monkeypatch):
    import pytest
    from fastapi import HTTPException
    from app import discovery
    monkeypatch.setattr(discovery,'request',lambda *args,**kwargs:{'brands':[]})
    with pytest.raises(HTTPException) as error:
        discovery.advanced_search(discovery.AdvancedSearch(query='shoes',revision=0,command_id='test',brand='Unknown'))
    assert error.value.status_code==422
def test_category_condition_and_color_use_verified_channel3_filters(monkeypatch):
    from app import discovery
    calls=[]
    def provider(path,payload=None):
        calls.append((path,payload))
        if path.startswith('/v1/categories/search'):
            return {'categories':[{'title':'Running Shoes','slug':'running-shoes'}]}
        return {'products':[],'next_page_token':None}
    monkeypatch.setattr(discovery,'request',provider)
    body=discovery.AdvancedSearch(query='running shoes',revision=0,command_id='filters',
        category='Running Shoes',condition='used',color_hex='#000000')
    discovery.advanced_search(body)
    assert calls[-1][1]['filters']=={'category_ids':['running-shoes'],'conditions':['used'],
        'colors':{'palette':[{'hex':'#000000'}]}}
