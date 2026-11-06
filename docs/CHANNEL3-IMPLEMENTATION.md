# Collaborative shopping implementation and verification

## Architecture and assessment

The Next.js frontend uses its runtime `BACKEND_URL` proxy for HTTP and WebSocket requests. FastAPI keeps room membership, shared snapshots, checkout records and shopping conversation state in its existing database. Channel3's Python SDK drives native shopping conversations on the server; Channel3 search, product detail and similar endpoints supply product data. Google ADK/Gemini is retained for collaborative decision assistance. WebRTC sends audio directly between browsers and uses the existing room signaling endpoint. PayPal Sandbox applies only to the fictional ShopSide inventory; Channel3 offers link to their original retailer URLs.

The provider conversation ID, history, question count, result snapshots, shortlist, votes and checkout status live in the room's existing JSON state. No new relational columns are necessary for these fields; run existing Alembic migrations as described in CLOUD-RUN.md.

## Channel3 capability matrix

| Capability | Status |
| --- | --- |
| Native conversations, continuation, text, suggestions, product results | Implemented using `channel3-sdk` on the server; buffered responses, not streaming |
| Maximum five clarification questions, skip and show products | Implemented server-side; forced search uses accumulated participant text |
| Search: default, agentic and keyword modes; price and availability; next page | Implemented using the documented search endpoint; other filter dimensions and locale controls are deferred |
| Product details, multiple offers, provider variants and similar products | Implemented; variant selection triggers provider resolution; data absent from Channel3 is not invented |
| Price history, subscriptions, webhooks, alerts | Deferred; account access and delivery have not been verified |
| Image search, URL lookup and category browsing | Deferred; no upload or arbitrary URL fetching is enabled |
| Official React components | Not integrated; compatibility, availability and licensing were not established |
| Affiliate reporting | Original retailer URLs are preserved; reporting and attribution dashboards are not implemented |

API references reviewed: [Channel3 API skills](https://github.com/channel3-ai/skills), including its current conversations and API reference. Channel3 is the source of product and merchant facts. Provider availability and output can change; a response is never substituted with invented products.

## Validation and limitations

Native Channel3 conversation, product detail and similar-product requests succeeded against the configured account during development. Live filtered default and agentic searches each returned 12 products and a next-page token. The backend regression suite passed 23 tests with one skipped; the two-browser room regression passed, and the frontend production build succeeded. Automated provider tests use mocks unless explicitly enabled.

There is no streaming, image search, price-history chart, affiliate reporting, webhook, or automated product alert yet. Gemini cannot create agreement or place orders: each shopper must vote explicitly and the designated payer must approve eligible checkout. Two-browser audio and a complete PayPal approval/capture require live browser/provider testing. Set up TURN for reliable calling across restrictive networks. Calls, WebSocket subscriptions, room locks and rate limits are currently process-local: run **one API instance with one worker** until shared coordination and cross-instance pub/sub are implemented. PostgreSQL alone does not provide multi-instance synchronization.

## Three-minute walkthrough

1. Open ShopSide and enter a natural-language request such as “I need checked luggage for a ten-day trip under $200.” Create the room. Answer or skip the provider's questions, or choose **Show products now**.
2. Explore the live results, filter them, select a product to inspect available variants and retailer offers, and save options. Choose **Invite a Friend**, share the link and join in a second browser.
3. Confirm both people see the same products, shortlist and comparison. Join the voice call where network conditions allow. Give each person's priorities and ask the decision assistant to compare evidence and tradeoffs.
4. Each shopper selects **Agree on this choice** for the same product. Open a live offer at its retailer. For the fictional ShopSide products, the authorized payer can use the PayPal Sandbox flow and confirm the provider's result.

Use configured provider credentials and a working network for the walkthrough; provider responses, inventory and prices are live and cannot be guaranteed. See ENVIRONMENT.md and CLOUD-RUN.md for configuration, and VERIFICATION.md for existing opt-in tests.
