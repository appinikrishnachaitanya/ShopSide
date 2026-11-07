"""Validate untrusted model proposals against server-owned retailer offers."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from .smart_bundle import item_for, make_bundle

class BundleChoice(BaseModel):
    model_config=ConfigDict(extra='forbid')
    slot_id:str=Field(max_length=10)
    product_id:str=Field(max_length=200)
    offer_id:str=Field(max_length=100)

class BundleRecommendation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    rank:int=Field(ge=1,le=3,strict=True)
    label:Literal['best_match','budget_saver','one_seller']
    choices:list[BundleChoice]=Field(min_length=2,max_length=4)
    fit_score:int=Field(ge=0,le=100,strict=True)
    ai_confidence_score:int=Field(ge=0,le=100,strict=True)
    score_breakdown:dict[str,Annotated[int,Field(ge=0,le=100,strict=True)]]=Field(default_factory=dict,max_length=8)
    reason:str=Field(default='',max_length=500)
    tradeoffs:list[str]=Field(default_factory=list,max_length=5)
    uncertainties:list[str]=Field(default_factory=list,max_length=5)

class BundleRecommendations(BaseModel):
    model_config=ConfigDict(extra='forbid')
    recommendations:list[BundleRecommendation]=Field(default_factory=list,max_length=3)
    search_summary:str=Field(default='',max_length=500)
    limitations:list[str]=Field(default_factory=list,max_length=5)


def evidence_level(items,now):
    """Conservative completeness indicator; not a calibrated probability."""
    if not items:return 'LOW'
    scores=[]
    for item in items:
        product=item['product'];offer=item['offer'];stamp=product.get('retrieved_at')
        points=2 # validated price/currency and retailer identity
        points+=bool(offer.get('availability') and offer['availability'].lower()!='unknown')
        points+=bool(product.get('attributes') or product.get('features') or offer.get('dimensions'))
        points+=bool(isinstance(stamp,(int,float)) and 0<=now-stamp<=86400)
        points+=bool(offer.get('delivery'))
        scores.append(points)
    minimum=min(scores)
    # Unknown delivery is material even when other fields are complete.
    delivery_known=all(bool(item['offer'].get('delivery')) for item in items)
    return 'HIGH' if minimum>=5 and delivery_known else 'MEDIUM' if minimum>=3 else 'LOW'


def validate_recommendations(proposals,slots,budget,currency,goal,preferences,fallback,now):
    """Return validated proposals and rejection reasons; prices never come from AI."""
    valid=[];failures=[];ranks=set();labels=set();seen=set()
    best_price=min((b['subtotal_cents'] for b in fallback),default=None)
    for proposal in proposals.recommendations:
        if proposal.rank in ranks or proposal.label in labels:
            failures.append('Duplicate rank or label');continue
        ranks.add(proposal.rank);labels.add(proposal.label)
        items=[item_for(slots,c.slot_id,c.product_id,c.offer_id) for c in proposal.choices]
        if any(item is None for item in items) or {i['slot_id'] for i in items}!={s['id'] for s in slots} or len(items)!=len(slots) or len({i['product']['id'] for i in items})!=len(items):
            failures.append('Unknown product, offer or category coverage');continue
        bundle=make_bundle(items,proposal.label,budget,currency,goal,preferences)
        if bundle['subtotal_cents']>budget:
            failures.append('Over budget');continue
        if proposal.label=='one_seller' and len({i['offer']['retailer'] for i in items})!=1:
            failures.append('Retailers do not match');continue
        if proposal.label=='budget_saver' and bundle['subtotal_cents']!=best_price:
            failures.append('Budget saver is not the lowest observed subtotal');continue
        if bundle['id'] in seen:
            failures.append('Duplicate combination');continue
        seen.add(bundle['id'])
        # Free-form claims cannot safely be verified by token overlap. Show only
        # independently derived facts and keep the numeric model assessment.
        bundle.update(rank=proposal.rank,fit_score=proposal.fit_score,ai_confidence_score=proposal.ai_confidence_score,
                      evidence_confidence=evidence_level(items,now),score_breakdown=proposal.score_breakdown)
        valid.append(bundle)
    return sorted(valid,key=lambda b:b['rank']),failures
