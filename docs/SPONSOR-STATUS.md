# Revised sponsor brief status

| Requirement | Status | Evidence / limitation |
| --- | --- | --- |
| Shared two-browser room | Implemented, previously verified | Desktop/mobile browser journey in tests |
| Channel3 v1 search/details | Implemented, live verified | Real Channel3 request through ADK; 12 results shared |
| Shared discovery and offer provenance | Implemented, live verified | Validated normalized models, retrieval time, external-only checkout |
| Gemini discovery/board tools | Implemented, live verified | Vertex express ADK discovery and board tools executed |
| AG Studio | Blocked | Sponsor page now accessible; official Studio documentation/SDK/licensing still need inspection |
| Real AG Grid fallback | Implemented | ag-grid-react/community 36.3.0; no Studio claim |
| Board presets, priorities and choice | Implemented | FastAPI persists preset and authoritative room selections |
| Numeric attribute chart | Omitted | No sourced comparable numeric attribute; no fabricated scores |
| Real-identity demo merchant matching | Not implemented | No exact identities verified; external products are retailer-only |
| PayPal sandbox | Implemented, live unverified | Mock provider domain tests only; requires merchant/buyer credentials |
| Recorded demo and pair feedback | Pending | Requires actual people and live provider run |

Channel3 base URL: https://api.trychannel3.com; POST /v1/search and GET /v1/products/{id}; x-api-key authentication. The normalizer accepts documented ProductDetail/Offer/Price shapes. The read cache serializes identical requests and expires after 30 seconds; bounded retry covers transient provider errors. Product descriptions are data, never authority to modify payment.

Required network settings additions for live checks/documentation: api.trychannel3.com, docs.trychannel3.com, paypalaihackathon.devpost.com, api-m.sandbox.paypal.com, www.paypal.com. Preserve existing allowlist settings. AG Studio documentation/package host must be established from the sponsor page once accessible. Keys belong in secure runtime configuration, never in chat or source.

Fixtures remain fictional demo merchant inventory. No discovered product is automatically matched or charged. Sandbox purchases ship no goods. Provider imagery is referenced from its returned HTTPS URL; confirm provider content-use terms before publication.
