"""Tenant-scoped sandbox merchants, consented demand, durable opportunities and quotes."""
import hashlib, json, os, secrets, time
from dataclasses import replace
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from .deal_rules import ListingPolicy, validate_offer
from .discovery import product_details, search_products
from .merchant_agent import propose

ALLOWED={'CREATED','MATCHING','MERCHANT_NOTIFIED','OFFER_PROPOSED','HUMAN_REVIEW','OFFER_PUBLISHED','COUNTERED','ACCEPTED','DECLINED','EXPIRED','CANCELLED'}
TERMINAL={'ACCEPTED','DECLINED','EXPIRED','CANCELLED','ORDER_COMPLETED'}
SANDBOX_CATALOG={
    1:[('compact-desk','Compact Desk','desk',18000,8),('ergonomic-chair','Ergonomic Chair','chair',11000,8),('desk-lamp','Desk Lamp','lamp',3500,12)],
    2:[('compact-desk','Compact Desk','desk',16500,8),('ergonomic-chair','Ergonomic Chair','chair',12500,8),('monitor-stand','Monitor Stand','stand',4500,12)],
    3:[('compact-desk','Compact Desk','desk',19000,8),('ergonomic-chair','Ergonomic Chair','chair',9500,8),('storage-shelf','Storage Shelf','shelf',5500,12)],
}
SANDBOX_NAMES={1:'Studio Furniture',2:'Urban Workspace',3:'Home Essentials'}

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
    db.execute('CREATE TABLE IF NOT EXISTS merchant_inventory(merchant_id TEXT NOT NULL, product_id TEXT NOT NULL, stock_quantity INTEGER NOT NULL, reserved_quantity INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(merchant_id,product_id))')
    db.execute('CREATE TABLE IF NOT EXISTS merchant_opportunities(id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, room_id TEXT NOT NULL, demand_key TEXT NOT NULL, state TEXT NOT NULL, UNIQUE(merchant_id,room_id,demand_key))')
    db.execute('CREATE TABLE IF NOT EXISTS merchant_jobs(id TEXT PRIMARY KEY, state TEXT NOT NULL)')
    db.commit()
    # Seeds are explicitly sandbox identities; credentials are supplied securely by the operator.
    for index in range(1,4):
        merchant_id=f'sandbox-merchant-{index}'
        if not db.execute('SELECT id FROM merchants WHERE id=?',(merchant_id,)).fetchone():
            merchant_data={'id':merchant_id,'name':SANDBOX_NAMES[index],'sandbox':True,'verified_domain':os.getenv(f'SHOPSIDE_MERCHANT_{index}_DOMAIN','').lower(),'agent_name':f'ShopSide Seller {index}',
                'opt_in':False,'active':False,'mode':'manual','policy':{'max_discount_bps':0,'minimum_price_cents':None,'max_counteroffers':3,'offer_lifetime_seconds':600,'review_policy':'out_of_policy','auto_approval_limit_cents':None},'activity':[]}
            put(db,'merchants',merchant_id,merchant_data)
        current=merchant(db,merchant_id)
        if current.get('name')==f'Sandbox Merchant {index}':
            current['name']=SANDBOX_NAMES[index]
            put(db,'merchants',merchant_id,current)
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
    for index, products in SANDBOX_CATALOG.items():
        merchant_id=f'sandbox-merchant-{index}'
        for sku,title,category,price,stock in products:
            product_id=f'shopside:{merchant_id}:{sku}'
            state={'id':product_id,'product_id':product_id,'merchant_id':merchant_id,'source':'SHOPSIDE_SANDBOX',
                'sku':sku,'title':title,'category':category,'currency':'USD','price_cents':price,
                'stock_quantity':stock,'active':True,'sandbox':True,'description':'Fictional ShopSide sandbox product. No goods shipped.',
                'status':'current','observed':{'name':title,'price_cents':price,'currency':'USD','availability':'InStock',
                    'retrieved_at':now(),'url':None}}
            db.execute('INSERT INTO merchant_products(merchant_id,product_id,state) VALUES(?,?,?) ON CONFLICT(merchant_id,product_id) DO NOTHING',
                (merchant_id,product_id,json.dumps(state)))
            db.execute('INSERT INTO merchant_inventory(merchant_id,product_id,stock_quantity,reserved_quantity) VALUES(?,?,?,0) ON CONFLICT(merchant_id,product_id) DO NOTHING',
                (merchant_id,product_id,stock))
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
    products=[read(row) for row in rows]
    for product in products:
        if product.get('source')=='SHOPSIDE_SANDBOX':
            stock=db.execute('SELECT stock_quantity,reserved_quantity FROM merchant_inventory WHERE merchant_id=? AND product_id=?',
                (merchant_id,product['product_id'])).fetchone()
            product['stock_quantity']=stock[0]-stock[1] if stock else 0
    return products

