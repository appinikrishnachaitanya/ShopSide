"""Deterministic validation for sandbox merchant offers.

LLM output is never an authority for stock, price, currency, or offer validity.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ListingPolicy:
    seller_id: str
    product_id: str
    currency: str
    list_price_cents: int
    minimum_price_cents: int
    max_discount_bps: int
    available_quantity: int
    max_order_quantity: int
    negotiation_enabled: bool
    offer_lifetime_seconds: int


def validate_offer(policy: ListingPolicy, *, seller_id: str, product_id: str,
                   currency: str, price_cents: int, quantity: int,
                   created_at: int, expires_at: int, now: int) -> int:
    """Return the exact total in cents, or reject the untrusted proposal."""
    values = (policy.list_price_cents, policy.minimum_price_cents, policy.max_discount_bps,
              policy.available_quantity, policy.max_order_quantity, policy.offer_lifetime_seconds,
              price_cents, quantity, created_at, expires_at, now)
    if any(type(value) is not int for value in values):
        raise ValueError('Offer values must be whole numbers')
    if not policy.seller_id or not policy.product_id or seller_id != policy.seller_id or product_id != policy.product_id:
        raise ValueError('Seller or product mismatch')
    if len(currency) != 3 or not currency.isascii() or not currency.isupper() or currency != policy.currency:
        raise ValueError('Currency mismatch')
    if not (0 < policy.list_price_cents and 0 < policy.minimum_price_cents <= policy.list_price_cents
            and 0 <= policy.max_discount_bps <= 10000 and policy.available_quantity >= 0
            and policy.max_order_quantity > 0 and policy.offer_lifetime_seconds > 0):
        raise ValueError('Invalid seller policy')
    if quantity < 1 or quantity > policy.max_order_quantity or quantity > policy.available_quantity:
        raise ValueError('Quantity unavailable')
    floor = max(policy.minimum_price_cents, (policy.list_price_cents * (10000 - policy.max_discount_bps) + 9999) // 10000)
    if price_cents < floor or price_cents > policy.list_price_cents:
        raise ValueError('Price outside approved policy')
    if not policy.negotiation_enabled and price_cents != policy.list_price_cents:
        raise ValueError('Negotiation is disabled')
    if created_at > now or expires_at <= now or expires_at <= created_at or expires_at - created_at > policy.offer_lifetime_seconds:
        raise ValueError('Offer expired or invalid')
    return price_cents * quantity
