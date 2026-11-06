"use client";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Box, Move3D, Plus, Rotate3D, Trash2 } from "lucide-react";

type Placement = { product_id:string; name:string; x:number; z:number; updated_by:string };
type Props = { room:any; focused:any; online:boolean; command:(kind:string,value:string)=>void };

export default function RoomPreview({room,focused,online,command}:Props) {
  const container=useRef<HTMLDivElement>(null);
  const sceneRef=useRef<THREE.Scene|null>(null);
  const markersRef=useRef<THREE.Group|null>(null);
  const placeRef=useRef<(x:number,z:number)=>void>(()=>{});
  const [placing,setPlacing]=useState(false);
  const [unavailable,setUnavailable]=useState(false);
  const placements:Placement[]=room.room_placements || [];
  placeRef.current=(x,z)=>{
    if (!placing || !online || !focused) return;
    command("placement_upsert",JSON.stringify({product_id:focused.id,x:Math.max(-2.5,Math.min(2.5,Math.round(x*10)/10)),z:Math.max(-2.5,Math.min(2.5,Math.round(z*10)/10))}));
    setPlacing(false);
  };
  useEffect(()=>{
    const host=container.current;
    if(!host)return;
    let renderer:THREE.WebGLRenderer;
    try {renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});}
    catch {setUnavailable(true);return;}
    renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.5));
    renderer.shadowMap.enabled=true;
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);
    const scene=new THREE.Scene();scene.background=new THREE.Color('#dce2f8');sceneRef.current=scene;
    const camera=new THREE.PerspectiveCamera(38,1,.1,100);camera.position.set(8,8,10);
    const controls=new OrbitControls(camera,renderer.domElement);
    controls.target.set(0,.6,0);controls.enableDamping=true;controls.minDistance=6;controls.maxDistance=18;controls.maxPolarAngle=Math.PI/2.08;controls.enablePan=false;controls.update();
    scene.add(new THREE.HemisphereLight(0xffffff,0x8385b8,2.1));
    const light=new THREE.DirectionalLight(0xffffff,2.1);light.position.set(5,10,6);light.castShadow=true;scene.add(light);
    const material=(color:string)=>new THREE.MeshStandardMaterial({color,roughness:.85});
    function block(w:number,h:number,d:number,color:string,x:number,y:number,z:number){
      const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material(color));m.position.set(x,y,z);m.receiveShadow=true;m.castShadow=true;scene.add(m);return m;
    }
    const floor=block(6.2,.16,6.2,'#f4d9b8',0,-.08,0);
    block(6.2,3.2,.12,'#f8f3ee',0,1.6,-3.1);block(.12,3.2,6.2,'#ece6e4',-3.1,1.6,0);
    // Architectural shapes are decorative; they make no claims about selected products.
    block(2.15,1.65,.05,'#9fbeec',.5,2.05,-3.02);block(.08,1.65,.06,'#f7f2ed',.5,2.05,-2.98);block(2.15,.08,.06,'#f7f2ed',.5,2.05,-2.98);
    block(1.3,.06,.65,'#e9b98d',-2.3,.64,-1.7);block(.08,.64,.08,'#a46545',-2.75,.32,-1.9);block(.08,.64,.08,'#a46545',-1.85,.32,-1.5);
    const rug=block(2.5,.025,1.8,'#b7befc',.5,.02,.35);rug.castShadow=false;
    // The set dressing is generic and intentionally distinct from selected products.
    block(1.85,.34,.75,'#858dc7',-1.65,.25,.6);block(1.85,.55,.18,'#737bb7',-1.65,.57,.28);
    block(.16,.38,.75,'#737bb7',-2.5,.43,.6);block(.16,.38,.75,'#737bb7',-.8,.43,.6);
    block(.9,.06,.55,'#f4b78e',.7,.42,.3);block(.07,.42,.07,'#ad745a',.37,.21,.14);block(.07,.42,.07,'#ad745a',1.03,.21,.46);
    block(.55,.65,.05,'#b9a9ea',-1.6,2.15,-3.01);block(.42,.5,.06,'#f4c19f',-1.6,2.15,-2.97);
    const pot=new THREE.Mesh(new THREE.CylinderGeometry(.23,.16,.36,24),material('#db8f74'));pot.position.set(2.1,.18,-2.35);pot.castShadow=true;scene.add(pot);
    for(const [x,y,z] of [[0,.6,0],[-.16,.55,0],[.16,.52,.04],[0,.48,-.16]]){const leaf=new THREE.Mesh(new THREE.SphereGeometry(.22,16,12),material('#568f76'));leaf.scale.set(.65,1,.65);leaf.position.set(2.1+x,y,-2.35+z);scene.add(leaf);}

    const markers=new THREE.Group();scene.add(markers);markersRef.current=markers;
    let down={x:0,y:0};const raycaster=new THREE.Raycaster();const pointer=new THREE.Vector2();
    const onDown=(e:PointerEvent)=>{down={x:e.clientX,y:e.clientY};};
    const onUp=(e:PointerEvent)=>{if(Math.hypot(e.clientX-down.x,e.clientY-down.y)>5)return;const rect=renderer.domElement.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,-((e.clientY-rect.top)/rect.height)*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObject(floor)[0];if(hit)placeRef.current(hit.point.x,hit.point.z);};
    renderer.domElement.addEventListener('pointerdown',onDown);renderer.domElement.addEventListener('pointerup',onUp);
    const resize=()=>{const w=host.clientWidth,h=host.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};
    const observer=new ResizeObserver(resize);observer.observe(host);resize();
    let frame=0;const draw=()=>{controls.update();renderer.render(scene,camera);frame=requestAnimationFrame(draw);};draw();
    return ()=>{cancelAnimationFrame(frame);observer.disconnect();renderer.domElement.removeEventListener('pointerdown',onDown);renderer.domElement.removeEventListener('pointerup',onUp);controls.dispose();scene.traverse(obj=>{if(obj instanceof THREE.Mesh){obj.geometry.dispose();const mats=Array.isArray(obj.material)?obj.material:[obj.material];mats.forEach(m=>m.dispose());}else if(obj instanceof THREE.Sprite){obj.material.map?.dispose();obj.material.dispose();}});renderer.dispose();renderer.domElement.remove();sceneRef.current=null;markersRef.current=null;};
  },[]);
  useEffect(()=>{
    const markers=markersRef.current;if(!markers)return;
    while(markers.children.length){const obj=markers.children[0];markers.remove(obj);obj.traverse(child=>{if(child instanceof THREE.Mesh){child.geometry.dispose();(child.material as THREE.Material).dispose();}else if(child instanceof THREE.Sprite){child.material.map?.dispose();child.material.dispose();}});}
    placements.forEach((item,index)=>{
      const color=['#ff724d','#6549eb','#2563eb','#e6a344','#eb6195'][index%5];
      const group=new THREE.Group();group.position.set(item.x,0,item.z);
      const body=new THREE.Mesh(new THREE.BoxGeometry(.62,.56,.62),new THREE.MeshStandardMaterial({color,roughness:.5}));body.position.y=.32;body.castShadow=true;group.add(body);
      const label=document.createElement('canvas');label.width=96;label.height=96;const ctx=label.getContext('2d');
      if(ctx){ctx.beginPath();ctx.arc(48,48,43,0,Math.PI*2);ctx.fillStyle='#ffffff';ctx.fill();ctx.fillStyle='#211740';ctx.font='bold 46px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(String(index+1),48,50);const texture=new THREE.CanvasTexture(label);const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,transparent:true}));sprite.position.y=.83;sprite.scale.set(.4,.4,.4);group.add(sprite);}
      markers.add(group);
    });
  },[room.room_placements]);
  const put=(p:Placement,x:number,z:number)=>command('placement_upsert',JSON.stringify({product_id:p.product_id,x:Math.max(-2.5,Math.min(2.5,Math.round(x*10)/10)),z:Math.max(-2.5,Math.min(2.5,Math.round(z*10)/10))}));
  return <section className="room-preview" aria-label="Shared 3D room">
    <div className="room-preview-head"><div><span className="section-kicker"><span className="live-pulse"/> YOUR LIVE SPACE</span><h2>See it together<span className="period">.</span></h2><p>Give your ideas a place to land.</p></div><span className="room-live-label">{online?'● LIVE ROOM':'○ RECONNECTING'}</span></div>
    <div className="room-preview-body"><div className="room-canvas-wrap"><div ref={container} className="room-canvas" aria-label="Interactive illustrative 3D room" />
      {unavailable && <div className="room-canvas-fallback">3D is unavailable in this browser. You can still manage placements below.</div>}
      <span className="room-canvas-tip"><Rotate3D size={15}/> Drag to orbit · scroll to zoom</span>
      {placing && <div className="placement-instruction">Tap the floor to place {focused?.name} <button onClick={()=>setPlacing(false)}>Cancel</button><button onClick={()=>placeRef.current(0,0)}>Place in center</button></div>}
    </div><div className="room-preview-panel"><div className="room-panel-title"><span><Box size={16}/> YOUR ROOM</span><span>{placements.length}/20</span></div><h3>Make some space.</h3><p>Choose a product, then place a marker in your room. Everyone sees the same layout.</p>
      <button className="place-product" disabled={!online || !focused} onClick={()=>setPlacing(!placing)}><Plus size={17}/>{placing?'Choose a spot':'Place focused product'}</button>
      {focused && <small className="focused-product">Focused: {focused.name}</small>}
      <div className="room-placements">{!placements.length && <p className="room-empty">Nothing here yet. Add your first idea ✳</p>}{placements.map((item,i)=><div className="placement-row" key={item.product_id}><span className="placement-number" style={{background:['#ff724d','#6549eb','#2563eb','#e6a344','#eb6195'][i%5]}}>{i+1}</span><div><strong>{item.name}</strong><small>Placed by {item.updated_by}</small></div><button aria-label={'Remove '+item.name} disabled={!online} onClick={()=>command('placement_remove',item.product_id)}><Trash2 size={14}/></button><div className="placement-move"><span><Move3D size={13}/> Move</span><button aria-label={'Move '+item.name+' left'} disabled={!online} onClick={()=>put(item,item.x-.3,item.z)}>←</button><button aria-label={'Move '+item.name+' right'} disabled={!online} onClick={()=>put(item,item.x+.3,item.z)}>→</button><button aria-label={'Move '+item.name+' back'} disabled={!online} onClick={()=>put(item,item.x,item.z-.3)}>↑</button><button aria-label={'Move '+item.name+' forward'} disabled={!online} onClick={()=>put(item,item.x,item.z+.3)}>↓</button></div></div>)}</div>
      <p className="room-preview-disclaimer">Illustrative markers only — not the product’s real shape, size, or a fit guarantee.</p></div></div>
  </section>;
}
