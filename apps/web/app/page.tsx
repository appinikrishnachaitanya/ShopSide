"use client";
import { useEffect, useState } from "react";
import DecisionBoard from "./DecisionBoard";
import AudioCall from "./AudioCall";
import Recommendations from "./Recommendations";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  Copy,
  Headphones,
  Heart,
  MessageCircle,
  Search,
  ShoppingBag,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";
export default function Home() {
  const [room, S] = useState<any>(null),
    [catalog, C] = useState<any[]>([]),
    [name, N] = useState(""),
    [invite, I] = useState(""),
    [error, E] = useState(""),
    [text, T] = useState(""),
    [online, O] = useState(false);
  async function api(path: string, body?: any) {
    const r = await fetch(
      "/api/" + path,
      body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        : undefined,
    );
    if (!r.ok) {
      const message = await r.text();
      try {
        throw Error(JSON.parse(message).detail);
      } catch (e: any) {
        throw Error(e instanceof SyntaxError ? message : e.message);
      }
    }
    return r.json();
  }
  useEffect(() => {
    api("catalog")
      .then(C)
      .catch((e) => E(e.message));
    const q = new URLSearchParams(location.search);
    I(q.get("invite") || "");
    const id = q.get("room");
    if (id)
      api("rooms/" + id)
        .then(S)
        .catch((e) => E(e.message));
  }, []);
  const [copied, CopyDone] = useState(false);
  const [me, M] = useState<any>(null),
    [variant, Variant] = useState("standard"),
    [quantity, Quantity] = useState(1),
    [thinking, Thinking] = useState(false),
    [tab, Tab] = useState("shop");
  useEffect(() => {
    if (room?.id)
      api("rooms/" + room.id + "/me")
        .then(M)
        .catch((e) => E(e.message));
  }, [room?.id]);
  const [reconnect, R] = useState(0),
    [target, G] = useState("everyone"),
    [query, Q] = useState(""),
    [quote, V] = useState<any>(null);
  useEffect(() => {
    if (!room) return;
    const ws = new WebSocket(
      (location.protocol === "https:" ? "wss://" : "ws://") +
        location.host +
        "/api/rooms/" +
        room.id +
        "/live",
    );
    ws.onmessage = (e) => {
      S(JSON.parse(e.data));
      O(true);
    };
    ws.onclose = () => O(false);
    ws.onerror = () => O(false);
    return () => ws.close();
  }, [room?.id, reconnect]);
  async function checkout() {
    try {
      const existing = await api("rooms/" + room.id + "/checkout");
      V(existing || (await api("rooms/" + room.id + "/quote", {})));
    } catch (e: any) {
      E(e.message);
    }
  }
  async function pay(action: string) {
    try {
      const result = await api(
        "rooms/" + room.id + "/payments/" + quote.id + "/" + action,
        {},
      );
      if (action === "create") {
        const cfg = await api("paypal/config");
        if (!cfg.client_id) throw Error("Configure PayPal sandbox credentials");
        const script = document.createElement("script");
        script.src =
          "https://www.paypal.com/sdk/js?client-id=" +
          encodeURIComponent(cfg.client_id) +
          "&currency=USD&intent=capture";
        script.onload = () => {
          (window as any).paypal
            .Buttons({
              createOrder: () => result.order_id,
              onApprove: () => pay("capture"),
              onCancel: () =>
                E("Approval cancelled. Check status before retrying."),
              onError: () => E("PayPal approval failed; check payment status."),
            })
            .render("#paypal-buttons");
        };
        document.body.appendChild(script);
      } else E("Payment status: " + result.status);
    } catch (e: any) {
      E(e.message);
    }
  }

  async function enter() {
    try {
      const result = await api(invite ? "join/" + invite : "rooms", { name });
      const r = result.room || result;
      S(r);
      history.replaceState({}, "", "?room=" + r.id);
      if (result.invite) I(result.invite);
      else I(r.invite);
      E("");
    } catch (e: any) {
      E(e.message);
    }
  }
  async function command(kind: string, value: string) {
    try {
      await api("rooms/" + room.id + "/commands", {
        kind,
        value,
        revision: room.revision,
        command_id: crypto.randomUUID(),
      });
      S(await api("rooms/" + room.id));
      E("");
    } catch (e: any) {
      E(e.message);
    }
  }
  const all = [...catalog, ...(room?.discovery || [])];
  const p = all.find((p) => p.id === room?.focus);
  async function discover() {
    try {
      await api("rooms/" + room.id + "/discovery", {
        query,
        max_price: room.budget ? room.budget / 100 : undefined,
      });
      E("");
    } catch (e: any) {
      E(e.message);
    }
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="ShopSide home">
          <span className="brand-mark">
            <ShoppingBag size={16} />
          </span>
          <span>
            shop<span className="brand-accent">side</span>
            <i>.</i>
          </span>
        </a>
        <span className="topbar-divider" />
        <span className="topbar-caption">A little closer, even from afar.</span>
        {room && (
          <div className="topbar-right">
            <span className={"connection " + (online ? "is-online" : "")}>
              <span className="connection-dot" />
              {online ? "Connected" : "Disconnected"}
            </span>
            <div className="avatar-stack">
              {room.people.map((person: string, i: number) => (
                <span
                  className={"avatar avatar-" + i}
                  title={person}
                  key={person}
                >
                  {person.charAt(0).toUpperCase()}
                </span>
              ))}
              {room.people.length < 2 && (
                <span className="avatar avatar-empty">+</span>
              )}
            </div>
            <span className="people-label">{room.people.join(" & ")}</span>
            <button
              className="invite-button"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    location.origin + "?invite=" + (room.invite || invite),
                  );
                  CopyDone(true);
                  setTimeout(() => CopyDone(false), 2200);
                } catch {
                  E("Could not copy invite link");
                }
              }}
            >
              {copied ? <Check size={15} /> : <Copy size={15} />}
              <span>{copied ? "Copied" : "Invite"}</span>
            </button>
          </div>
        )}
        {room && !online && (
          <button className="reconnect" onClick={() => R(reconnect + 1)}>
            Reconnect
          </button>
        )}
      </header>
      {error && (
        <p role="alert" className="error">
          {error}
          <button aria-label="Dismiss message" onClick={() => E("")}>
            ×
          </button>
        </p>
      )}
      {!room ? (
        <main className="welcome">
          <div className="welcome-grid">
            <div className="welcome-copy">
              <div className="welcome-tag">
                <span /> YOUR SPACE TO CHOOSE TOGETHER
              </div>
              <h1>
                Different places.
                <br />
                <em>Same great finds.</em>
              </h1>
              <p>
                All the opinions, none of the endless links. ShopSide brings
                your favorite people and your next favorite thing into one
                space.
              </p>
              <form
                className="welcome-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  enter();
                }}
              >
                <label htmlFor="welcome-name">WHAT SHOULD WE CALL YOU?</label>
                <div>
                  <input
                    id="welcome-name"
                    aria-label="Your name"
                    placeholder="Enter your name"
                    value={name}
                    onChange={(e) => N(e.target.value)}
                    required
                  />
                  <button>
                    {invite ? "Join your friend" : "Create your room"}{" "}
                    <ArrowRight size={18} />
                  </button>
                </div>
              </form>
              <div className="welcome-note">
                <span className="mini-avatars">
                  <b>K</b>
                  <b>P</b>
                </span>
                <span>
                  Better decisions, together.
                  <br />
                  <small>No account needed to get started.</small>
                </span>
              </div>
            </div>
            <div className="welcome-art">
              <div className="welcome-art-glow" />
              <div className="welcome-art-top">
                <span>THE TOGETHER EDIT</span>
                <span>01 / 08</span>
              </div>
              <img
                src="/products/headphones-render.png"
                alt="Illustrative rendering of fictional headphones"
              />
              <div className="welcome-art-bottom">
                <div>
                  <span>MADE FOR SHARED MOMENTS</span>
                  <strong>
                    Find your
                    <br />
                    perfect match.
                  </strong>
                </div>
                <span className="art-arrow">
                  <ArrowUpRight size={22} />
                </span>
              </div>
              <div className="floating-note">
                <Heart size={16} fill="currentColor" />
                <span>
                  <strong>Made for two</strong>
                  <small>Decide together, from anywhere.</small>
                </span>
              </div>
            </div>
          </div>
          <div className="welcome-footer">
            <span>✳ &nbsp; A BETTER WAY TO SHOP TOGETHER</span>
            <span>GOOD COMPANY. GOOD FINDS.</span>
          </div>
        </main>
      ) : (
        <>
          <div className="room-heading">
            <div>
              <div className="breadcrumb">
                <span>YOUR SPACE</span>
                <span>/</span>
                <span>SHOPPING ROOM</span>
              </div>
              <div className="room-title-row">
                <h1>{room.title}</h1>
                <button
                  className="edit-title"
                  disabled={!online}
                  onClick={() => {
                    const title = prompt("Room title", room.title);
                    if (title) command("title", title);
                  }}
                >
                  Edit
                </button>
              </div>
              <p>
                A little browsing. A lot of together. <span>✳</span>
              </p>
            </div>
            <div className="heading-side">
              <span className="room-index">YOUR SHARED SPACE</span>
              <span className="heading-spark">
                <Sparkles size={21} />
              </span>
            </div>
          </div>
          <main className={"room tab-" + tab}>
            <section id="shop" className="shop-column">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">
                    <span className="lime-dot" /> THE MAIN EVENT
                  </span>
                  <h2>
                    On the spotlight<span className="period">.</span>
                  </h2>
                </div>
                <span className="section-meta">
                  PICKED FOR YOUR ROOM <span>↗</span>
                </span>
              </div>
              <article className="stage">
                <div className="stage-top">
                  <span className="stage-pill">
                    <span className="lime-dot" />
                    {room.spotlight_by
                      ? room.spotlight_by + " is showing this"
                      : "YOUR SHARED SPOTLIGHT"}
                  </span>
                  <span className="stage-index">01 / THE SPOTLIGHT</span>
                </div>
                <div className="stage-content">
                  <div className="stage-product">
                    <div className="product-orbit orbit-one" />
                    <div className="product-orbit orbit-two" />
                    <img
                      className="headphones"
                      src={p?.image || "/products/headphones-render.png"}
                      alt={
                        p?.image
                          ? p?.name
                          : "Illustrative rendering of fictional headphones"
                      }
                    />
                    <span className="stage-product-caption">
                      A GOOD FIND, TOGETHER.
                    </span>
                  </div>
                  <div className="stage-details">
                    <div className="product-category">
                      <span />{" "}
                      {p?.provenance === "channel3"
                        ? "LIVE DISCOVERY"
                        : "THE SHOPSIDE EDIT"}
                    </div>
                    <h2>{p?.name || "Find your next favorite"}</h2>
                    <p className="product-description">
                      {(p?.provenance !== "channel3"
                        ? p?.description?.replace(/\bdemo\b/gi, "sample")
                        : p?.description) ||
                        "Pick something to share with your room."}
                    </p>
                    <div className="stage-price">
                      {p?.price != null
                        ? "$" + (p.price / 100).toFixed(2)
                        : "See retailer offers"}
                      <small>
                        {p?.price != null ? " USD · SAMPLE PRICE" : ""}
                      </small>
                    </div>
                    <div className="stage-actions">
                      <button
                        className="primary-button"
                        disabled={!online || !p}
                        onClick={() => command("shortlist", p.id)}
                      >
                        <Sparkles size={16} />
                        {room.shortlist.includes(p?.id)
                          ? "Saved to Together"
                          : "Save to Together"}
                      </button>
                      <button
                        className="like-button"
                        disabled={!online || !p}
                        onClick={() => command("reaction", p.id)}
                        aria-label={
                          "Like · " +
                          ((room.reactions[p?.id] || []).join(", ") ||
                            "Be the first")
                        }
                      >
                        <Heart size={17} />
                        <span>
                          {(room.reactions[p?.id] || []).length || "Like"}
                        </span>
                      </button>
                    </div>
                    <p className="reaction-caption">
                      {(room.reactions[p?.id] || []).length
                        ? (room.reactions[p?.id] || []).join(", ") +
                          " liked this"
                        : "No likes yet. What do you think?"}
                    </p>
                  </div>
                </div>
                {p?.provenance === "channel3" && (
                  <p className="stage-disclaimer">
                    Live Channel3 discovery · retailer checkout only · price and
                    variant must be verified at retailer
                  </p>
                )}
              </article>
              {p?.provenance !== "channel3" && (
                <div className="cart-controls">
                  <div className="cart-controls-title">
                    <span className="small-icon">
                      <ShoppingBag size={16} />
                    </span>
                    <span>
                      <strong>Make it yours</strong>
                      <small>SHOPSIDE · SANDBOX ONLY</small>
                    </span>
                  </div>
                  <label>
                    Variant
                    <select
                      aria-label="Product variant"
                      value={variant}
                      onChange={(e) => Variant(e.target.value)}
                    >
                      <option value="standard">Sage / standard</option>
                      <option value="midnight">Midnight</option>
                    </select>
                  </label>
                  <label>
                    Qty
                    <input
                      aria-label="Product quantity"
                      type="number"
                      min="1"
                      max="10"
                      value={quantity}
                      onChange={(e) => Quantity(Number(e.target.value))}
                    />
                  </label>
                  <button
                    className="cart-add"
                    disabled={!online || !!room.checkout}
                    onClick={() =>
                      command(
                        "cart_line",
                        JSON.stringify({ product: p?.id, variant, quantity }),
                      )
                    }
                  >
                    Add to cart <ArrowRight size={15} />
                  </button>
                </div>
              )}
              <div className="discovery">
                <div className="section-heading">
                  <div>
                    <span className="section-kicker">
                      <span className="lime-dot" /> EXPLORE TOGETHER
                    </span>
                    <h2>
                      Find something good<span className="period">.</span>
                    </h2>
                  </div>
                  <span className="section-meta">
                    POWERED BY CHANNEL3 <ArrowUpRight size={14} />
                  </span>
                </div>
                <form
                  className="discovery-search"
                  onSubmit={(e) => {
                    e.preventDefault();
                    discover();
                  }}
                >
                  <Search size={19} />
                  <input
                    aria-label="Live product search"
                    placeholder="Search real products together..."
                    value={query}
                    onChange={(e) => Q(e.target.value)}
                  />
                  <button disabled={!query.trim()}>
                    Search Channel3 <ArrowRight size={15} />
                  </button>
                </form>
                {room.discovery?.length > 0 && (
                  <div className="live-grid">
                    {room.discovery.map((item: any) => (
                      <article className="live-product" key={item.id}>
                        {item.image && <img src={item.image} alt={item.name} />}
                        <div>
                          <span className="card-tag">LIVE DISCOVERY</span>
                          <h3>{item.name}</h3>
                          <div className="live-actions">
                            <button
                              disabled={!online}
                              onClick={() => command("focus", item.id)}
                            >
                              Look at this
                            </button>
                            <button
                              disabled={!online}
                              onClick={() => command("shortlist", item.id)}
                            >
                              Save
                            </button>
                          </div>
                          {item.offers.map((o: any, i: number) => (
                            <p key={i}>
                              <a
                                href={o.url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {o.retailer} · {o.currency}{" "}
                                {(o.price_cents / 100).toFixed(2)} ↗
                              </a>
                              <small>
                                {" "}
                                {o.availability || "Availability unknown"} ·
                                Variant unknown
                              </small>
                            </p>
                          ))}
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </div>
              <div className="catalog-section">
                <div className="catalog-head">
                  <div>
                    <span className="section-kicker">
                      <span className="lime-dot" /> THE SHOPSIDE COLLECTION
                    </span>
                    <h2>
                      A few good possibilities<span className="period">.</span>
                    </h2>
                    <p>
                      Fictional products · PayPal sandbox · No goods shipped
                    </p>
                  </div>
                  <div className="catalog-search">
                    <Search size={15} />
                    <input
                      aria-label="Search catalog"
                      placeholder="Filter collection"
                      value={query}
                      onChange={(e) => Q(e.target.value)}
                    />
                  </div>
                </div>
                <div className="catalog">
                  {catalog
                    .filter((item) =>
                      item.name.toLowerCase().includes(query.toLowerCase()),
                    )
                    .map((item, i) => (
                      <button
                        key={item.id}
                        className={
                          "product-card product-tone-" +
                          (i % 4) +
                          (room.focus === item.id ? " is-selected" : "")
                        }
                        disabled={!online}
                        onClick={() => command("focus", item.id)}
                      >
                        <span className="product-card-image">
                          <span className="product-card-number">0{i + 1}</span>
                          <img
                            className="mini"
                            src="/products/headphones-render.png"
                            alt=""
                          />
                          <span className="product-card-arrow">
                            <ArrowUpRight size={15} />
                          </span>
                        </span>
                        <span className="product-card-info">
                          <strong>{item.name}</strong>
                          <small>SHOPSIDE COLLECTION</small>
                          <span className="product-card-price">
                            ${(item.price / 100).toFixed(2)}{" "}
                            <span>
                              Look at this <ArrowRight size={12} />
                            </span>
                          </span>
                        </span>
                      </button>
                    ))}
                </div>
              </div>
              <div className="together-header" id="together">
                <div>
                  <span className="section-kicker">
                    <span className="lime-dot" /> BETTER TOGETHER
                  </span>
                  <h2>
                    Your shared edit<span className="period">.</span>
                  </h2>
                  <p>
                    {room.shortlist.length
                      ? room.shortlist.length + " saved to your shortlist"
                      : "The good stuff goes here. Save a few favorites to get started."}
                  </p>
                </div>
                <button
                  className="outline-button"
                  disabled={
                    !online ||
                    room.shortlist.length < 2 ||
                    room.shortlist.length > 3
                  }
                  onClick={() => command("compare", room.shortlist.join(","))}
                >
                  Compare picks <ArrowUpRight size={15} />
                </button>
              </div>
              <Recommendations
                room={room}
                products={all}
                select={(id) => command("focus", id)}
              />
              <DecisionBoard room={room} products={all} command={command} />
            </section>
            <aside id="chat" className="conversation">
              <div className="conversation-top">
                <div className="conversation-icon">
                  <MessageCircle size={18} />
                </div>
                <div>
                  <span className="section-kicker">YOUR SHARED SPACE</span>
                  <h2>
                    The conversation<span className="period">.</span>
                  </h2>
                </div>
                <span className="conversation-menu">•••</span>
              </div>
              <p className="conversation-subtitle">
                Good decisions are better together.
              </p>
              <AudioCall roomId={room.id} online={online} />
              <div className="conversation-label">
                <span>THE ROOM CHAT</span>
                <span>{room.people.length} PEOPLE</span>
              </div>
              <div className="messages">
                {room.messages.length === 0 ? (
                  <div className="chat-empty">
                    <span>
                      <MessageCircle size={21} />
                    </span>
                    <strong>Start the conversation</strong>
                    <p>
                      Share a thought, ask a question, or let ShopSide help you
                      decide.
                    </p>
                  </div>
                ) : (
                  room.messages.map((m: any, i: number) => (
                    <article
                      key={i}
                      className={m.actor === "ShopSide" ? "agent-message" : ""}
                    >
                      <span className="message-avatar">
                        {m.actor === "ShopSide" ? (
                          <Sparkles size={13} />
                        ) : (
                          m.actor.charAt(0).toUpperCase()
                        )}
                      </span>
                      <div>
                        <strong>{m.actor}</strong>
                        <p>{m.text}</p>
                      </div>
                    </article>
                  ))
                )}
              </div>
              <form
                className="message-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (target === "everyone") command("chat", text);
                  else {
                    Thinking(true);
                    api("rooms/" + room.id + "/agent", {
                      text,
                      revision: room.revision,
                    })
                      .catch((e) => E(e.message))
                      .finally(() => Thinking(false));
                  }
                  T("");
                }}
              >
                <div className="message-target">
                  <Sparkles size={13} />
                  <select
                    aria-label="Message target"
                    value={target}
                    onChange={(e) => G(e.target.value)}
                  >
                    <option value="everyone">Everyone</option>
                    <option value="agent">Ask ShopSide</option>
                  </select>
                  <ChevronDown size={13} />
                </div>
                <div className="message-compose">
                  <input
                    aria-label="Message everyone"
                    placeholder="Say something nice..."
                    value={text}
                    onChange={(e) => T(e.target.value)}
                  />
                  <button
                    aria-label="Send message"
                    disabled={!online || thinking || !text.trim()}
                  >
                    <ArrowRight size={18} />
                  </button>
                </div>
              </form>
              <p className="thinking" role="status">
                {thinking ? "✳ ShopSide is thinking…" : ""}
              </p>
              <div className="agent-note">
                <Sparkles size={15} />
                <span>
                  ShopSide can use shared messages to help when asked.
                </span>
              </div>
              <details className="side-details">
                <summary>
                  <span>
                    <Zap size={15} /> Room priorities
                  </span>
                  <span>＋</span>
                </summary>
                <div>
                  <label>CONFIRMED BUDGET</label>
                  <input
                    disabled={!online || !me?.is_payer}
                    aria-label="Budget USD"
                    type="number"
                    min="0"
                    placeholder="Set your budget in USD"
                    onBlur={(e) => {
                      if (e.target.value)
                        command(
                          "budget",
                          String(Math.round(Number(e.target.value) * 100)),
                        );
                    }}
                  />
                  <p>
                    {room.budget
                      ? "$" + (room.budget / 100).toFixed(2)
                      : "No budget confirmed"}
                  </p>
                  <label>WHAT MATTERS TO YOU?</label>
                  <input
                    aria-label="Your shopping preference"
                    placeholder="e.g. comfortable for long calls"
                    onBlur={(e) => {
                      if (e.target.value) command("preference", e.target.value);
                    }}
                  />
                  {Object.entries(room.preferences || {}).map(
                    ([actor, value]) => (
                      <p key={actor}>
                        {actor}: {String(value)}
                      </p>
                    ),
                  )}
                </div>
              </details>
              <details className="side-details">
                <summary>
                  <span>
                    <Sparkles size={15} /> Agent activity
                  </span>
                  <span>{room.activity?.length || "＋"}</span>
                </summary>
                <div>
                  {room.activity?.slice(-5).map((a: any, i: number) => (
                    <p key={i}>
                      {a.tool}: {a.outcome}
                    </p>
                  )) || <p>No activity yet.</p>}
                </div>
              </details>
              <details className="side-details cart-details" open={!!quote}>
                <summary>
                  <span>
                    <ShoppingBag size={15} /> Shared cart
                  </span>
                  <span className="cart-count">{room.cart?.length || 0}</span>
                </summary>
                <div>
                  {room.cart?.length === 0 && (
                    <p>
                      Nothing in your cart yet. Find something you both love.
                    </p>
                  )}
                  {room.cart?.map((item: any) => (
                    <div
                      className="cart-line"
                      key={item.product + item.variant}
                    >
                      <p>
                        {catalog.find((p) => p.id === item.product)?.name} ·{" "}
                        {item.variant}
                      </p>
                      <label>
                        Quantity{" "}
                        <input
                          aria-label={
                            "Quantity " + item.product + " " + item.variant
                          }
                          type="number"
                          min="0"
                          max="10"
                          defaultValue={item.quantity}
                          disabled={!online || !!room.checkout}
                          onBlur={(e) =>
                            command(
                              "cart_line",
                              JSON.stringify({
                                ...item,
                                quantity: Number(e.target.value),
                              }),
                            )
                          }
                        />
                      </label>
                      <button
                        disabled={!online || !!room.checkout}
                        onClick={() =>
                          command(
                            "cart_line",
                            JSON.stringify({ ...item, quantity: 0 }),
                          )
                        }
                      >
                        Remove item
                      </button>
                    </div>
                  ))}
                  {room.proposals?.map((proposal: any) => (
                    <button
                      key={proposal.id}
                      onClick={() => command("accept_proposal", proposal.id)}
                    >
                      Accept {proposal.proposer}'s proposal:{" "}
                      {catalog.find((p) => p.id === proposal.product)?.name}
                    </button>
                  ))}
                  <button
                    className="checkout-button"
                    disabled={!online || !me?.is_payer}
                    onClick={checkout}
                  >
                    {me?.is_payer
                      ? "Review exact quote"
                      : room.payer + " handles checkout"}
                  </button>
                  {quote && (
                    <section className="quote">
                      <h3>Sandbox quote</h3>
                      <p>
                        ShopSide merchant · PayPal sandbox · No goods shipped
                      </p>
                      {quote.items?.map((item: any) => (
                        <p key={item.product + item.variant}>
                          {item.name || item.product} · {item.variant} ×{" "}
                          {item.quantity} · $
                          {((item.price * item.quantity) / 100).toFixed(2)}
                        </p>
                      ))}
                      <p>Fees $0.00</p>
                      <strong>
                        Total ${(quote.total / 100).toFixed(2)} USD
                      </strong>
                      <button onClick={() => pay("create")}>
                        Continue with PayPal sandbox
                      </button>
                      <div id="paypal-buttons" />
                      <button onClick={() => pay("status")}>
                        Check payment status
                      </button>
                      <button onClick={() => pay("cancel")}>
                        Cancel unused quote
                      </button>
                    </section>
                  )}
                  {room.checkout && (
                    <p role="status">
                      {room.checkout.status === "paid"
                        ? "You chose this together. Payment verified."
                        : "Checkout: " + room.checkout.status}
                    </p>
                  )}
                </div>
              </details>
              <div className="conversation-footer">
                <span>
                  <span className="lime-dot" /> YOUR ROOM IS PRIVATE
                </span>
                <span>MADE FOR TWO ✳</span>
              </div>
            </aside>
          </main>
          <nav className="mobile-nav" aria-label="Room navigation">
            {[
              ["shop", "Shop", Headphones],
              ["together", "Together", Heart],
              ["chat", "Chat", MessageCircle],
            ].map(([key, label, Icon]: any) => (
              <button
                key={key}
                aria-pressed={tab === key}
                onClick={() => {
                  Tab(key);
                  document
                    .getElementById(key)
                    ?.scrollIntoView({ behavior: "smooth" });
                }}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
          </nav>
        </>
      )}
    </div>
  );
}
