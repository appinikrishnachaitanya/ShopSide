"use client";

/** Render a small safe subset of the assistant's Markdown without HTML injection. */
export default function AssistantMessage({ text, products }: { text: string; products: any[] }) {
  const clean = String(text || "").replace(/`?(channel3:[A-Za-z0-9_-]+)`?/g, (_match, id) =>
    products.find(product => product.id === id)?.name || "this product");
  return <>{clean.split(/(\*\*[^*\n]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part
  )}</>;
}
