"use client";
import {useEffect,useState} from "react";
import {useParams} from "next/navigation";
import {sessionFetch} from "../../lib/session";

type Line={product_id:string;name:string;variant?:string;quantity:number;reference_price_cents:number};
type Receipt={order_id:string;merchant_name:string;items:Line[];reference_total_cents:number;total_cents:number;savings_cents:number;currency:string;paypal_sandbox_order_id:string;paypal_sandbox_authorization_id?:string;paypal_sandbox_capture_id:string;paid_at:string;disclosure:string;deal_rescue_id?:string;buyer_maximum_cents?:number;authorized_at?:string;seller_approved_at?:number;buyer_policy_version?:number;merchant_explanation?:string;room_members?:string[];payer?:string;decision_trail?:{event:string;label:string;actor?:string;at:number}[]};
const money=(cents:number,currency:string)=>new Intl.NumberFormat("en-US",{style:"currency",currency}).format(cents/100);

export default function OrderSummary(){
  const {orderId}=useParams<{orderId:string}>();
  const [receipt,setReceipt]=useState<Receipt|null>(null),[error,setError]=useState(""),[roomId,setRoomId]=useState("");
  useEffect(()=>{
    const room=new URLSearchParams(window.location.search).get("room")||"";
    setRoomId(room);
    if(!room||!orderId){setError("A room and completed order are required.");return;}
    let active=true;
    sessionFetch(`/api/rooms/${encodeURIComponent(room)}/orders/${encodeURIComponent(orderId)}/receipt`)
      .then(async response=>{const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.detail||"Completed order unavailable.");return data as Receipt;})
      .then(data=>{if(active)setReceipt(data);})
      .catch(err=>{if(active)setError(err.message)});
    return()=>{active=false};
  },[orderId]);
  return <main className="order-summary-page"><div className="order-summary-shell"><header><a href={roomId?`/?room=${encodeURIComponent(roomId)}`:"/"}>← Back to shopping room</a><span>SHOP<span>SIDE</span> · ORDER SUMMARY</span></header>
    {error?<div role="alert" className="order-summary-card"><h1>Order summary unavailable</h1><p>{error}</p></div>:!receipt?<p role="status">Loading your completed order…</p>:<article className="order-summary-card"><div className="order-summary-hero"><span>SANDBOX INVOICE · PAYPAL CAPTURE VERIFIED</span><h1>Your order, confirmed.</h1><p>A record of your ShopSide merchant order and the decisions recorded in your shared room.</p></div>
      <div className="order-summary-meta"><div><small>SHOPSIDE ORDER</small><strong>{receipt.order_id}</strong></div><div><small>MERCHANT</small><strong>{receipt.merchant_name}</strong></div><div><small>PAID AT</small><strong>{receipt.paid_at?new Date(receipt.paid_at).toLocaleString():"Not recorded"}</strong></div></div>
      <h2>Items</h2><div className="order-summary-lines">{receipt.items.map(line=><div key={`${line.product_id}:${line.variant||''}`}><span>{line.name}<small>Quantity {line.quantity}{line.variant?` · ${line.variant}`:''}</small></span><strong>{money(line.reference_price_cents*line.quantity,receipt.currency)}</strong></div>)}</div>
      <div className="order-summary-totals"><div><span>Listed item subtotal</span><strong>{money(receipt.reference_total_cents,receipt.currency)}</strong></div><div><span>Merchant offer savings</span><strong>−{money(receipt.savings_cents,receipt.currency)}</strong></div><div className="order-summary-total"><span>Amount captured</span><strong>{money(receipt.total_cents,receipt.currency)}</strong></div></div>
      <div className="order-summary-proof"><small>PAYMENT METHOD</small><span>PayPal Sandbox</span><small>PAYMENT STATUS</small><span>Completed · capture verified</span><small>PAYPAL SANDBOX ORDER</small><span>{receipt.paypal_sandbox_order_id}</span>{receipt.paypal_sandbox_authorization_id&&<><small>AUTHORIZATION</small><span>{receipt.paypal_sandbox_authorization_id}</span></>}<small>CAPTURE</small><span>{receipt.paypal_sandbox_capture_id}</span></div>
      {receipt.deal_rescue_id&&<div className="order-summary-meta"><div><small>DEAL RESCUE CASE</small><strong>{receipt.deal_rescue_id}</strong></div>{receipt.buyer_maximum_cents!=null&&<div><small>BUYER MAXIMUM</small><strong>{money(receipt.buyer_maximum_cents,receipt.currency)}</strong></div>}{receipt.authorized_at&&<div><small>PAYPAL AUTHORIZED</small><strong>{new Date(receipt.authorized_at).toLocaleString()}</strong></div>}{receipt.seller_approved_at&&<div><small>SELLER APPROVED</small><strong>{new Date(receipt.seller_approved_at*1000).toLocaleString()}</strong></div>}</div>}
      {receipt.merchant_explanation&&<p className="order-summary-disclosure">Merchant explanation: {receipt.merchant_explanation}</p>}
      <section className="order-decision-map" aria-label="Decision receipt"><span>DECISION RECEIPT</span><h2>How this order happened</h2><p>{receipt.room_members?.length?`Shared room: ${receipt.room_members.join(" and ")}. `:""}{receipt.payer?`${receipt.payer} was the designated payer.`:""}</p><ol>{(receipt.decision_trail||[]).map((event,index)=><li key={`${event.event}-${index}`}><strong>{event.label}</strong><small>{event.actor&&event.actor!=="system"?`${event.actor} · `:""}{new Date(event.at*1000).toLocaleString()}</small></li>)}</ol>{!receipt.decision_trail?.length&&<p>No additional decision events were recorded for this order.</p>}<small>Room membership does not imply that every member approved payment.</small></section>
      <p className="order-summary-disclosure">{receipt.disclosure} Shipping and taxes were not calculated for this sandbox order.</p><button type="button" onClick={()=>window.print()}>Print or save as PDF</button>
    </article>}</div></main>;
}
