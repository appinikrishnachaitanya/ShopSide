from dataclasses import replace
import pytest
from app.deal_rules import ListingPolicy, validate_offer

POLICY = ListingPolicy('seller-a', 'product-a', 'USD', 15000, 12000, 1000, 3, 2, True, 600)
BASE = dict(seller_id='seller-a', product_id='product-a', currency='USD', price_cents=13500,
            quantity=2, created_at=100, expires_at=700, now=101)

def test_valid_offer_uses_exact_integer_total():
    assert validate_offer(POLICY, **BASE) == 27000

@pytest.mark.parametrize('change', [
    {'price_cents': 13499}, {'price_cents': 11999}, {'price_cents': 13500.0},
    {'quantity': 4}, {'quantity': 0}, {'seller_id': 'seller-b'},
    {'product_id': 'channel3:other'}, {'currency': 'EUR'}, {'now': 700},
    {'expires_at': 701},
])
def test_rejects_unauthorized_or_invalid_offers(change):
    with pytest.raises(ValueError): validate_offer(POLICY, **{**BASE, **change})

def test_disabled_negotiation_cannot_discount():
    with pytest.raises(ValueError): validate_offer(replace(POLICY, negotiation_enabled=False), **BASE)
