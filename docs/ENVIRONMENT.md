# Configure integrations

Use secure environment settings or an ignored local `.env` file. Never send secrets in chat. Backend integrations read process variables; local startup can use `uvicorn --env-file .env` after installing python-dotenv, or Docker Compose's env_file.

| Name | Source / value |
| --- | --- |
| PAYPAL_ENV | sandbox |
| PAYPAL_CLIENT_ID | Client ID from a sandbox REST app in PayPal Developer Dashboard |
| PAYPAL_CLIENT_SECRET | Secret from that same sandbox app; direct runtime value is needed for Basic OAuth authentication |
| PAYPAL_MERCHANT_ID | Merchant ID of the sandbox business account bound to that app |
| CHANNEL3_API_KEY | Channel3 developer account API key |
| GEMINI_API_KEY | Google AI Studio API key |
| GEMINI_MODEL | Exact tool-capable model ID available to your account; verified during smoke test |
| WEB_ORIGIN | http://localhost:3000 for local use; must match browser Origin exactly |
| SHOPSIDE_DB | /workspace/shopside.sqlite3 locally, /data/shopside.sqlite3 in Compose |
| COOKIE_SECURE | false locally; true for HTTPS hosting |

PayPal sandbox buyer: create a separate personal sandbox account in the PayPal Developer Dashboard. Use its credentials only in PayPal's approval window. Do not configure buyer login/password in this app. No incoming webhook is required for explicit read-back reconciliation. No webhook URL/ID is currently required.

Cloud draft contains requirements and required hostnames. Review/save, then publish to activate; saving the draft alone does not update current credentials or networking. PayPal client secret must be supplied as a confidential direct runtime value, since the OAuth client encodes it into Basic authentication; a proxy placeholder is not sufficient. Gemini/Channel3 header credentials can use destination-bound secret injection.

Hosts: api.trychannel3.com, docs.trychannel3.com, generativelanguage.googleapis.com, api-m.sandbox.paypal.com, www.paypal.com, www.sandbox.paypal.com, paypalaihackathon.devpost.com. Existing package-manager access must remain enabled.

AG Studio documentation/SDK/licensing remain blocked pending access to the sponsor page. There is no guessed Studio environment variable. The implemented AG Grid fallback needs no license key.

## GCP Vertex AI / ADK
`AI_PROVIDER=vertex` is now the default. Standard Vertex AI requires GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION and usable ADC from a configured GCP identity with Vertex permissions; GOOGLE_APPLICATION_CREDENTIALS must refer to a valid supplied credential selector. No GCP identity was present at inspection. A project selector makes the client use ADC, even if a Gemini API key is also present.

Vertex express mode omits GOOGLE_CLOUD_PROJECT and uses VERTEX_API_KEY or GEMINI_API_KEY with vertexai=True. Destination-bound key injection must include aiplatform.googleapis.com. The existing GEMINI_API_KEY secret currently targets only generativelanguage.googleapis.com; edit its destination list in environment settings for express mode. The configuration tool cannot replace that existing binding. Do not add duplicate keys to work around it.

The Gemini Developer API is available only with AI_PROVIDER=developer. A prior Developer API 403 does not establish that a Vertex key is invalid.

Confirmed user mode: Vertex AI express. Use AI_PROVIDER=vertex-express; this explicitly ignores ambient project variables and uses the configured API key. Update the existing GEMINI_API_KEY destination list to include aiplatform.googleapis.com, then save/publish. No project ID, ADC service account or replacement API key is required for this mode. Current-runtime metadata still showed Developer API-only key injection at verification, so live Vertex inference was not attempted through a blocked destination.
