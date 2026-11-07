"""One scoped ADK seller agent. Its output is advice; merchant_rules owns quotes."""
import asyncio, json, os
from pydantic import BaseModel, Field
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.adk.agents.run_config import RunConfig
from google.genai import types
from .ai_config import configured_client

class OfferProposal(BaseModel):
    product_id: str
    price_cents: int = Field(gt=0, strict=True)
    explanation: str = Field(max_length=300)
    needs_review: bool = False

async def propose(merchant, opportunity, products, market):
    """Bounded model run with read-only scoped tools and a structured answer."""
    client=configured_client(); calls=0; tool_calls=0; audit=[]
    policy=merchant['policy']
    def tool(name, value):
        nonlocal tool_calls
        tool_calls+=1
        if tool_calls>7:raise ValueError('Merchant tool limit exceeded')
        audit.append(name)
        return value
    def get_merchant_policy()->dict:
        """Read this merchant's approved pricing and negotiation policy."""
        return tool('get_merchant_policy',policy)
    def get_eligible_products()->list[dict]:
        """Read only this merchant's connected and eligible product references."""
        return tool('get_eligible_products',products)
    def get_market_price_context()->list[dict]:
        """Read public observed Channel3 prices; these are not merchant costs."""
        return tool('get_market_price_context',market)
    def get_buyer_opportunity()->dict:
        """Read the consented minimal buyer demand, without chat or identities."""
        return tool('get_buyer_opportunity',opportunity)
    async def before_model(_context, request):
        nonlocal calls
        calls+=1
        if calls>3:raise ValueError('Merchant model call limit exceeded')
        content=json.dumps(request.model_dump(mode='json',exclude={'tools_dict'}),default=str)
        if len(content.encode())>40000:raise ValueError('Merchant model input too large')
        count=await asyncio.wait_for(asyncio.to_thread(client.models.count_tokens,model=os.environ['GEMINI_MODEL'],contents=request.contents),timeout=8)
        if count.total_tokens is None or count.total_tokens>8000:raise ValueError('Merchant model token limit exceeded')
    try:
        agent=Agent(name='merchant_sales_agent',model=Gemini(model=os.environ['GEMINI_MODEL'],client=client),
            instruction=('You represent exactly one opted-in sandbox merchant. Call the four read-only tools before proposing. '
            'Use only eligible product IDs and observed prices. Market prices are not merchant costs. '
            'For a multi-product request, price_cents is the combined total for every required product_id, and product_id is the first requested ID. '
            'Propose one fair offer in integer cents, considering a buyer counteroffer if present. Do not invent stock, authority or discounts. '
            'Flag any price outside approved automated limits for human review. Do not message buyers or take payments.'),
            tools=[get_merchant_policy,get_eligible_products,get_market_price_context,get_buyer_opportunity],
            output_schema=OfferProposal,before_model_callback=before_model,
            generate_content_config=types.GenerateContentConfig(max_output_tokens=700,temperature=0.2))
        runner=InMemoryRunner(agent=agent,app_name='shopside_merchant')
        session=await runner.session_service.create_session(app_name='shopside_merchant',user_id=merchant['id'])
        answer=[]
        async def run():
            async for event in runner.run_async(user_id=merchant['id'],session_id=session.id,
                new_message=types.Content(role='user',parts=[types.Part(text=json.dumps({'opportunity_id':opportunity['id'],'merchant_id':merchant['id']}))]),
                run_config=RunConfig(max_llm_calls=3)):
                if event.is_final_response() and event.content:
                    answer.extend(part.text for part in event.content.parts or [] if part.text and not part.thought)
        await asyncio.wait_for(run(),timeout=35)
        if not {'get_merchant_policy','get_eligible_products','get_market_price_context','get_buyer_opportunity'}.issubset(audit):
            raise ValueError('Merchant agent skipped required evidence')
        return OfferProposal.model_validate_json('\n'.join(answer)),{'model_calls':calls,'tools':audit,'outcome':'proposed'}
    finally:client.close()
