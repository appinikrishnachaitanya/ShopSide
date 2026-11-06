import logging
logging.disable(logging.CRITICAL)
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as a,TestClient(app) as b:
 result=a.post('/api/rooms',json={'name':'Discovery verification'}).json();base='/api/rooms/'+result['room']['id']
 b.post('/api/join/'+result['invite'],json={'name':'Second viewer'})
 response=a.post(base+'/agent',json={'text':'Call discover_products once for over-ear headphones, max_price 150. Then call update_decision_board with the first two channel3: product IDs in those results. Do not use fictional products. Keep the final reply one short sentence.','revision':1})
 print('ADK discovery HTTP:',response.status_code)
 s=a.get(base).json();other=b.get(base).json()
 print('Tools:',[x['tool'] for x in s['activity']])
 print('Live products saved:',len(s.get('discovery',[])))
 print('Live board selection:',len(s['comparison']),all(x.startswith('channel3:') for x in s['comparison']))
 print('Second member synchronized:',s.get('discovery')==other.get('discovery') and s['comparison']==other['comparison'])
 if not response.is_success:print('API error:',response.json().get('detail'))
