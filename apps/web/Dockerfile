FROM node:24-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["sh", "-c", "exec npx next start --hostname 0.0.0.0 --port ${PORT:-3000}"]
