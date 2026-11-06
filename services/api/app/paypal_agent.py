"""Official PayPal MCP stdio adapter, restricted to reading the bound order."""
import os,json
from pathlib import Path
import httpx
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
SERVER=Path(__file__).resolve().parents[2]/'paypal-mcp/node_modules/@paypal/mcp/dist/index.js'
async def inspect_order(order_id=None):
    if os.getenv('PAYPAL_ENV','sandbox')!='sandbox': raise ValueError('Sandbox required')
    async with httpx.AsyncClient(timeout=20) as client:
        response=await client.post('https://api-m.sandbox.paypal.com/v1/oauth2/token',auth=(os.environ['PAYPAL_CLIENT_ID'],os.environ['PAYPAL_CLIENT_SECRET']),data={'grant_type':'client_credentials'})
        response.raise_for_status(); token=response.json()['access_token']
    child_env={k:os.environ[k] for k in ['PATH','HTTPS_PROXY','HTTP_PROXY','NO_PROXY','NODE_EXTRA_CA_CERTS','SSL_CERT_FILE'] if k in os.environ}
    child_env.update(PAYPAL_ACCESS_TOKEN=token,PAYPAL_ENVIRONMENT='SANDBOX')
    params=StdioServerParameters(command='node',args=[str(SERVER),'--tools=orders.get','--paypal-environment=SANDBOX'],env=child_env)
    with open(os.devnull,'w') as errors:
        async with stdio_client(params,errlog=errors) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize(); listing=await session.list_tools()
                tools=[t.name for t in listing.tools]
                if not order_id:return {'transport':'stdio','tools':tools,'sandbox':True}
                tool=next(t for t in listing.tools if t.name=='get_order')
                result=await session.call_tool(tool.name,{'id':order_id})
                if result.is_error: return {'error':'PayPal MCP order read failed'}
                # Never return raw payment/customer data to the model or shared room.
                for block in result.content:
                    if getattr(block,'type',None)=='text':
                        try:
                            data=json.loads(block.text)
                            status=data.get('status')
                            if not isinstance(status,str) or status not in ['CREATED','SAVED','APPROVED','VOIDED','COMPLETED','PAYER_ACTION_REQUIRED']: return {'error':'PayPal MCP provider request failed','source':'PayPal MCP'}
                            return {'status':status,'source':'PayPal MCP'}
                        except (ValueError,AttributeError):continue
                return {'status':'unknown','source':'PayPal MCP'}
