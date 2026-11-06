"use client";
import { AgGridReact } from "ag-grid-react";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
} from "ag-grid-community";
ModuleRegistry.registerModules([AllCommunityModule]);
export default function DecisionBoard({
  room,
  products,
  command,
}: {
  room: any;
  products: any[];
  command: (kind: string, value: string) => void;
}) {
  const selected = products.filter((p) =>
    (room.comparison || []).includes(p.id),
  );
  const rows = selected.map((p) => ({
    name: p.name,
    price:
      p.price != null
        ? "$" + (p.price / 100).toFixed(2)
        : p.offers?.[0]
          ? p.offers[0].currency +
            " " +
            (p.offers[0].price_cents / 100).toFixed(2)
          : "Unknown",
    variant: p.variant || "Unknown",
    microphone: p.attributes?.microphone_quality || "Unknown",
    evidence:
      p.provenance === "channel3"
        ? "Channel3 · " + new Date(p.retrieved_at * 1000).toLocaleString()
        : "Fictional sample fixture",
    reactions: (room.reactions[p.id] || []).join(", ") || "No explicit likes",
  }));
  return (
    <section className="board">
      <p className="eyebrow">OUR DECISION BOARD</p>
      <small>AG Grid comparison fallback · Studio access pending</small>
      <nav>
        {["Browse", "Compare", "Decide"].map((p) => (
          <button
            aria-pressed={(room.board_preset || "Browse") === p}
            key={p}
            onClick={() => command("board_preset", p)}
          >
            {p}
          </button>
        ))}
      </nav>
      <h3>Our priorities</h3>
      <p>
        Confirmed budget:{" "}
        {room.budget ? "$" + (room.budget / 100).toFixed(2) : "Not set"}
      </p>
      {Object.entries(room.preferences || {}).map(([name, v]) => (
        <p key={name}>
          <strong>{name}:</strong> {String(v)}
        </p>
      ))}
      <div style={{ height: 320, width: "100%" }}>
        <AgGridReact
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
          columnDefs={(
            [
              "name",
              "price",
              "variant",
              "microphone",
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
        />
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
        Agreement is shown only through explicit likes. Unstated objections are
        unknown.
      </p>
      <small>
        No comparable sourced numeric attribute is available, so no score or
        chart is shown.
      </small>
    </section>
  );
}
