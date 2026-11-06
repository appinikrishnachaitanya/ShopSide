FROM node:24-slim AS paypal
WORKDIR /mcp
COPY paypal-mcp/package*.json ./
RUN npm ci --omit=dev
FROM python:3.12-slim
COPY --from=paypal /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY api/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY api/app app
COPY --from=paypal /mcp /paypal-mcp
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--workers", "1"]
