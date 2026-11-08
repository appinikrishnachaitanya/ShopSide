import type { Page } from '@playwright/test';
/** Seed a legacy Move-In room when exercising the existing planning controls.
 * Intent extraction has separate provider-mocked backend tests. */
export async function seedMoveInRoom(page: Page) {
  await page.route('**/api/rooms', async route => {
    if (route.request().method() !== 'POST') return route.continue();
    const body = route.request().postDataJSON();
    await route.continue({postData: JSON.stringify({...body, mode: 'move_in'})});
  });
}
