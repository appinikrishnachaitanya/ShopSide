import { test, expect } from '@playwright/test';

test('the selected product is shown immediately while shared focus is updating', async ({ page }) => {
  await page.goto(process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000');
  await page.getByRole("button", { name: "Move-In Studio", exact: true }).click();await page.getByLabel('Your name').fill('Alex');
  await page.getByRole('button', { name: 'Create your shopping room' }).click();
  await expect(page.getByText('Connected', { exact: true })).toBeVisible();
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/rooms/*/commands', async route => {
    if (route.request().postDataJSON().kind === 'focus') await pending;
    await route.continue();
  });
  await page.getByRole('button', { name: /Sunday Studio.*Look at this/ }).click();
  await expect(page.locator('.stage h2')).toHaveText('Sunday Studio');
  await expect(page.locator('.stage h2')).not.toHaveText('Home Office Desk Lamp');
  release();
});
