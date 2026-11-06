"use client";
import { useEffect, useRef, useState } from "react";

type Remote = { name:string; stream:MediaStream };
function RemoteAudio({remote}:{remote:Remote}) {
  const element=useRef<HTMLAudioElement|null>(null);
  useEffect(()=>{if(element.current){element.current.srcObject=remote.stream;element.current.play().catch(()=>{});}},[remote.stream]);
  return <div><small>{remote.name}</small><audio ref={element} autoPlay controls className="call-audio" aria-label={`${remote.name} audio`} /></div>;
}
export default function AudioCall({roomId,online}:{roomId:string;online:boolean}) {
  const [status,setStatus]=useState("idle"),[muted,setMuted]=useState(false),[error,setError]=useState(""),[remotes,setRemotes]=useState<Remote[]>([]);
  const ws=useRef<WebSocket|null>(null),stream=useRef<MediaStream|null>(null),peers=useRef(new Map<string,RTCPeerConnection>()),pending=useRef(new Map<string,RTCIceCandidateInit[]>()),timers=useRef(new Map<string,ReturnType<typeof setTimeout>>());
  function closePeer(name:string){const timer=timers.current.get(name);if(timer)clearTimeout(timer);timers.current.delete(name);peers.current.get(name)?.close();peers.current.delete(name);pending.current.delete(name);setRemotes(prev=>prev.filter(remote=>remote.name!==name));}
  function stop(){const socket=ws.current;ws.current=null;socket?.close();for(const name of [...peers.current.keys()])closePeer(name);stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;setRemotes([]);setMuted(false);setStatus("idle");}
  useEffect(()=>()=>{ws.current?.close();for(const peer of peers.current.values())peer.close();for(const timer of timers.current.values())clearTimeout(timer);stream.current?.getTracks().forEach(track=>track.stop());},[roomId]);
  async function join(){
    try{
      setError("");setStatus("joining");
      const media=await navigator.mediaDevices.getUserMedia({audio:true,video:false});stream.current=media;
      const config=await fetch('/api/rooms/'+roomId+'/call-config');if(!config.ok)throw Error('Voice configuration unavailable');const ice=await config.json();
      const socket=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/api/rooms/'+roomId+'/call');ws.current=socket;
      const send=(to:string,type:string,payload?:unknown)=>{if(socket.readyState===WebSocket.OPEN)socket.send(JSON.stringify({to,type,payload}));};
      function connection(name:string){
        const existing=peers.current.get(name);if(existing)return existing;
        const peer=new RTCPeerConnection(ice);peers.current.set(name,peer);media.getTracks().forEach(track=>peer.addTrack(track,media));
        peer.onicecandidate=e=>{if(e.candidate)send(name,'ice',e.candidate.toJSON());};
        peer.ontrack=e=>{const remote=e.streams[0];if(remote)setRemotes(prev=>[...prev.filter(x=>x.name!==name),{name,stream:remote}]);};
        peer.onconnectionstatechange=()=>{if(peer.connectionState==='connected'){const timer=timers.current.get(name);if(timer)clearTimeout(timer);timers.current.delete(name);setStatus('connected');}else if(['failed','disconnected'].includes(peer.connectionState)){setError(`Voice connection with ${name} was interrupted.`);}};
        return peer;
      }
      function waitFor(name:string){const previous=timers.current.get(name);if(previous)clearTimeout(previous);timers.current.set(name,setTimeout(()=>setError(`Could not establish audio with ${name}. Check your network connection.`),20000));}
      async function applyCandidates(name:string,peer:RTCPeerConnection){for(const candidate of pending.current.get(name)||[])await peer.addIceCandidate(candidate);pending.current.delete(name);}
      socket.onopen=()=>setStatus('waiting');
      socket.onerror=()=>setError('Call signaling failed. Check your connection.');
      socket.onclose=()=>{if(ws.current===socket){setError('Call disconnected. The voice room may be full.');stop();}};
      socket.onmessage=async event=>{try{
        const data=JSON.parse(event.data),name=data.peer;
        if(typeof name!=='string')return;
        if(data.type==='peer_ready'){
          setStatus('connecting');waitFor(name);const peer=connection(name);const offer=await peer.createOffer();await peer.setLocalDescription(offer);send(name,'offer',offer);
        }else if(data.type==='offer'){
          setStatus('connecting');waitFor(name);const peer=connection(name);await peer.setRemoteDescription(data.payload);await applyCandidates(name,peer);const answer=await peer.createAnswer();await peer.setLocalDescription(answer);send(name,'answer',answer);
        }else if(data.type==='answer'){
          const peer=peers.current.get(name);if(peer){await peer.setRemoteDescription(data.payload);await applyCandidates(name,peer);}
        }else if(data.type==='ice'){
          const peer=peers.current.get(name);if(peer?.remoteDescription)await peer.addIceCandidate(data.payload);else pending.current.set(name,[...(pending.current.get(name)||[]),data.payload]);
        }else if(data.type==='peer_left'||data.type==='hangup'){
          closePeer(name);if(peers.current.size===0){setStatus('waiting');setError('Your friend left the call.');}else setError(`${name} left the call.`);
        }
      }catch{setError('Could not connect the call. Please try again.');}};
    }catch(e:any){setError(e?.message==='Voice configuration unavailable'?e.message:'Microphone permission is needed to join a call.');stop();}
  }
  return <section className="call-panel" aria-label="Voice call"><div><span className="call-icon" aria-hidden="true">◌</span><div><strong>Talk while you shop</strong><small>{status==='idle'?'Audio is off':status==='waiting'?'Waiting for your friend to join…':status==='joining'||status==='connecting'?'Connecting…':'Voice connected'}</small></div></div>
    {remotes.map(remote=><RemoteAudio key={remote.name} remote={remote}/>)}
    {status==='idle'?<button disabled={!online} onClick={join}>Join voice</button>:<div className="call-actions"><button onClick={()=>{stream.current?.getAudioTracks().forEach(track=>track.enabled=muted);setMuted(!muted);}}>{muted?'Unmute':'Mute'}</button><button onClick={stop}>Leave</button></div>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
