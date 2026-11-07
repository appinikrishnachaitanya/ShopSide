"use client";
import {useEffect,useState} from "react";
import {useParams} from "next/navigation";
import {sessionFetch} from "../../lib/session";

type Line={product_id:string;name:string;quantity:number;reference_price_cents:number};
type Receipt={order_id:string;merchant_name:string;items:Line[];reference_total_cents:number;total_cents:number;savings_cents:number;currency:string;paypal_sandbox_order_id:string;paypal_sandbox_capture_id:string;paid_at:string;disclosure:string};
const money=(cents:number,currency:string)=>new Intl.NumberFormat("en-US",{style:"currency",currency}).format(cents/100);

export default function OrderSummary(){
  const {orderId}=useParams<{orderId:string}>();
  const [receipt,setReceipt]=useState<Receipt|null>(null),[error,setError]=useState(""),[roomId,setRoomId]=useState("");
  useEffect(()=>{
    const room=new URLSearchParams(window.location.search).get("room")||"";
    setRoomId(room);
    if(!room||!orderId){setError("A room and completed order are required.");return;}
    let active=true;
    sessionFetch(`/api/rooms/${encodeURIComponent(room)}/merchant-orders/${encodeURIComponent(orderId)}/receipt`)
      .then(async response=>{const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.detail||"Completed order unavailable.");return data as Receipt;})
      .then(data=>{if(active)setReceipt(data);})
      .catch(err=>{if(active)setError(err.message)});
    return()=>{active=false};
  },[orderId]);
  return <main className="order-summary-page"><div className="order-summary-shell"><header><a href={roomId?`/?room=${encodeURIComponent(roomId)}`:"/"}>← Back to shopping room</a><span>SHOP<span>SIDE</span> · ORDER SUMMARY</span></header>
    {error?<div role="alert" className="order-summary-card"><h1>Order summary unavailable</h1><p>{error}</p></div>:!receipt?<p role="status">Loading your completed order…</p>:<article className="order-summary-card"><div className="order-summary-hero"><span>PAYPAL SANDBOX · CAPTURE VERIFIED</span><h1>Chosen together. Paid in sandbox.</h1><p>A record of your ShopSide merchant order.</p></div>
      <div className="order-summary-meta"><div><small>SHOPSIDE ORDER</small><strong>{receipt.order_id}</strong></div><div><small>MERCHANT</small><strong>{receipt.merchant_name}</strong></div><div><small>PAID AT</small><strong>{new Date(receipt.paid_at).toLocaleString()}</strong></div></div>
      <h2>Items</h2><div className="order-summary-lines">{receipt.items.map(line=><div key={line.product_id}><span>{line.name}<small>Quantity {line.quantity}</small></span><strong>{money(line.reference_price_cents*line.quantity,receipt.currency)}</strong></div>)}</div>
      <div className="order-summary-totals"><div><span>Listed item subtotal</span><strong>{money(receipt.reference_total_cents,receipt.currency)}</strong></div><div><span>Merchant offer savings</span><strong>−{money(receipt.savings_cents,receipt.currency)}</strong></div><div className="order-summary-total"><span>Amount captured</span><strong>{money(receipt.total_cents,receipt.currency)}</strong></div></div>
      <div className="order-summary-proof"><small>PAYPAL SANDBOX ORDER</small><span>{receipt.paypal_sandbox_order_id}</span><small>CAPTURE</small><span>{receipt.paypal_sandbox_capture_id}</span></div>
      <p className="order-summary-disclosure">{receipt.disclosure} Shipping and taxes were not calculated for this sandbox order.</p><button type="button" onClick={()=>window.print()}>Print order summary</button>
    </article>}</div></main>;
}
