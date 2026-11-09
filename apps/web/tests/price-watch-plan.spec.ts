import {test,expect} from '@playwright/test';

test('the plan shows this participant’s price alerts and payer controls',async({page})=>{
 const base=process.env.SHOPSIDE_TEST_URL||'http://localhost:3000';
 await page.routeWebSocket('**/api/rooms/*/live?*',socket=>{
  const server=socket.connectToServer();
  server.onMessage(message=>{
   if(typeof message!=='string'){socket.send(message);return;}
   const state=JSON.parse(message);
   state.price_watch_alerts=[
    {id:'own-alert',participant:'Alex',kind:'price',currency:'USD',price_cents:3900,message:'Your watched desk price changed.',observed_at:Date.now()/1000},
    {id:'other-alert',participant:'Jamie',kind:'price',currency:'USD',price_cents:2900,message:'Another shopper’s private watch.',observed_at:Date.now()/1000},
   ];
   state.deal_rescue_draft={source:'CHANNEL3_PRICE_WATCH',owned_alternative_category:'desk',disclosure:'Separate fictional merchant alternative.'};
   socket.send(JSON.stringify(state));
  });
 });
 await page.goto(base);
 await page.getByLabel('Your name').fill('Alex');
 await page.getByRole('button',{name:'Create your shopping room'}).click();
 await expect(page.getByText('Connected',{exact:true})).toBeVisible();
 await expect(page.getByLabel('Your room identity')).toHaveText('You’re Alex');
 await page.getByRole('button',{name:'View plan',exact:true}).click();
 await expect(page.getByText('Your watched desk price changed.',{exact:true})).toBeVisible();
 await expect(page.getByText('Another shopper’s private watch.',{exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Explore ShopSide-owned alternatives',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Remove draft',exact:true})).toBeVisible();
});
