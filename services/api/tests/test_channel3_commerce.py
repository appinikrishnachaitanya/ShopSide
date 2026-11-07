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
