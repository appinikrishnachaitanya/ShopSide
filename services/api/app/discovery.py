"""Channel3 v1, verified against @channel3/skills 1.0.0 API reference."""
import os,time,threading,re,contextvars,logging
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse
from urllib.parse import urlencode
import httpx
from pydantic import BaseModel,Field,ConfigDict
from fastapi import HTTPException
class Search(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=1,max_length=500)
    max_price:float|None=Field(default=None,ge=0,le=100000)
class AdvancedSearch(Search):
    revision:int
    command_id:str=Field(min_length=1,max_length=100)
    min_price:float|None=Field(default=None,ge=0,le=100000)
    availability:list[str]=Field(default_factory=list,max_length=2)
    mode:str=Field(default='default',pattern='^(default|agentic|keyword)$')
    page_token:str|None=Field(default=None,max_length=2000)
    country:str|None=Field(default=None,pattern='^[A-Z]{2}$')
    currency:str|None=Field(default=None,pattern='^[A-Z]{3}$')
    language:str|None=Field(default=None,pattern='^[a-z]{2}$')
    brand:str|None=Field(default=None,min_length=1,max_length=100)
    retailer_domain:str|None=Field(default=None,min_length=3,max_length=253,pattern=r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$')
class Price(BaseModel):
    price:Decimal=Field(ge=0)
    currency:str=Field(min_length=3,max_length=3)
class Offer(BaseModel):
    url:str
    domain:str
    price:Price
    availability:str|None=None
    dimensions:dict|None=None
    condition:str|None=None
    delivery: Any=None
    shipping: Any=None
class Image(BaseModel):
    url:str
class Product(BaseModel):
    id:str
    title:str
    description:str|None=None
    images:list[Image]=[]
    offers:list[Offer]=[]
    variants:dict|None=None
    structured_attributes:dict|None=None
    key_features:list[str]|None=None
    brands:list[dict]|None=None
    category:dict|None=None
    ratings:dict|None=None
def safe_url(value):
    return value if urlparse(value).scheme=='https' else None
def exact_cents(value):
    cents=value*100
    return int(cents) if cents==cents.to_integral_value() else None
def normalize(raw):
    p=Product.model_validate(raw)
    from .experience_router import spatial_eligible
    category=(p.category or {}).get('title') if isinstance(p.category,dict) else None
    return dict(id='channel3:'+p.id,provider_id=p.id,name=p.title,description=p.description,provenance='channel3',source='CHANNEL3_LIVE',category=category,spatial_eligible=spatial_eligible({'category':category,'name':p.title}),brand=(p.brands or [{}])[0].get('name'),retrieved_at=time.time(),image=next((safe_url(i.url) for i in p.images or [] if safe_url(i.url)),None),offers=[dict(retailer=o.domain,url=safe_url(o.url),price_cents=exact_cents(o.price.price),currency=o.price.currency,availability=o.availability,variant=None,condition=o.condition,dimensions=o.dimensions,delivery=o.delivery or o.shipping,checkout='retailer') for o in p.offers or [] if safe_url(o.url)],attributes=p.structured_attributes or {},variants=p.variants,key_features=p.key_features or [],ratings=p.ratings,merchant_offer=None)

def relevant_results(query, products):
    """Exclude obvious sofa accessories when the shopper asks for seating."""
    if not re.search(r'\b(?:sofas?|couches?|loveseats?)\b', query, re.I): return products
    if re.search(r'\b(?:tables?|nightstands?|covers?|slipcovers?)\b', query, re.I): return products
    accessory=re.compile(r'\b(?:nightstands?|end\s+tables?|side\s+tables?|coffee\s+tables?|console\s+tables?|sofa\s+tables?|slipcovers?|sofa\s+covers?)\b', re.I)
    return [p for p in products if not accessory.search(p['name'])]
cache={}; guard=threading.Lock()
class Channel3Budget:
    """Counts real HTTP attempts across threads, including transient retries."""
    def __init__(self,limit=10):self.limit=limit;self.count=0;self.lock=threading.Lock()
    def claim(self):
        with self.lock:
            if self.count>=self.limit:raise HTTPException(503,'Channel3 request limit reached')
            self.count+=1
channel3_budget=contextvars.ContextVar('channel3_budget',default=None)
def request(path,payload=None):
    key=os.getenv('CHANNEL3_API_KEY')
    if not key: raise HTTPException(503,'Live discovery unavailable — configure Channel3')
    identity=(path,str(payload))
    with guard:
        cached=cache.get(identity)
        if cached and time.monotonic()-cached[0]<30:return cached[1]
    try:
        budget=channel3_budget.get()
        with httpx.Client(timeout=10 if budget else 15) as client:
            for attempt in range(2):
                if budget:budget.claim()
                response=client.request('POST' if payload else 'GET','https://api.trychannel3.com'+path,json=payload,headers={'x-api-key':key})
                if response.status_code not in [429,502,503,504] or attempt:break
                time.sleep(.25)
            response.raise_for_status(); data=response.json()
            with guard:cache[identity]=(time.monotonic(),data)
            return data
    except (httpx.HTTPError,ValueError) as exc: raise HTTPException(502,'Channel3 request failed; retry later') from exc

def cancel_subscription(subscription_id):
    key=os.getenv('CHANNEL3_API_KEY')
    if not key:raise HTTPException(503,'Live discovery unavailable — configure Channel3')
    try:
        response=httpx.delete('https://api.trychannel3.com/v1/product-subscriptions/'+subscription_id,
            headers={'x-api-key':key},timeout=15)
        response.raise_for_status()
    except httpx.HTTPError as exc:raise HTTPException(502,'Channel3 subscription cancellation failed; retry later') from exc
def search_products(query,max_price=None):
    body={'query':query,'limit':12}
    if max_price is not None:body['filters']={'price':{'max_price':max_price}}
    try:return relevant_results(query,[normalize(p) for p in request('/v1/search',body)['products']])
    except (ValueError,KeyError) as exc:raise HTTPException(502,'Channel3 response did not match its documented schema') from exc
def product_details(id,selected_options=None):
    from channel3_sdk import Channel3
    key=os.getenv('CHANNEL3_API_KEY')
    if not key:raise HTTPException(503,'Live discovery unavailable — configure Channel3')
    try:
        client=Channel3(api_key=key,timeout=15,max_retries=0)
        raw=client.products.retrieve(id,selected_options=selected_options or None).model_dump(mode='json')
        result=normalize(raw)
    except HTTPException:raise
    except Exception as exc:raise HTTPException(502,'Channel3 product details unavailable') from exc
    if selected_options:
        effective={str(x['name']).casefold():str(x['label']).casefold() for x in (result.get('variants') or {}).get('selected',[])}
        if any(effective.get(str(name).casefold())!=str(label).casefold() for name,label in selected_options.items()):
            raise HTTPException(409,'Requested variation is unavailable; choose another size or color')
    return result
def similar_products(id,max_price=None):
    body={'product_id':id,'limit':12}
    if max_price is not None:body['filters']={'price':{'max_price':max_price}}
    try:return [normalize(p) for p in request('/v1/similar',body)['products']]
    except (ValueError,KeyError) as exc:raise HTTPException(502,'Channel3 response did not match its documented schema') from exc

def price_history(id,days=90):
    """SDK 4.8.0 history is optional; never infer trends from current offers."""
    from channel3_sdk import Channel3
    key=os.getenv('CHANNEL3_API_KEY')
    if not key:raise HTTPException(503,'Live discovery unavailable — configure Channel3')
    try:
        data=Channel3(api_key=key,timeout=15,max_retries=0).price_tracking.retrieve_history(id,days=days)
    except Exception:
        logging.getLogger(__name__).exception('Channel3 price history retrieval failed for product %s',id)
        return {'available':False,'reason':'Price history is unavailable for this product.'}
    try:
        stats=data.statistics
        if not stats or not data.history:
            return {'available':False,'reason':'No observed price history is available for this product.'}
        values=[{'at':point.timestamp.isoformat(),'price_cents':exact_cents(Decimal(str(point.price))),
                 'currency':point.currency} for point in data.history if exact_cents(Decimal(str(point.price))) is not None]
        if not values:return {'available':False,'reason':'No usable price history is available.'}
        return {'available':True,'observations':values[-90:],'statistics':{
            'minimum_cents':round(Decimal(str(stats.min_price))*100),
            'maximum_cents':round(Decimal(str(stats.max_price))*100),
            'mean_cents':round(Decimal(str(stats.mean))*100),
            'current_cents':round(Decimal(str(stats.current_price))*100),
            'std_dev_cents':round(Decimal(str(stats.std_dev))*100),
            'classification':stats.current_status,'currency':stats.currency},
            'source':'Channel3 observed history','as_of':values[-1]['at']}
    except Exception:
        logging.getLogger(__name__).exception('Channel3 price history data could not be normalized for product %s',id)
        return {'available':False,'reason':'Usable price history is unavailable for this product.'}

def advanced_search(body:AdvancedSearch):
    if body.min_price is not None and body.max_price is not None and body.min_price>body.max_price:
        raise HTTPException(422,'Minimum price exceeds maximum price')
    if any(v not in ('InStock','OutOfStock') for v in body.availability):
        raise HTTPException(422,'Invalid availability')
    payload={'query':body.query,'limit':12,'config':{'mode':body.mode}}
    if body.country:payload['config']['country']=body.country
    if body.currency:payload['config']['currency']=body.currency
    if body.language:payload['config']['language']=body.language
    if body.page_token:payload['page_token']=body.page_token
    filters={}
    price={}
    if body.min_price is not None:price['min_price']=body.min_price
    if body.max_price is not None:price['max_price']=body.max_price
    if price:filters['price']=price
    if body.availability:filters['availability']=body.availability
    if body.brand:
        response=request('/v1/brands/search?'+urlencode({'query':body.brand.strip(),'limit':20}))
        brands=response.get('brands') if isinstance(response,dict) else None
        if not isinstance(brands,list):raise HTTPException(502,'Channel3 brand lookup returned an invalid response')
        matches=[brand for brand in brands if isinstance(brand,dict) and isinstance(brand.get('name'),str) and brand['name'].casefold()==body.brand.strip().casefold() and isinstance(brand.get('id'),str) and brand['id']]
        if len(matches)!=1:raise HTTPException(422,'Brand not found uniquely on Channel3. Check its exact name or search without a brand filter.')
        filters['brand_ids']=[matches[0]['id']]
    if body.retailer_domain:filters['website_ids']=[body.retailer_domain.lower()]
    if filters:payload['filters']=filters
    try:
        result=request('/v1/search',payload)
        return {'products':relevant_results(body.query,[normalize(p) for p in result['products']]),'next_page_token':result.get('next_page_token')}
    except (ValueError,KeyError) as exc:raise HTTPException(502,'Channel3 response did not match its documented schema') from exc
