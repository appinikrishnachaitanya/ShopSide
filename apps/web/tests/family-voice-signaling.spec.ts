import {test,expect} from '@playwright/test';
// The WebRTC transport is mocked; the server signaling and browser contexts are real.
test('four participants negotiate separate voice peers',async({browser})=>{
 test.setTimeout(60000);
 const base=process.env.SHOPSIDE_TEST_URL || 'http://localhost:3000';const contexts=await Promise.all(Array.from({length:4},()=>browser.newContext()));
 for(const context of contexts)await context.addInitScript(()=>{
   const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type:any,...args:any[]):any{if(type==='webgl'||type==='webgl2'||type==='experimental-webgl')return null;return (original as any).call(this,type,...args);};
   Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>new MediaStream()}});
   class FakePeer {connectionState='new';remoteDescription:any=null;onicecandidate:any;ontrack:any;onconnectionstatechange:any;addTrack(){}async createOffer(){return {type:'offer',sdp:'fake'};}async createAnswer(){return {type:'answer',sdp:'fake'};}async setLocalDescription(){}async setRemoteDescription(value:any){this.remoteDescription=value;this.connectionState='connected';this.onconnectionstatechange?.();}async addIceCandidate(){}close(){this.connectionState='closed';}}
   (window as any).RTCPeerConnection=FakePeer;
 });
 const pages=await Promise.all(contexts.map(c=>c.newPage()));await pages[0].goto(base);await pages[0].getByLabel('Your name').fill('A');await pages[0].getByRole('button',{name:'Create your room'}).click();await expect(pages[0]).toHaveURL(/room=/);
 const id=new URL(pages[0].url()).searchParams.get('room');const state=await(await pages[0].request.get(base+'/api/rooms/'+id)).json();
 for(let i=1;i<4;i++){await pages[i].goto(base+'?invite='+state.invite);await pages[i].getByLabel('Your name').fill(String.fromCharCode(65+i));await pages[i].getByRole('button',{name:'Join your friend'}).click();await expect(pages[i]).toHaveURL(/room=/);}
 for(const page of pages)await page.getByRole('button',{name:'Join voice'}).click();
 for(const page of pages)await expect(page.getByText('Voice connected',{exact:true})).toBeVisible({timeout:15000});
 await pages[3].getByRole('button',{name:'Leave',exact:true}).click();
 for(const page of pages.slice(0,3))await expect(page.getByText('D left the call.')).toBeVisible();
 await Promise.all(contexts.map(c=>c.close()));
});
