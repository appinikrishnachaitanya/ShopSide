import {test,expect} from '@playwright/test';
test('room remains usable without WebGL',async({browser})=>{
 const context=await browser.newContext();
 await context.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type:any,...args:any[]):any{if(type==='webgl'||type==='webgl2'||type==='experimental-webgl')return null;return (original as any).call(this,type,...args);};});
 const page=await context.newPage();await page.goto(process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000');await page.getByLabel('Your name').fill('Fallback');await page.getByRole('button',{name:'Create your room'}).click();
 await page.getByRole('button',{name:'3D room',exact:true}).click();
 const room=page.getByLabel('Shared 3D room');await expect(room.getByLabel('Simplified shared room preview')).toBeVisible();
 await room.getByRole('button',{name:'Place focused product'}).click();await room.getByRole('button',{name:'Place in center'}).click();
 await expect(room.getByText('Home Office Desk Lamp',{exact:true})).toBeVisible();
 await room.getByRole('button',{name:'Move Home Office Desk Lamp right'}).click();
 await expect(room.getByText(/simplified room because 3D graphics are unavailable/)).toBeVisible();await context.close();
});
