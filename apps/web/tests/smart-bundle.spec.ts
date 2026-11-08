import {test,expect} from '@playwright/test';

// Runs against the dedicated test API with mocked Gemini and Channel3.
test('two shoppers select, swap, save and approve the same bundle',async({browser})=>{
 test.skip(process.env.SHOPSIDE_FIXTURE_API !== 'true','Requires the deterministic Gemini and Channel3 fixture API');
 const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';
 const a=await browser.newContext(),b=await browser.newContext();const first=await a.newPage(),second=await b.newPage();
 await first.goto(base);await first.getByLabel('Your name').fill('Alex');await first.getByLabel('What are you shopping for today?').fill('Desk and ergonomic chair under $300');await first.getByRole('button',{name:'Create your shopping room'}).click();
 const bundle=first.getByLabel('Smart Bundle');await expect(bundle).toBeVisible();await bundle.getByRole('button',{name:'Find bundles'}).click();
 await expect(bundle.getByRole('button',{name:'Choose bundle'}).first()).toBeVisible();await bundle.getByRole('button',{name:'Choose bundle'}).first().click();
 await expect(bundle.getByText('Waiting for everyone’s approval')).toHaveCount(0);await expect(bundle.getByText('Invite someone to decide together')).toBeVisible();
 const id=new URL(first.url()).searchParams.get('room');const state=await(await first.request.get(base+'/api/rooms/'+id)).json();
 await second.goto(base+'?invite='+state.invite);await second.getByLabel('Your name').fill('Sam');await second.getByRole('button',{name:'Join your friend'}).click();
 const other=second.getByLabel('Smart Bundle');await expect(other.getByText('Waiting for everyone’s approval')).toBeVisible();
 await bundle.getByRole('button',{name:'Approve bundle'}).click();await other.getByRole('button',{name:'Approve bundle'}).click();
 await expect(bundle.getByText('Everyone approved this bundle')).toBeVisible();
 await bundle.getByRole('button',{name:'Save to shared plan'}).click();
 await expect(first.getByText('1 saved bundle')).toBeVisible();
 await bundle.getByRole('button',{name:/Swap.*chair/}).click();
 await bundle.getByRole('button',{name:'Find more alternatives with AI'}).click();
 await expect(bundle.locator('.bundle-alternative').filter({hasText:'New chair'})).toBeVisible();
 const alternative=bundle.locator('.bundle-alternative').filter({hasText:'Comfy chair'});await alternative.getByRole('button',{name:'Use this'}).click();
 await expect(other.locator('.bundle-item').filter({hasText:'Comfy chair'})).toBeVisible();await expect(other.getByText('Waiting for everyone’s approval')).toBeVisible();
 await expect(bundle.locator('.bundle-item').filter({hasText:'Desk'})).toBeVisible();await expect(bundle.getByText('USD 220.00').first()).toBeVisible();
 await first.getByRole('button',{name:'View plan'}).click();await expect(first.getByText('Saved bundle')).toBeVisible();
 await a.close();await b.close();
});
