"""Tenant-scoped sandbox merchants, consented demand, durable opportunities and quotes."""
import hashlib, json, os, secrets, time
from dataclasses import replace
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from .deal_rules import ListingPolicy, validate_offer
from .discovery import product_details, search_products
from .merchant_agent import propose

ALLOWED={'CREATED','MATCHING','MERCHANT_NOTIFIED','OFFER_PROPOSED','HUMAN_REVIEW','OFFER_PUBLISHED','COUNTERED','ACCEPTED','DECLINED','EXPIRED','CANCELLED'}
TERMINAL={'ACCEPTED','DECLINED','EXPIRED','CANCELLED'}

def now():return int(time.time())
def identity(token):return hashlib.sha256(token.encode()).hexdigest()
def read(row):return json.loads(row[0]) if row else None
def put(db,table,id,state):
    db.execute(f'INSERT INTO {table}(id,state) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state',(id,json.dumps(state)))
    db.commit()

def setup(db):
    db.execute('CREATE TABLE IF NOT EXISTS merchants(id TEXT PRIMARY KEY, state TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS merchant_users(token_hash TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, name TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS merchant_products(merchant_id TEXT NOT NULL, product_id TEXT NOT NULL, state TEXT NOT NULL, PRIMARY KEY(merchant_id,product_id))')
    db.execute('CREATE TABLE IF NOT EXISTS merchant_opportunities(id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, room_id TEXT NOT NULL, demand_key TEXT NOT NULL, state TEXT NOT NULL, UNIQUE(merchant_id,room_id,demand_key))')
    db.execute('CREATE TABLE IF NOT EXISTS merchant_jobs(id TEXT PRIMARY KEY, state TEXT NOT NULL)')
    db.commit()
    # Seeds are explicitly sandbox identities; credentials are supplied securely by the operator.
    for index in range(1,4):
        merchant_id=f'sandbox-merchant-{index}'
        if not db.execute('SELECT id FROM merchants WHERE id=?',(merchant_id,)).fetchone():
            merchant={'id':merchant_id,'name':f'Sandbox Merchant {index}','sandbox':True,'verified_domain':os.getenv(f'SHOPSIDE_MERCHANT_{index}_DOMAIN','').lower(),'agent_name':f'ShopSide Seller {index}',
                'opt_in':False,'active':False,'mode':'manual','policy':{'max_discount_bps':0,'minimum_price_cents':None,'max_counteroffers':3,'offer_lifetime_seconds':600,'review_policy':'out_of_policy'},'activity':[]}
            put(db,'merchants',merchant_id,merchant)
        domain=os.getenv(f'SHOPSIDE_MERCHANT_{index}_DOMAIN','').lower()
        if domain:
            current=merchant(db,merchant_id)
            if current.get('verified_domain')!=domain:
                current['verified_domain']=domain
                put(db,'merchants',merchant_id,current)
        token=os.getenv(f'SHOPSIDE_MERCHANT_{index}_TOKEN')
        if token and len(token)>=24:
            db.execute('DELETE FROM merchant_users WHERE merchant_id=?',(merchant_id,))
            db.execute('INSERT INTO merchant_users(token_hash,merchant_id,name) VALUES(?,?,?) ON CONFLICT(token_hash) DO NOTHING',(identity(token),merchant_id,f'Sandbox operator {index}'))
    db.commit()

def merchant_auth(db,request:Request):
    bearer=request.headers.get('authorization','')
    token=request.headers.get('x-shopside-merchant-token') or (bearer[7:] if bearer.startswith('Bearer ') else '')
    if not token:raise HTTPException(401,'Merchant bearer token required')
    row=db.execute('SELECT merchant_id,name FROM merchant_users WHERE token_hash=?',(identity(token),)).fetchone()
    if not row:raise HTTPException(403,'Merchant access denied')
    return row[0],row[1]
def merchant(db,id):
    value=read(db.execute('SELECT state FROM merchants WHERE id=?',(id,)).fetchone())
    if not value:raise HTTPException(404,'Merchant not found')
    return value
def scoped_opportunity(db,merchant_id,op_id):
    row=db.execute('SELECT state FROM merchant_opportunities WHERE id=? AND merchant_id=?',(op_id,merchant_id)).fetchone()
    if not row:raise HTTPException(404,'Opportunity not found')
    return read(row)
def save_op(db,op):
    db.execute('UPDATE merchant_opportunities SET state=? WHERE id=? AND merchant_id=?',(json.dumps(op),op['id'],op['merchant_id']))
    db.commit()
def audit(op,event,actor,**details):
    op.setdefault('activity',[]).append({'event':event,'actor':actor,'at':now(),**details})

def product_rows(db,merchant_id):
    rows=db.execute('SELECT state FROM merchant_products WHERE merchant_id=?',(merchant_id,)).fetchall()
    return [read(row) for row in rows]

