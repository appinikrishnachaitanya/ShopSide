"use client";
import { useEffect, useState } from "react";
import { ArrowUpRight, House, Sparkles, Users } from "lucide-react";

type Props = { room: any; online: boolean; me: any; api: (path: string, body?: any) => Promise<any>; initialLoading?: boolean; onResults?: () => void };
export default function MoveIn({ room, online, me, api, initialLoading = false, onResults }: Props) {
  const state = room.move_in;
  const [mission, setMission] = useState<any>(state?.mission);
  const [answer, setAnswer] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const [shares, setShares] = useState<Record<string,string>>({});
  const [shareMode, setShareMode] = useState("amount");
  const [shareTotal, setShareTotal] = useState("");
  useEffect(() => setMission(state?.mission), [state?.mission]);
  if (!state || !mission) return null;
  const entries = Object.values(state.items || {}) as any[];
  const searchBrief = [state.history?.filter((h:any)=>h.actor !== "ShopSide").map((h:any)=>h.text).join(" "), ...(mission.priorities || []), ...(mission.must_have || [])].filter(Boolean).join(" ").slice(0,500);
  const knownTotal = entries.reduce((sum,item)=>sum+(item.currency === mission.currency ? item.observed_price_cents || 0 : 0),0);
  const unknownPrices = entries.some(item=>item.observed_price_cents == null || item.currency !== mission.currency);
  async function post(path:string, data:any) {
    setWorking(true);setError("");
    try { await api(`rooms/${room.id}/move-in/${path}`, {...data, revision:room.revision, command_id:crypto.randomUUID()}); return true; }
    catch (e:any) { setError(e.message || "Please try again."); return false; }
    finally { setWorking(false); }
  }
  const update = (key:string, value:any) => setMission({...mission,[key]:value});
  const list = (key:string) => (mission[key] || []).join(", ");
  const split = (key:string, value:string) => update(key,value.split(",").map(x=>x.trim()).filter(Boolean));
  return <section className="move-studio" aria-label="Move-In Studio">
    <div className="move-header"><div><span className="section-kicker">YOUR NEXT CHAPTER</span><h2>Move in, together<span className="period">.</span></h2><p>A practical plan for the home you’re building together.</p></div><span className="move-badge">MOVE-IN STUDIO</span></div>
    {error && <p role="alert" className="concierge-error">{error}</p>}
    <div className="move-progress" aria-label="Your move-in progress">
      <div><span className="progress-icon"><Sparkles size={15}/></span><span><strong>01. Make a plan</strong><small>{state.history?.length ? "Your brief is started" : "Start with your story"}</small></span></div>
      <div><span className="progress-icon"><House size={15}/></span><span><strong>02. Find your favorites</strong><small>{entries.length ? `${entries.length} item${entries.length === 1 ? "" : "s"} in your plan` : "Discover something good"}</small></span></div>
      <div><span className="progress-icon"><Users size={15}/></span><span><strong>03. Decide together</strong><small>{room.people.length > 1 ? "You’re in this together" : "Invite your person"}</small></span></div>
    </div>
    <div className="move-layout">
      <div className="move-card move-card-mission"><div className="move-card-top"><span className="section-kicker">01 / YOUR MISSION</span><span className="move-card-icon"><Sparkles size={17}/></span></div><h3>The blueprint</h3>
        <p className="move-hint">Tell the assistant more, or edit the details yourself. It asks at most four questions.</p>
        {initialLoading && <p role="status" className="move-loading">Reading your request and preparing your mission…</p>}
        {state.history?.map((h:any,i:number)=><p className="move-history" key={i}><strong>{h.actor}: </strong>{h.text}</p>)}
        {state.question && <p className="move-question">{state.question}</p>}
        <form onSubmit={e=>{e.preventDefault();post("turn",{text:answer}).then(ok=>{if(ok)setAnswer("");});}}><label>Tell us more<input value={answer} onChange={e=>setAnswer(e.target.value)} maxLength={2000} placeholder="A home office and kitchen under $500" /></label><button disabled={!online || working || initialLoading || !answer.trim()}>{working ? "Working…" : "Update with AI"}</button></form>
        <details><summary>Edit mission details</summary><div className="move-fields">
          <label>Household<input value={mission.household} onChange={e=>update("household",e.target.value)} /></label>
          <label>Country code<input maxLength={2} value={mission.country} onChange={e=>update("country",e.target.value.toUpperCase())} /></label>
          <label>Currency<input maxLength={3} value={mission.currency} onChange={e=>update("currency",e.target.value.toUpperCase())} /></label>
          <label>Target date<input type="date" value={mission.deadline || ""} onChange={e=>update("deadline",e.target.value || null)} /></label>
          <label>Budget in cents<input type="number" min="0" value={mission.budget_cents ?? ""} onChange={e=>update("budget_cents",e.target.value === "" ? null : Number(e.target.value))} /></label>
          {[["priorities","Room and category priorities"],["owned","Already owned"],["must_have","Must have"],["later","Buy later"],["constraints","Constraints"]].map(([key,label])=><label key={key}>{label} (comma separated)<input defaultValue={list(key)} key={key+list(key)} onBlur={e=>split(key,e.target.value)} /></label>)}
        </div><button disabled={!online || working} onClick={()=>post("mission",{mission})}>Save mission</button></details>
        <div className="move-budget"><span>MOVE-IN BUDGET</span><strong>{mission.budget_cents == null ? "Not set" : `${mission.currency} ${(mission.budget_cents/100).toFixed(2)}`}</strong><small>Known selection prices: {mission.currency} {(knownTotal/100).toFixed(2)}{unknownPrices ? " · some prices unavailable" : ""}. Retailer prices may change.</small>{mission.budget_cents > 0 && <progress aria-label="Known selection prices against budget" value={Math.min(knownTotal, mission.budget_cents)} max={mission.budget_cents} />}</div>
      </div>
      <div className="move-card move-card-plan"><div className="move-card-top"><span className="section-kicker">02 / THE PLAN</span><span className="move-card-icon"><ArrowUpRight size={18}/></span></div><h3>Make the choices yours</h3><p className="move-hint">Explore live products below, focus an option and add it to your plan. Retailer checkout stays with the retailer.</p><button disabled={!online || working || !searchBrief.trim()} onClick={async()=>{setWorking(true);setError("");try{await api(`rooms/${room.id}/search`,{query:searchBrief,mode:"agentic",country:mission.country || undefined,currency:mission.currency,max_price:mission.budget_cents == null ? undefined : mission.budget_cents/100,revision:room.revision,command_id:crypto.randomUUID()});onResults?.();}catch(e:any){setError(e.message || "Live product search is unavailable.");}finally{setWorking(false);}}}>{working ? "Searching…" : "Find essentials with Channel3"}</button>
        {room.focus && <button disabled={!online || working} onClick={()=>post("item",{product_id:room.focus,status:"proposed"})}>Add focused item to plan</button>}
        {!entries.length && <p className="move-empty"><span className="empty-spark">✳</span>Your plan starts with one good find.</p>}
        {entries.map(item=><div className="move-item" key={item.product_id}><strong>{item.name}</strong><span>{item.status.replace("_"," ")}</span>{item.observed_price_cents != null && <small>{item.currency} {(item.observed_price_cents/100).toFixed(2)} observed · verify current price</small>}<div>{room.people.map((person:string)=><small key={person}>{person}: {item.approvals?.[person] ? "approved" : "not approved"} </small>)}</div><div className="move-actions"><button disabled={!online || working || item.status === "purchased"} onClick={()=>post("item",{product_id:item.product_id,approve:!item.approvals?.[me?.name]})}>{item.approvals?.[me?.name] ? "Withdraw approval" : "I approve"}</button><select disabled={item.status === "purchased"} aria-label={`Status for ${item.name}`} value={["proposed","shortlisted","comparing","buy_later"].includes(item.status)?item.status:"proposed"} onChange={e=>post("item",{product_id:item.product_id,status:e.target.value})}><option value="proposed">Proposed</option><option value="shortlisted">Shortlisted</option><option value="comparing">Comparing</option><option value="buy_later">Buy later</option></select></div></div>)}
      </div>
      <div className="move-card move-card-together"><div className="move-card-top"><span className="section-kicker">03 / TOGETHER</span><span className="move-card-icon"><Users size={17}/></span></div><h3>Decisions, shared</h3><p className="move-hint">Use the shared decision assistant below to weigh everyone’s preferences. All members must approve a choice.</p><button disabled={!online || working || room.people.length < 2} onClick={async()=>{setWorking(true);setError("");try{await api(`rooms/${room.id}/agent`,{revision:room.revision,text:"Using all participants’ stated preferences, current shortlisted Channel3 products, and the move-in budget, suggest style-first, budget-first, and balanced options. Cite available evidence and uncertainty, identify disagreements, and never imply agreement or make cart changes."});}catch(e:any){setError(e.message || "The decision assistant is unavailable.");}finally{setWorking(false);}}}>Ask AI for a compromise</button><div className="move-people">{room.people.map((p:string)=><span key={p}>{p}</span>)}</div>
        <details><summary>Record a cost share</summary><p className="move-hint">A record only; no one is charged.</p>
          <label>Allocation method<select value={shareMode} onChange={e=>{setShareMode(e.target.value);setShares({});}}><option value="amount">Amounts in cents</option><option value="percentage">Percentages</option></select></label>
          {shareMode === "percentage" && <label>Total in cents<input type="number" min="0" step="1" value={shareTotal} onChange={e=>setShareTotal(e.target.value)} /></label>}
          {room.people.map((p:string)=><label key={p}>{p} {shareMode === "percentage" ? "%" : "cents"}<input type="number" min="0" step={shareMode === "percentage" ? "0.01" : "1"} value={shares[p] || ""} onChange={e=>setShares({...shares,[p]:e.target.value})} /></label>)}
          <button disabled={!online || working || room.people.some((p:string)=>shares[p]===undefined || shares[p]==="") || (shareMode === "percentage" && shareTotal === "")} onClick={()=>{
            if (shareMode === "percentage") {const basis_points=Object.fromEntries(room.people.map((p:string)=>[p,Math.round(Number(shares[p])*100)]));post("allocation-percent",{total_cents:Number(shareTotal),currency:mission.currency,basis_points});}
            else {const amounts=Object.fromEntries(room.people.map((p:string)=>[p,Number(shares[p])]));post("allocation",{total_cents:Object.values(amounts).reduce((a:any,b:any)=>a+b,0),currency:mission.currency,shares:amounts});}
          }}>Record shares</button></details>
        {state.allocation && <p className="move-hint">Recorded: {Object.entries(state.allocation.shares).map(([p,v]:any)=>`${p}: ${state.allocation.currency} ${(v/100).toFixed(2)}`).join(" · ")}. No payment taken.</p>}
        <h4>Shared timeline</h4>{!state.timeline?.length && <p className="move-empty">Your shared decisions will appear here.</p>}{[...(state.timeline || [])].reverse().slice(0,6).map((event:any,i:number)=><p key={i} className="move-timeline"><strong>{event.actor}</strong> {event.event}</p>)}
      </div>
    </div>
  </section>;
}
