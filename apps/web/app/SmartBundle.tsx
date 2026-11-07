"use client";
import { useState } from "react";
import { sessionFetch } from "./lib/session";

type Props = { room: any; me: any; online: boolean; selectProduct: (id: string) => void };
const labels: Record<string,string> = {best_match:'Best match',budget_saver:'Budget saver',one_seller:'One seller',custom:'Your bundle'};
const money = (cents: number, currency: string) => `${currency} ${(cents / 100).toFixed(2)}`;

export default function SmartBundle({room,me,online,selectProduct}:Props) {
  const [working,setWorking]=useState(false),[error,setError]=useState(''),[amount,setAmount]=useState(''),[alternatives,setAlternatives]=useState<any>(null);
  const intent=room.shopping_intent, bundle=room.smart_bundle || {}, selected=bundle.selected;
  if (!intent?.bundle_requested || (intent.product_requirements || []).length < 2) return null;
  const mission=room.move_in?.mission;
  const budget=mission?.budget_cents ?? room.budget ?? intent.budget_cents;
  const currency=mission?.budget_cents != null ? mission.currency : room.budget != null ? 'USD' : intent.currency;
  const progress=bundle.progress;
  async function request(path:string,body?:any) {
    const response=await sessionFetch(`/api/rooms/${room.id}/bundle/${path}`,body === undefined ? undefined : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if (!response.ok) { const data=await response.json().catch(()=>({}));throw new Error(typeof data.detail==='string'?data.detail:'Please try again.'); }
    return response.json();
  }
  async function perform(path:string,body?:any) {
    setWorking(true);setError('');
    try { const result=await request(path,body); return result; }
    catch(e:any){setError(e.message);return null;} finally {setWorking(false);}
  }
  async function action(action:string,fields:any={}) {
    const result=await perform('action',{action,expected_version:bundle.version,command_id:crypto.randomUUID(),...fields});
    if(result && action==='swap')setAlternatives(null);
  }
  async function showAlternatives(slot:string) {
    const result=await perform(`alternatives/${encodeURIComponent(slot)}`);
    if(result)setAlternatives(result);
  }
  const agreed = selected && room.people.length >= 2 && room.people.every((name:string)=>bundle.approvals?.[name]===bundle.version);
  return <section className="smart-bundle" aria-label="Smart Bundle">
    <div className="smart-bundle-heading"><div><span className="section-kicker">SHOP TOGETHER · SMART BUNDLE</span><h2>Your bundle matches</h2><p>{intent.shopping_goal || 'Your shared shopping goal'} · {(intent.product_requirements || []).join(' + ')}</p></div>{budget!=null && currency && <strong>{money(budget,currency)} budget</strong>}</div>
    <p className="bundle-caveat">Retailer prices are observed, not guaranteed. Check shipping, tax, availability and compatibility with each retailer.</p>
    <p className="bundle-caveat">AI match is an uncalibrated model assessment. Evidence describes the completeness of returned product and retailer data, not a guarantee.</p>
    {(budget==null || !currency) && <div className="bundle-budget"><label>Set a total budget (USD)<input aria-label="Total bundle budget" type="number" min="0" step="0.01" value={amount} onChange={e=>setAmount(e.target.value)} /></label><button disabled={!online || working || !me?.is_payer || !amount || !Number.isFinite(Number(amount)) || Number(amount)<0} onClick={()=>perform('budget',{amount_cents:Math.round(Number(amount)*100),currency:'USD',expected_version:bundle.version || 0,command_id:crypto.randomUUID()})}>Save budget</button>{!me?.is_payer && <small>{room.payer} can set the budget.</small>}</div>}
    {error && <p role="alert">{error}</p>}{bundle.error && <p role="alert">{bundle.error}</p>}
    {progress && <p role="status">{progress.phase === 'comparing' ? 'Comparing retailer offers and building combinations…' : progress.phase === 'ready' ? 'Preparing and verifying recommendations…' : `Finding products: ${progress.completed.length} of ${progress.requirements.length} searches completed${progress.completed.length ? ` · ${progress.completed.join(', ')}` : '…'}`}</p>}
    {bundle.agent_activity && <details className="bundle-agent-activity"><summary>Agent activity · {bundle.agent_activity.status}</summary><p>{bundle.agent_activity.search_count != null ? `${bundle.agent_activity.search_count} searches · ${bundle.agent_activity.candidate_count} candidates · ${bundle.agent_activity.bundle_count} bundles · ${bundle.agent_activity.elapsed_ms} ms` : 'Working with verified tool results.'}</p>{(bundle.agent_activity.tools || []).map((entry:any,index:number)=><small key={index}>{entry.tool} · {entry.outcome}{entry.elapsed_ms != null ? ` · ${entry.elapsed_ms} ms` : ''}</small>)}</details>}
    <button className="bundle-search-button" disabled={!online || working || !!progress || budget==null || !currency} onClick={()=>perform('search',{command_id:crypto.randomUUID()})}>{working || progress ? 'Finding combinations…' : 'Find bundles'}</button>
    {Array.isArray(bundle.options) && !bundle.options.length && !progress && <p>No complete combinations were found within this budget. Try another budget or search.</p>}
    {Array.isArray(bundle.options) && bundle.options.length>0 && !bundle.one_seller_available && <p>No single-seller combination found.</p>}
    <div className="bundle-cards">{(bundle.options || []).map((option:any)=><article key={option.id} className={'bundle-card'+(selected?.id===option.id?' selected':'')}>
      <span className="bundle-kind">{labels[option.kind] || option.kind}{option.also_qualifies?.length ? ` · Also ${option.also_qualifies.map((kind:string)=>labels[kind] || kind).join(' · ')}` : ''}</span><div className="bundle-thumbnails">{option.items.map((item:any)=><div key={item.slot_id}>{item.product.image && <img src={item.product.image} alt=""/>}<strong>{item.product.name}</strong><small>{money(item.offer.price_cents,option.currency)} · {item.offer.retailer}</small></div>)}</div>
      <strong>{money(option.subtotal_cents,option.currency)}</strong><small>{money(option.remaining_cents,option.currency)} remaining before shipping and tax</small><small>{option.fit_score != null ? `AI match: ${option.fit_score}/100 · ` : ''}Evidence: {option.evidence_confidence || 'Not assessed'}</small>{option.ai_confidence_score != null && <small>Model self-assessment: {option.ai_confidence_score}/100 (not a calibrated probability)</small>}
      <p>{option.kind==='budget_saver'?'Lowest observed complete combination.':option.kind==='one_seller'?'Every selected offer is from the same retailer.':'Matches available product names and stated preferences where supported.'}</p>
      <button disabled={!online || working || !!progress} onClick={()=>action('select',{bundle_id:option.id})}>{selected?.id===option.id?'Choose again':'Choose bundle'}</button>
    </article>)}</div>
    {selected && <div className="bundle-selected"><div className="bundle-selected-head"><div><span className="section-kicker">SHARED SELECTION · VERSION {bundle.version}</span><h3>{labels[selected.kind] || 'Your bundle'}</h3></div><strong>{money(selected.subtotal_cents,selected.currency)}</strong></div>
      <div className="bundle-meter"><div style={{width:`${selected.budget_cents ? Math.min(100,selected.subtotal_cents/selected.budget_cents*100) : 0}%`}} /></div><p>{money(selected.remaining_cents,selected.currency)} remaining before shipping and tax.</p>
      {selected.items.map((item:any)=><div className="bundle-item" key={item.slot_id}><div>{item.product.image && <img src={item.product.image} alt=""/>}<span><strong>{item.product.name}</strong><small>{item.requirement} · {money(item.offer.price_cents,selected.currency)} · {item.offer.retailer} · {item.offer.availability}</small><small>{item.match_explanation}</small>{item.product.retrieved_at && <small>Observed {new Date(item.product.retrieved_at * 1000).toLocaleString()}</small>}{!!item.unverified_constraints?.length && <small>Check: {item.unverified_constraints.join(', ')}</small>}<a href={item.offer.url} target="_blank" rel="noopener noreferrer">View retailer ↗</a></span></div><div><button onClick={()=>selectProduct(item.product.id)}>Details</button><button disabled={!online || working} onClick={()=>showAlternatives(item.slot_id)}>Swap {item.requirement}</button></div></div>)}
      {alternatives && alternatives.version===bundle.version && <div className="bundle-alternatives"><div><strong>Choose an alternative</strong><button onClick={()=>setAlternatives(null)} aria-label="Close alternatives">×</button></div><button disabled={!online || working} onClick={async()=>{const slot=alternatives.slot_id;const result=await perform(`alternatives/${encodeURIComponent(slot)}/search`,{expected_version:bundle.version,command_id:crypto.randomUUID()});if(result)await showAlternatives(slot);}}>{working?'Searching…':'Find more alternatives with AI'}</button>{alternatives.alternatives.map((candidate:any)=><div className="bundle-alternative" key={candidate.offer.id}>{candidate.product.image && <img src={candidate.product.image} alt=""/>}<span><strong>{candidate.product.name}</strong><small>{money(candidate.offer.price_cents,selected.currency)} · {candidate.offer.retailer}{candidate.product.alternative_fit_score != null ? ` · AI match ${candidate.product.alternative_fit_score}/100` : ''}</small><small>New total: {money(candidate.new_total_cents,selected.currency)}{candidate.new_total_cents>selected.budget_cents ? ` · Over budget by ${money(candidate.new_total_cents-selected.budget_cents,selected.currency)}` : ''}</small></span><button disabled={!online || working || candidate.new_total_cents>selected.budget_cents} onClick={()=>action('swap',{slot_id:alternatives.slot_id,product_id:candidate.product.id,offer_id:candidate.offer.id})}>Use this</button></div>)}</div>}
      <div className="bundle-approval"><strong>{agreed?'Everyone approved this bundle':room.people.length<2?'Invite someone to decide together':'Waiting for everyone’s approval'}</strong><div>{room.people.map((person:string)=><span key={person}>{person}: {bundle.approvals?.[person]===bundle.version?'Approved':'Deciding'}</span>)}</div><div><button disabled={!online || working} onClick={()=>action(bundle.approvals?.[me?.name]===bundle.version?'withdraw':'approve')}>{bundle.approvals?.[me?.name]===bundle.version?'Withdraw approval':'Approve bundle'}</button><button disabled={!online || working} onClick={()=>action('save')}>Save to shared plan</button></div><small>Approval is a shared decision, not payment authorization.</small></div>
    </div>}
  </section>;
}
