import {test,expect} from '@playwright/test';
test('explicit budget is visible while onboarding is processing and survives provider failure',async({page})=>{
  const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';
  let release!:()=>void;const waiting=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/rooms/*/move-in/turn',async route=>{await waiting;await route.fulfill({status:502,contentType:'application/json',body:JSON.stringify({detail:'Mission assistant unavailable'})});});
  await page.goto(base);await page.getByLabel('What are you shopping for today?').fill('We need a home office and kitchen under $700.');
  await page.getByRole("button", { name: "Move-In Studio", exact: true }).click();await page.getByLabel('Your name').fill('Alex');await page.getByRole('button',{name:'Create your shopping room'}).click();
  await expect(page).toHaveURL(/room=/);await page.getByRole('button',{name:'View plan',exact:true}).click();const mission=page.getByLabel('Move-In Studio');
  await expect(mission.getByText('USD 700.00',{exact:true})).toBeVisible();
  await expect(mission.getByRole('status')).toContainText('Reading your request');
  release();await expect(page.locator('p[role=alert]')).toContainText('Mission assistant unavailable');
  await expect(mission.getByText('USD 700.00',{exact:true})).toBeVisible();
});
