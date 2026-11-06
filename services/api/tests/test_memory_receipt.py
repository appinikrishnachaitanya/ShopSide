import json
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app

def test_memory_requires_two_approvals_and_verified_distinct_payments(monkeypatch):
    import app.main as main
    import app.memory_receipt as memory
    async def line(facts):return 'A choice made together.'
    monkeypatch.setattr(memory,'generate_memory_line',line)
    a,b,outsider=TestClient(app),TestClient(app),TestClient(app)
    created=a.post('/api/rooms',json={'name':'A','mode':'move_in'}).json();r=created['room']['id'];base='/api/rooms/'+r
    assert b.post('/api/join/'+created['invite'],json={'name':'B'}).status_code==200
    def command(client,kind,value,id):
        revision=client.get(base).json()['revision'];return client.post(base+'/commands',json={'kind':kind,'value':value,'revision':revision,'command_id':id})
    assert command(a,'placement_upsert',json.dumps({'product_id':'11','x':0,'z':0}),'place').status_code==200
    assert command(a,'marker_reaction',json.dumps({'product_id':'11','reaction':'love'}),'reaction').status_code==200
    def approve(client,id):
        revision=client.get(base).json()['revision'];return client.post(base+'/move-in/item',json={'product_id':'11','approve':True,'revision':revision,'command_id':id})
    assert approve(a,'a').status_code==200
    assert a.post(base+'/memory-receipts',json={'product_id':'11'}).status_code==409
    assert approve(b,'b').status_code==200
    item=a.get(base).json()['move_in']['items']['11'];committed=item['committed_at']
    assert datetime.fromisoformat(committed).tzinfo is not None
    assert outsider.get(base+'/memory-receipts/status').status_code==403
    assert outsider.post(base+'/memory-receipts',json={'product_id':'11'}).status_code==403
    def paid(payer,number,**overrides):
        p={'id':'payment'+str(number),'room':r,'payer':payer,'status':'paid','verification':'paypal_order_readback','verified_at':committed,'capture':'capture'+str(number),'provider_id':'order'+str(number),'currency':'USD','total':1000,'items':[{'product':'11'}]}
        p.update(overrides);main.payment_save(p)
    paid('A',1)
    assert a.post(base+'/memory-receipts',json={'product_id':'11'}).status_code==409
    paid('B',2,capture='capture1')
    assert a.post(base+'/memory-receipts',json={'product_id':'11'}).status_code==409
    paid('B',2)
    assert a.get(base+'/memory-receipts/status').json()['ready']==['11']
    response=a.post(base+'/memory-receipts',json={'product_id':'11'});assert response.status_code==200
    receipt=response.json();assert receipt['line']=='A choice made together.' and receipt['committed_at']==committed
    assert receipt['members'][0]['reaction']=='love' and receipt['members'][1]['reaction'] is None
    assert receipt['payments_verified']==2 and receipt['environment']=='sandbox'
    assert b.get(base).json()['memory_receipts']['11']==receipt
    assert command(b,'marker_reaction',json.dumps({'product_id':'11','reaction':'price'}),'later').status_code==200
    assert b.post(base+'/memory-receipts',json={'product_id':'11'}).json()==receipt

def test_legacy_approval_times_are_not_fabricated():
    from app.memory_receipt import eligible_memory
    state={'people':['A','B'],'move_in':{'items':{'11':{'name':'Lamp','approvals':{'A':True,'B':True}}}}}
    assert eligible_memory(state,'11',[]) is None