def current_product(mapping):
    try:
        product=product_details(mapping['product_id'].removeprefix('channel3:'))
        offer=next((o for o in product['offers'] if o.get('retailer','').lower()==mapping['domain'].lower() and o.get('price_cents') is not None),None)
        if not offer:return {**mapping,'status':'unavailable','observed':None}
        return {**mapping,'status':'current','observed':{'name':product['name'],'price_cents':offer['price_cents'],'currency':offer['currency'],'availability':offer['availability'],'url':offer['url'],'retrieved_at':product['retrieved_at']}}
    except Exception:
        return {**mapping,'status':'stale' if mapping.get('observed') else 'unavailable'}

def market_context(products):
    """Public observed offers only; no cost basis or invented price history."""
    result=[]
    for mapping in products[:3]:
        try:
            product=product_details(mapping['product_id'].removeprefix('channel3:'))
            result.extend({'product_id':mapping['product_id'],'domain':offer['retailer'],
                           'price_cents':offer['price_cents'],'currency':offer['currency'],
                           'availability':offer.get('availability'),'observed_at':product['retrieved_at']}
                          for offer in product.get('offers',[])[:5] if offer.get('price_cents') is not None)
        except Exception:pass
    return result[:12]

def policy_for(m, product):
    rules=m['policy']; observed=product.get('observed') or {}
    price=observed.get('price_cents')
    if not isinstance(price,int) or price<=0:raise HTTPException(409,'Current merchant price unavailable')
    floor=rules.get('minimum_price_cents')
    if not isinstance(floor,int) or floor<=0 or floor>price:raise HTTPException(409,'Merchant minimum price must be approved first')
    return ListingPolicy(m['id'],product['product_id'],observed['currency'],price,floor,rules['max_discount_bps'],1,1,m['active'],rules['offer_lifetime_seconds'])

def demand_from_room(room):
    bundle=room.get('smart_bundle') or {}; intent=room.get('shopping_journey',{}).get('intent') or room.get('shopping_intent') or {}
    categories=[str(x)[:80] for x in (intent.get('product_requirements') or [])[:4]]
    if not categories:
        categories=[str(s.get('requirement',''))[:80] for s in bundle.get('slots',[]) if isinstance(s,dict)][:4]
    categories=[c for c in categories if c.strip()]
    if not categories:return None
    budget=bundle.get('budget_cents') or room.get('budget')
    if not isinstance(budget,int) or budget<=0:return None
    return {'categories':categories,'budget_cents':budget,'currency':'USD','requirements':[str(x)[:100] for x in (intent.get('constraints') or [])[:5]],'product_refs':[str(i.get('product',{}).get('id')) for b in bundle.get('options',[])[:2] for i in b.get('items',[]) if i.get('product',{}).get('id')][:8]}

def match(db,room_id,room,notify):
    consent=room.get('seller_offers') or {}
    if not consent.get('enabled'):return []
    demand=demand_from_room(room)
    if not demand:return []
    key=consent['demand_key']; expires=consent['expires_at']
    if expires<=now():return []
    eligible=[]
    for row in db.execute('SELECT state FROM merchants').fetchall():
        m=read(row)
        if not m['opt_in'] or not m['active']:continue
        for p in product_rows(db,m['id']):
            observed=p.get('observed') or {}
            if p.get('status')!='current' or now()-observed.get('retrieved_at',0)>3600:continue
            if observed.get('availability') in ('OutOfStock','Unavailable'):continue
            if observed.get('currency')!=demand['currency'] or observed.get('price_cents',10**12)>demand['budget_cents']:continue
            if not any(category.lower() in (p.get('category','')+' '+observed.get('name','')).lower() for category in demand['categories']):continue
            eligible.append((observed['price_cents'],m['id'],p));break
    result=[]
    for _,merchant_id,product in sorted(eligible,key=lambda x:(x[0],x[1]))[:3]:
        existing=db.execute('SELECT id FROM merchant_opportunities WHERE merchant_id=? AND room_id=? AND demand_key=?',(merchant_id,room_id,key)).fetchone()
        if existing:result.append(existing[0]);continue
        op_id=secrets.token_urlsafe(15)
        op={'id':op_id,'merchant_id':merchant_id,'room_id':room_id,'demand_key':key,'status':'MERCHANT_NOTIFIED',
            'demand':{**demand,'expires_at':expires},'product_id':product['product_id'],'offer':None,'counter_count':0,'created_at':now(),'activity':[]}
        audit(op,'created','system');audit(op,'matching','system');audit(op,'merchant_notified','system')
        db.execute('INSERT INTO merchant_opportunities VALUES(?,?,?,?,?)',(op_id,merchant_id,room_id,key,json.dumps(op)))
        put(db,'merchant_jobs',op_id,{'id':op_id,'opportunity_id':op_id,'status':'pending','attempts':0,'next_at':now()})
        result.append(op_id)
    db.commit()
    if result:notify(room_id)
    return result

