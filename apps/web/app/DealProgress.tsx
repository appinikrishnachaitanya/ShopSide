"use client";
import {useEffect,useState} from "react";
import {sessionFetch} from "./lib/session";

type Opportunity={id:string;merchant_id:string;merchant_name:string;label:string;status:string;preauthorization_available:boolean};
export default function DealProgress({room,onPreauthorize}:{room:any;onPreauthorize?:(opportunity:Opportunity)=>Promise<void>}){
 const [opportunities,setOpportunities]=useState<Opportunity[]>([]);
 const [error,setError]=useState(false);
 useEffect(()=>{
  if(!room?.id||!room.seller_offers?.enabled){setOpportunities([]);return}
  const controller=new AbortController();
  const timer=setTimeout(async()=>{
   try{
    const response=await sessionFetch(`/api/rooms/${encodeURIComponent(room.id)}/deal-rescue`,{signal:controller.signal});
    if(!response.ok)throw new Error('Could not load seller progress');
    const result=await response.json();setOpportunities(result.opportunities||[]);setError(false);
   }catch{if(!controller.signal.aborted)setError(true)}
  },250);
  return()=>{clearTimeout(timer);controller.abort()};
 },[room?.id,room?.revision,room?.seller_offers?.enabled]);
 if(error)return <p role="status">Seller progress is temporarily unavailable. Your offers remain in the room.</p>;
 if(!opportunities.length)return null;
 return <section className="deal-progress" aria-label="Deal Rescue progress"><strong>Deal Rescue · seller progress</strong><p>Negotiation can continue while you’re away. Preauthorization needs your explicit PayPal approval first.</p><ul>{opportunities.map(item=><li key={item.id}><span>{item.merchant_name}</span><strong>{item.label}</strong>{onPreauthorize&&item.preauthorization_available&&room.seller_offers?.merchant_id===item.merchant_id&&room.seller_offers?.auto_accept_limit_cents>0&&!room.checkout&&!['EXPIRED','DECLINED','CANCELLED','ORDER_COMPLETED'].includes(item.status)&&<button type="button" onClick={()=>onPreauthorize(item)}>Authorize up to ${(room.seller_offers.auto_accept_limit_cents/100).toFixed(2)} in PayPal</button>}</li>)}</ul></section>;
}
