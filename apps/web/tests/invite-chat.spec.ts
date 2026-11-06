import {test,expect} from '@playwright/test';
test('invite needs only a name; two tabs retain distinct identities and shared chat',async({browser})=>{
 const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';
 const context=await browser.newContext();
 await context.addInitScript(()=>{
   const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type:any,...args:any[]):any{if(type==='webgl'||type==='webgl2'||type==='experimental-webgl')return null;return (original as any).call(this,type,...args);};
   const NativeSocket=window.WebSocket;(window as any).__roomSockets=[];
   class TrackingSocket extends NativeSocket {constructor(url:string|URL,protocols?:string|string[]){if(protocols)super(url,protocols);else super(url);if(String(url).includes('/live'))(window as any).__roomSockets.push(this);}}
   window.WebSocket=TrackingSocket;
 });
 const first=await context.newPage();await first.goto(base);await first.getByLabel('Your name').fill('Alex');await first.getByRole('button',{name:'Create your room'}).click();await expect(first).toHaveURL(/room=/);await expect(first.getByText('Connected',{exact:true})).toBeVisible();
 const id=new URL(first.url()).searchParams.get('room');const state=await (await first.request.get(base+'/api/rooms/'+id)).json();
 const second=await context.newPage();await second.goto(base+'?invite='+state.invite);
 await expect(second.getByLabel('What are you shopping for today?')).toHaveCount(0);await expect(second.getByLabel('Shopping mode')).toHaveCount(0);
 await second.getByLabel('Your name').fill('Sam');await second.getByRole('button',{name:'Join your friend'}).click();await expect(second).toHaveURL(/room=/);
 await expect(first.getByText('Alex & Sam')).toBeVisible();await expect(second.getByText('Alex & Sam')).toBeVisible();
 await expect(first.getByRole('status').filter({hasText:'Sam joined the room.'})).toBeVisible();
 await expect(first.getByLabel('Your room identity')).toHaveText('You’re Alex');await expect(second.getByLabel('Your room identity')).toHaveText('You’re Sam');
 await first.getByLabel('Message everyone').fill('Message from Alex');await first.getByRole('button',{name:'Send message'}).click();
 await expect(second.locator('.messages article').filter({hasText:'Message from Alex'})).toContainText('Alex');
 await expect(second.getByRole('status').filter({hasText:'Alex sent a message.'})).toBeVisible();
 await expect(first.getByRole('status').filter({hasText:'Alex sent a message.'})).toHaveCount(0);
 await expect(second.getByRole('button',{name:'Enable sound'})).toHaveAttribute('aria-pressed','false');
 await second.getByLabel('Message everyone').fill('Message from Sam');await second.getByRole('button',{name:'Send message'}).click();
 await expect(first.locator('.messages article').filter({hasText:'Message from Sam'})).toContainText('Sam');
 await expect(first.locator('.messages article').filter({hasText:'Message from Alex'})).toHaveClass(/message-own/);
 await expect(first.locator('.messages article').filter({hasText:'Message from Sam'})).toHaveClass(/message-incoming/);
 await expect(second.locator('.messages article').filter({hasText:'Message from Alex'})).toHaveClass(/message-incoming/);
 await expect(second.locator('.messages article').filter({hasText:'Message from Sam'})).toHaveClass(/message-own/);
 await first.reload();await second.reload();
 await expect(first.getByLabel('Your room identity')).toHaveText('You’re Alex');await expect(second.getByLabel('Your room identity')).toHaveText('You’re Sam');
 await expect(first.locator('.messages article').filter({hasText:'Message from Alex'})).toContainText('Alex');
 await expect(first.locator('.messages article').filter({hasText:'Message from Sam'})).toContainText('Sam');
 await expect(second.locator('.messages article').filter({hasText:'Message from Alex'})).toContainText('Alex');
 await expect(second.locator('.messages article').filter({hasText:'Message from Sam'})).toContainText('Sam');
 await expect(first.locator('.messages article').filter({hasText:'Message from Alex'})).toHaveClass(/message-own/);
 await expect(second.locator('.messages article').filter({hasText:'Message from Sam'})).toHaveClass(/message-own/);
 await first.getByLabel('Message everyone').fill('Still Alex after refresh');await first.getByRole('button',{name:'Send message'}).click();
 await expect(second.locator('.messages article').filter({hasText:'Still Alex after refresh'})).toContainText('Alex');
 let staleOnce=true;const conflictIds:string[]=[];
 await first.route('**/api/rooms/*/commands',async route=>{
   const data=route.request().postDataJSON();
   if(data.kind==='chat' && data.value==='Revision conflict'){
     conflictIds.push(data.command_id);
     if(staleOnce){staleOnce=false;await route.fulfill({status:409,contentType:'application/json',body:JSON.stringify({detail:'Room changed; refresh and retry'})});return;}
   }
   await route.continue();
 });
 await first.getByLabel('Message everyone').fill('Revision conflict');await first.getByRole('button',{name:'Send message'}).click();
 await expect(second.locator('.messages article').filter({hasText:'Revision conflict'})).toContainText('Alex');
 expect(conflictIds).toHaveLength(2);expect(conflictIds[0]).toBe(conflictIds[1]);
 await first.unroute('**/api/rooms/*/commands');
 let firstAttempt=true;const sentIds:string[]=[];
 await first.route('**/api/rooms/*/commands',async route=>{
   const data=route.request().postDataJSON();
   if(data.kind==='chat' && data.value==='Retry without a duplicate'){
     sentIds.push(data.command_id);
     if(firstAttempt){firstAttempt=false;const response=await route.fetch();expect(response.ok()).toBeTruthy();await route.abort('failed');return;}
   }
   await route.continue();
 });
 await first.getByLabel('Message everyone').fill('Retry without a duplicate');await first.getByRole('button',{name:'Send message'}).click();
 await expect(first.getByLabel('Message everyone')).toHaveValue('Retry without a duplicate');
 await first.getByRole('button',{name:'Send message'}).click();
 await expect(first.getByLabel('Message everyone')).toHaveValue('');
 expect(sentIds).toHaveLength(2);expect(sentIds[0]).toBe(sentIds[1]);
 await expect(second.locator('.messages article').filter({hasText:'Retry without a duplicate'})).toHaveCount(1);
 await first.evaluate(()=>{const sockets=(window as any).__roomSockets;sockets[sockets.length-1].close();});
 await expect.poll(()=>first.evaluate(()=>(window as any).__roomSockets.length),{timeout:15000}).toBeGreaterThan(1);
 await expect(first.getByText('Connected',{exact:true})).toBeVisible();
 await first.getByLabel('Message everyone').fill('Back online');await first.getByRole('button',{name:'Send message'}).click();
 await expect(second.locator('.messages article').filter({hasText:'Back online'})).toContainText('Alex');
 await context.close();
});
