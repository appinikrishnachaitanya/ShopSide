import {test,expect} from '@playwright/test';
test('stale shortlist save retries once with the same command ID',async({page})=>{
 const product={id:'channel3:qa',name:'QA desk',provider_id:'qa',offers:[{retailer:'example.com',currency:'USD',price_cents:10000}]};
 const room:any={id:'qa',revision:1,title:'QA',people:['Alex','Jamie'],payer:'Alex',budget:50000,shortlist:[],discovery:[product],messages:[],cart:[],external_cart:[],reactions:{},preferences:{}};
 const ids:string[]=[];let conflict=true;
 await page.route('**/api/**',route=>{
  const path=new URL(route.request().url()).pathname;
  if(path==='/api/catalog')return route.fulfill({json:[]});
  if(path.endsWith('/me'))return route.fulfill({json:{name:'Alex',is_payer:true}});
  if(path.endsWith('/commands')){
   const body=route.request().postDataJSON();ids.push(body.command_id);
   if(conflict){conflict=false;room.revision++;return route.fulfill({status:409,json:{detail:'Room changed'}});}
   expect(body.revision).toBe(room.revision);room.shortlist.push(body.value);room.revision++;
  }
  return route.fulfill({json:room});
 });
 await page.routeWebSocket('**/api/rooms/*/live?*',s=>s.send(JSON.stringify(room)));
 await page.goto((process.env.SHOPSIDE_TEST_URL||'http://localhost:3000')+'?room=qa');
 await page.locator('.live-product').first().getByRole('button',{name:'Save',exact:true}).click();
 await expect(page.getByText(/1 shortlisted product/).first()).toBeVisible();
 expect(ids).toHaveLength(2);expect(ids[0]).toBe(ids[1]);
});
