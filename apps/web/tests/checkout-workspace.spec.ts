import { seedMoveInRoom } from "./move-in-fixture";
import { test, expect } from '@playwright/test';

test('sandbox cart shows the quote and PayPal approval boundary', async ({ page }) => {
  const base = process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';
  await page.route('**/api/rooms/*/payments/*/create', route => route.fulfill({ json: { status: 'approval', order_id: 'TEST-SANDBOX-ORDER' } }));
  await page.route('**/api/paypal/config', route => route.fulfill({ json: { client_id: 'test-client', currency: 'USD' } }));
  await page.route('https://www.paypal.com/sdk/js?*', route => route.fulfill({ contentType: 'application/javascript', body: 'window.paypal={Buttons:()=>({render:(target)=>{document.querySelector(target).textContent="Sandbox approval ready";return Promise.resolve()}})};' }));
  await page.goto(base);
  await seedMoveInRoom(page);await page.getByLabel('Your name').fill('Payer');
  await page.getByRole('button', { name: 'Create your shopping room' }).click();
  await page.getByRole('button', { name: /Home Office Desk Lamp.*Look at this/ }).click();
  await expect(page.getByRole('dialog', { name: 'Product details' })).toBeVisible();
  await page.getByRole('button', { name: 'Add to cart', exact: true }).click();
  await expect(page.getByText('$39.00 each · $39.00')).toBeVisible();
  await page.getByRole('button', { name: 'Review sandbox checkout' }).click();
  await expect(page.getByText('Total $39.00 USD')).toBeVisible();
  await page.getByRole('button', { name: 'Create PayPal sandbox order' }).click();
  await expect(page.getByText('TEST-SANDBOX-ORDER')).toBeVisible();
  await expect(page.getByText('Sandbox approval ready')).toBeVisible();
  await expect(page.getByText('PayPal sandbox payment verified.')).toHaveCount(0);
});
