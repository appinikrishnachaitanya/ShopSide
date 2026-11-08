import {test,expect} from '@playwright/test';

test('seller invitation moves to Our plan and stays dismissed in this browser',async({page})=>{
  await page.goto(process.env.SHOPSIDE_TEST_URL||'http://localhost:3000');
  await page.getByLabel('Your name').fill('Alex');
  await page.getByRole('button',{name:'Create your shopping room'}).click();
  const invitation=page.getByRole('complementary',{name:'Seller offers invitation'});
  await expect(invitation).toBeVisible();
  await invitation.getByRole('button',{name:'View in plan'}).click();
  await expect(page.getByLabel('Shopping plan').locator('#plan-deals')).toBeVisible();
  await expect(page.locator('#plan-deals')).toHaveClass(/plan-deals-highlight/);
  await page.getByRole('button',{name:'Close Our plan'}).click();
  await expect(invitation).toHaveCount(0);
  await page.reload();
  await expect(invitation).toHaveCount(0);
  await page.getByRole('button',{name:'View plan'}).click();
  await expect(page.locator('#plan-deals').getByText('Deals come to your room.')).toBeVisible();
});
