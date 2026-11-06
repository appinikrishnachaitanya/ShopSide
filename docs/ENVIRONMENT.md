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
