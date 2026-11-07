import {test,expect} from '@playwright/test';

test('live ADK and Channel3 bundle can be shared, swapped, and approved',async({browser})=>{
 test.skip(process.env.SHOPSIDE_LIVE_BUNDLE!=='1','Requires live Gemini and Channel3 credentials');
 test.setTimeout(150000);
 const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';
 const a=await browser.newContext(),b=await browser.newContext();const first=await a.newPage(),second=await b.newPage();
 await first.goto(base);await first.getByLabel('Your name').fill('Alex');await first.getByLabel('What are you shopping for today?').fill('Desk and ergonomic chair under $1,200');await first.getByRole('button',{name:'Create your shopping room'}).click();
 const bundle=first.getByLabel('Smart Bundle');await expect(bundle).toBeVisible({timeout:60000});await bundle.getByRole('button',{name:'Find bundles'}).click();
 await expect(bundle.getByRole('button',{name:'Choose bundle'}).first()).toBeVisible({timeout:60000});await bundle.getByRole('button',{name:'Choose bundle'}).first().click();
 const id=new URL(first.url()).searchParams.get('room');const before=await(await first.request.get(base+'/api/rooms/'+id)).json();
 await second.goto(base+'?invite='+before.invite);await second.getByLabel('Your name').fill('Sam');await second.getByRole('button',{name:'Join your friend'}).click();
 const peer=second.getByLabel('Smart Bundle');await expect(peer.locator('.bundle-item')).toHaveCount(2);
 const state=await(await first.request.get(base+'/api/rooms/'+id)).json();const current=state.smart_bundle.selected.items[1];
 await peer.getByRole('button',{name:new RegExp('Swap.*'+current.requirement.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'i')}).click();
 const alternatives=await(await second.request.get(base+'/api/rooms/'+id+'/bundle/alternatives/'+current.slot_id)).json();
 const different=alternatives.alternatives.find((x:any)=>x.product.id!==current.product.id && x.new_total_cents<=state.smart_bundle.budget_cents);
 expect(different,'Live provider must return a different affordable alternative for this test').toBeTruthy();
 const row=peer.locator('.bundle-alternative').filter({hasText:different.product.name}).filter({hasText:different.offer.retailer}).first();await row.getByRole('button',{name:'Use this'}).click();
 await expect(first.locator('.bundle-item').filter({hasText:different.product.name})).toBeVisible();
 await bundle.getByRole('button',{name:'Approve bundle'}).click();await peer.getByRole('button',{name:'Approve bundle'}).click();await expect(bundle.getByText('Everyone approved this bundle')).toBeVisible();
 await bundle.getByRole('button',{name:'Save to shared plan'}).click();await first.getByRole('button',{name:'View plan'}).click();await expect(first.locator('.plan-saves').getByText('SAVED BUNDLE',{exact:true})).toBeVisible();
 await a.close();await b.close();
});
