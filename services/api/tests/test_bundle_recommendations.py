import time
import pytest
from pydantic import ValidationError
from app.bundle_recommendations import BundleRecommendations, evidence_level, validate_recommendations
from app.smart_bundle import normalized_candidates,build_bundles
from app.discovery import Channel3Budget


def sample(name,price,retailer='store.example',availability='InStock'):
    return {'id':'channel3:'+name,'name':name,'retrieved_at':time.time(),'attributes':{'material':'wood'},'offers':[{'url':'https://'+retailer+'/'+name,'retailer':retailer,'price_cents':price,'currency':'USD','availability':availability}]}

def fixtures():
    slots=normalized_candidates(['desk','chair'],[[sample('desk',10000)],[sample('chair',12000)]],'USD')
    options,_=build_bundles(slots,30000,'USD','workspace')
    choices=[{'slot_id':s['id'],'product_id':s['products'][0]['id'],'offer_id':s['products'][0]['offers'][0]['id']} for s in slots]
    return slots,options,choices

def proposal(choices,**changes):
    data={'rank':1,'label':'best_match','choices':choices,'fit_score':85,'ai_confidence_score':60,'score_breakdown':{'fit':85},'reason':'Unverified shipping promise','tradeoffs':[],'uncertainties':[]}
    return {**data,**changes}

def test_model_proposal_is_validated_and_total_is_server_calculated():
    slots,fallback,choices=fixtures();schema=BundleRecommendations(recommendations=[proposal(choices)])
    results,failures=validate_recommendations(schema,slots,30000,'USD','workspace',[],fallback,time.time())
    assert not failures and results[0]['subtotal_cents']==22000
    assert results[0]['fit_score']==85 and results[0]['evidence_confidence'] in ('MEDIUM','HIGH')
    assert 'Unverified shipping promise' not in str(results)
    assert 'shipping' in results[0]['caveat'].lower()


def test_unverified_apparel_variant_hides_numeric_ai_match():
    slots,fallback,choices=fixtures()
    proposals=BundleRecommendations(recommendations=[proposal(choices,fit_score=92)])
    results,_=validate_recommendations(proposals,slots,30000,'USD','workspace',['size M'],fallback,time.time())
    assert results[0]['variant_status']=='unverified'
    assert results[0]['fit_score'] is None
    assert results[0]['ai_confidence_score'] is None

@pytest.mark.parametrize('change',[
    {'fit_score':101},{'ai_confidence_score':-1},{'score_breakdown':{'fit':101}},{'price_cents':1},
])
def test_invalid_scores_or_model_supplied_prices_are_rejected(change):
    _,_,choices=fixtures()
    with pytest.raises(ValidationError):BundleRecommendations(recommendations=[proposal(choices,**change)])

def test_invalid_ids_duplicates_and_over_budget_are_rejected():
    slots,fallback,choices=fixtures()
    invalid=[{**choices[0],'product_id':'channel3:made-up'},choices[1]]
    results,errors=validate_recommendations(BundleRecommendations(recommendations=[proposal(invalid)]),slots,30000,'USD','',[],fallback,time.time())
    assert not results and errors
    duplicate=[choices[0],choices[0]]
    results,errors=validate_recommendations(BundleRecommendations(recommendations=[proposal(duplicate)]),slots,30000,'USD','',[],fallback,time.time())
    assert not results and errors
    results,errors=validate_recommendations(BundleRecommendations(recommendations=[proposal(choices)]),slots,20000,'USD','',[],fallback,time.time())
    assert not results and errors==['Over budget']

def test_evidence_level_is_not_model_confidence():
    slots,_,choices=fixtures();from app.smart_bundle import item_for
    items=[item_for(slots,x['slot_id'],x['product_id'],x['offer_id']) for x in choices]
    assert evidence_level(items,time.time())=='MEDIUM'
    for item in items:item['offer']['delivery']='Delivery details provided'
    assert evidence_level(items,time.time())=='HIGH'
    for item in items:
        item['product']['attributes']={};item['product']['retrieved_at']=0;item['offer']['availability']='Unknown';item['offer']['delivery']=None
    assert evidence_level(items,time.time())=='LOW'

def test_http_attempt_limit_counts_retries():
    budget=Channel3Budget(2);budget.claim();budget.claim()
    with pytest.raises(Exception):budget.claim()
    assert budget.count==2

def test_model_input_guardrail_rejects_unknown_and_excessive_counts():
    from app.smart_bundle_agent import enforce_input_limits
    enforce_input_limits(1000,16000)
    for byte_count,tokens in [(1000,None),(1000,16001),(80001,10)]:
        with pytest.raises(ValueError):enforce_input_limits(byte_count,tokens)

def test_input_size_guard_handles_pydantic_response_schema():
    from google.adk.models import LlmRequest
    from google.genai import types
    from app.shopping_intent import ShoppingIntent
    from app.smart_bundle_agent import serialized_model_input_size
    request=LlmRequest(config=types.GenerateContentConfig(response_schema=ShoppingIntent))
    assert serialized_model_input_size(request)>0

def test_unverified_one_seller_claim_is_rejected():
    slots=normalized_candidates(['desk','chair'],[[sample('desk',10000,'a.example')],[sample('chair',12000,'b.example')]],'USD')
    fallback,_=build_bundles(slots,30000,'USD','workspace')
    choices=[{'slot_id':s['id'],'product_id':s['products'][0]['id'],'offer_id':s['products'][0]['offers'][0]['id']} for s in slots]
    schema=BundleRecommendations(recommendations=[proposal(choices,label='one_seller')])
    result,errors=validate_recommendations(schema,slots,30000,'USD','workspace',[],fallback,time.time())
    assert result==[] and errors==['Retailers do not match']
