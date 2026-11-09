import {test,expect} from '@playwright/test';

const item=(id:string,name:string,image=true)=>({slot_id:id,requirement:id,product:{id:`channel3:${id}`,name,...(image?{image:'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="120" height="80" fill="tan"/></svg>'}:{}),brand:'Example'},offer:{id,retailer:'retailer.example',price_cents:7500,availability:'InStock'},match_explanation:'Observed retailer listing'});
const options=[{id:'a',kind:'best_match',items:[item('desk','A compact writing desk'),item('chair','Ergonomic chair')],subtotal_cents:15000,remaining_cents:35000,currency:'USD',budget_cents:50000,evidence_confidence:'medium'}, {id:'b',kind:'budget_saver',items:[item('desk2','Extra long product name with adjustable height, compact footprint, drawers and oak finish',false),item('chair2','Chair with lumbar support and adjustable arms')],subtotal_cents:14000,remaining_cents:36000,currency:'USD',budget_cents:50000,evidence_confidence:'high',ai_confidence_score:75}];
const room={id:'layout-room',title:'Our shopping room',revision:1,people:['Alex','Jamie'],payer:'Alex',budget:50000,shortlist:[],discovery:[],messages:[],cart:[],external_cart:[],reactions:{},preferences:{},shopping_intent:{shopping_goal:'Desk and chair',product_requirements:['desk','chair'],bundle_requested:true,currency:'USD',budget_cents:50000},smart_bundle:{version:1,options,selected:options[0],saved:options[0],approvals:{},one_seller_available:false}};

for (const width of [320,390,768,844]) test(`mobile workspace flows at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:width===844?390:740});
 await page.route('**/api/**',route=>{const path=new URL(route.request().url()).pathname;return route.fulfill({json:path==='/api/catalog'?[]:path.endsWith('/me')?{name:'Alex',is_payer:true}:room});});
 await page.routeWebSocket('**/api/rooms/*/live?*',socket=>socket.send(JSON.stringify(room)));
 await page.goto((process.env.SHOPSIDE_TEST_URL||'http://localhost:3000')+'?room=layout-room');
 await expect(page.getByLabel('Smart Bundle',{exact:true})).toBeVisible();
 await page.locator('.filter-details').first().locator('summary').click();
 const outliers=await page.locator('.filter-details[open] input,.filter-details[open] select,.filter-details[open] button').evaluateAll(es=>es.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.x<0||r.right>innerWidth+1)}).map(e=>e.outerHTML));expect(outliers).toEqual([]);
 await page.getByRole('button',{name:'View plan',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Our plan',exact:true});await expect(dialog).toBeVisible();
 await dialog.getByLabel('Your shopping preference').fill('Comfort for long calls');
 await expect(dialog.getByRole('button',{name:'Save preference'})).toBeVisible();
 await dialog.getByRole('button',{name:'Close Our plan',exact:true}).click();
 await page.getByRole('button',{name:/Cart & checkout/}).first().click();
 const close=page.getByRole('button',{name:'Close cart and checkout',exact:true});await expect(close).toBeVisible();
 const cart=page.locator('.cart-details[open]');const rect=await cart.boundingBox();expect(rect!.x).toBeGreaterThanOrEqual(0);expect(rect!.width).toBeLessThanOrEqual(width);await cart.locator(':scope > summary').click();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(width+1);
 if(width<=640){const size=await page.getByLabel('Live product search').evaluate(e=>parseFloat(getComputedStyle(e).fontSize));expect(size).toBeGreaterThanOrEqual(16);}
 await page.screenshot({path:`/tmp/shopside-mobile-${width}.png`,fullPage:true});
});

test('mobile onboarding and merchant entry stay within the viewport',async({page})=>{
 await page.setViewportSize({width:320,height:740});
 await page.route('**/api/catalog',r=>r.fulfill({json:[]}));
 await page.goto(process.env.SHOPSIDE_TEST_URL||'http://localhost:3000');
 await page.getByLabel('Your name').fill('Alex');
 await page.getByRole('button',{name:'Create your shopping room'}).scrollIntoViewIfNeeded();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(321);
 await page.goto((process.env.SHOPSIDE_TEST_URL||'http://localhost:3000')+'/merchant');
 await expect(page.getByPlaceholder('Paste your sandbox merchant token')).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(321);
});
