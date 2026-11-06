# Google ADK and official PayPal MCP

The shared coordinator now runs as a Google ADK Agent with an InMemoryRunner, bounded model calls, validated room tools and persisted room outcomes. ADK sessions are per invocation; durable chat, preferences, proposals and activity remain in SQLite. No agent memory is required after restart.

PayPal MCP is the official @paypal/mcp 1.8.1 stdio process, pinned by services/paypal-mcp/package-lock.json. It receives a freshly issued sandbox token through the child environment, never command arguments. Only orders.get is enabled. The ADK paypal_order_status tool binds the order ID from the authenticated room checkout, returns minimal status, and never exposes raw customer/provider data. A friend receives only the stored shared checkout status. Create/capture remain payer-authorized domain operations with durable request identities. MCP does not authorize human spending.

Verified in this runtime:
- Sandbox OAuth 200 with supplied credentials.
- Channel3 live search 200 with one real product.
- Official MCP handshake and tools/list: get_order only.
- Persisted app sandbox order creation 200, without approval or capture.
- MCP get_order provider response denied (403); official toolkit uses api.sandbox.paypal.com, which needs the added network domain activated. No successful order read is claimed.
- Gemini model discovery: 403 PERMISSION_DENIED, reason API_KEY_SERVICE_BLOCKED. Permit Generative Language API on this key in Google Cloud API restrictions, and ensure the API is enabled in the key's project. No successful ADK inference is claimed.
- Ten offline tests pass; the ADK test uses an explicitly fake runner to verify actual room tool execution, shared activity persistence and absence of payment mutation tools.

Setup: npm ci --prefix services/paypal-mcp; install services/api/requirements.lock. No additional PayPal key is required. Existing client ID/secret mint the temporary MCP token. Node 24 is needed alongside Python 3.12. Compose now includes Node and the pinned MCP installation in the API container; container execution remains unverified.

## Current Vertex verification
The earlier Developer API failure is superseded by successful Vertex AI express inference. Live ADK calls executed catalog lookup and comparison, then actual Channel3 search and shared board selection. Two independently authenticated API clients observed identical results. The official MCP order read also succeeded after its host became active, returning CREATED. See VERIFICATION.md for the current evidence; no real buyer approval/capture is claimed.
