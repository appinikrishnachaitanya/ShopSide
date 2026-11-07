import { test, expect } from '@playwright/test';

test('shopping together is the default and move-in remains optional', async ({page}) => {
  await page.goto(process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000');
  await expect(page.getByRole('heading', { name: /Shopping is.*better together/i })).toBeVisible();
  await expect(page.getByLabel('Shopping mode')).toHaveCount(0);
  await page.getByRole('button', { name: 'Build my workspace' }).click();
  await expect(page.getByLabel('What are you shopping for today?')).toHaveValue(/desk and chair/);
  await page.getByLabel('What are you shopping for today?').clear();
  await page.getByLabel('Your name').fill('Alex');
  await page.getByRole('button', { name: 'Create your shopping room' }).click();
  await expect(page).toHaveURL(/room=/);
  const roomId = new URL(page.url()).searchParams.get('room');
  const room = await (await page.request.get(`${new URL(page.url()).origin}/api/rooms/${roomId}`)).json();
  expect(room.mode).toBe('general');
});
