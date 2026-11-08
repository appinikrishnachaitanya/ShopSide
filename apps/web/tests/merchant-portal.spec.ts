import {test,expect} from '@playwright/test';
test('merchant portal shows three screens and live deal evidence',async({page})=>{
 const base=process.env.SHOPSIDE_TEST_URL||'http://localhost:13319';
 const merchant={id:'sandbox-merchant-1',name:'Studio Furniture',sandbox:true,verified_domain:'',agent_name:'Nora',opt_in:true,active:true,mode:'manual',policy:{max_discount_bps:1000,minimum_price_cents:12000,max_counteroffers:3,offer_lifetime_seconds:600,review_policy:'out_of_policy'}};
 const opportunity={id:'op-sandbox-1',status:'MERCHANT_NOTIFIED',demand:{categories:['desk'],budget_cents:20000,expires_at:Math.floor(Date.now()/1000)+3600},product_id:'shopside:sandbox-merchant-1:compact-desk',offer:null,activity:[{event:'merchant_notified',at:Math.floor(Date.now()/1000)}]};
 const products=[{product_id:'shopside:sandbox-merchant-1:compact-desk',source:'SHOPSIDE_SANDBOX',title:'Compact Desk',sku:'compact-desk',price_cents:18000,currency:'USD',stock_quantity:8,description:'Fictional sandbox item'}];
 await page.route('**/api/merchant/me',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({merchant,products,orders:[],opportunities:[opportunity],metrics:{new_opportunities:1,active_negotiations:0,accepted_deals:0,confirmed_orders:0}})}));
 await page.goto(base+'/merchant');
 await page.getByPlaceholder('Paste your sandbox merchant token').fill('sandbox-test-token');
 await page.getByRole('button',{name:'Open merchant workspace'}).click();
 await expect(page.getByRole('heading',{name:'Make every moment count.'})).toBeVisible();
 await expect(page.getByText('Buyer opportunities')).toBeVisible();
 await page.getByRole('button',{name:'My AI Agent'}).click();
 await expect(page.getByRole('heading',{name:'Set the rules. Let AI sell.'})).toBeVisible();
 await page.getByRole('button',{name:'Deal Box',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Deals worth your attention.'})).toBeVisible();
 await expect(page.getByText('op-sandbox-1').first()).toBeVisible();
 await page.getByRole('button',{name:'Products (1)'}).click();
 await expect(page.getByText('Compact Desk')).toBeVisible();
 await expect(page.getByText('8 available')).toBeVisible();
 await page.screenshot({path:'/tmp/shopside-merchant-portal.png',fullPage:true});
});

test('merchant workspace handles a non-JSON server error and can retry',async({page})=>{
 let attempts=0;
 const merchant={id:'sandbox-merchant-1',name:'Studio Furniture',verified_domain:'',agent_name:'Nora',opt_in:true,active:true,mode:'manual',policy:{max_discount_bps:1000,minimum_price_cents:12000,max_counteroffers:3,offer_lifetime_seconds:600,review_policy:'out_of_policy'}};
 await page.route('**/api/merchant/me',route=>{
  attempts++;
  return attempts===1?route.fulfill({status:500,contentType:'text/plain',body:'Internal Server Error'}):route.fulfill({json:{merchant,products:[],orders:[],opportunities:[],metrics:{}}});
 });
 await page.goto((process.env.SHOPSIDE_TEST_URL||'http://localhost:13319')+'/merchant');
 await page.getByPlaceholder('Paste your sandbox merchant token').fill('sandbox-test-token');
 await page.getByRole('button',{name:'Open merchant workspace'}).click();
 await expect(page.locator('p[role="alert"]')).toContainText('Merchant workspace unavailable (500)');
 await page.getByRole('button',{name:'Retry'}).click();
 await page.getByRole('button',{name:'Deal Box',exact:true}).click();
 await expect(page.getByRole('button',{name:'Products (0)'})).toBeVisible();
});
