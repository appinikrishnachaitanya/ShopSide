"""The owned sandbox catalog, not retailer references, drives seller matching."""
import json
import sqlite3

from app import merchant as service
from app.merchant_agent import OfferProposal


def database():
    db=sqlite3.connect(':memory:')
    service.setup(db)
    for index in range(1,4):
        m=service.merchant(db,f'sandbox-merchant-{index}')
        m.update(opt_in=True,active=True)
        m['policy'].update(minimum_price_cents=20000,max_discount_bps=1000)
        service.put(db,'merchants',m['id'],m)
    return db


def room(requirements,budget=50000):
    return {'seller_offers':{'enabled':True,'demand_key':'test-demand','expires_at':service.now()+3600},
        'shopping_intent':{'product_requirements':requirements},'budget':budget,'flash_offers':[]}


def test_three_owned_bundle_matches_with_real_totals():
    with database() as db:
        state=room(['compact desk','ergonomic chair'])
        ids=service.match(db,'buyer-room',state,lambda _id:None)
        assert len(ids)==3
        ops=[service.read(row) for row in db.execute('SELECT state FROM merchant_opportunities').fetchall()]
        assert sorted(op['reference_total_cents'] for op in ops)==[28500,29000,29000]
        assert all(len(op['product_ids'])==2 for op in ops)
        assert all(pid.startswith('shopside:') for op in ops for pid in op['product_ids'])
        assert service.match(db,'buyer-room',state,lambda _id:None)==ids


def test_one_product_budget_and_no_eligible_merchant():
    with database() as db:
        assert len(service.match(db,'single-room',room(['desk'],20000),lambda _id:None))==3
        assert service.match(db,'over-budget',room(['desk','chair'],20000),lambda _id:None)==[]
        assert service.match(db,'unknown',room(['sofa']),lambda _id:None)==[]


def test_stock_opt_in_and_external_references_cannot_match():
    with database() as db:
        first=service.merchant(db,'sandbox-merchant-1');first['opt_in']=False;service.put(db,'merchants',first['id'],first)
        product=next(p for p in service.product_rows(db,'sandbox-merchant-2') if p['sku']=='ergonomic-chair')
        db.execute('UPDATE merchant_inventory SET stock_quantity=0 WHERE merchant_id=? AND product_id=?',(product['merchant_id'],product['product_id']))
        external={'merchant_id':'sandbox-merchant-1','product_id':'channel3:desk','source':'CHANNEL3_LIVE','status':'current',
            'category':'desk','observed':{'name':'Compact Desk','price_cents':100,'currency':'USD','availability':'InStock','retrieved_at':service.now()}}
        db.execute('INSERT INTO merchant_products VALUES(?,?,?)',(external['merchant_id'],external['product_id'],json.dumps(external)))
        db.commit()
        ids=service.match(db,'stock-room',room(['desk','chair']),lambda _id:None)
        assert len(ids)==1
        assert service.read(db.execute('SELECT state FROM merchant_opportunities WHERE id=?',(ids[0],)).fetchone())['merchant_id']=='sandbox-merchant-3'


def test_bundle_quote_uses_owned_lines_and_merchant_policy():
    with database() as db:
        state=room(['desk','chair'])
        op_id=service.match(db,'quote-room',state,lambda _id:None)[0]
        op=service.read(db.execute('SELECT state FROM merchant_opportunities WHERE id=?',(op_id,)).fetchone())
        m=service.merchant(db,op['merchant_id'])
        result=service.publish(db,state,op,m,OfferProposal(product_id=op['product_id'],price_cents=27000,explanation='A desk and chair together.'),'merchant',lambda _id:None)
        quote=result['quote']
        assert quote['price_cents']==27000
        assert len(quote['items'])==2
        assert sum(item['price_cents'] for item in quote['items'])==quote['reference_price_cents']


def test_ai_offer_above_auto_approval_limit_waits_for_human():
    with database() as db:
        state=room(['desk','chair'])
        op_id=service.match(db,'review-room',state,lambda _id:None)[0]
        op=service.read(db.execute('SELECT state FROM merchant_opportunities WHERE id=?',(op_id,)).fetchone())
        m=service.merchant(db,op['merchant_id'])
        m['policy']['auto_approval_limit_cents']=26000
        result=service.publish(db,state,op,m,OfferProposal(product_id=op['product_id'],price_cents=27000,
            explanation='Bundle price.'),'merchant_ai',lambda _id:None)
        assert result['review_required'] is True
        assert state['flash_offers']==[]
        assert service.scoped_opportunity(db,m['id'],op_id)['status']=='HUMAN_REVIEW'


def test_buyer_auto_accept_limit_never_authorizes_payment():
    with database() as db:
        state=room(['desk','chair'])
        state['seller_offers']['auto_accept_limit_cents']=27000
        op_id=service.match(db,'accept-room',state,lambda _id:None)[0]
        op=service.read(db.execute('SELECT state FROM merchant_opportunities WHERE id=?',(op_id,)).fetchone())
        m=service.merchant(db,op['merchant_id'])
        quote=service.publish(db,state,op,m,OfferProposal(product_id=op['product_id'],price_cents=27000,
            explanation='Bundle price.'),'merchant_ai',lambda _id:None)['quote']
        assert quote['status']=='ACCEPTED' and quote['auto_accepted'] is True
        assert state.get('checkout') is None
