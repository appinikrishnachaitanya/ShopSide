"use client";
import { useEffect, useState } from "react";
import { sessionFetch } from "./lib/session";
import { AgGridReact } from "ag-grid-react";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
} from "ag-grid-community";
ModuleRegistry.registerModules([AllCommunityModule]);

function displayFact(value: any): string {
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (Array.isArray(value)) return value.map(displayFact).filter(Boolean).join(", ");
  if (value && typeof value === "object") {
    if ("value" in value || "number" in value) return [displayFact(value.value ?? value.number), displayFact(value.unit)].filter(Boolean).join(" ");
    return Object.entries(value).map(([key, item]) => [key.replace(/([a-z])([A-Z])/g, "$1 $2"), displayFact(item)].filter(Boolean).join(": ")).join(" · ");
  }
  return "";
}
function formatDimensions(raw: any): string {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return displayFact(raw);
  const axes = ("length" in raw ? ["length", "width", "height"] : ["width", "depth", "height"])
    .filter(axis => raw[axis] != null);
  const measurements = axes.map(axis => {
    const entry = raw[axis];
    const value = entry && typeof entry === "object" ? (entry.number ?? entry.value) : entry;
    const unit = entry && typeof entry === "object" ? entry.unit : raw.unit;
    return {value: typeof value === "number" || typeof value === "string" ? String(value).trim() : "", unit: typeof unit === "string" ? unit.trim() : ""};
  }).filter(item => item.value && /^-?\d+(?:\.\d+)?$/.test(item.value));
  if (measurements.length < 2) return displayFact(raw);
  const common = measurements[0].unit && measurements.every(item => item.unit === measurements[0].unit);
  return measurements.map(item => item.value + (common || !item.unit ? "" : ` ${item.unit}`)).join(" × ") + (common ? ` ${measurements[0].unit}` : "");
}

function attributeValue(product: any, keys: string[]): any {
  const attributes = product.attributes || {};
  const entry = Object.entries(attributes).find(([key]) => keys.includes(key.toLowerCase().replace(/[^a-z0-9]/g, "")));
  return entry?.[1];
}
function attribute(product: any, keys: string[]): string {
  return displayFact(attributeValue(product, keys));
}

export default function DecisionBoard({
  room,
  products,
}: {
  room: any;
  products: any[];
}) {
  const selected = products.filter((p) =>
    (room.comparison || []).includes(p.id),
  );
  const [details, setDetails] = useState<Record<string, any>>({});
  const selectedIds = selected.filter(p => p.provenance === "channel3").map(p => p.id).sort().join("|");
  useEffect(() => {
    let active = true;
    const ids = selectedIds ? selectedIds.split("|") : [];
    Promise.all(ids.map(async id => {
      const providerId = id.slice("channel3:".length);
      try {
        const response = await sessionFetch(`/api/rooms/${encodeURIComponent(room.id)}/discovery/${encodeURIComponent(providerId)}`);
        return response.ok ? [id, await response.json()] as const : null;
      } catch { return null; }
    })).then(results => { if (active) setDetails(Object.fromEntries(results.filter((entry): entry is readonly [string, any] => entry !== null))); });
    return () => { active = false; };
  }, [room.id, selectedIds]);
  const rows = selected.map((original) => {
    const p = details[original.id] || original;
    const offer = p.offers?.[0];
    return ({
    name: p.name,
    price:
      p.price != null
        ? "$" + (p.price / 100).toFixed(2)
        : offer?.price_cents != null
          ? offer.currency +
            " " +
            (offer.price_cents / 100).toFixed(2)
          : "Not provided",
    dimensions: formatDimensions(offer?.dimensions) || formatDimensions(attributeValue(p, ["dimensions", "size", "productdimensions"])) || "Not provided",
    seating: attribute(p, ["seatingcapacity", "seatcapacity", "numberofseats", "seats"]) || "Not provided",
    material: attribute(p, ["material", "materials", "upholstery", "upholsterymaterial", "fabric"]) || "Not provided",
    delivery: displayFact(offer?.delivery) || attribute(p, ["delivery", "shipping", "deliverytime"]) || "Not provided",
    evidence:
      p.provenance === "channel3"
        ? "Channel3 · " + new Date(p.retrieved_at * 1000).toLocaleString()
        : "Fictional sample fixture",
    reactions: (room.reactions[p.id] || []).join(", ") || "No explicit likes",
  }); });
  return (
    <section className="board">
      <p className="eyebrow">OUR DECISION BOARD</p>
      <small>Compare the details you have together.</small>
      {!selected.length && <p>Save two or three products in your plan, then choose Compare saved products.</p>}
      <h3>Our priorities</h3>
      <p>
        Confirmed budget:{" "}
        {room.mode === "move_in" && room.move_in?.mission?.budget_cents != null ? room.move_in.mission.currency + " " + (room.move_in.mission.budget_cents / 100).toFixed(2) : room.budget ? "$" + (room.budget / 100).toFixed(2) : "Not set"}
      </p>
      {Object.entries(room.preferences || {}).map(([name, v]) => (
        <p key={name}>
          <strong>{name}:</strong> {String(v)}
        </p>
      ))}
      <div style={{ height: 320, width: "100%" }}>
        {selected.length ? <AgGridReact
          theme={themeQuartz.withParams({
            backgroundColor: "#171b16",
            foregroundColor: "#dbe5d6",
            headerBackgroundColor: "#22291f",
            headerTextColor: "#b8c6b1",
            borderColor: "#343c31",
            accentColor: "#c5f874",
            fontFamily: "Inter, system-ui, sans-serif",
            fontSize: 12,
          })}
          rowData={rows}
          suppressNoRowsOverlay={true}
          columnDefs={(
            [
              "name",
              "price",
              "dimensions",
              "seating",
              "material",
              "delivery",
              "evidence",
              "reactions",
            ] as const
          ).map((field) => ({
            field,
            flex: 1,
            minWidth: 140,
            wrapText: true,
            autoHeight: true,
          }))}
        /> : <p className="board-grid-empty" role="status">
          {room.comparison?.length ? products.length ? "The compared products are not available in this room yet. Refresh or add them again from discovery." : "Loading the selected products…" : "Compare saved products to see their details here."}
        </p>}
      </div>
      {selected
        .filter((p) => p.provenance === "channel3")
        .map((p) => (
          <p key={p.id}>
            {p.name}:{" "}
            {p.offers?.map((o: any, i: number) => (
              <a key={i} href={o.url} target="_blank" rel="noopener noreferrer">
                Evidence / {o.retailer} checkout ↗{" "}
              </a>
            ))}
          </p>
        ))}
      <h3>Our choice</h3>
      <p>
        {room.cart?.length
          ? room.cart
              .map((i: any) => products.find((p) => p.id === i.product)?.name)
              .join(", ")
          : "No item chosen"}
      </p>
      <p>
        Likes and approvals are separate. Both participants must explicitly approve a choice.
      </p>
      <small>
        Details come from available product and retailer data; verify price, dimensions and delivery with the retailer.
      </small>
    </section>
  );
}
