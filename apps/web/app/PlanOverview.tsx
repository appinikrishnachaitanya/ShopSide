"use client";
import {useEffect,useState} from "react";
import {ArrowRight, Check, Compass, Pencil, Scale, Users} from "lucide-react";

type Props={room:any;me:any;online:boolean;products:any[];showRoomOption:boolean;api:(path:string,body?:any)=>Promise<any>;onState:(state:any)=>void;onDiscover:()=>void;onCompare:()=>void;onRoom:()=>void;toggleShortlist:(id:string)=>void};
const money=(cents:number,currency:string)=>`${currency} ${(cents/100).toFixed(2)}`;
export default function PlanOverview({room,me,online,products,showRoomOption,api,onState,onDiscover,onCompare,onRoom,toggleShortlist}:Props){
 const mission=room.move_in?.mission;
 const currency=mission?.currency||room.shopping_intent?.currency||"USD";
 const budget=mission?.budget_cents??room.budget??room.shopping_intent?.budget_cents;
 const [editing,setEditing]=useState(false),[amount,setAmount]=useState(""),[saving,setSaving]=useState(false),[error,setError]=useState("");
 const [preferenceDraft,setPreferenceDraft]=useState(""),[savingPreference,setSavingPreference]=useState(false),[preferenceError,setPreferenceError]=useState("");
 useEffect(()=>{if(!editing)setAmount(budget==null?"":(budget/100).toFixed(2))},[budget,editing]);
 useEffect(()=>setPreferenceDraft(String(room.preferences?.[me?.name]||"")),[room.preferences?.[me?.name],me?.name]);
 const saved=room.smart_bundle?.saved;
 const shortlist=(room.shortlist||[]).map((id:string)=>products.find((item:any)=>item.id===id)).filter(Boolean);
 const canCompare=shortlist.length>=2&&shortlist.length<=3;
 async function saveBudget(){
  const parsed=Number(amount);
  if(!Number.isFinite(parsed)||parsed<0||!/^\d+(?:\.\d{1,2})?$/.test(amount.trim())){setError("Enter a budget with up to two decimal places.");return}
  setSaving(true);setError("");
  try{const state=await api(`rooms/${room.id}/plan/budget`,{amount_cents:Math.round(parsed*100),currency,revision:room.revision,command_id:crypto.randomUUID()});onState(state);setEditing(false)}
  catch(e:any){setError(e.message||"Could not update the budget. Refresh and try again.")}
  finally{setSaving(false)}
 }
 async function openSavedRetailer(item:any){
  const tab=window.open('about:blank','_blank');
  try{const value=await api(`rooms/${room.id}/products/${encodeURIComponent(item.product.id.replace(/^channel3:/,''))}/retailer-link?retailer=${encodeURIComponent(item.offer.retailer)}`);if(tab){tab.opener=null;tab.location.href=value.url}else window.location.href=value.url}
  catch(e:any){tab?.close();setError(e.message||'Current retailer offer unavailable')}
 }
 async function savePreference(){
  setSavingPreference(true);setPreferenceError("");
  try{await api(`rooms/${room.id}/commands`,{kind:"preference",value:preferenceDraft.trim(),revision:room.revision,command_id:crypto.randomUUID()});onState(await api(`rooms/${room.id}`))}
  catch(e:any){setPreferenceError(e.message||"Could not save your preference. Refresh and try again.")}
  finally{setSavingPreference(false)}
 }
 return <section className="plan-overview" aria-label="Plan overview">
   <div className="plan-hero"><span className="section-kicker">YOUR SHARED PLAN</span><h2>Everything you’re choosing, in one place.</h2><p>Set the budget, keep the best ideas, compare them together, and decide when you’re ready.</p></div>
   <div className="plan-stats"><div className="plan-budget-stat"><span>YOUR TOTAL BUDGET</span><strong>{budget==null?"Not set":money(budget,currency)}</strong>{me?.is_payer?<button type="button" onClick={()=>{setAmount(budget==null?"":(budget/100).toFixed(2));setEditing(!editing);setError("")}}><Pencil size={14}/> {editing?"Cancel":"Edit budget"}</button>:<small>{room.payer} can edit the shared budget.</small>}</div><div><span>SHORTLIST</span><strong>{shortlist.length}</strong><small>{shortlist.length===1?"product":"products"} saved to compare</small></div><div><span>SAVED BUNDLE</span><strong>{saved?"1":"0"}</strong><small>{saved?"Retailer offer snapshot":"No bundle saved yet"}</small></div></div>
   {editing&&<div className="plan-budget-edit"><label>New total budget ({currency})<input aria-label="New total budget" type="number" min="0" max="1000000" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")void saveBudget()}}/></label><button disabled={!online||saving||!amount.trim()} onClick={saveBudget}>{saving?"Saving…":"Save budget"}</button><small>Changing the budget clears current bundle matches and approvals. Your saved bundle stays as a snapshot.</small>{error&&<p role="alert">{error}</p>}</div>}
   <section className="plan-preferences" aria-label="Shared preferences"><div><span className="section-kicker">SHOPPING PREFERENCES</span><h3>What matters to each of you?</h3><p>Your priorities stay visible to everyone in this room and help guide the discussion.</p></div><div className="plan-preference-list">{Object.entries(room.preferences||{}).filter(([,value])=>String(value).trim()).map(([person,value])=><p key={person}><strong>{person}</strong><span>{String(value)}</span></p>)}{!Object.values(room.preferences||{}).some(value=>String(value).trim())&&<p className="plan-empty">No priorities shared yet.</p>}</div><div className="plan-preference-edit"><label>Your preference<input aria-label="Your shopping preference" maxLength={1000} placeholder="e.g. comfortable for long calls" value={preferenceDraft} onChange={e=>setPreferenceDraft(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")void savePreference()}}/></label><button disabled={!online||savingPreference||preferenceDraft.trim()===String(room.preferences?.[me?.name]||"")} onClick={savePreference}>{savingPreference?"Saving…":"Save preference"}</button></div>{preferenceError&&<p role="alert">{preferenceError}</p>}</section>
   <div className="plan-next"><div><span className="section-kicker">NEXT STEP</span><h3>{shortlist.length>=2?"Compare your favorites.":"Find a few favorites."}</h3><p>{shortlist.length>=2?"See the evidence side by side, then talk it through in your room.":"Save two or three products to compare side by side."}</p></div><div className="plan-next-actions"><button onClick={onDiscover}><Compass size={16}/> Explore products</button><button disabled={!canCompare} onClick={onCompare}><Scale size={16}/> Compare saved products <ArrowRight size={15}/></button>{showRoomOption&&<button onClick={onRoom}><Users size={16}/> Open our room</button>}</div></div>
   <div className="plan-saves"><section><div className="plan-section-head"><span className="section-kicker">YOUR SHORTLIST</span><strong>{shortlist.length} {shortlist.length===1?"product":"products"}</strong></div>{shortlist.length?shortlist.map((item:any)=><div className="plan-shortlist-item" key={item.id}>{item.image&&<img src={item.image} alt=""/>}<div><strong>{item.name}</strong><small>{item.offers?.[0]?.price_cents!=null?`${item.offers[0].currency} ${(item.offers[0].price_cents/100).toFixed(2)} observed`:item.price!=null?money(item.price,item.currency||"USD"):"Price not provided"}</small></div><button onClick={()=>toggleShortlist(item.id)} aria-label={`Remove ${item.name} from shortlist`}>Remove</button></div>):<p className="plan-empty">Your shortlist is empty. Explore products and save the ones worth discussing.</p>}</section><section><div className="plan-section-head"><span className="section-kicker">SAVED BUNDLE</span>{saved&&<Check size={16}/>}</div>{saved?<><div className="plan-saved-title"><strong>{saved.items.map((item:any)=>item.product.name).join(" + ")}</strong><span>{money(saved.subtotal_cents,saved.currency)} observed</span></div><p>Saved retailer prices are snapshots. Check current price, availability, shipping, and fit before buying.</p>{saved.items.map((item:any)=><button key={item.slot_id} onClick={()=>openSavedRetailer(item)}>{item.product.name} · Check {item.offer.retailer} ↗</button>)}</>:<p className="plan-empty">A bundle you save in Discover will appear here for everyone in the room.</p>}</section></div>
 </section>
}
