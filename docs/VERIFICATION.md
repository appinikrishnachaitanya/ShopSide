# Actual verification
- Backend: four passing tests. Membership, two-member capacity, stale revision, deduplication, shared reactions, WebSocket updates, payer-only quote, cart freeze, exact total and duplicate capture protection.
- Payment tests use an explicitly mocked provider. They do not establish real PayPal authorization or capture.
- Playwright: one passing test using installed Chromium, two independent desktop/mobile contexts. Create, join, spotlight, reaction, both refresh, persisted restoration and 375px no-overflow check passed.
- Screenshots generated in `/tmp/shopside-desktop.png` and `/tmp/shopside-mobile.png`; mobile inspected and catalog search grid issue corrected.
- Next.js production build passed before final visual refinements.
- Live Gemini/PayPal checks, full checkout browser flow, real pair feedback, fresh Docker build and deployment have not been verified.

## Revised sponsor increment
- Six backend tests passed, including normalized shared Channel3 fixture results, missing-key 503 and external-offer cart rejection. Fixtures are explicitly test data.
- Production build passed with AG Grid Community 36.3.0.
- Desktop/mobile Playwright shared-room test rerun passed (1 test, 4.2s).
- Real Channel3 request and AG Studio integration remain unverified/blocked as detailed in SPONSOR-STATUS.md.

## Checkout hardening
- Nine backend tests passed: added lost capture response reconciliation, receipt authorization, foreign-origin rejection, variant pricing, inventory reservation/release and cancelled-operation replay.
- Expanded desktop/mobile browser journey passed: create/join, spotlight/reaction, refresh, shared shortlist/chat, midnight variant × 2, exact $198 quote, friend checkout disabled and safe quote cancellation.
- Fixed quote review sending GET instead of POST, discovered by that browser test.
- Event-driven WebSocket subscriber notifications replace polling of SQLite.
- Live credentials, Studio access, real identity/offer matching and actual pair feedback remain outstanding; passing offline checks do not establish provider success.

## Live Vertex AI express verification — November 6, 2026
Published configuration confirmed: key injection includes aiplatform.googleapis.com, AI_PROVIDER is present, and Vertex express inference succeeded.

- Real Vertex generation returned text successfully.
- Real ADK turn executed search_catalog and update_decision_board. Comparison [0,2] persisted; a second authenticated member fetched the same comparison and shared response.
- Real ADK discovery turn executed discover_products and update_decision_board, saved 12 actual Channel3 results and selected two Channel3 products. Both authenticated members fetched identical results and board selection.
- These checks used API clients with distinct cookie jars, not browser contexts; the earlier Playwright desktop/mobile journey is separate evidence.
- Reproduce the live discovery check with `PYTHONPATH=services/api .venv/bin/python scripts/verify_live_discovery.py` after configuring credentials. It creates a verification room and uses real model/provider calls.
- No buyer approval or capture was performed during these checks. These checks do not establish a completed sandbox purchase.
- A separate live ADK turn invoked paypal_order_status through the official PayPal MCP server against an app-created persisted sandbox order. API status 200, MCP tool activity recorded, and final agent response reported CREATED. The order remained unapproved and uncaptured.

## Voice, recommendations and UI
- Voice signaling backend test verifies origin/membership and forwarding of offer/answer only to another authenticated room member.
- The Chromium two-context voice test exchanged peer_ready, offer and answer, but no ICE candidates were gathered in this cloud environment (a separate direct Chromium diagnostic returned `iceGatheringState=complete`, zero candidates). Audio connection and mute/leave browser assertions therefore failed and remain unverified; no claim of working cross-network audio is made. Test uses a fake microphone, not an actual human call.
- Room desktop/mobile browser journey still passed after the UI change. The public Railway deployment has not been performed or tested. The STUN default may require an externally configured TURN relay for restrictive networks.
- Recommendations use the shared state, including exact product names mentioned by humans, confirmed preferences, shortlist, explicit likes and budget; they do not infer missing product performance facts.

## Cart regression
- Sample-product cart: desktop/mobile browsers verified add feedback, automatic cart opening, shared quantity changes, exact quote and payer restriction.
- Live Channel3 cart: two independent browsers verified a real retailer listing can be added, seen by both participants and retained after refresh. Retailer-only carts cannot create a ShopSide PayPal quote; retailer offers remain separate from merchant inventory.
- SQLite backend: 16 tests passed, one PostgreSQL-specific test skipped. PostgreSQL 17.11: 17 tests passed, including the new cart boundary tests.
- These are local tests using an isolated database; Cloud Run deployment has not been verified by this check.
- Expanded desktop/mobile journey: both participants spotlight and shortlist two products, compare them, send chat, refresh and retain the shared state, then change cart quantities and review the same quote.
- Live ADK journey: a second participant saved a preference and made an actual Vertex AI + Channel3 request; both browser contexts received the two-product comparison and it survived refresh. No mock model or catalog was used for this test.
