import {test,expect} from '@playwright/test';
test('merchant portal shows three screens and live deal evidence',async({page})=>{
 const base=process.env.SHOPSIDE_TEST_URL||'http://localhost:13319';
 const merchant={id:'sandbox-merchant-1',name:'Sandbox Merchant 1',sandbox:true,verified_domain:'sandbox.example',agent_name:'Nora',opt_in:true,active:true,mode:'manual',policy:{max_discount_bps:1000,minimum_price_cents:12000,max_counteroffers:3,offer_lifetime_seconds:600,review_policy:'out_of_policy'}};
 const opportunity={id:'op-sandbox-1',status:'MERCHANT_NOTIFIED',demand:{categories:['desk'],budget_cents:20000,expires_at:Math.floor(Date.now()/1000)+3600},product_id:'channel3:desk-1',offer:null,activity:[{event:'merchant_notified',at:Math.floor(Date.now()/1000)}]};
 await page.route('**/api/merchant/me',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({merchant,products:[],opportunities:[opportunity],metrics:{new_opportunities:1,active_negotiations:0,accepted_deals:0,confirmed_orders:0}})}));
 await page.goto(base+'/merchant');
 await page.getByPlaceholder('Paste your sandbox merchant token').fill('sandbox-test-token');
 await page.getByRole('button',{name:'Open merchant workspace'}).click();
 await expect(page.getByRole('heading',{name:'Make every moment count.'})).toBeVisible();
 await expect(page.getByText('Buyer opportunities')).toBeVisible();
 await page.getByRole('button',{name:'My AI Agent'}).click();
 await expect(page.getByRole('heading',{name:'Set the rules. Let AI sell.'})).toBeVisible();
 await page.getByRole('button',{name:'Deal Box'}).click();
 await expect(page.getByRole('heading',{name:'Deals worth your attention.'})).toBeVisible();
 await expect(page.getByText('op-sandbox-1').first()).toBeVisible();
 await page.screenshot({path:'/tmp/shopside-merchant-portal.png',fullPage:true});
});
