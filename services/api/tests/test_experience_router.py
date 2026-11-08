from app.experience_router import route_intent,spatial_eligible


def test_unified_category_routing_requires_explicit_studio():
    cases=[(['shirt','pants'],'STANDARD_COMMERCE',False),
           (['running shoes'],'STANDARD_COMMERCE',False),
           (['watch'],'STANDARD_COMMERCE',False),
           (['necklace','earrings'],'STANDARD_COMMERCE',False),
           (['gaming laptop','headphones'],'STANDARD_COMMERCE',False),
           (['desk','chair'],'SPATIAL_ELIGIBLE',True),
           (['shirt','desk'],'MIXED_COMMERCE',True)]
    for items,mode,eligible in cases:
        result=route_intent({'product_requirements':items},'Find '+', '.join(items))
        assert result['shopping_mode']==mode
        assert result['spatial_eligible'] is eligible
        assert result['studio_requested'] is False
    assert route_intent({'product_requirements':['desk']},'Place this desk in my room')['studio_requested'] is True
    assert route_intent({'product_requirements':['shirt']},'Place this shirt in my room')['studio_requested'] is False
    assert spatial_eligible({'category':'Furniture','name':'Accent chair'}) is True


def test_hard_constraints_require_verified_attributes():
    from app.smart_bundle import hard_constraints_match
    shoe={'variants':{'selected':[{'name':'US Size','label':'9'}]},'attributes':{'color':['black']}}
    assert hard_constraints_match('running shoes',shoe,{'size':'9','color':'black'})
    assert not hard_constraints_match('running shoes',shoe,{'size':'10'})
    assert not hard_constraints_match('running shoes',{'attributes':{}},{'size':'9'})
