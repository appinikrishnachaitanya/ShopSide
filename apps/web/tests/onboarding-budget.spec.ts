import {test,expect} from '@playwright/test';
test('explicit budget is visible while intent is processing and survives provider failure',async({page})=>{
  const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';
  let release!:()=>void;const waiting=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/rooms/*/intent',async route=>{await waiting;await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Intent assistant unavailable'})});});
  await page.goto(base);await page.getByLabel('What are you shopping for today?').fill('We need a home office and kitchen under $700.');
  await page.getByLabel('Your name').fill('Alex');await page.getByRole('button',{name:'Create your shopping room'}).click();
  await expect(page).toHaveURL(/room=/);await expect(page.getByText(/USD 700.00 budget/).first()).toBeVisible();
  await expect(page.getByRole('status').filter({hasText:'Understanding your shopping goal'})).toBeVisible();
  release();await expect(page.locator('p[role=alert]')).toContainText('Intent assistant unavailable');
  await expect(page.getByText(/USD 700.00 budget/).first()).toBeVisible();
});
