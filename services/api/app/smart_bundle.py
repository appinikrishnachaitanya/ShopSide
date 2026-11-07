"""Bounded, evidence-based bundle generation and server-side mutations."""
import hashlib
import itertools
import json
import re
from urllib.parse import urlparse

MAX_CATEGORIES = 4
MAX_PRODUCTS = 6
MAX_OFFERS = 3


def stable_id(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:24]


def category_matches(requirement, product):
    """Conservative title/structured-category check; do not use description alone."""
    words = re.findall(r'[a-z0-9]+', requirement.lower())
    stop = {'a','an','the','for','with','and','or','small','compact','ergonomic','modern','gaming','wooden','office','bedroom'}
    meaningful = [w for w in words if w not in stop]
    if not meaningful:
        return False
    known={'sofa','couch','loveseat','chair','desk','table','bed','lamp','keyboard','mouse','mice','monitor'}
    nouns=[w.rstrip('s') for w in meaningful if w.rstrip('s') in known]
    head = nouns[-1] if nouns else meaningful[-1].rstrip('s')
    synonyms = {'sofa': ['sofa','couch','loveseat'], 'couch': ['sofa','couch','loveseat'],
                'chair': ['chair'], 'desk': ['desk'], 'table': ['table'],
                'bed': ['bed'], 'lamp': ['lamp'], 'keyboard': ['keyboard'], 'mouse': ['mouse','mice']}
    allowed = synonyms.get(head, [head])
    name = str(product.get('name') or '').lower()
    category = str(product.get('category') or '').lower()
    if head in ('sofa','couch') and re.search(r'\b(?:end|side|coffee|console|sofa)\s+tables?\b|\bnightstands?\b',name):
        return False
    return any(re.search(r'\b'+re.escape(term)+r's?\b',name+' '+category) for term in allowed)


def normalized_candidates(requirements, batches, currency):
    slots=[]
    for index,(requirement,products) in enumerate(zip(requirements,batches)):
        options=[]
        for product in products:
            if len(options)>=MAX_PRODUCTS:break
            if not str(product.get('id','')).startswith('channel3:') or not category_matches(requirement,product):continue
            offers=[]
            for offer in product.get('offers') or []:
                url=offer.get('url')
                try: parsed=urlparse(url) if isinstance(url,str) else None
                except ValueError: continue
                price=offer.get('price_cents'); availability=offer.get('availability')
                try:
                    if not parsed or parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:continue
                except ValueError: continue
                if type(price) is not int or price<0 or offer.get('currency')!=currency:continue
                if str(availability or '').lower() in ('outofstock','out_of_stock','out of stock'):continue
                retailer=str(offer.get('retailer') or '').strip().lower().rstrip('.')
                if retailer.startswith('www.'):retailer=retailer[4:]
                if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+',retailer):continue
                entry={'id':stable_id([product['id'],url,retailer,price,currency]),'url':url,'retailer':retailer,
                       'price_cents':price,'currency':currency,'availability':availability or 'Unknown',
                       'delivery':offer.get('delivery'),'dimensions':offer.get('dimensions'),'condition':offer.get('condition')}
                offers.append(entry)
            offers=sorted({o['id']:o for o in offers}.values(),key=lambda o:o['price_cents'])[:MAX_OFFERS]
            if offers:
                options.append({'id':product['id'],'name':product.get('name') or 'Product','image':product.get('image'),
                                'retrieved_at':product.get('retrieved_at'),'features':(product.get('key_features') or [])[:5],
                                'description_summary':str(product.get('description') or '')[:180],
                                'attributes':product.get('attributes') or {},'offers':offers})
        slots.append({'id':str(index),'requirement':requirement,'products':options})
    return slots


def match_score(requirement, product, preferences):
    fields=' '.join([product['name'],*map(str,product.get('features') or []),json.dumps(product.get('attributes') or {},sort_keys=True)]).lower()
    terms=set(re.findall(r'[a-z0-9]+', ' '.join([requirement,*preferences]).lower()))
    terms={x for x in terms if len(x)>3 and x not in {'with','that','under','have','need','room'}}
    return sum(1 for x in terms if re.search(r'\b'+re.escape(x)+r'\b',fields))


def make_bundle(items, kind, budget, currency, goal, preferences=None):
    preferences=[p for p in (preferences or []) if isinstance(p,str) and p.strip()]
    items=[dict(item) for item in items]
    for item in items:
        product=item['product']
        facts=' '.join([product['name'],*map(str,product.get('features') or []),json.dumps(product.get('attributes') or {},sort_keys=True)]).lower()
        supported=[p for p in preferences if p.lower() in facts]
        item['match_explanation']='Product title or category matches the requested type.' + ((' Observed: '+', '.join(supported)+'.') if supported else '')
        item['unverified_constraints']=[p for p in preferences if p not in supported]
    subtotal=sum(item['offer']['price_cents'] for item in items)
    identity=[[item['slot_id'],item['product']['id'],item['offer']['id']] for item in items]
    return {'id':stable_id(identity),'kind':kind,'version':1,'goal':goal,'currency':currency,'budget_cents':budget,
            'subtotal_cents':subtotal,'total_cents':subtotal,'remaining_cents':budget-subtotal,
            'items':items,'products':[item['product']['id'] for item in items],'preferences':preferences,
            'caveat':'Observed product prices only; shipping, tax, availability and compatibility must be verified with retailers.'}


def build_bundles(slots, budget, currency, goal, preferences=None):
    preferences=preferences or []
    if not (2<=len(slots)<=MAX_CATEGORIES) or type(budget) is not int or budget<0 or not currency:return [],False
    if any(not slot['products'] for slot in slots):return [],False
    choices=[]
    for slot in slots:
        choices.append([{'slot_id':slot['id'],'requirement':slot['requirement'],'product':p,'offer':o,
                         'match_score':match_score(slot['requirement'],p,preferences)}
                        for p in slot['products'] for o in p['offers']])
    valid=[]
    for items in itertools.product(*choices):
        if len({item['product']['id'] for item in items}) != len(items):continue
        total=sum(item['offer']['price_cents'] for item in items)
        if total<=budget:valid.append((items,total,sum(x['match_score'] for x in items)))
    if not valid:return [],False
    budget_choice=min(valid,key=lambda v:(v[1],-v[2]))
    match_choice=min(valid,key=lambda v:(-v[2],v[1]))
    one_seller=[v for v in valid if len({x['offer']['retailer'] for x in v[0]})==1]
    winners=[('best_match',match_choice),('budget_saver',budget_choice)]
    if one_seller:winners.append(('one_seller',min(one_seller,key=lambda v:(v[1],-v[2]))))
    result=[];seen={}
    for kind,(items,_,_) in winners:
        bundle=make_bundle(list(items),kind,budget,currency,goal,preferences)
        if bundle['id'] in seen:
            seen[bundle['id']].setdefault('also_qualifies',[]).append(kind)
            continue
        seen[bundle['id']]=bundle;result.append(bundle)
    return result,bool(one_seller)


def item_for(slots, slot_id, product_id, offer_id):
    slot=next((s for s in slots if s['id']==slot_id),None)
    if not slot:return None
    product=next((p for p in slot['products'] if p['id']==product_id),None)
    if not product:return None
    offer=next((o for o in product['offers'] if o['id']==offer_id),None)
    return {'slot_id':slot_id,'requirement':slot['requirement'],'product':product,'offer':offer} if offer else None
