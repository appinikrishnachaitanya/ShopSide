import {test,expect} from '@playwright/test';
test('four family members can join and see the same room',async({browser})=>{
 test.setTimeout(75000);
 const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';const contexts=await Promise.all(Array.from({length:5},()=>browser.newContext()));
 for(const context of contexts)await context.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type:any,...args:any[]):any{if(type==='webgl'||type==='webgl2'||type==='experimental-webgl')return null;return (original as any).call(this,type,...args);};});
 const pages=await Promise.all(contexts.map(c=>c.newPage()));
 await pages[0].goto(base);await pages[0].getByLabel('Your name').fill('A');await pages[0].getByRole('button',{name:'Create your room'}).click();await expect(pages[0]).toHaveURL(/room=/);
 const id=new URL(pages[0].url()).searchParams.get('room');const state=await(await pages[0].request.get(base+'/api/rooms/'+id)).json();
 for(let i=1;i<4;i++){await pages[i].goto(base+'?invite='+state.invite);await pages[i].getByLabel('Your name').fill(String.fromCharCode(65+i));await pages[i].getByRole('button',{name:'Join your friend'}).click();await expect(pages[i]).toHaveURL(/room=/,{timeout:15000});}
 await expect.poll(async()=>((await(await pages[0].request.get(base+'/api/rooms/'+id)).json()).people.length)).toBe(4);
 await expect(pages[0].getByLabel('Move-In Studio').getByText('D',{exact:true})).toBeVisible();
 await pages[4].goto(base+'?invite='+state.invite);await pages[4].getByLabel('Your name').fill('E');await pages[4].getByRole('button',{name:'Join your friend'}).click();await expect(pages[4].locator('p[role=alert]')).toContainText('maximum four people');
 await Promise.all(contexts.map(c=>c.close()));
});
