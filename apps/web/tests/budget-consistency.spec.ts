import { seedMoveInRoom } from "./move-in-fixture";
import {test,expect} from '@playwright/test';
test('saved items use the Move-In mission budget and comparable prices',async({page})=>{
 const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';
 await page.goto(base);await seedMoveInRoom(page);await page.getByLabel('Your name').fill('Budget tester');await page.getByRole('button',{name:'Create your shopping room'}).click();await expect(page).toHaveURL(/room=/);
 const id=new URL(page.url()).searchParams.get('room');const endpoint=base+'/api/rooms/'+id;
 let room=await (await page.request.get(endpoint)).json();const mission={...room.move_in.mission,budget_cents:80000,currency:'USD'};
 expect((await page.request.post(endpoint+'/move-in/mission',{data:{mission,revision:room.revision,command_id:'budget'}})).ok()).toBeTruthy();
 for(const product of ['11','12']){room=await(await page.request.get(endpoint)).json();expect((await page.request.post(endpoint+'/commands',{data:{kind:'shortlist',value:product,revision:room.revision,command_id:'save-'+product}})).ok()).toBeTruthy();}
 await page.getByRole('button',{name:'Compare',exact:false}).first().click();
 const rec=page.locator('.recommendations');await expect(rec.locator('.priority-pills')).toContainText('800.00');
 await expect(rec.getByText('Within total budget (item only)',{exact:false})).toHaveCount(2);
 await expect(rec.getByText(/Price or budget not confirmed/)).toHaveCount(0);
});
