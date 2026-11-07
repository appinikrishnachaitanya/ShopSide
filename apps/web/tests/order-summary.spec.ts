import {test,expect} from '@playwright/test';

test('completed sandbox order has a dedicated authenticated summary',async({page})=>{
  await page.route('**/api/rooms/room-1/merchant-orders/order-1/receipt',route=>route.fulfill({
    status:200,contentType:'application/json',body:JSON.stringify({order_id:'order-1',merchant_name:'Urban Workspace',
      items:[{product_id:'desk',name:'Desk',quantity:1,reference_price_cents:27000}],reference_total_cents:27000,
      total_cents:26100,savings_cents:900,currency:'USD',paypal_sandbox_order_id:'PAYPAL-SANDBOX-ORDER',
      paypal_sandbox_capture_id:'CAPTURE-1',paid_at:'2026-11-07T10:00:00+00:00',
      disclosure:'Fictional ShopSide sandbox products; no goods shipped and no real money charged.',
      room_members:['Alex','Sam'],payer:'Alex',decision_trail:[
        {event:'accepted',label:'Buyer accepted the offer',actor:'Alex',at:1794045600},
        {event:'payment_captured',label:'PayPal Sandbox payment verified',actor:'paypal',at:1794045700}]})}));
  await page.goto((process.env.SHOPSIDE_TEST_URL||'http://localhost:3000')+'/orders/order-1?room=room-1');
  await expect(page.getByRole('heading',{name:'Your order, confirmed.'})).toBeVisible();
  await expect(page.getByText('$261.00')).toBeVisible();
  await expect(page.getByText('PAYPAL-SANDBOX-ORDER')).toBeVisible();
  await expect(page.getByText(/no goods shipped and no real money charged/i)).toBeVisible();
  await expect(page.getByRole('region',{name:'Decision receipt'}).getByText('Buyer accepted the offer')).toBeVisible();
});
