"use client";
import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
export default function Concierge({
  room,
  online,
}: {
  room: any;
  online: boolean;
}) {
  const [text, setText] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const journey = room.shopping_journey;
  async function submit(action: string, value = "") {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/rooms/" + room.id + "/concierge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: value,
          action,
          revision: room.revision,
          command_id: crypto.randomUUID(),
        }),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Please try again");
      }
      setText("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const question = journey?.question;
  return (
    <section className="concierge-panel" aria-label="Shopping concierge">
      <div className="concierge-heading">
        <span className="concierge-icon">
          <Sparkles size={18} />
        </span>
        <div>
          <span className="section-kicker">YOUR SHOPPING CONCIERGE</span>
          <h2>What are you shopping for today?</h2>
        </div>
      </div>
      <p>
        Tell us what you need. ShopSide will ask a few questions and find
        options together.
      </p>
      {journey?.history?.length > 0 && (
        <div className="concierge-history">
          {journey.history.map((h: any, i: number) => (
            <div key={i}>
              <strong>{h.actor}</strong>
              <span>{h.text}</span>
            </div>
          ))}
        </div>
      )}
      {journey?.intent?.request && (
        <div className="intent-summary">
          <span>{journey.intent.request}</span>
          {journey.intent.intended_use && (
            <span>{journey.intent.intended_use}</span>
          )}
          {journey.intent.budget != null && (
            <span>
              Budget: {journey.intent.currency} {journey.intent.budget}
            </span>
          )}
          {journey.intent.preferences?.map((x: string) => (
            <span key={x}>{x}</span>
          ))}
        </div>
      )}
      {question && journey?.status === "question" && (
        <div className="concierge-question">
          <strong>{question.text}</strong>
          {question.reason && <p>{question.reason}</p>}
          <div className="concierge-chips">
            {question.choices.map((choice: string) => (
              <button
                key={choice}
                disabled={!online || busy}
                onClick={() => submit("answer", choice)}
              >
                {choice}
              </button>
            ))}
          </div>
        </div>
      )}
      {journey?.status === "searching" && (
        <p role="status">Searching for products you can explore together…</p>
      )}
      {journey?.status === "results" && (
        <p role="status">
          {room.discovery?.length
            ? `${room.discovery.length} live products found. Explore them below, or invite a friend for a second opinion.`
            : "No products found. Try changing your request."}
        </p>
      )}
      {journey?.status === "results" && journey?.suggestions?.length > 0 && (
        <div className="concierge-chips" aria-label="Refine results">
          {journey.suggestions.map((choice: string) => (
            <button
              key={choice}
              disabled={!online || busy}
              onClick={() => submit("answer", choice)}
            >
              {choice}
            </button>
          ))}
        </div>
      )}
      {journey?.status === "results" && room.discovery?.length > 0 && (
        <div className="concierge-invite">
          <strong>Want a second opinion? Shop together.</strong>
          <button
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(
                  location.origin + "?invite=" + room.invite,
                );
              } catch {
                setError(
                  "Could not copy your invitation. Use the Invite button above.",
                );
              }
            }}
          >
            Invite a Friend
          </button>
        </div>
      )}
      {(error || journey?.error) && (
        <p role="alert" className="concierge-error">
          {error || journey.error}
        </p>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(journey?.status === "results" ? "revise" : "answer", text);
        }}
      >
        <input
          aria-label="Shopping request"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={
            question ? "Type your answer…" : "I need luggage for my trip…"
          }
          maxLength={2000}
        />
        <button disabled={!online || busy || !text.trim()}>
          {busy ? "Thinking…" : "Continue"} <ArrowRight size={16} />
        </button>
      </form>
      <div className="concierge-actions">
        {question && (
          <button disabled={!online || busy} onClick={() => submit("skip")}>
            Skip
          </button>
        )}
        {journey?.history?.length > 0 && (
          <button disabled={!online || busy} onClick={() => submit("show")}>
            Show products now
          </button>
        )}
        {journey?.status === "error" && (
          <button disabled={!online || busy} onClick={() => submit("show")}>
            Retry search
          </button>
        )}
        {journey?.status === "results" && (
          <small>To change an answer, describe the change above.</small>
        )}
      </div>
    </section>
  );
}
