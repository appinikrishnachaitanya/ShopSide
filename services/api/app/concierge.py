"""Channel3's native shopping conversation, authenticated only on the server."""
import os
import httpx
from channel3_sdk import AsyncChannel3
from channel3_sdk.types import UserMessage, UserMessagePartsItem_Text
from .discovery import normalize

async def conversation_turn(message:str,conversation_id:str|None)->dict:
    key=os.getenv('CHANNEL3_API_KEY')
    if not key: raise RuntimeError('Channel3 is not configured')
    async with httpx.AsyncClient(timeout=45) as http:
        client=AsyncChannel3(api_key=key,timeout=45,max_retries=0,httpx_client=http)
        kwargs={'message':UserMessage(role='user',parts=[UserMessagePartsItem_Text(type='text',text=message)])}
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
    return {'conversation_id':raw['conversation_id'],'text':'\n'.join(messages)[:5000],
            'suggestions':[str(x)[:200] for x in raw.get('message',{}).get('suggestions',[])[:6]],
            'products':products[:30]}
