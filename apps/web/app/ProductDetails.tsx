"use client";
import { sessionFetch } from "./lib/session";
import { useEffect, useState } from "react";
export default function ProductDetails({
  product,
  room,
  online,
}: {
  product: any;
  room: any;
  online: boolean;
}) {
  const [detail, setDetail] = useState<any>(null),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [lens,setLens]=useState<any>(null),
    [history,setHistory]=useState<any>(null);
  useEffect(() => {
    let active = true;
    setDetail(null);
    setLens(null);setHistory(null);
    setError("");
    sessionFetch(
      "/api/rooms/" +
        room.id +
        "/discovery/" +
        encodeURIComponent(product.provider_id),
    )
      .then(async (r) => {
        if (!r.ok) throw Error("Product details are unavailable.");
        return r.json();
      })
      .then((x) => {
        if (active) setDetail(x);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [product.id, product.retrieved_at, room.id]);
  async function action(
    kind: string,
    options: Record<string, string> = {},
    variantProductId?: string,
  ) {
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const response = await sessionFetch(
        "/api/rooms/" + room.id + "/product/" + kind,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider_id: product.provider_id,
            selected_options: options,
            variant_product_id: variantProductId,
            revision: room.revision,
            command_id: crypto.randomUUID(),
          }),
        },
      );
      if (!response.ok) {
        const d = await response.json();
        throw Error(d.detail || "Please try again");
      }
      const result = await response.json();
      if (kind === "cheaper") setNotice(result.count ? `${result.count} lower-priced similar products added below.` : "No lower-priced similar products found with a comparable currency.");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  const variants = detail?.variants;
  async function commerceView(kind:"seller-lens"|"price-intelligence"){
    setLoading(true);setError("");
    try{
      const response=await sessionFetch(`/api/rooms/${room.id}/products/${encodeURIComponent(product.provider_id)}/${kind}`);
      const value=await response.json().catch(()=>null);
      if(!response.ok)throw Error(value?.detail||"Price or seller data is temporarily unavailable. Please retry.");
      if(!value)throw Error("Price or seller data is temporarily unavailable. Please retry.");
      if(kind==="seller-lens"){setLens(value);setDetail(value.product)}else setHistory(value);
    }catch(e:any){setError(e.message)}finally{setLoading(false)}
  }
  async function openRetailer(retailer:string){
    const tab=window.open("about:blank","_blank");
    try{
      const response=await sessionFetch(`/api/rooms/${room.id}/products/${encodeURIComponent(product.provider_id)}/retailer-link?retailer=${encodeURIComponent(retailer)}`);
      const value=await response.json();if(!response.ok)throw Error(value.detail||"Retailer offer is unavailable.");
      if(tab){tab.opener=null;tab.location.href=value.url}else window.location.href=value.url;
    }catch(e:any){tab?.close();setError(e.message)}
  }
  function chooseVariant(option:any,label:string){
    const selectedValues=Object.fromEntries((variants.selected||[]).map((x:any)=>[x.name,x.label]));
    selectedValues[option.name]=label;
    const choice=option.values.find((x:any)=>x.label===label);
    action("resolve",selectedValues as Record<string,string>,choice?.product_id||undefined);
  }
  return (
    <section className="provider-details" aria-label="Product details">
      <div className="provider-details-heading">
        <span className="section-kicker">PRODUCT DETAILS · CHANNEL3</span>
        <button disabled={!online || loading} onClick={() => action("similar")}>
          Find similar products ↗
        </button>
        <button disabled={!online || loading} onClick={() => action("cheaper")}>Find a better price</button>
      </div>
      {notice && <p role="status">{notice}</p>}
      {!detail && !error && (
        <p role="status">Loading verified product details…</p>
      )}
      {error && (
        <p role="alert">
          {error} <button onClick={() => location.reload()}>Retry</button>
        </p>
      )}
      {detail && (
        <>
          <p>{detail.description || "No additional description available."}</p>
          {detail.key_features?.length > 0 && (
            <ul>
              {detail.key_features.slice(0, 6).map((x: string) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          )}
          {variants?.options?.map((option: any) => {
            const selected =
              variants.selected?.find((x: any) => x.name === option.name)
                ?.label || "";
            return (
              <fieldset className="variant-studio" key={option.name}><legend>{option.name} {selected&&<small>· {selected}</small>}</legend><div className="variant-choices">{option.values.map((value:any)=><button type="button" key={value.label} aria-label={`${option.name} ${value.label}`} aria-pressed={selected===value.label} disabled={!online||loading||value.exists===false||value.available==="OutOfStock"} onClick={()=>chooseVariant(option,value.label)}>{value.thumbnail_url&&<img src={value.thumbnail_url} alt=""/>}<span>{value.label}</span>{value.available==="OutOfStock"&&<small>Unavailable</small>}</button>)}</div></fieldset>
            );
          })}
          <div className="commerce-tools"><button disabled={loading} onClick={()=>commerceView("seller-lens")}>Seller Lens · compare offers</button><button disabled={loading} onClick={()=>commerceView("price-intelligence")}>Price Intelligence</button></div>
          {lens&&<section className="seller-lens" aria-label="Seller Lens"><h3>Same product. Different retailers.</h3><p>Observed {new Date(lens.observed_at*1000).toLocaleString()} · Listed prices exclude unknown delivery, taxes and fees.</p>{lens.offers?.map((offer:any)=><div key={offer.retailer+offer.url}><strong>{offer.retailer}</strong><span>{offer.price_cents==null?"Price unavailable":`${offer.currency} ${(offer.price_cents/100).toFixed(2)}`} · {offer.availability||"Availability unknown"}</span><button onClick={()=>openRetailer(offer.retailer)}>Check current retailer link ↗</button></div>)}{!lens.offers?.length&&<p>No current retailer offers available.</p>}</section>}
          {history&&<section className="price-intelligence" aria-label="Price Intelligence"><h3>Observed price history</h3>{history.available?<><p>{history.statistics?.classification==="low"?"Currently near the observed low.":history.statistics?.classification==="high"?"Currently near the observed high.":"Currently in the typical observed range."} Data through {new Date(history.as_of).toLocaleDateString()}.</p><div><span>Low {history.statistics.currency} {(history.statistics.minimum_cents/100).toFixed(2)}</span><span>Mean {history.statistics.currency} {(history.statistics.mean_cents/100).toFixed(2)}</span><span>High {history.statistics.currency} {(history.statistics.maximum_cents/100).toFixed(2)}</span></div><div className="price-history-bars" aria-label="Observed historical prices">{history.observations?.slice(-30).map((point:any,i:number)=><i key={i} title={`${point.currency} ${(point.price_cents/100).toFixed(2)} · ${point.at}`} style={{height:`${Math.max(8,Math.min(100,(point.price_cents/history.statistics.maximum_cents)*100))}%`}}/>)}</div><small>Historical observations do not predict future prices.</small></>:<p>{history.reason}</p>}</section>}
          <h3>Retailer offers</h3>
          {detail.offers?.length ? (
            detail.offers.map((offer: any, i: number) => (
              <p key={i}>
                <button onClick={()=>openRetailer(offer.retailer)}>
                  {offer.retailer} · {offer.currency}{" "}
                  {offer.price_cents == null ? 'Price unavailable' : (offer.price_cents / 100).toFixed(2)} ↗
                </button>{" "}
                · {offer.availability || "Availability unknown"}
                {offer.condition ? " · " + offer.condition : ""}
              </p>
            ))
          ) : (
            <p>No retailer offers available.</p>
          )}
          <small>
            Prices and availability are observed, may change, and are confirmed
            at the retailer. Selecting a variant fetches new offers. Saved cart
            items keep their previous selection until removed and added again.
          </small>
        </>
      )}
    </section>
  );
}
