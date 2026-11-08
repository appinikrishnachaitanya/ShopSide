"use client";
import MoveIn from "./MoveIn";
import MemoryReceipt from "./MemoryReceipt";
import dynamic from "next/dynamic";
import WhyPick from "./WhyPick";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { sessionFetch, sessionSocket, startInviteSession } from "./lib/session";
import DecisionBoard from "./DecisionBoard";
import CartQuantity from "./CartQuantity";
import WelcomeIllustration from "./WelcomeIllustration";
import Recommendations from "./Recommendations";
import Concierge from "./Concierge";
import ProductDetails from "./ProductDetails";
import WorkspaceOverlay from "./WorkspaceOverlay";
import SmartBundle from "./SmartBundle";
import PlanOverview from "./PlanOverview";
import SellerOffers from "./SellerOffers";
const RoomPreview=dynamic(()=>import("./RoomPreview"),{ssr:false,loading:()=> <p role="status">Opening Move-in Studio…</p>});
const spatialEligible=(product:any)=>product?.spatial_eligible===true||/\b(?:furniture|decor|lamp|desk|chair|table|sofa|couch|loveseat|bed|shelf|cabinet|dresser|rug|nightstand)s?\b/i.test(`${product?.category||""} ${product?.name||""}`);
import AssistantMessage from "./AssistantMessage";
import {
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
} from "lucide-react";
export default function Home() {
  const [room, S] = useState<any>(null),
    [catalog, C] = useState<any[]>([]),
    [name, N] = useState(""),
    [invite, I] = useState(""),
    [error, E] = useState(""),
    [text, T] = useState(""),
    [online, O] = useState(false);
  const [entryReady, setEntryReady] = useState(false);
  const [sendingChat, setSendingChat] = useState(false);
  const pendingChat = useRef<{ text: string; id: string } | null>(null);
  const chatInFlight = useRef(false);
  async function api(path: string, body?: any) {
    const r = await sessionFetch(
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
      let detail = message;
      try { const data = JSON.parse(message); detail = typeof data.detail === "string" ? data.detail : message; } catch {}
      const error = new Error(detail || "Request failed") as Error & { status?: number };
      error.status = r.status;
      throw error;
    }
    return r.json();
  }
  useEffect(() => {
    const q = new URLSearchParams(location.search);
    const inviteCode = q.get("invite") || "";
    if (inviteCode) startInviteSession();
    I(inviteCode);
    api("catalog").then(C).catch((e) => E(e.message));
    const id = q.get("room");
    if (id) {
      api("rooms/" + id + "/session", {})
        .then(() => api("rooms/" + id))
        .then(S)
        .catch((e) => E(e.message));
    }
    setEntryReady(true);
  }, []);
  const [shoppingRequest, setShoppingRequest] = useState("");
  const [workspaceView, setWorkspaceView] = useState<"discover" | "product" | "plan" | "room" | "together">("discover");
  const [studioActive,setStudioActive]=useState(false);
  const [pendingFocus, setPendingFocus] = useState<string | null>(null);
  const [catalogQuery, setCatalogQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [orderRef, setOrderRef] = useState("");
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [paypalReady, setPaypalReady] = useState(false);
  const [preauthorization, setPreauthorization] = useState(false);
  const [initialMissionLoading, setInitialMissionLoading] = useState(false);
  const [hiddenDealPromptKey, setHiddenDealPromptKey] = useState("");
  const [highlightPlanDeals, setHighlightPlanDeals] = useState(false);
  const [followUpAnswer, setFollowUpAnswer] = useState("");
  const [followUpBusy, setFollowUpBusy] = useState(false);
  const [followUpError, setFollowUpError] = useState("");
  async function answerFollowUp(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!room || !followUpAnswer.trim() || followUpBusy) return;
    setFollowUpBusy(true); setFollowUpError("");
    try {
      const updated = await api(`rooms/${room.id}/intent/answer`, {text: followUpAnswer.trim(), revision: room.revision, command_id: crypto.randomUUID()});
      S(updated); setFollowUpAnswer("");
    } catch (err: any) {
      if (err.status === 409) {
        try { S(await api(`rooms/${room.id}`)); } catch {}
      }
      setFollowUpError(err.message);
    } finally { setFollowUpBusy(false); }
  }
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [inStock, setInStock] = useState(false);
  const [searchMode, setSearchMode] = useState("default");
  const [searchLocale, setSearchLocale] = useState("US:USD:en");
  const [resultBrand, setResultBrand] = useState("");
  const [resultRetailer, setResultRetailer] = useState("");
  const [copied, CopyDone] = useState(false);
  const [cartOpen, setCartOpen] = useState(false),
    [notice, setNotice] = useState("");
  useEffect(() => {
    if (!cartOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") setCartOpen(false); };
    document.addEventListener("keydown", closeOnEscape);
    return () => { document.body.style.overflow = previousOverflow; document.removeEventListener("keydown", closeOnEscape); };
  }, [cartOpen]);
  const [me, M] = useState<any>(null),
    [variant, Variant] = useState("standard"),
    [quantity, Quantity] = useState(1),
    [thinking, Thinking] = useState(false),
    [tab, Tab] = useState("shop");
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [roomAlert, setRoomAlert] = useState("");
  const soundContext = useRef<AudioContext | null>(null);
  const previousRoom = useRef<any>(null);
  function playNotification(agreement = false) {
    const context = soundContext.current;
    if (!soundEnabled || !context || context.state !== "running") return;
    const now = context.currentTime;
    const notes = agreement ? [660, 880] : [660];
    notes.forEach((frequency, index) => {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const start = now + index * 0.13;
      oscillator.type = "sine"; oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.045, start + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.12);
      oscillator.connect(gain); gain.connect(context.destination);
      oscillator.start(start); oscillator.stop(start + 0.13);
    });
  }
  async function toggleSound() {
    if (soundEnabled) { setSoundEnabled(false); return; }
    try {
      const context = soundContext.current || new AudioContext();
      soundContext.current = context;
      await context.resume();
      if (context.state !== "running") throw new Error("Audio unavailable");
      setSoundEnabled(true);
    } catch { setRoomAlert("Sound could not be enabled in this browser."); }
  }
  useEffect(() => () => { void soundContext.current?.close(); }, []);
  useEffect(() => {
    if (!room?.id || !me?.name) return;
    const previous = previousRoom.current;
    previousRoom.current = room;
    if (!previous || previous.id !== room.id || room.revision <= previous.revision) return;
    let alert = "";
    let agreement = false;
    const productName = (id: string) => (room.move_in?.items?.[id]?.name || room.discovery?.find((p: any) => p.id === id)?.name || catalog.find((p: any) => p.id === id)?.name || "a product");
    if (room.agreed_product && room.agreed_product !== previous.agreed_product) {
      alert = `Everyone agreed on ${productName(room.agreed_product)}.`; agreement = true;
    } else {
      for (const [id, raw] of Object.entries(room.move_in?.items || {})) {
        const item: any = raw, old = previous.move_in?.items?.[id];
        if (item.status === "agreed" && old?.status !== "agreed") {
          alert = `Everyone approved ${item.name}.`; agreement = true; break;
        }
        const approver = Object.keys(item.approvals || {}).find(person => person !== me.name && item.approvals[person] === true && old?.approvals?.[person] !== true);
        if (approver) { alert = `${approver} approved ${item.name}.`; agreement = true; break; }
      }
      if (!alert) {
        const voter = Object.keys(room.agreement_votes || {}).find(person => person !== me.name && room.agreement_votes[person] && room.agreement_votes[person] !== previous.agreement_votes?.[person]);
        if (voter) { alert = `${voter} agrees on ${productName(room.agreement_votes[voter])}.`; agreement = true; }
      }
    }
    const newMessages = (room.messages || []).slice((previous.messages || []).length);
    const incoming = newMessages.find((message: any) => message.actor !== me.name);
    if (!alert && incoming) alert = `${incoming.actor} sent a message.`;
    const joined = (room.people || []).filter((person: string) => person !== me.name && !(previous.people || []).includes(person));
    if (!alert && joined.length) alert = `${joined.join(", ")} joined the room.`;
    if (alert) { setRoomAlert(alert); playNotification(agreement); }
  }, [room, me?.name]);
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
  useEffect(()=>{if(quote)setCartOpen(true)},[quote]);
  useEffect(() => {
    if (!room?.id) return;
    let stopped = false;
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;
    function connect() {
      if (stopped) return;
      socket = sessionSocket("/api/rooms/" + room.id + "/live");
      socket.onmessage = (e) => {
        if (stopped) return;
        try {
          const incoming = JSON.parse(e.data);
          S((current: any) => !current || incoming.revision >= current.revision ? incoming : current);
          attempts = 0;
          O(true);
        } catch { socket?.close(); }
      };
      socket.onclose = () => {
        if (stopped) return;
        O(false);
        if (!stopped) {
          const delay = Math.min(1000 * 2 ** attempts, 15000);
          attempts += 1;
          retryTimer = setTimeout(connect, delay);
        }
      };
      socket.onerror = () => socket?.close();
    }
    connect();
    return () => { stopped = true; if (retryTimer) clearTimeout(retryTimer); socket?.close(); };
  }, [room?.id, reconnect]);
  async function checkout() {
    try {
      const existing = await api("rooms/" + room.id + "/checkout");
      V(existing || (await api("rooms/" + room.id + "/quote", {})));
    } catch (e: any) {
      E(e.message);
    }
  }
  async function pay(action: string, authorizeMode = preauthorization || quote?.authorization_mode === "PREAUTHORIZED" || room?.checkout?.authorization_mode === "PREAUTHORIZED") {
    if (paymentBusy) return;
    setPaymentBusy(true);
    let waitingForSdk = false;
    try {
      const result = await api(
        "rooms/" + room.id + "/payments/" + quote.id + "/" + (authorizeMode ? "preauthorize/" : "") + action,
        {},
      );
      if (action === "create") {
        if (!result.order_id) throw Error("The sandbox order was not created. Check payment status before retrying.");
        setOrderRef(result.order_id);
        const cfg = await api("paypal/config");
        if (!cfg.client_id) throw Error("Configure PayPal sandbox credentials");
        const script = document.createElement("script");
        script.src =
          "https://www.paypal.com/sdk/js?client-id=" +
          encodeURIComponent(cfg.client_id) +
          "&currency=USD&intent=" + (authorizeMode ? "authorize" : "capture");
        waitingForSdk = true;
        script.onerror = () => { setPaymentBusy(false); E("Could not load PayPal. Check payment status before retrying."); };
        script.onload = () => {
          try {
            const paypal = (window as any).paypal;
            if (!paypal?.Buttons) throw Error("PayPal approval is unavailable. Check payment status before retrying.");
            Promise.resolve(paypal.Buttons({
              createOrder: () => result.order_id,
              onApprove: () => pay(authorizeMode ? "authorize" : "capture", authorizeMode),
              onCancel: () =>
                E("Approval cancelled. Check status before retrying."),
              onError: () => E("PayPal approval failed; check payment status."),
            }).render("#paypal-buttons")).then(() => setPaypalReady(true)).catch(() => E("PayPal approval could not be displayed. Check payment status before retrying.")).finally(() => setPaymentBusy(false));
          } catch (err: any) { setPaymentBusy(false); E(err.message); }
        };
        document.body.appendChild(script);
      } else {
        if ((action === "cancel" && result.status === "cancelled") || (action === "void" && result.status === "voided")) { V(null); setOrderRef(""); setPaypalReady(false); setPreauthorization(false); }
        setNotice("Sandbox payment status: " + result.status); E("");
      }
    } catch (e: any) {
      waitingForSdk = false;
      E(e.message);
    } finally {
      if (!waitingForSdk) setPaymentBusy(false);
    }
  }

  async function enter() {
    try {
      const result = await api(invite ? "join/" + invite : "rooms", { name, mode: "general", initial_request: invite ? "" : shoppingRequest.trim() });
      const r = result.room || result;
      if (!invite && shoppingRequest.trim()) setInitialMissionLoading(true);
      S(r);
      history.replaceState({}, "", "?room=" + r.id);
      if (result.invite) I(result.invite);
      else I(r.invite);
      E("");
      if (!invite && shoppingRequest.trim()) {
        try {
          const interpreted = await api("rooms/" + r.id + "/intent", {});
          if (interpreted.intent?.shopping_context === "general" && !interpreted.intent?.bundle_requested && !interpreted.intent?.follow_up) {
            const fresh = await api("rooms/" + r.id);
            await api("rooms/" + r.id + "/concierge", { text: shoppingRequest.trim(), action: "answer", revision: fresh.revision, command_id: crypto.randomUUID() });
          }
        } catch (err: any) {
          E(err.message);
        } finally {
          setInitialMissionLoading(false);
        }
      }
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
      const incoming = await api("rooms/" + room.id);
      S((current: any) =>
        !current || incoming.revision >= current.revision ? incoming : current,
      );
      if (
        ["cart_line", "external_cart_add", "accept_proposal"].includes(kind)
      ) {
        setCartOpen(true);
        const line = kind === "cart_line" ? JSON.parse(value) : null;
        if (workspaceView === "product" && (!line || line.quantity > 0)) setWorkspaceView("discover");
        const existed =
          line &&
          room.cart?.some(
            (item: any) =>
              item.product === line.product && item.variant === line.variant,
          );
        setNotice(
          kind === "external_cart_add"
            ? "Added to your shared cart. This item is purchased at the retailer."
            : line?.quantity === 0
              ? "Removed from your shared cart."
              : existed
                ? "Cart quantity updated."
                : "Added to your shared cart.",
        );
      } else if (kind === "external_cart_remove")
        setNotice("Removed from your shared cart.");
      E("");
    } catch (e: any) {
      E(e.message);
      if (String(e.message).includes("Room changed")) {
        try {
          const fresh = await api("rooms/" + room.id);
          S((current: any) =>
            !current || fresh.revision >= current.revision ? fresh : current,
          );
        } catch {}
      }
    }
  }

  async function sendChat(message: string): Promise<boolean> {
    if (chatInFlight.current) return false;
    chatInFlight.current = true;
    setSendingChat(true);
    const pending = pendingChat.current?.text === message
      ? pendingChat.current
      : { text: message, id: crypto.randomUUID() };
    pendingChat.current = pending;
    try {
      let revision = room.revision;
      try {
        await api("rooms/" + room.id + "/commands", {kind:"chat", value:message, revision, command_id:pending.id});
      } catch (err: any) {
        if (err.status !== 409) throw err;
        const fresh = await api("rooms/" + room.id);
        S((current: any) => !current || fresh.revision >= current.revision ? fresh : current);
        revision = fresh.revision;
        await api("rooms/" + room.id + "/commands", {kind:"chat", value:message, revision, command_id:pending.id});
      }
      pendingChat.current = null;
      E("");
      try {
        const fresh = await api("rooms/" + room.id);
        S((current: any) => !current || fresh.revision >= current.revision ? fresh : current);
      } catch {} // The accepted message will also arrive through the room socket.
      return true;
    } catch (err: any) {
      E(err.message || "Message could not be sent. Your draft is still here.");
      return false;
    } finally {
      chatInFlight.current = false;
      setSendingChat(false);
    }
  }

  const all = [...catalog, ...(room?.discovery || [])];
  const p = all.find((p) => p.id === (pendingFocus || room?.focus));
  const sandboxSubtotal = (room?.cart || []).reduce((total: number, item: any) => total + (catalog.find(product => product.id === item.product)?.price || 0) * item.quantity, 0);
  const cartItemCount = (room?.cart || []).reduce((total: number, item: any) => total + item.quantity, 0) + (room?.external_cart?.length || 0);
  const liveDealOffers = (room?.flash_offers || []).filter((offer: any) => ["OFFER_PUBLISHED", "COUNTERED", "ACCEPTED"].includes(offer.status));
  const dealPromptKey = room ? `${room.id}:${liveDealOffers.at(-1)?.id || "intro"}` : "";
  useEffect(() => {
    if (!dealPromptKey) return;
    try { setHiddenDealPromptKey(sessionStorage.getItem(`shopside-deal-prompt:${dealPromptKey}`) ? dealPromptKey : ""); }
    catch { setHiddenDealPromptKey(""); }
  }, [dealPromptKey]);
  useEffect(() => {
    if (workspaceView !== "plan" || !highlightPlanDeals) return;
    const frame = requestAnimationFrame(() => document.getElementById("plan-deals")?.scrollIntoView({behavior:"smooth",block:"start"}));
    return () => cancelAnimationFrame(frame);
  }, [workspaceView, highlightPlanDeals]);
  function dismissDealPrompt() {
    if (!dealPromptKey) return;
    try { sessionStorage.setItem(`shopside-deal-prompt:${dealPromptKey}`, "1"); } catch {}
    setHiddenDealPromptKey(dealPromptKey);
  }
  const showRoomOption = Boolean(room && (
    room.mode === "move_in" || room.move_in ||
    room.shopping_intent?.shopping_context === "move_in" ||
    room.shopping_intent?.spatial_eligible ||
    spatialEligible(p) ||
    (room.shortlist || []).some((id: string) => spatialEligible(all.find(item => item.id === id)))
  ));
  async function focusProduct(id: string) {
    setPendingFocus(id);
    setWorkspaceView("product");
    await command("focus", id);
    setPendingFocus(current => current === id ? null : current);
  }
  function openCart() {
    setWorkspaceView("discover");
    setCartOpen(true);
  }
  async function openRetailerCheckout(productId:string,retailer:string){
    const tab=window.open("about:blank","_blank");
    try{
      const response=await sessionFetch(`/api/rooms/${encodeURIComponent(room.id)}/products/${encodeURIComponent(productId.replace(/^channel3:/,""))}/retailer-link?retailer=${encodeURIComponent(retailer)}`);
      const data=await response.json().catch(()=>null);
      if(!response.ok||!data?.url)throw Error(data?.detail||"This retailer offer is no longer available. Try another offer.");
      if(tab){tab.opener=null;tab.location.href=data.url}else location.href=data.url;
    }catch(e:any){tab?.close();E(e.message)}
  }
  async function discover(pageToken?: string) {
    setSearching(true);
    try {
      await api("rooms/" + room.id + "/search", {
        query,
        min_price: minPrice ? Number(minPrice) : undefined,
        max_price: maxPrice ? Number(maxPrice) : undefined,
        availability: inStock ? ["InStock"] : [],
        mode: searchMode,
        brand: resultBrand.trim() || undefined,
        retailer_domain: resultRetailer.trim() || undefined,
        country: searchLocale.split(":")[0],
        currency: searchLocale.split(":")[1],
        language: searchLocale.split(":")[2],
        page_token: pageToken,
        revision: room.revision,
        command_id: crypto.randomUUID(),
      });
      const fresh=await api("rooms/"+room.id);
      S((current:any)=>!current || fresh.revision>=current.revision ? fresh : current);
      E("");
    } catch (e: any) {
      E(e.message);
    } finally { setSearching(false); }
  }
  async function findForMission() {
    const mission=room.move_in?.mission;
    const history=(room.move_in?.history || []).filter((entry:any)=>entry.actor!=="ShopSide").map((entry:any)=>entry.text);
    const brief=[...history,...(mission?.priorities || []),...(mission?.must_have || [])].join(" ").trim().slice(0,500);
    if (!brief) { setWorkspaceView("plan"); return; }
    setSearching(true);
    try {
      await api("rooms/"+room.id+"/search",{query:brief,mode:"agentic",country:mission?.country || undefined,currency:mission?.currency || undefined,max_price:mission?.budget_cents == null ? undefined : mission.budget_cents/100,revision:room.revision,command_id:crypto.randomUUID()});
      const fresh=await api("rooms/"+room.id);
      S((current:any)=>!current || fresh.revision>=current.revision ? fresh : current);
      E("");
    } catch (err:any) { E(err.message); }
    finally { setSearching(false); }
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
        <span className="topbar-caption">A little closer, even from afar</span>
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
              {room.people.length < 4 && (
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
      {roomAlert && workspaceView === "discover" && <div className="room-alert" role="status"><span>{roomAlert}</span><button type="button" aria-label="Dismiss room update" onClick={() => setRoomAlert("")}>×</button></div>}
      {notice && (
        <p role="status" className="cart-notice">
          <span>{notice}</span>
          <button className="view-cart" onClick={openCart}>
            View cart
          </button>
          <button
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            ×
          </button>
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
          <button aria-label="Dismiss message" onClick={() => E("")}>
            ×
          </button>
        </p>
      )}
      {!room && !entryReady ? (
        <main className="welcome" aria-busy="true">Opening your space…</main>
      ) : !room ? (
        <main className="welcome">
          <div className="welcome-grid">
            <div className="welcome-copy">
              <div className="welcome-tag">
                <span /> A little closer, even from afar
              </div>
              {invite ? <><h1>You’re invited<span className="period">.</span><br /><em>Come on in.</em></h1><p>Pick a name and join the shared room. Everything your friend has already planned will be there.</p></> : <><h1>Shopping is<br /><em>better together.</em></h1><p>One shared room for any shopping goal. Explore real products, compare with AI, and choose with your people.</p></>}
              <form
                className="welcome-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  enter();
                }}
              >
                {!invite && <>
                <label htmlFor="welcome-shopping">
                  WHAT ARE YOU SHOPPING FOR?
                </label>
                <input
                  id="welcome-shopping"
                  aria-label="What are you shopping for today?"
                  placeholder="Describe your goal, budget, and who you’re shopping with…"
                  value={shoppingRequest}
                  onChange={(e) => setShoppingRequest(e.target.value)}
                  maxLength={2000}
                />
                <div className="inspiration" aria-label="Shopping inspiration"><span>Need inspiration?</span>{[["Furnish my apartment", "We’re moving into a new apartment and need to furnish it together."], ["Build my workspace", "We need a desk and chair for our workspace."], ["Find the perfect gift", "Help us find a gift together."], ["Compare products", "Help us compare products and choose together."]].map(([label, goal]) => <button key={label} type="button" onClick={() => setShoppingRequest(goal)}>{label}</button>)}</div>
                </>}
                <label htmlFor="welcome-name">WHAT SHOULD WE CALL YOU?</label>
                <div className="welcome-name-row">
                  <input
                    id="welcome-name"
                    aria-label="Your name"
                    placeholder="Enter your name"
                    value={name}
                    onChange={(e) => N(e.target.value)}
                    required
                  />
                  <button>
                    {invite ? "Join your friend" : "Create your shopping room"}{" "}
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
                  Shop live. Compare with AI. Decide together.
                  <br />
                  <small>No account needed to get started.</small>
                </span>
              </div>
            </div>
            <WelcomeIllustration />
          </div>
          <div className="welcome-footer">
            <span>✳ &nbsp; A BETTER WAY TO SHOP TOGETHER</span>
            <a href="/merchant">Merchant workspace ↗</a>
          </div>
        </main>
      ) : (
        <>
          <main className={"room tab-" + tab}>
            <section id="shop" className="shop-column">
              <div className="workspace-bar">
                <div className="workspace-bar-title"><span className="workspace-orb"><Sparkles size={17}/></span><div><div className="workspace-name"><strong>{room.title}</strong><button className="edit-title" disabled={!online} onClick={()=>{const title=prompt("Room title",room.title);if(title)command("title",title);}}>Edit</button></div><small>{me?.name && <><span aria-label="Your room identity">You’re {me.name}</span> · </>}{room.people.length} {room.people.length === 1 ? "person" : "people"} · {online ? "Live" : "Reconnecting"}{room.move_in?.mission?.budget_cents != null ? ` · ${room.move_in.mission.currency} ${(room.move_in.mission.budget_cents/100).toFixed(2)} budget` : ""}</small></div></div>
                <button className="workspace-cart" onClick={openCart}><ShoppingBag size={16}/> Cart & checkout <span>{(room.cart || []).reduce((sum:number,item:any)=>sum+item.quantity,0)+(room.external_cart?.length || 0)}</span></button>
              </div>
              <div className="workspace-summary" aria-label="Your shared workspace">
                <div><strong>Our plan</strong><span>{room.move_in?.mission?.budget_cents != null ? `${room.move_in.mission.currency} ${(room.move_in.mission.budget_cents / 100).toFixed(2)} budget` : room.budget != null ? `USD ${(room.budget / 100).toFixed(2)} budget` : "Budget not set"} · {room.shortlist.length} shortlisted {room.shortlist.length===1?"product":"products"}{room.smart_bundle?.saved ? " · 1 saved bundle" : ""}</span></div>
                <div className="workspace-summary-actions">
                  <button type="button" onClick={()=>setWorkspaceView("plan")}>View plan</button>
                  {showRoomOption && <button type="button" onClick={()=>{setStudioActive(false);setWorkspaceView("room")}}>Open our room</button>}
                  {p && <button type="button" onClick={()=>setWorkspaceView("product")}>View selected</button>}
                </div>
              </div>
              <div className="workspace-panel" aria-label="Discover products">
              {initialMissionLoading && <p role="status">Understanding your shopping goal…</p>}
              {room.shopping_intent?.shopping_goal && <div className="bundle-panel"><strong>Your shopping goal</strong><p>{room.shopping_intent.shopping_goal}</p>{room.shopping_intent.follow_up && <form className="intent-answer" onSubmit={answerFollowUp}><label htmlFor="intent-answer-input">{room.shopping_intent.follow_up}</label><div className="intent-answer-row"><input id="intent-answer-input" value={followUpAnswer} onChange={event=>setFollowUpAnswer(event.target.value)} placeholder="For example: a tailored suit, a dress, or a saree" maxLength={400} autoComplete="off" required/><button type="submit" disabled={!online || followUpBusy}>{followUpBusy ? "Planning…" : "Continue planning"} <ArrowRight size={16}/></button></div>{followUpError && <p role="alert" className="intent-answer-error">{followUpError}</p>}</form>}</div>}
              <SmartBundle room={room} me={me} online={online} selectProduct={focusProduct} openPlan={()=>setWorkspaceView("plan")} saveProduct={id=>command("shortlist",id)} openStudio={async id=>{await focusProduct(id);setStudioActive(true);setWorkspaceView("room")}} />
              {dealPromptKey !== hiddenDealPromptKey && <aside className="deal-prompt" aria-label="Seller offers invitation"><span className="deal-prompt-icon"><Sparkles size={17}/></span><div><strong>{liveDealOffers.length ? `${liveDealOffers.length} seller ${liveDealOffers.length===1?"offer is":"offers are"} ready` : "Seller offers, when you want them"}</strong><p>{liveDealOffers.length ? "Review the sandbox offer together in Our plan." : "Opt in to hear from ShopSide sandbox merchants. You can choose this later in Our plan."}</p></div><button type="button" className="deal-prompt-action" onClick={()=>{dismissDealPrompt();setHighlightPlanDeals(true);setWorkspaceView("plan")}}>View in plan <ArrowRight size={14}/></button><button type="button" className="deal-prompt-close" aria-label="Dismiss seller offers invitation" onClick={dismissDealPrompt}>×</button></aside>}
              <div className="discovery">
                <div className="section-heading">
                  <div>
                    <span className="section-kicker">
                      <span className="lime-dot" /> EXPLORE TOGETHER
                    </span>
                    <h2>
                      Find your next favorite<span className="period">.</span>
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
                  <button disabled={!online || searching || !query.trim()}>
                    {searching ? "Searching…" : "Search Channel3"} <ArrowRight size={15} />
                  </button>
                </form>
                <details className="filter-details"><summary>Filters <span>Price · availability · brand · retailer</span></summary><div className="search-filters">
                  <label>Min price <input aria-label="Minimum price" type="number" min="0" value={minPrice} onChange={e => setMinPrice(e.target.value)} /></label>
                  <label>Max price <input aria-label="Maximum price" type="number" min="0" value={maxPrice} onChange={e => setMaxPrice(e.target.value)} /></label>
                  <label><input type="checkbox" checked={inStock} onChange={e => setInStock(e.target.checked)} /> In stock</label>
                  <label>Search mode <select value={searchMode} onChange={e => setSearchMode(e.target.value)}><option value="default">Standard</option><option value="agentic">Agentic</option><option value="keyword">Keyword</option></select></label>
                  <label>Search market <select value={searchLocale} onChange={e=>setSearchLocale(e.target.value)}><option value="US:USD:en">United States · USD</option><option value="GB:GBP:en">United Kingdom · GBP</option><option value="CA:CAD:en">Canada · CAD</option><option value="AU:AUD:en">Australia · AUD</option></select></label>
                  <label>Brand <input value={resultBrand} onChange={e=>setResultBrand(e.target.value)} placeholder="e.g. Nike" maxLength={100}/></label>
                  <label>Retailer domain <input value={resultRetailer} onChange={e=>setResultRetailer(e.target.value)} placeholder="e.g. nike.com" maxLength={253}/></label>
                </div>
                <p>Filters apply to your next Channel3 search. Enter the brand’s exact name and the retailer’s domain.</p>
                </details>
                {room.search_page_token && room.search_query === query && <button onClick={() => discover(room.search_page_token)}>Next results</button>}
                {room.mode === "move_in" && <button className="search-from-brief" disabled={!online || searching} onClick={findForMission}><Sparkles size={15}/> Find matches from your plan</button>}
                {room.discovery?.length > 0 ? (
                  <><div className="results-heading"><strong>Live results</strong><span>{room.discovery.length} products · shared with your room</span></div><div className="live-grid">
                    {room.discovery.map((item: any) => (
                      <article className="live-product" key={item.id}>
                        {item.image && <img src={item.image} alt={item.name} />}
                        <div>
                          <span className="card-tag">LIVE DISCOVERY</span>
                          <h3>{item.name}</h3>
                          {(item.key_features?.[0] || item.description) && <p>{item.key_features?.[0] || item.description}</p>}
                          <div className="live-actions">
                            <button
                              disabled={!online}
                              onClick={() => focusProduct(item.id)}
                            >
                              Look at this
                            </button>
                            <button
                              disabled={
                                !online ||
                                !!room.checkout ||
                                !item.offers?.length
                              }
                              onClick={() =>
                                command("external_cart_add", item.id)
                              }
                            >
                              Add to cart
                            </button>
                            <button
                              disabled={!online}
                              onClick={() => command("shortlist", item.id)}
                            >
                              Save
                            </button>
                          </div>
                          {(item.offers || []).slice(0, 2).map((o: any, i: number) => (
                            <p key={i}>
                              <a
                                href={o.url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {o.retailer} · {o.currency}{" "}
                                {o.price_cents == null ? "Price unavailable" : (o.price_cents / 100).toFixed(2)} ↗
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
                  </div></>
                ) : <div className="workspace-empty"><span>✳</span><div><strong>Ready when you are.</strong><p>Search real products or use your plan to find options together.</p></div></div>}
              </div>
              <details className="catalog-disclosure" open={!room.discovery?.length}>
              <summary>ShopSide sandbox collection <span>Fictional · PayPal Sandbox</span></summary>
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
                      value={catalogQuery}
                      onChange={(e) => setCatalogQuery(e.target.value)}
                    />
                  </div>
                </div>
                <div className="catalog" tabIndex={0} aria-label="Sandbox products">
                  {[...catalog].sort((a,b) => room.mode === "move_in" ? Number(Number(b.id) >= 11) - Number(Number(a.id) >= 11) : 0)
                    .filter((item) =>
                      item.name.toLowerCase().includes(catalogQuery.toLowerCase()),
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
                        onClick={() => focusProduct(item.id)}
                      >
                        <span className="product-card-image">
                          <span className="product-card-number">0{i + 1}</span>
                          <img
                            className="mini"
                            src={
                              item.image || "/products/headphones-render.png"
                            }
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
              </details>
              </div>
              <WorkspaceOverlay open={workspaceView!=="discover"} title={workspaceView === "product" ? "Product details" : workspaceView === "plan" ? "Our plan" : workspaceView === "room" ? studioActive ? "Move-in Studio" : "Our room" : "Compare together"} drawer={workspaceView === "plan"} onClose={()=>{setStudioActive(false);setHighlightPlanDeals(false);setWorkspaceView("discover")}}>
              {roomAlert && workspaceView !== "discover" && <div className="room-alert" role="status"><span>{roomAlert}</span><button type="button" aria-label="Dismiss room update" onClick={() => setRoomAlert("")}>×</button></div>}
              <div className="workspace-panel spotlight-panel" hidden={workspaceView!=="product"} aria-label="Product spotlight">
              {room.agreed_product && (
                <div role="status" className="agreement-banner">
                  ✓ We chose{" "}
                  {all.find((item) => item.id === room.agreed_product)?.name ||
                    "this item"}{" "}
                  together.
                </div>
              )}
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
                    <button
                      className="agreement-button"
                      disabled={!online || !p}
                      onClick={() => command("agreement", p.id)}
                    >
                      {room.agreement_votes?.[me?.name] === p?.id
                        ? "You agree with this choice"
                        : "Agree on this choice"}
                    </button>
                    {room.agreed_product === p?.id && (
                      <p role="status" className="agreement-success">
                        ✓ We chose this together.
                      </p>
                    )}
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
              {p && spatialEligible(p) && <button className="view-in-room" onClick={()=>{setStudioActive(true);setWorkspaceView("room")}}>Try in Move-in Studio <ArrowUpRight size={15}/></button>}
              {p && <WhyPick room={room} product={p} />}
              {workspaceView === "product" && p?.provenance === "channel3" && (
                <ProductDetails key={p.id} product={p} room={room} online={online} />
              )}
              {p?.provenance === "channel3" ? (
                <div className="cart-controls">
                  <span className="retailer-copy">
                    Retailer item · purchased on the retailer’s site
                  </span>
                  <button
                    className="cart-add"
                    disabled={!online || !!room.checkout || !p?.offers?.length}
                    onClick={() => command("external_cart_add", p.id)}
                  >
                    Add to cart <ArrowRight size={15} />
                  </button>
                </div>
              ) : (
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
                      <option value="standard">Standard</option>
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
                    disabled={
                      !online ||
                      !!room.checkout ||
                      !p ||
                      !Number.isInteger(quantity) ||
                      quantity < 1 ||
                      quantity > 10
                    }
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
              </div>
              <div className="workspace-panel" hidden={workspaceView!=="plan"} aria-label="Shopping plan">
                <PlanOverview room={room} me={me} online={online} products={all} showRoomOption={showRoomOption} api={api} onState={fresh=>S((current:any)=>!current || fresh.revision>=current.revision?fresh:current)} onDiscover={()=>setWorkspaceView("discover")} onRoom={()=>{setStudioActive(false);setWorkspaceView("room")}} toggleShortlist={id=>command("shortlist",id)} onCompare={async()=>{try{if(room.comparison?.join(",")!==room.shortlist.join(","))await api("rooms/"+room.id+"/commands",{kind:"compare",value:room.shortlist.join(","),revision:room.revision,command_id:crypto.randomUUID()});setWorkspaceView("together");E("")}catch(e:any){E(e.message)}}} />
                {(room.price_watch_alerts||[]).filter((alert:any)=>alert.participant===me).slice(-3).map((alert:any)=><div key={alert.id} className="plan-deals-highlight" role="status"><strong>Price Watch · ${((alert.price_cents||0)/100).toFixed(2)} USD</strong><p>{alert.message}</p><small>Observed {new Date(alert.observed_at).toLocaleString()} · Open the product to check its latest retailer offer.</small></div>)}
                <div id="plan-deals" tabIndex={-1} className={"plan-deals"+(highlightPlanDeals?" plan-deals-highlight":"")}><SellerOffers room={room} me={me} onCheckout={async offer=>{try{const payment=await api(`rooms/${room.id}/seller-offers/${offer.id}/checkout`,{});V(payment);openCart();E("")}catch(e:any){E(e.message)}}} /></div>
                {room.mode === "move_in" ? <details className="plan-more"><summary>Move-in planning details</summary><MoveIn room={room} online={online} me={me} api={api} initialLoading={initialMissionLoading} onResults={()=>setWorkspaceView("discover")} /><MemoryReceipt room={room} online={online} /></details> : <details className="plan-more"><summary>Ask ShopSide about your plan</summary><Concierge room={room} online={online} /><button type="button" disabled={!online} onClick={async()=>{try{await api("rooms/"+room.id+"/home-plan",{});E("");}catch(e:any){E(e.message);}}}>Add move-in planning</button></details>}
              </div>
              <div className="workspace-panel" hidden={workspaceView!=="room"} aria-label="Room view">
                {workspaceView==="room" && (studioActive ? <RoomPreview room={room} focused={spatialEligible(p)?p:null} online={online} me={me} command={command} /> : <section className="shared-room-entry"><span className="section-kicker">YOUR SHARED SHOPPING ROOM</span><h2>Decide together, wherever you are.</h2><p>Your chat, shortlist, bundle and approvals stay in sync across devices. Browsing together never requires 3D.</p>{spatialEligible(p)&&<button onClick={()=>setStudioActive(true)}>Try {p.name} in Move-in Studio →</button>}</section>)}
              </div>
              <div className="workspace-panel" hidden={workspaceView!=="together"} aria-label="Compare together">
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
              </div>
              <Recommendations
                room={room}
                products={all}
                select={focusProduct}
              />
              <DecisionBoard room={room} products={all} />
              </div>
              </WorkspaceOverlay>
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
              <div className="conversation-label">
                <span>THE ROOM CHAT</span>
                <span>{room.people.length} PEOPLE · <button type="button" className="sound-toggle" aria-pressed={soundEnabled} onClick={toggleSound}>{soundEnabled ? "Sound on" : "Enable sound"}</button></span>
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
                      className={m.actor === "ShopSide" ? "agent-message" : m.actor === me?.name ? "message-own" : "message-incoming"}
                    >
                      <span className="message-avatar">
                        {m.actor === "ShopSide" ? (
                          <Sparkles size={13} />
                        ) : (
                          m.actor.charAt(0).toUpperCase()
                        )}
                      </span>
                      <div>
                        <strong>{m.actor}{m.actor === me?.name && m.actor !== "ShopSide" ? " · You" : ""}</strong>
                        <p>{m.actor === "ShopSide" ? <AssistantMessage text={m.text} products={all} /> : m.text}</p>
                      </div>
                    </article>
                  ))
                )}
              </div>
              <form
                className="message-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const draft = text.trim();
                  if (!draft || thinking || sendingChat) return;
                  if (target === "everyone") {
                    if (await sendChat(draft)) T((current) => current.trim() === draft ? "" : current);
                  } else {
                    Thinking(true);
                    try {
                      await api("rooms/" + room.id + "/agent", { text: draft, revision: room.revision });
                      T((current) => current.trim() === draft ? "" : current);
                      E("");
                    } catch (err: any) { E(err.message); }
                    finally { Thinking(false); }
                  }
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
                    disabled={!online || thinking || sendingChat || !text.trim()}
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
              <button type="button" className="chat-cart-entry" onClick={openCart}><ShoppingBag size={15}/> Cart & checkout <span className="cart-count">{cartItemCount}</span></button>
              {cartOpen && createPortal(<><button className="cart-backdrop" aria-label="Close cart and checkout" onClick={()=>setCartOpen(false)} />
              <details
                className="side-details cart-details"
                role="dialog"
                aria-modal="true"
                aria-label="Cart and checkout"
                open={cartOpen}
                onToggle={(e) => {
                  setCartOpen(e.currentTarget.open);
                }}
              >
                <summary>
                  <span>
                    <ShoppingBag size={15} /> Cart & checkout
                  </span>
                  <span className="cart-count">
                    {(room.cart || []).reduce(
                      (count: number, item: any) => count + item.quantity,
                      0,
                    ) + (room.external_cart?.length || 0)}
                  </span>
                </summary>
                <div>
                  <div className="cart-intro"><span>YOUR SHARED CART</span><h2>Ready when you are.</h2><p>{cartItemCount} {cartItemCount===1?"item":"items"} chosen together. Review each item and its checkout destination.</p></div>
                  <div className="cart-progress" aria-label="Checkout progress"><span className="is-current">1 <b>Review</b></span><span className={quote?"is-current":""}>2 <b>Checkout</b></span><span className={room.checkout?.status==="paid"?"is-current":""}>3 <b>Receipt</b></span></div>
                  {room.cart?.length === 0 && !room.external_cart?.length && (
                    <div className="cart-empty"><ShoppingBag size={26}/><strong>Your cart is waiting for a good find.</strong><p>Explore products, save what you like, and add your favorites here.</p><button type="button" onClick={()=>setCartOpen(false)}>Keep shopping <ArrowRight size={15}/></button></div>
                  )}
                  {!!room.cart?.length && <div className="cart-section-heading"><span>01 · PAYPAL SANDBOX</span><h3>ShopSide merchant items</h3><p>Fictional products for the demo. No goods ship.</p></div>}
                  {room.cart?.map((item: any) => (
                    <div
                      className="cart-line cart-product"
                      key={item.product + item.variant}
                    >
                      {(() => {const product=catalog.find(p=>p.id===item.product);return <div className="cart-product-main"><img src={product?.image || "/products/headphones-render.png"} alt=""/><div><strong>{product?.name||"Product"}</strong><small>{item.variant} · ShopSide sandbox</small><p>{product ? `$${(product.price / 100).toFixed(2)} each · $${((product.price * item.quantity) / 100).toFixed(2)}` : "Price unavailable"}</p></div></div>})()}
                      <CartQuantity
                        item={item}
                        disabled={!online || !!room.checkout}
                        update={(quantity) =>
                          command(
                            "cart_line",
                            JSON.stringify({ ...item, quantity }),
                          )
                        }
                        remove={() =>
                          command(
                            "cart_line",
                            JSON.stringify({ ...item, quantity: 0 }),
                          )
                        }
                      />
                    </div>
                  ))}
                  {!!room.external_cart?.length && (
                    <section aria-label="Retailer items">
                      <div className="cart-section-heading"><span>02 · RETAILER CHECKOUT</span><h3>Live retailer items</h3><p>Buy directly on each retailer’s site. Current price, delivery and availability are confirmed there. ShopSide may earn a commission from retailer links.</p></div>
                      {room.external_cart.map((item: any) => (
                        <div className="cart-line cart-product" key={item.id}>
                          <div className="cart-product-main">{item.image && <img src={item.image} alt=""/>}<div><strong>{item.name}</strong><small>Live product · retailer checkout</small></div></div>
                          {item.offers.map((offer: any, i: number) => (
                            <div className="cart-retailer-offer" key={i}><span>{offer.retailer}<small>{offer.price_cents == null ? "Price unavailable" : `${offer.currency} ${(offer.price_cents / 100).toFixed(2)} observed`}</small></span><button type="button" onClick={()=>openRetailerCheckout(item.id,offer.retailer)}>Buy at retailer ↗</button></div>
                          ))}
                          <button
                            disabled={!online || !!room.checkout}
                            onClick={() =>
                              command("external_cart_remove", item.id)
                            }
                          >
                            Remove retailer item
                          </button>
                        </div>
                      ))}
                    </section>
                  )}
                  {room.proposals?.map((proposal: any) => (
                    <button
                      key={proposal.id}
                      onClick={() => command("accept_proposal", proposal.id)}
                    >
                      Accept {proposal.proposer}'s proposal:{" "}
                      {catalog.find((p) => p.id === proposal.product)?.name}
                    </button>
                  ))}
                  {(!!room.cart?.length || !!room.checkout) && !quote && <div className="cart-checkout-cta"><div><strong>${(sandboxSubtotal/100).toFixed(2)} USD</strong><small>Sandbox subtotal · no real charge</small></div><button
                    className="checkout-button"
                    disabled={
                      !online ||
                      !me?.is_payer ||
                      (!room.cart?.length && !room.checkout)
                    }
                    onClick={checkout}
                  >
                    {me?.is_payer
                      ? "Continue to PayPal Sandbox"
                      : room.payer + " handles checkout"}
                  </button></div>}
                  {quote && (
                    <section className="quote">
                      <span className="cart-section-eyebrow">PAYMENT REVIEW · PAYPAL SANDBOX</span><h3>{quote.merchant_id?"Merchant offer checkout":"Review your order"}</h3>
                      <p>
                        {quote.merchant_name?quote.merchant_name+" · ":"ShopSide merchant · "}PayPal sandbox · No goods shipped
                      </p>
                      {quote.items?.map((item: any) => (
                        <p key={item.product + item.variant}>
                          {item.name || item.product} · {item.variant} ×{" "}
                          {item.quantity} · $
                          {((item.price * item.quantity) / 100).toFixed(2)}
                        </p>
                      ))}
                      <p>ShopSide fees $0.00 · No goods shipped</p>
                      <strong className="quote-total">
                        Total ${(quote.total / 100).toFixed(2)} USD
                      </strong>
                      {quote.reference_total!=null&&<p>Original ${(quote.reference_total/100).toFixed(2)} · Savings ${((quote.reference_total-quote.total)/100).toFixed(2)}</p>}
                      {room.checkout?.status==="paid"&&quote.merchant_id&&<div className="order-receipt"><span>ORDER COMPLETED · PAYPAL SANDBOX</span><h4>Chosen together. Paid in sandbox.</h4><p>{quote.merchant_name} · {quote.items?.map((item:any)=>`${item.name} × ${item.quantity}`).join(" + ")}</p><strong>ShopSide order {room.checkout.order_id||quote.id}</strong><small>PayPal capture {room.checkout.paypal_capture_id||quote.capture} · ${((quote.total||0)/100).toFixed(2)} USD · No goods shipped</small><a href={`/orders/${encodeURIComponent(room.checkout.order_id||quote.id)}?room=${encodeURIComponent(room.id)}`}>View order summary →</a></div>}
                      {orderRef && <p className="order-reference">Sandbox order: <strong>{orderRef}</strong> · {room.checkout?.status === "paid" ? "payment verified" : room.checkout?.status === "authorized" ? "authorized hold; settlement pending" : "awaiting PayPal approval"}</p>}
                      {room.checkout?.status!=="paid" && <p className="quote-approval-note">{preauthorization ? "PayPal will place a temporary authorization hold for this exact sandbox merchant and amount. The accepted offer can settle within 24 hours while you are away." : "You’ll review and approve the payment in PayPal before anything is captured."}</p>}
                      {quote.preauthorization_available && (room.checkout?.status || quote.status)==="quoted" && !paypalReady && <label className="quote-approval-note"><input type="checkbox" checked={preauthorization} onChange={event=>setPreauthorization(event.target.checked)} /> Authorize now, settle later if this merchant’s offer still qualifies</label>}
                      {room.checkout?.status!=="paid" && <button className="quote-primary" disabled={paymentBusy || paypalReady} onClick={() => pay("create")}>
                        {paymentBusy ? "Preparing PayPal…" : paypalReady ? "Approve with PayPal below" : preauthorization ? "Create PayPal authorization" : "Create PayPal sandbox order"}
                      </button>}
                      <div id="paypal-buttons" />
                      {room.checkout?.status!=="paid" && <button disabled={paymentBusy} onClick={() => pay("status")}>
                        Check payment status
                      </button>}
                      {room.checkout?.status==="authorized" && <button disabled={paymentBusy} onClick={() => pay("void", true)}>Void authorization</button>}
                      {room.checkout?.status!=="paid" && <button disabled={paymentBusy || (room.checkout?.status || quote.status) !== "quoted"} onClick={() => pay("cancel")}>
                        Cancel unused quote
                      </button>}
                    </section>
                  )}
                  {room.checkout && (
                    <p role="status">
                      {room.checkout.status === "paid"
                        ? `Order completed · ${room.checkout.order_id || room.checkout.id} · PayPal Sandbox capture ${room.checkout.paypal_capture_id || "verified"}`
                        : "Checkout: " + room.checkout.status}
                    </p>
                  )}
                </div>
              </details></>,document.body)}
              <div className="conversation-footer">
                <span>
                  <span className="lime-dot" /> YOUR ROOM IS PRIVATE
                </span>
                <span>MADE TO SHARE ✳</span>
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
                  if (key === "shop") setWorkspaceView("discover");
                  if (key === "together") setWorkspaceView("together");
                  requestAnimationFrame(() => document.getElementById(key === "chat" ? "chat" : "shop")?.scrollIntoView({ behavior: "smooth" }));
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
