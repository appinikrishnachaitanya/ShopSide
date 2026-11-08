"""Explicit checkout destinations for products supported today."""
from enum import Enum
from fastapi import HTTPException


class CheckoutMode(str, Enum):
    EXTERNAL_RETAILER = 'EXTERNAL_RETAILER'
    SHOP_SIDE_MERCHANT = 'SHOP_SIDE_MERCHANT'
    CHANNEL3_CHECKOUT_BETA = 'CHANNEL3_CHECKOUT_BETA'


def checkout_mode_for_source(source: str) -> CheckoutMode:
    if source == 'CHANNEL3_LIVE':
        return CheckoutMode.EXTERNAL_RETAILER
    if source == 'SHOPSIDE_SANDBOX':
        return CheckoutMode.SHOP_SIDE_MERCHANT
    raise HTTPException(409, 'No checkout method is available for this product')


def require_checkout_mode(source: str, expected: CheckoutMode) -> None:
    if expected == CheckoutMode.CHANNEL3_CHECKOUT_BETA:
        raise HTTPException(503, 'Channel3 checkout is not enabled')
    if checkout_mode_for_source(source) != expected:
        raise HTTPException(409, 'Product is not eligible for this checkout method')
