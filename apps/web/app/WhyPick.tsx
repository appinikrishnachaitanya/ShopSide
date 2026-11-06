"use client";
import { Lightbulb, CircleDollarSign, MessageCircle, ScanSearch } from "lucide-react";
const reactions:Record<string,string>={love:"❤️ Loves it",price:"💸 Too pricey",size:"📏 Check the size",discuss:"🤔 Let's discuss"};
export default function WhyPick({room,product}:{room:any;product:any}) {
  if(!product)return null;
  const mission=room.move_in?.mission;
  const budget=mission?.budget_cents ?? room.budget;
  const currency=mission?.currency || 'USD';
  const offers=(product.offers || []).filter((o:any)=>o.currency===currency && typeof o.price_cents==='number');
  const prices:number[]=offers.map((o:any)=>o.price_cents);
  if(product.currency===currency && typeof product.price==='number')prices.push(product.price);
  const cheapest=prices.length ? Math.min(...prices) : null;
  let budgetText='Set a budget to compare this item.';
  if(budget != null && cheapest == null)budgetText=`No ${currency} price available to compare with your budget.`;
  else if(budget != null && cheapest != null)budgetText=`${currency} ${(cheapest/100).toFixed(2)} is ${cheapest<=budget?'within':'over'} your total budget of ${(budget/100).toFixed(2)} for this item alone.`;
  const facts:string[]=[];
  if(product.category)facts.push(`Category: ${product.category}`);
  if(product.key_features?.length)facts.push(...product.key_features.filter((x:any)=>typeof x==='string').slice(0,2));
  const attrs=product.attributes || {};
  const dim=Object.entries(attrs).filter(([k,v])=>/dimension|height|width|depth|weight/i.test(k) && (typeof v==='string'||typeof v==='number'));
  dim.slice(0,2).forEach(([k,v])=>facts.push(`${k.replace(/_/g,' ')}: ${v}`));
  const offerDims=(product.offers || []).find((o:any)=>o.dimensions && Object.keys(o.dimensions).length)?.dimensions;
  const needs:string[]=[];
  if(!dim.length && !offerDims)needs.push('Dimensions not provided; check the retailer before deciding on fit.');
  needs.push(product.provenance==='channel3'?'Price, availability and delivery need confirmation at the retailer.':'Fictional ShopSide sandbox item; no goods will ship.');
  return <section className="why-pick" aria-label="Why this pick">
    <div className="why-pick-head"><span className="why-icon"><Lightbulb size={18}/></span><div><span className="section-kicker">A LITTLE CLARITY</span><h3>Why this pick?</h3></div></div>
    <p className="why-intro">A quick look at what you know about <strong>{product.name}</strong>.</p>
    <div className="why-grid">
      <div><span className="why-label"><CircleDollarSign size={15}/> BUDGET</span><p>{budgetText}</p></div>
      <div><span className="why-label"><ScanSearch size={15}/> PRODUCT DETAILS</span>{facts.length?<ul>{facts.map((f,i)=><li key={i}>{f}</li>)}</ul>:<p>No comparable details provided yet.</p>}</div>
      <div><span className="why-label"><Lightbulb size={15}/> WORTH CHECKING</span><ul>{needs.map(x=><li key={x}>{x}</li>)}</ul></div>
      <div><span className="why-label"><MessageCircle size={15}/> TOGETHER</span>{room.people.map((person:string)=>{const reaction=room.marker_reactions?.[product.id]?.[person];const approval=room.move_in?.items?.[product.id]?.approvals?.[person] || room.agreement_votes?.[person]===product.id;return <p key={person}><strong>{person}:</strong> {reaction ? reactions[reaction] || 'Shared a reaction' : 'No room reaction yet'}{approval?' · explicitly approved':''}</p>})}</div>
    </div>
    {!!Object.keys(room.preferences || {}).length && <p className="why-context">Your stated preferences: {Object.entries(room.preferences).map(([name,value])=>`${name}: ${String(value)}`).join(' · ')}. Check the product details above to see whether they match.</p>}
    <small>Based on the information currently available. Prices can change, and unknown details are not assumed.</small>
  </section>;
}
