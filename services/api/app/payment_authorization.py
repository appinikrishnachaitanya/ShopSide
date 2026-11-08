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


def require_authorized_scope(payment,room,offer,consent):
    if payment.get('authorization_mode')!='PREAUTHORIZED' or payment.get('status')!='authorized':
        raise HTTPException(409,'Verified buyer authorization required')
    if not payment.get('authorization_id') or not payment.get('provider_id'):
        raise HTTPException(409,'PayPal authorization is missing')
    if not payment.get('merchant_id') or offer.get('merchant_id')!=payment['merchant_id']:
        raise HTTPException(409,'Merchant changed')
    if offer.get('id')!=payment.get('quote_id') or offer.get('status')!='ACCEPTED':
        raise HTTPException(409,'Merchant offer changed')
    if offer.get('price_cents')!=payment['total'] or offer.get('expires_at',0)<=time.time():
        raise HTTPException(409,'Price or offer expiry changed')
    if not consent.get('enabled') or consent.get('expires_at',0)<=time.time():
        raise HTTPException(409,'Buyer consent expired or was revoked')
    if room.get('payer')!=payment.get('payer') or room.get('checkout',{}).get('id')!=payment['id']:
        raise HTTPException(409,'Buyer or checkout changed')
    if time.time()>payment.get('authorization_expires',0):
        raise HTTPException(409,'PayPal authorization window expired')
    return merchant_payee(payment['merchant_id'])
