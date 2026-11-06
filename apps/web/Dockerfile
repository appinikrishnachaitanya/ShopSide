# Build dependencies and compile Next.js once; Cloud Run only starts the production server.
FROM node:24-slim AS dependencies
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:24-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencies /app/node_modules ./node_modules
COPY package*.json ./
COPY . .
# Next.js evaluates rewrites during the build, so the API URL is a build argument.
ARG API_INTERNAL_URL
ENV API_INTERNAL_URL=${API_INTERNAL_URL}
RUN npm run build && npm prune --omit=dev

FROM node:24-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder --chown=node:node /app/package.json ./package.json
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/.next ./.next
COPY --from=builder --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["sh", "-c", "exec ./node_modules/.bin/next start --hostname 0.0.0.0 --port ${PORT:-3000}"]
