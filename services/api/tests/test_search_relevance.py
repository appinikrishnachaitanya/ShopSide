from app.discovery import AdvancedSearch, advanced_search, search_products

def test_fractional_cents_are_not_silently_rounded():
    from app.discovery import normalize
    item=normalize({'id':'desk','title':'Desk','offers':[{'url':'https://shop.example/item','domain':'shop.example','price':{'price':'12.345','currency':'USD'}}]})
    assert item['offers'][0]['price_cents'] is None


def test_sofa_search_filters_accessories_but_preserves_deliberate_table_search(monkeypatch):
    products = [
        {'id': 'sofa', 'title': 'Compact sofa', 'offers': []},
        {'id': 'love', 'title': 'Loveseat for small spaces', 'offers': []},
        {'id': 'table', 'title': 'Sofa End Table with Drawer', 'offers': []},
        {'id': 'nightstand', 'title': 'Sofa Nightstand', 'offers': []},
    ]
    monkeypatch.setattr('app.discovery.request', lambda *args: {'products': products, 'next_page_token': 'next'})
    assert [p['provider_id'] for p in search_products('compact sofa')] == ['sofa', 'love']
    result = advanced_search(AdvancedSearch(query='compact sofa', revision=0, command_id='x'))
    assert [p['provider_id'] for p in result['products']] == ['sofa', 'love']
    assert result['next_page_token'] == 'next'
    assert len(search_products('sofa end table')) == 4
