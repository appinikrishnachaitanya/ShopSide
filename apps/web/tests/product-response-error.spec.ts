import {test,expect} from '@playwright/test';

test('product actions replace non-JSON server failures with a readable error',async({page})=>{
 const product={id:'channel3:desk-a',provider_id:'desk-a',name:'Saved Desk',provenance:'channel3',retrieved_at:1,attributes:{},offers:[{retailer:'shop.example',url:'https://shop.example/desk',currency:'USD',price_cents:9900}]};
 await page.routeWebSocket('**/api/rooms/*/live?*',socket=>{
  const server=socket.connectToServer();
  server.onMessage(message=>{
   if(typeof message!=='string'){socket.send(message);return;}
   const state=JSON.parse(message);state.discovery=[product];state.focus=product.id;
   socket.send(JSON.stringify(state));
  });
 });
 await page.route('**/api/rooms/*/discovery/desk-a',route=>route.fulfill({json:product}));
 await page.route('**/api/rooms/*/product/similar',route=>route.fulfill({status:502,contentType:'text/html',body:'<h1>Internal Server Error</h1>'}));
 await page.goto(process.env.SHOPSIDE_TEST_URL||'http://localhost:3000');
 await page.getByLabel('Your name').fill('Alex');
 await page.getByRole('button',{name:'Create your shopping room'}).click();
 await page.getByRole('button',{name:'View selected',exact:true}).click();
 await page.getByRole('button',{name:'Find similar products ↗',exact:true}).click();
 await expect(page.locator('.provider-details [role=alert]')).toContainText('Product options are temporarily unavailable. Please try again.');
 await expect(page.locator('.provider-details')).not.toContainText('Unexpected token');
});
