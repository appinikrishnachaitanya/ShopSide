# Build context: services/
# Stage 1: install the official PayPal MCP Node.js dependency.
FROM node:24-slim AS paypal
WORKDIR /mcp
COPY paypal-mcp/package*.json ./
RUN npm ci --omit=dev

# Stage 2: package the FastAPI backend and PayPal MCP.
FROM python:3.12-slim
COPY --from=paypal /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY api/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY api/app ./app
COPY api/alembic.ini ./alembic.ini
COPY api/alembic ./alembic
COPY --from=paypal /mcp /paypal-mcp
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
