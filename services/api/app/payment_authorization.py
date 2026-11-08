"""Narrow, explicit PayPal authorization policy for owned sandbox merchants."""
import json
import os
import time
from fastapi import HTTPException


def merchant_payee(merchant_id):
    try: mapping=json.loads(os.getenv('PAYPAL_MERCHANT_IDS_JSON','{}'))
    except ValueError as exc:raise HTTPException(503,'Invalid PayPal merchant mapping') from exc
    payee=mapping.get(merchant_id) if isinstance(mapping,dict) else None
    if not isinstance(payee,str) or not payee.strip():
        raise HTTPException(503,'Merchant is not enabled for PayPal authorization')
    return payee


def partial_capture_enabled(merchant_id):
    try: enabled=json.loads(os.getenv('PAYPAL_PARTIAL_CAPTURE_MERCHANT_IDS_JSON','[]'))
    except ValueError:return False
    return isinstance(enabled,list) and merchant_id in enabled


def same_amount(value,cents,currency='USD'):
    """PayPal may add a breakdown to the amount object on readback."""
    return (isinstance(value,dict) and value.get('currency_code')==currency
            and value.get('value')==f'{cents//100}.{cents%100:02d}')


def require_authorized_scope(payment,room,offer,consent):
    if payment.get('authorization_mode')!='PREAUTHORIZED' or payment.get('status')!='authorized':
        raise HTTPException(409,'Verified buyer authorization required')
    if not payment.get('authorization_id') or not payment.get('provider_id'):
        raise HTTPException(409,'PayPal authorization is missing')
    if not payment.get('merchant_id') or offer.get('merchant_id')!=payment['merchant_id']:
        raise HTTPException(409,'Merchant changed')
    if (payment.get('quote_id') and offer.get('id')!=payment['quote_id']) or offer.get('status')!='ACCEPTED':
        raise HTTPException(409,'Merchant offer changed')
    if offer.get('price_cents',0)<=0 or offer['price_cents']>payment['total'] or offer.get('expires_at',0)<=time.time():
        raise HTTPException(409,'Price or offer expiry changed')
    if offer.get('currency')!=payment.get('currency') or payment.get('currency')!='USD':
        raise HTTPException(409,'Merchant offer currency changed')
    if not consent.get('enabled') or consent.get('expires_at',0)<=time.time():
        raise HTTPException(409,'Buyer consent expired or was revoked')
    if room.get('payer')!=payment.get('payer') or room.get('checkout',{}).get('id')!=payment['id']:
        raise HTTPException(409,'Buyer or checkout changed')
    if payment.get('demand_key') and consent.get('demand_key')!=payment['demand_key']:
        raise HTTPException(409,'Buyer policy changed')
    if payment.get('policy_version') and consent.get('policy_version')!=payment['policy_version']:
        raise HTTPException(409,'Buyer policy version changed')
    if payment.get('shipping_max_cents',0)!=0 or payment.get('tax_max_cents',0)!=0 or consent.get('shipping_max_cents',0)!=0 or consent.get('tax_max_cents',0)!=0:
        raise HTTPException(409,'Shipping or tax terms changed')
    if payment.get('provisional'):
        if offer.get('opportunity_id')!=payment.get('opportunity_id'):
            raise HTTPException(409,'Merchant opportunity changed')
        if consent.get('auto_accept_limit_cents')!=payment['total']:
            raise HTTPException(409,'Buyer maximum changed')
        if [(item['product'],item.get('sku'),item['quantity']) for item in payment['items']]!=[(item['product_id'],item.get('sku'),item['quantity']) for item in offer.get('items',[])]:
            raise HTTPException(409,'Product or SKU changed')
    if time.time()>payment.get('authorization_expires',0):
        raise HTTPException(409,'PayPal authorization window expired')
    return merchant_payee(payment['merchant_id'])
