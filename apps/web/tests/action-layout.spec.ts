import {test,expect} from '@playwright/test';

const item=(id:string,name:string,image=true)=>({slot_id:id,requirement:id,product:{id:`channel3:${id}`,name,...(image?{image:'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="120" height="80" fill="tan"/></svg>'}:{}),brand:'Example'},offer:{id,retailer:'retailer.example',price_cents:7500,availability:'InStock'},match_explanation:'Observed retailer listing'});
const options=[{id:'a',kind:'best_match',items:[item('desk','A compact writing desk'),item('chair','Ergonomic chair')],subtotal_cents:15000,remaining_cents:35000,currency:'USD',budget_cents:50000,evidence_confidence:'medium'}, {id:'b',kind:'budget_saver',items:[item('desk2','Extra long product name with adjustable height, compact footprint, drawers and oak finish',false),item('chair2','Chair with lumbar support and adjustable arms')],subtotal_cents:14000,remaining_cents:36000,currency:'USD',budget_cents:50000,evidence_confidence:'high',ai_confidence_score:75}];
const room={id:'layout-room',title:'Our shopping room',revision:1,people:['Alex','Jamie'],payer:'Alex',budget:50000,shortlist:[],discovery:[],messages:[],cart:[],external_cart:[],reactions:{},preferences:{},shopping_intent:{shopping_goal:'Desk and chair',product_requirements:['desk','chair'],bundle_requested:true,currency:'USD',budget_cents:50000},smart_bundle:{version:1,options,selected:options[0],saved:options[0],approvals:{},one_seller_available:false}};

for(const width of [1440,768,390])test(`bundle cards and actions align at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:1000});
 await page.route('**/api/**',route=>{
  const url=new URL(route.request().url());
  if(url.pathname==='/api/catalog')return route.fulfill({json:[]});
  if(url.pathname.endsWith('/me'))return route.fulfill({json:{name:'Alex',is_payer:true}});
  return route.fulfill({json:room});
 });
 await page.routeWebSocket('**/api/rooms/*/live?*',socket=>socket.send(JSON.stringify(room)));
 await page.goto((process.env.SHOPSIDE_TEST_URL||'http://localhost:3000')+'?room=layout-room');
 const bundle=page.getByLabel('Smart Bundle',{exact:true});await expect(bundle).toBeVisible();
 const cards=bundle.locator('.bundle-card');await expect(cards).toHaveCount(2);
 const boxes=await cards.evaluateAll(els=>els.map(e=>{const r=e.getBoundingClientRect();const a=e.querySelector('.bundle-choose')!.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,actionY:a.y,actionHeight:a.height}}));
 if(Math.abs(boxes[0].y-boxes[1].y)<2){expect(Math.abs(boxes[0].height-boxes[1].height)).toBeLessThan(2);expect(Math.abs(boxes[0].actionY-boxes[1].actionY)).toBeLessThan(2);}
 for(const box of boxes){expect(box.x).toBeGreaterThanOrEqual(0);expect(box.x+box.width).toBeLessThanOrEqual(width+1);expect(box.actionHeight).toBeGreaterThanOrEqual(44);}
 const images=await bundle.locator('.bundle-product-image').evaluateAll(es=>es.map(e=>e.getBoundingClientRect().height));expect(new Set(images).size).toBe(1);
 const save=bundle.getByRole('button',{name:'Save to shared plan',exact:true});await expect(save).toHaveCSS('background-color','rgb(187, 167, 255)');

 // Verify rendered contrast for both primary actions and secondary captions.
 const contrast=await bundle.locator('.bundle-choose, .bundle-card-summary > small').evaluateAll(elements=>{
  const rgb=(value:string)=>value.match(/[\d.]+/g)!.slice(0,3).map(Number);
  const luminance=(values:number[])=>values.map(v=>{const s=v/255;return s<=.04045?s/12.92:((s+.055)/1.055)**2.4}).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
  return elements.map(el=>{
   const fg=rgb(getComputedStyle(el).color);let parent:Element|null=el,bg='';
   while(parent){bg=getComputedStyle(parent).backgroundColor;if(bg!=='rgba(0, 0, 0, 0)'&&bg!=='transparent')break;parent=parent.parentElement;}
   const a=luminance(fg),b=luminance(rgb(bg));return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
  });
 });
 for(const ratio of contrast)expect(ratio).toBeGreaterThanOrEqual(4.5);
 await bundle.screenshot({path:`/tmp/shopside-bundles-${width}.png`});
 await page.getByRole('button',{name:'View plan',exact:true}).click();
 const plan=page.getByLabel('Shopping plan',{exact:true});await expect(plan).toBeVisible();
 const links=plan.locator('.plan-saves > section > button');await expect(links).toHaveCount(2);
 for(const button of await links.all()){await expect(button).not.toHaveCSS('background-color','rgb(239, 239, 239)');}
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);expect(overflow).toBe(false);
 await page.screenshot({path:`/tmp/shopside-layout-${width}.png`,fullPage:true});
});