def publish(db,room,op,merchant,proposal,actor,notify,human=False):
    if op['status'] in TERMINAL:raise HTTPException(409,'Opportunity closed')
    if not merchant['opt_in'] or not merchant['active']:raise HTTPException(409,'Merchant opted out or paused')
    consent=room.get('seller_offers') or {}
    if not consent.get('enabled') or consent.get('demand_key')!=op['demand_key']:raise HTTPException(409,'Buyer consent revoked')
    if op['demand']['expires_at']<=now():raise HTTPException(409,'Opportunity expired')
    product=next((p for p in product_rows(db,merchant['id']) if p['product_id']==proposal.product_id),None)
    if not product or product['product_id']!=op['product_id']:raise HTTPException(422,'Product not owned for this opportunity')
    product=current_product(product)
    if product['status']!='current' or product['observed'].get('availability') in ('OutOfStock','Unavailable'):
        raise HTTPException(409,'Merchant listing unavailable')
    policy=policy_for(merchant,product)
    audit(op,'offer_proposed',actor,price_cents=proposal.price_cents)
    if human:policy=replace(policy,max_discount_bps=10000)
    elif merchant['policy'].get('review_policy')=='all':
        op['status']='HUMAN_REVIEW';op['pending']={'product_id':proposal.product_id,'price_cents':proposal.price_cents,'reason':'Merchant policy requires human review','explanation':proposal.explanation[:300]}
        audit(op,'human_review_required',actor,reason='Merchant policy requires human review');save_op(db,op)
        return {'review_required':True,'reason':'Merchant policy requires human review'}
    created=now();expires=min(created+policy.offer_lifetime_seconds,op['demand']['expires_at'])
    try:total=validate_offer(policy,seller_id=merchant['id'],product_id=product['product_id'],currency=policy.currency,
        price_cents=proposal.price_cents,quantity=1,created_at=created,expires_at=expires,now=created)
    except ValueError as exc:
        if human:raise HTTPException(422,str(exc)) from exc
        op['status']='HUMAN_REVIEW';op['pending']={'product_id':proposal.product_id,'price_cents':proposal.price_cents,'reason':str(exc),'explanation':proposal.explanation[:300]}
        audit(op,'human_review_required',actor,reason=str(exc));save_op(db,op)
        return {'review_required':True,'reason':str(exc)}
    quote={'id':secrets.token_urlsafe(16),'opportunity_id':op['id'],'merchant_id':merchant['id'],'merchant_name':merchant['name'],
        'agent_name':merchant['agent_name'],'product_id':product['product_id'],'product_name':product['observed']['name'],
        'reference_price_cents':policy.list_price_cents,'price_cents':total,'currency':policy.currency,
        'limitations':'Sandbox quote only. No payment or retailer purchase. Price and availability checked when published.',
        'explanation':proposal.explanation[:300],'created_at':created,'expires_at':expires,'status':'OFFER_PUBLISHED'}
    op['offer']=quote;op['status']='OFFER_PUBLISHED';op.pop('pending',None);audit(op,'offer_published',actor,quote_id=quote['id']);save_op(db,op)
    for old in room.get('flash_offers',[]):
        if old.get('opportunity_id')==op['id'] and old.get('status') in ('OFFER_PUBLISHED','COUNTERED'):
            old['status']='CANCELLED'
    room.setdefault('flash_offers',[]).append(quote)
    notify(op['room_id'])
    return {'quote':quote}

class MerchantPolicyUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str|None=Field(default=None,max_length=80)
    agent_name:str|None=Field(default=None,max_length=80)
    opt_in:bool|None=None
    active:bool|None=None
    mode:str|None=Field(default=None,pattern='^(automatic|manual)$')
    max_discount_bps:int|None=Field(default=None,ge=0,le=10000)
    minimum_price_cents:int|None=Field(default=None,gt=0)
    max_counteroffers:int|None=Field(default=None,ge=0,le=3)
    offer_lifetime_seconds:int|None=Field(default=None,ge=60,le=3600)
    review_policy:str|None=Field(default=None,pattern='^(out_of_policy|all)$')

class ConnectProduct(BaseModel):
    product_id:str=Field(pattern='^channel3:[^ ]+$',max_length=200)
    domain:str=Field(min_length=3,max_length=200)
    category:str=Field(min_length=2,max_length=80)

class DealRequest(BaseModel):
    command_id:str=Field(min_length=8,max_length=100)
    action:str=Field(pattern='^(generate|approve|reject|decline|close)$')
    price_cents:int|None=Field(default=None,gt=0)
    explanation:str=Field(default='',max_length=300)

class BuyerDealAction(BaseModel):
    command_id:str=Field(min_length=8,max_length=100)
    action:str=Field(pattern='^(accept|counter|dismiss|invite|remove)$')
    offer_id:str|None=None
    price_cents:int|None=Field(default=None,gt=0)
