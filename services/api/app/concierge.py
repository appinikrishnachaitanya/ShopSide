"""Channel3's native shopping conversation, authenticated only on the server."""
import json
import os
import re
import httpx
from channel3_sdk import AsyncChannel3
from channel3_sdk.types import UserMessage, UserMessagePartsItem_Text
from .discovery import normalize

_DIMENSION_CLAIM=re.compile(r'\b(?:dimensions?|width|height|depth|length|wide|tall|deep|long)\b',re.I)
_CAPACITY_CLAIM=re.compile(r'\b(?:weight|capacity|load)\b|\b(?:supports?|holds?)\b.{0,35}\b(?:up to|\d|lb|kg|pound)',re.I)
_UNKNOWN_SPEC=re.compile(r'\b(?:not (?:listed|provided|available|specified)|unknown|unavailable|could not verify)\b',re.I)
_NUMBER=re.compile(r'\d+(?:[.,]\d+)?')
_UNIT_PATTERNS=[
    (re.compile(r'\b(?:in|inch|inches)\b|[″"]',re.I),'in'),
    (re.compile(r'\b(?:cm|centimeter|centimeters)\b',re.I),'cm'),
    (re.compile(r'\b(?:mm|millimeter|millimeters)\b',re.I),'mm'),
    (re.compile(r'\b(?:ft|foot|feet)\b|[′]',re.I),'ft'),
    (re.compile(r'\b(?:kg|kilogram|kilograms)\b',re.I),'kg'),
    (re.compile(r'\b(?:lb|lbs|pound|pounds)\b',re.I),'lb'),
    (re.compile(r'\b(?:g|gram|grams)\b',re.I),'g'),
]

def measurement_units(value):
    text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,default=str)
    return {canonical for pattern,canonical in _UNIT_PATTERNS if pattern.search(text)}

def grounded_spec_text(text:str,products:list[dict])->str:
    """Drop numeric dimension/load claims unless matching structured evidence exists."""
    clean=[];removed=False
    for sentence in re.split(r'(?<=[.!?])\s+|\n+',text.strip()):
        if not sentence:continue
        if _UNKNOWN_SPEC.search(sentence) and not _NUMBER.search(sentence):
            clean.append(sentence);continue
        claim_type='dimensions' if _DIMENSION_CLAIM.search(sentence) else 'capacity' if _CAPACITY_CLAIM.search(sentence) else None
        if not claim_type:
            clean.append(sentence);continue
        numbers=set(_NUMBER.findall(sentence))
        if not numbers:
            clean.append(sentence);continue
        identified=[product for product in products if product.get('name') and
                    re.search(re.escape(product['name']),sentence,re.I)]
        if len(products)>1 and len(identified)!=1:
            removed=True;continue
        evidence_products=identified or products
        evidence=[]
        for product in evidence_products:
            if claim_type=='dimensions':
                evidence.extend(offer.get('dimensions') for offer in product.get('offers') or []
                                if offer.get('dimensions') is not None)
                evidence.append({key:value for key,value in (product.get('attributes') or {}).items()
                                 if re.search(r'dimension|width|height|depth|length',key,re.I)})
            else:
                evidence.append({key:value for key,value in (product.get('attributes') or {}).items()
                                 if re.search(r'weight|capacity|load|support',key,re.I)})
                evidence.extend(value for value in (product.get('key_features') or [])
                                if re.search(r'weight|capacity|load|support|hold',str(value),re.I))
                if re.search(r'weight|capacity|load|support|hold',product.get('description') or '',re.I):
                    evidence.append(product['description'])
        evidence_text=json.dumps(evidence,ensure_ascii=False,default=str)
        evidence_numbers=set(_NUMBER.findall(evidence_text))
        units=measurement_units(sentence)
        if numbers and numbers.issubset(evidence_numbers) and units.issubset(measurement_units(evidence_text)):clean.append(sentence)
        else:removed=True
    result=' '.join(clean).strip()
    if removed:
        note='I could not verify the dimensions or load details from the product data returned. Check the retailer listing before relying on those specifications.'
        result=(result+'\n\n' if result else '')+note
    return result

async def conversation_turn(message:str,conversation_id:str|None)->dict:
    key=os.getenv('CHANNEL3_API_KEY')
    if not key: raise RuntimeError('Channel3 is not configured')
    async with httpx.AsyncClient(timeout=45) as http:
        client=AsyncChannel3(api_key=key,timeout=45,max_retries=0,httpx_client=http)
        grounding_policy=(
            'ShopSide evidence policy: Use only product facts explicitly returned by catalog tools. '
            'For dimensions, weight limits, capacity, materials, compatibility, delivery, stock, and ratings, '
            'name the matching product and cite the exact returned value in plain language. '
            'If the evidence does not contain the requested attribute, say it is unknown or not provided; '
            'never infer, estimate, or borrow a fact from another product. Keep price comparisons tied to '
            'the returned offer and currency.\n\nShopper request: '
        )
        kwargs={'message':UserMessage(role='user',parts=[UserMessagePartsItem_Text(type='text',text=grounding_policy+message)])}
        if conversation_id: kwargs['conversation_id']=conversation_id
        turn=await client.conversations.create_turn(**kwargs)
    raw=turn.model_dump(mode='json',exclude_none=True)
    messages=[];products=[]
    for part in raw.get('message',{}).get('parts',[]):
        if part.get('type')=='text':messages.append(part.get('text',''))
        elif part.get('type')=='tool':
            output=part.get('output') or {}
            if isinstance(output,dict):
                for product in output.get('products',[]):
                    try:products.append(normalize(product))
                    except (ValueError,TypeError):continue
    text=grounded_spec_text('\n'.join(messages)[:5000],products)
    return {'conversation_id':raw['conversation_id'],'text':text,
            'suggestions':[str(x)[:200] for x in raw.get('message',{}).get('suggestions',[])[:6]],
            'products':products[:30]}
