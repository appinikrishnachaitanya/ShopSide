"use client";
export default function Recommendations({
  room,
  products,
  select,
}: {
  room: any;
  products: any[];
  select: (id: string) => void;
}) {
  const preferences = Object.entries(room.preferences || {}).filter(([, v]) =>
    String(v).trim(),
  );
  const mentions = new Map<string, string[]>();
  for (const message of room.messages || []) {
    if (!room.people.includes(message.actor)) continue;
    for (const product of products) {
      if (
        product.name &&
        String(message.text).toLowerCase().includes(product.name.toLowerCase())
      )
        mentions.set(product.id, [
          ...new Set([...(mentions.get(product.id) || []), message.actor]),
        ]);
    }
  }
  const candidates = products.filter(
    (p) => (room.shortlist || []).includes(p.id) || mentions.has(p.id),
  );
  const items = candidates
    .sort((a, b) => Number(mentions.has(b.id)) - Number(mentions.has(a.id)))
    .slice(0, 6);
  if (!preferences.length && !items.length)
    return (
      <section className="recommendations">
        <span className="eyebrow">A LITTLE HELP DECIDING</span>
        <h2>Find your common ground.</h2>
        <p>
          Share what matters to each of you and save a few favorites. Your
          shortlist and priorities will appear here.
        </p>
      </section>
    );
  return (
    <section className="recommendations">
      <span className="eyebrow">YOUR SHARED PRIORITIES</span>
      <h2>Good choices start here.</h2>
      <div className="priority-pills">
        {preferences.map(([who, value]) => (
          <span key={who}>
            <strong>{who}:</strong> {String(value)}
          </span>
        ))}
        {room.budget != null && (
          <span>
            <strong>Budget:</strong> ${(room.budget / 100).toFixed(2)}
          </span>
        )}
      </div>
      {items.length ? (
        <>
          <p>
            Revisit the items saved in this room. Check unknown details before
            deciding.
          </p>
          <div className="recommended-list">
            {items.map((p: any) => {
              const amount = p.price ?? p.offers?.[0]?.price_cents;
              const currency =
                p.price != null ? "USD" : p.offers?.[0]?.currency;
              const budget =
                room.budget != null && currency === "USD" && amount != null
                  ? amount <= room.budget
                    ? "Within confirmed budget"
                    : "Above confirmed budget"
                  : null;
              return (
                <button key={p.id} onClick={() => select(p.id)}>
                  <span>
                    <strong>{p.name}</strong>
                    <small>
                      {mentions.has(p.id)
                        ? "Mentioned by " +
                          mentions.get(p.id)?.join(", ") +
                          " · "
                        : ""}
                      {budget || "Price or budget not confirmed"} ·{" "}
                      {(room.reactions[p.id] || []).length} explicit likes
                    </small>
                  </span>
                  <span aria-hidden="true">↗</span>
                </button>
              );
            })}
          </div>
        </>
      ) : (
        <p>Save products to compare them against your confirmed budget.</p>
      )}
      <small>
        Based on shared messages, preferences, shortlist, reactions and the
        displayed price. Preferences are not automatically verified product
        features.
      </small>
    </section>
  );
}
