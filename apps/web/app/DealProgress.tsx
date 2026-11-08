"use client";
import {useEffect,useState} from "react";
import {sessionFetch} from "./lib/session";

type Opportunity={id:string;merchant_name:string;label:string};
export default function DealProgress({room}:{room:any}){
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
 return <section className="deal-progress" aria-label="Deal Rescue progress"><strong>Deal Rescue · seller progress</strong><p>Negotiation can continue while you’re away. A PayPal payment still needs your approval.</p><ul>{opportunities.map(item=><li key={item.id}><span>{item.merchant_name}</span><strong>{item.label}</strong></li>)}</ul></section>;
}
