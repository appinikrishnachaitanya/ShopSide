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
    [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    setDetail(null);
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
  return (
    <section className="provider-details" aria-label="Product details">
      <div className="provider-details-heading">
        <span className="section-kicker">PRODUCT DETAILS · CHANNEL3</span>
        <button disabled={!online || loading} onClick={() => action("similar")}>
          Find similar products ↗
        </button>
        <button disabled={!online || loading} onClick={() => action("cheaper")}>Find cheaper similar options</button>
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
              <label key={option.name}>
                {option.name}
                <select
                  aria-label={"Select " + option.name}
                  value={selected}
                  disabled={!online || loading}
                  onChange={(e) => {
                    const selectedValues = Object.fromEntries(
                      (variants.selected || []).map((x: any) => [
                        x.name,
                        x.label,
                      ]),
                    );
                    selectedValues[option.name] = e.target.value;
                    const choice = option.values.find(
                      (x: any) => x.label === e.target.value,
                    );
                    action(
                      "resolve",
                      selectedValues as Record<string, string>,
                      choice?.product_id || undefined,
                    );
                  }}
                >
                  <option value="" disabled>
                    Choose {option.name}
                  </option>
                  {option.values.map((value: any) => (
                    <option
                      key={value.label}
                      value={value.label}
                      disabled={
                        value.exists === false ||
                        value.available === "OutOfStock"
                      }
                    >
                      {value.label}
                      {value.available === "OutOfStock" ? " · unavailable" : ""}
                    </option>
                  ))}
                </select>
              </label>
            );
          })}
          <h3>Retailer offers</h3>
          {detail.offers?.length ? (
            detail.offers.map((offer: any, i: number) => (
              <p key={i}>
                <a href={offer.url} target="_blank" rel="noopener noreferrer">
                  {offer.retailer} · {offer.currency}{" "}
                  {(offer.price_cents / 100).toFixed(2)} ↗
                </a>{" "}
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
