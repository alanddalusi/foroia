FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --global npm@11.21.1 && npm ci --no-audit --no-fund
COPY . .
RUN npm run typecheck && npm run build
FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/.output ./.output
# Development TLS tooling is not required behind Caddy and must stay out of runtime.
RUN test -z "$(find /app/.output -path '*/node-forge/package.json' -print -quit)"
USER node
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
