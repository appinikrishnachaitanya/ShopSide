import { test, expect } from '@playwright/test';

test('assistant text is readable and comparison shows sourced product facts', async ({ page }) => {
  await page.routeWebSocket('**/api/rooms/*/live?*', socket => {
    const server = socket.connectToServer();
    server.onMessage(message => {
      if (typeof message !== 'string') { socket.send(message); return; }
      const room = JSON.parse(message);
      const products = [
        { id:'channel3:sofa1', provider_id:'sofa1', name:'Compact Sofa', provenance:'channel3', retrieved_at:1, offers:[{retailer:'shop.example',url:'https://shop.example/sofa',currency:'USD',price_cents:50000}], attributes:{} },
        { id:'channel3:sofa2', provider_id:'sofa2', name:'Loveseat', provenance:'channel3', retrieved_at:1, offers:[{retailer:'shop.example',url:'https://shop.example/love',currency:'USD',price_cents:45000}], attributes:{} },
      ];
      room.discovery = products; room.comparison = products.map(p => p.id); room.shortlist = products.map(p => p.id); room.focus = products[0].id;
      room.messages = [{actor:'ShopSide',text:'**Best choice:** channel3:sofa1. Compare with channel3:missing.'}];
      socket.send(JSON.stringify(room));
    });
  });
  await page.route('**/api/rooms/*/discovery/sofa*', route => route.fulfill({json:{
    id:'channel3:sofa1', provenance:'channel3', retrieved_at:1,
    attributes:{seating_capacity:2, material:'Linen'},
    offers:[{currency:'USD',price_cents:50000,dimensions:{length:{number:39.5,unit:'in'},width:{number:19.5,unit:'in'},height:{number:35.5,unit:'in'}},delivery:'Ships in 5 days'}],
  }}));
  await page.goto(process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000');
  await page.getByLabel('Your name').fill('Alex');
  await page.getByRole('button',{name:'Create your shopping room'}).click();
  const message = page.locator('.agent-message');
  await expect(message.locator('p strong')).toHaveText('Best choice:');
  await expect(message).toContainText('Compact Sofa');
  await expect(message).toContainText('this product');
  await expect(message).not.toContainText('channel3:');
  await page.getByRole('button',{name:'View plan'}).click();
  await page.getByRole('button',{name:'Compare saved products'}).click();
  const grid = page.locator('.board');
  await expect(grid.getByText('Linen').first()).toBeVisible();
  await expect(grid.getByText('Ships in 5 days').first()).toBeVisible();
  await expect(grid.getByText('39.5 × 19.5 × 35.5 in').first()).toBeVisible();
  await expect(grid).not.toContainText('number:');
  await page.getByRole('button',{name:'Close Compare together'}).click();
  await page.getByRole('button',{name:'View selected'}).click();
  await expect(page.getByRole('button',{name:'Find a better price'})).toBeVisible();
});
