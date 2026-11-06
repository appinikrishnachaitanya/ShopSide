"""Channel3 v1, verified against @channel3/skills 1.0.0 API reference."""
import os,time,threading
from decimal import Decimal
from urllib.parse import quote,urlparse
import httpx
from pydantic import BaseModel,Field,ConfigDict
from fastapi import HTTPException
class Search(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=1,max_length=500)
    max_price:float|None=Field(default=None,ge=0,le=100000)
class Price(BaseModel):
    price:Decimal=Field(ge=0)
    currency:str=Field(min_length=3,max_length=3)
class Offer(BaseModel):
    url:str
    domain:str
    price:Price
    availability:str|None=None
class Image(BaseModel):
    url:str
class Product(BaseModel):
    id:str
    title:str
    description:str|None=None
    images:list[Image]=[]
    offers:list[Offer]=[]
def safe_url(value):
    return value if urlparse(value).scheme=='https' else None
def normalize(raw):
    p=Product.model_validate(raw)
    return dict(id='channel3:'+p.id,provider_id=p.id,name=p.title,description=p.description,provenance='channel3',retrieved_at=time.time(),image=next((safe_url(i.url) for i in p.images if safe_url(i.url)),None),offers=[dict(retailer=o.domain,url=safe_url(o.url),price_cents=int(o.price.price*100),currency=o.price.currency,availability=o.availability,variant=None,checkout='retailer') for o in p.offers if safe_url(o.url)],attributes={},merchant_offer=None)
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
    try:return [normalize(p) for p in request('/v1/search',body)['products']]
    except (ValueError,KeyError) as exc:raise HTTPException(502,'Channel3 response did not match its documented schema') from exc
def product_details(id):
    return normalize(request('/v1/products/'+quote(id,safe='')))
