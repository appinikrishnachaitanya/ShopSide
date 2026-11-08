import pytest
from fastapi import HTTPException
from app.checkout_capabilities import CheckoutMode, checkout_mode_for_source, require_checkout_mode


def test_checkout_source_boundaries():
    assert checkout_mode_for_source('CHANNEL3_LIVE')==CheckoutMode.EXTERNAL_RETAILER
    assert checkout_mode_for_source('SHOPSIDE_SANDBOX')==CheckoutMode.SHOP_SIDE_MERCHANT
    with pytest.raises(HTTPException):require_checkout_mode('CHANNEL3_LIVE',CheckoutMode.SHOP_SIDE_MERCHANT)
    with pytest.raises(HTTPException):require_checkout_mode('SHOPSIDE_SANDBOX',CheckoutMode.EXTERNAL_RETAILER)
    with pytest.raises(HTTPException) as beta:require_checkout_mode('CHANNEL3_LIVE',CheckoutMode.CHANNEL3_CHECKOUT_BETA)
    assert beta.value.status_code==503
