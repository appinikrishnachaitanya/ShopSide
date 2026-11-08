"""Deterministic guard around AI shopping intent and optional spatial tools."""
import re

SPATIAL={'furniture','decor','lamp','desk','chair','table','sofa','couch','loveseat','bed','shelf','cabinet','dresser','rug','nightstand'}
STUDIO_REQUEST=re.compile(r'\b(?:move[- ]in studio|(?:place|position|arrange|visuali[sz]e|preview)\b.{0,40}\b(?:room|3d|space)|3d\b.{0,40}\b(?:room|preview))',re.I)

def spatial_eligible(value):
    if isinstance(value,dict):
        value=' '.join(str(value.get(key) or '') for key in ('category','name','title'))
    words=set(re.findall(r'[a-z]+',str(value).lower()))
    return bool(words & SPATIAL)

def route_intent(intent,request_text=''):
    """The shared commerce workspace is always the default, even for furniture."""
    items=intent.get('product_requirements') or []
    spatial=[item for item in items if spatial_eligible(item)]
    explicit=bool(STUDIO_REQUEST.search(request_text))
    mode='MIXED_COMMERCE' if spatial and len(spatial)<len(items) else 'SPATIAL_ELIGIBLE' if spatial else 'STANDARD_COMMERCE'
    return {'shopping_mode':mode,'spatial_eligible':bool(spatial),'studio_requested':explicit and bool(spatial),
            'spatial_items':spatial,'hard_constraints':intent.get('hard_constraints') or {},
            'preferences':intent.get('preferences') or {}}