def current_product(mapping):
    if mapping.get('source')=='SHOPSIDE_SANDBOX':
        return {**mapping,'status':'current' if mapping.get('active') and mapping.get('stock_quantity',0)>0 else 'unavailable',
            'observed':{**mapping['observed'],'availability':'InStock' if mapping.get('stock_quantity',0)>0 else 'OutOfStock',
                'retrieved_at':now(),'price_cents':mapping['price_cents']}}
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
        if mapping.get('source')=='SHOPSIDE_SANDBOX':continue
        try:
            product=product_details(mapping['product_id'].removeprefix('channel3:'))
            result.extend({'product_id':mapping['product_id'],'domain':offer['retailer'],
                           'price_cents':offer['price_cents'],'currency':offer['currency'],
                           'availability':offer.get('availability'),'observed_at':product['retrieved_at']}
                          for offer in product.get('offers',[])[:5] if offer.get('price_cents') is not None)
        except Exception:pass
    return result[:12]

def demand_from_room(room):
    bundle=room.get('smart_bundle') or {}; intent=room.get('shopping_journey',{}).get('intent') or room.get('shopping_intent') or {}
    # Sandbox merchant prices and checkout are USD only. Never reinterpret a
    # non-USD budget as USD when matching or negotiating.
    currencies=[bundle.get('currency'),intent.get('currency'),(room.get('move_in') or {}).get('mission',{}).get('currency')]
    if any(currency and currency!='USD' for currency in currencies):return None
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
        if not m['opt_in'] or not m['active'] or not m.get('sandbox'):continue
        if consent.get('merchant_id') and consent['merchant_id']!=m['id']:continue
        available=[p for p in product_rows(db,m['id']) if p.get('source')=='SHOPSIDE_SANDBOX' and p.get('active') and p.get('stock_quantity',0)>0 and p.get('currency')==demand['currency']]
        chosen=[]
        for requirement in demand['categories']:
            words={word for word in requirement.lower().split() if word not in ('a','an','the','and','with')}
            candidates=[p for p in available if p['category'].lower() in words and p not in chosen]
            if not candidates:break
            chosen.append(min(candidates,key=lambda p:(p['price_cents'],p['product_id'])))
        if len(chosen)!=len(demand['categories']):continue
        total=sum(p['price_cents'] for p in chosen)
        if total>demand['budget_cents']:continue
        eligible.append((total,m['id'],chosen))
    result=[]
    for total,merchant_id,products in sorted(eligible,key=lambda x:(x[0],x[1]))[:3]:
        existing=db.execute('SELECT id FROM merchant_opportunities WHERE merchant_id=? AND room_id=? AND demand_key=?',(merchant_id,room_id,key)).fetchone()
        if existing:result.append(existing[0]);continue
        op_id=secrets.token_urlsafe(15)
        op={'id':op_id,'merchant_id':merchant_id,'room_id':room_id,'demand_key':key,'status':'MERCHANT_NOTIFIED',
            'demand':{**demand,'expires_at':expires},'product_id':products[0]['product_id'],
            'product_ids':[p['product_id'] for p in products],'reference_total_cents':total,
            'offer':None,'counter_count':0,'created_at':now(),'activity':[]}
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
    product_ids=op.get('product_ids') or [op['product_id']]
    if proposal.product_id!=op['product_id']:raise HTTPException(422,'Product not owned for this opportunity')
    rows={p['product_id']:p for p in product_rows(db,merchant['id']) if p.get('source')=='SHOPSIDE_SANDBOX'}
    if any(product_id not in rows for product_id in product_ids):raise HTTPException(422,'Product not owned for this opportunity')
    products=[current_product(rows[product_id]) for product_id in product_ids]
    if any(p['status']!='current' or p.get('stock_quantity',0)<1 for p in products):raise HTTPException(409,'Merchant listing unavailable')
    if len({p['currency'] for p in products})!=1:raise HTTPException(422,'Mixed currencies are not supported')
    reference_total=sum(p['price_cents'] for p in products)
    floor=merchant['policy'].get('minimum_price_cents')
    if not isinstance(floor,int) or floor<=0 or floor>reference_total:raise HTTPException(409,'Merchant minimum price must be approved first')
    policy=ListingPolicy(merchant['id'],op['product_id'],products[0]['currency'],reference_total,floor,
        merchant['policy']['max_discount_bps'],1,1,merchant['active'],merchant['policy']['offer_lifetime_seconds'])
    audit(op,'offer_proposed',actor,price_cents=proposal.price_cents)
    if human:policy=replace(policy,max_discount_bps=10000)
    elif proposal.needs_review:
        op['status']='HUMAN_REVIEW';op['pending']={'product_id':proposal.product_id,'price_cents':proposal.price_cents,
            'reason':'Agent requested human approval','explanation':proposal.explanation[:300]}
        audit(op,'human_review_required',actor,reason='Agent requested human approval');save_op(db,op)
        return {'review_required':True,'reason':'Agent requested human approval'}
    elif merchant['policy'].get('review_policy')=='all':
        op['status']='HUMAN_REVIEW';op['pending']={'product_id':proposal.product_id,'price_cents':proposal.price_cents,'reason':'Merchant policy requires human review','explanation':proposal.explanation[:300]}
        audit(op,'human_review_required',actor,reason='Merchant policy requires human review');save_op(db,op)
        return {'review_required':True,'reason':'Merchant policy requires human review'}
    elif actor=='merchant_ai' and merchant['policy'].get('auto_approval_limit_cents') is not None and proposal.price_cents>merchant['policy']['auto_approval_limit_cents']:
        op['status']='HUMAN_REVIEW';op['pending']={'product_id':proposal.product_id,'price_cents':proposal.price_cents,
            'reason':'Above merchant auto-approval limit','explanation':proposal.explanation[:300]}
        audit(op,'human_review_required',actor,reason='Above merchant auto-approval limit');save_op(db,op)
        return {'review_required':True,'reason':'Above merchant auto-approval limit'}
    created=now();expires=min(created+policy.offer_lifetime_seconds,op['demand']['expires_at'])
    try:total=validate_offer(policy,seller_id=merchant['id'],product_id=op['product_id'],currency=policy.currency,
        price_cents=proposal.price_cents,quantity=1,created_at=created,expires_at=expires,now=created)
    except ValueError as exc:
        if human:raise HTTPException(422,str(exc)) from exc
        op['status']='HUMAN_REVIEW';op['pending']={'product_id':proposal.product_id,'price_cents':proposal.price_cents,'reason':str(exc),'explanation':proposal.explanation[:300]}
        audit(op,'human_review_required',actor,reason=str(exc));save_op(db,op)
        return {'review_required':True,'reason':str(exc)}
    if total>op['demand']['budget_cents']:raise HTTPException(422,'Offer exceeds buyer budget')
    quote={'id':secrets.token_urlsafe(16),'opportunity_id':op['id'],'merchant_id':merchant['id'],'merchant_name':merchant['name'],
        'agent_name':merchant['agent_name'],'product_id':op['product_id'],'product_name':' + '.join(p['title'] for p in products),
        'items':[{'product_id':p['product_id'],'sku':p['sku'],'name':p['title'],'quantity':1,'price_cents':p['price_cents']} for p in products],
        'reference_price_cents':policy.list_price_cents,'price_cents':total,'currency':policy.currency,
        'limitations':'Fictional ShopSide sandbox products. No goods shipped. Payment requires a buyer-approved PayPal Sandbox checkout or a verified authorization for this exact merchant and scope.',
        'explanation':proposal.explanation[:300],'created_at':created,'expires_at':expires,'status':'OFFER_PUBLISHED'}
    limit=consent.get('auto_accept_limit_cents')
    if isinstance(limit,int) and limit>0 and total<=limit:
        quote['status']='ACCEPTED';quote['auto_accepted']=True
    elif isinstance(limit,int) and limit>0 and total>limit and op.get('counter_count',0)<merchant['policy']['max_counteroffers']:
        quote['status']='COUNTERED';quote['buyer_agent_countered']=True
        op['counter_count']=op.get('counter_count',0)+1
        op['counter_price_cents']=limit
        audit(op,'buyer_agent_countered','buyer_agent',price_cents=limit,quote_id=quote['id'])
        job_id=op['id']+'-buyer-agent-'+str(op['counter_count'])
        put(db,'merchant_jobs',job_id,{'id':job_id,'opportunity_id':op['id'],'status':'pending','attempts':0,'next_at':now()})
        quote['counter_job_id']=job_id
    op['offer']=quote;op['status']=quote['status'];op.pop('pending',None);audit(op,'offer_published',actor,quote_id=quote['id'])
    if quote.get('auto_accepted'):audit(op,'auto_accepted_within_buyer_limit','buyer',limit_cents=limit)
    save_op(db,op)
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
    auto_approval_limit_cents:int|None=Field(default=None,gt=0)

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
