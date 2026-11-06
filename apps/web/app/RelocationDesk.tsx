"use client";
import {useState} from "react";
import {AgGridReact} from "ag-grid-react";
import {AllCommunityModule,ModuleRegistry,themeQuartz} from "ag-grid-community";
ModuleRegistry.registerModules([AllCommunityModule]);
export default function RelocationDesk() {
  const [token,setToken]=useState(""); const [name,setName]=useState("");
  const [allowance,setAllowance]=useState(""); const [threshold,setThreshold]=useState("");
  const [categories,setCategories]=useState("kitchen, home office, bedroom, living room");
  const [code,setCode]=useState(""); const [ledger,setLedger]=useState<any>(null); const [error,setError]=useState("");
  async function call(path:string,body?:any){
    setError("");try{
      const response=await fetch('/api/relocation/'+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
      const result=await response.json();if(!response.ok)throw Error(result.detail || 'Request failed');return result;
    }catch(e:any){setError(e.message);return null;}
  }
  return <details className="relocation-desk"><summary>Illustrative Employer Relocation Desk</summary><p>For authorized administrators. This is a standalone policy scenario; it is not connected to payroll or HR systems. Room conversations remain private.</p>
    {error && <p role="alert">{error}</p>}
    <label>Administrator access token<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)} /></label>
    <label>Policy name<input value={name} onChange={e=>setName(e.target.value)} placeholder="Relocation allowance" /></label>
    <label>Allowance in cents<input type="number" min="0" value={allowance} onChange={e=>setAllowance(e.target.value)} /></label>
    <label>Approval threshold in cents<input type="number" min="0" value={threshold} onChange={e=>setThreshold(e.target.value)} /></label>
    <label>Eligible categories, comma separated<input value={categories} onChange={e=>setCategories(e.target.value)} /></label>
    <button type="button" disabled={!token || !name || allowance==='' || threshold===''} onClick={async()=>{const result=await call('policies',{name,allowance_cents:Number(allowance),currency:'USD',approval_threshold_cents:Number(threshold),eligible_categories:categories.split(',').map(x=>x.trim()).filter(Boolean)});if(result)setCode(result.code);}}>Create allocation</button>
    <label>Allocation code<input value={code} onChange={e=>setCode(e.target.value)} /></label><small>Share this private code with the employee. Anyone with it can create a room from this allocation.</small>
    <button type="button" disabled={!code || !token} onClick={async()=>{const result=await call('policies/'+encodeURIComponent(code)+'/ledger');if(result)setLedger(result);}}>View purchase ledger</button>
    {ledger && <><p>Verified sandbox purchases: USD {(ledger.spent_cents/100).toFixed(2)}. Amount is the sum across rooms; each room receives its own allowance.</p><div style={{height:220,width:'100%'}}><AgGridReact theme={themeQuartz.withParams({backgroundColor:'#171b16',foregroundColor:'#dbe5d6',headerBackgroundColor:'#22291f',accentColor:'#c5f874'})} rowData={ledger.entries} columnDefs={[{field:'status'},{field:'total_cents',headerName:'Total (cents)'},{field:'currency'},{field:'payment_reference',headerName:'Receipt reference'}]} /></div></>}
  </details>;
}
