"""Channel3 v1, verified against @channel3/skills 1.0.0 API reference."""
import os,time,threading,re
from decimal import Decimal
from typing import Any
from urllib.parse import quote,urlparse
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
def safe_url(value):
    return value if urlparse(value).scheme=='https' else None
def normalize(raw):
    p=Product.model_validate(raw)
    return dict(id='channel3:'+p.id,provider_id=p.id,name=p.title,description=p.description,provenance='channel3',retrieved_at=time.time(),image=next((safe_url(i.url) for i in p.images if safe_url(i.url)),None),offers=[dict(retailer=o.domain,url=safe_url(o.url),price_cents=int(o.price.price*100),currency=o.price.currency,availability=o.availability,variant=None,condition=o.condition,dimensions=o.dimensions,delivery=o.delivery or o.shipping,checkout='retailer') for o in p.offers if safe_url(o.url)],attributes=p.structured_attributes or {},variants=p.variants,key_features=p.key_features or [],merchant_offer=None)

def relevant_results(query, products):
    """Exclude obvious sofa accessories when the shopper asks for seating."""
    if not re.search(r'\b(?:sofas?|couches?|loveseats?)\b', query, re.I): return products
    if re.search(r'\b(?:tables?|nightstands?|covers?|slipcovers?)\b', query, re.I): return products
    accessory=re.compile(r'\b(?:nightstands?|end\s+tables?|side\s+tables?|coffee\s+tables?|console\s+tables?|sofa\s+tables?|slipcovers?|sofa\s+covers?)\b', re.I)
    return [p for p in products if not accessory.search(p['name'])]
cache={}; guard=threading.Lock()
def request(path,payload=None):
    key=os.getenv('CHANNEL3_API_KEY')
    if not key: raise HTTPException(503,'Live discovery unavailable — configure Channel3')
    identity=(path,str(payload))
    with guard:
        cached=cache.get(identity)
        if cached and time.monotonic()-cached[0]<30:return cached[1]
        try:
            with httpx.Client(timeout=15) as client:
                for attempt in range(2):
                    response=client.request('POST' if payload else 'GET','https://api.trychannel3.com'+path,json=payload,headers={'x-api-key':key})
                    if response.status_code not in [429,502,503,504] or attempt:break
                    time.sleep(.25)
                response.raise_for_status(); data=response.json()
                cache[identity]=(time.monotonic(),data);return data
        except (httpx.HTTPError,ValueError) as exc: raise HTTPException(502,'Channel3 request failed; retry later') from exc
def search_products(query,max_price=None):
    body={'query':query,'limit':12}
    if max_price is not None:body['filters']={'price':{'max_price':max_price}}
    try:return relevant_results(query,[normalize(p) for p in request('/v1/search',body)['products']])
    except (ValueError,KeyError) as exc:raise HTTPException(502,'Channel3 response did not match its documented schema') from exc
def product_details(id,selected_options=None):
    from urllib.parse import urlencode
    path='/v1/products/'+quote(id,safe='')
    if selected_options:path+='?'+urlencode({'option_'+k:v for k,v in selected_options.items()})
    return normalize(request(path))
def similar_products(id):
    try:return [normalize(p) for p in request('/v1/similar',{'product_id':id,'limit':12})['products']]
    except (ValueError,KeyError) as exc:raise HTTPException(502,'Channel3 response did not match its documented schema') from exc

def advanced_search(body:AdvancedSearch):
    if body.min_price is not None and body.max_price is not None and body.min_price>body.max_price:
        raise HTTPException(422,'Minimum price exceeds maximum price')
    if any(v not in ('InStock','OutOfStock') for v in body.availability):
        raise HTTPException(422,'Invalid availability')
    payload={'query':body.query,'limit':12,'config':{'mode':body.mode}}
    if body.country:payload['config']['country']=body.country
    if body.currency:payload['config']['currency']=body.currency
    if body.page_token:payload['page_token']=body.page_token
    filters={}
    price={}
    if body.min_price is not None:price['min_price']=body.min_price
    if body.max_price is not None:price['max_price']=body.max_price
    if price:filters['price']=price
    if body.availability:filters['availability']=body.availability
    if filters:payload['filters']=filters
    try:
        result=request('/v1/search',payload)
        return {'products':relevant_results(body.query,[normalize(p) for p in result['products']]),'next_page_token':result.get('next_page_token')}
    except (ValueError,KeyError) as exc:raise HTTPException(502,'Channel3 response did not match its documented schema') from exc
