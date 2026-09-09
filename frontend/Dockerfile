# syntax=docker/dockerfile:1.7

ARG BUN_IMAGE=oven/bun:1.3.13-slim

FROM ${BUN_IMAGE} AS build
WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM ${BUN_IMAGE} AS runtime

ARG APP_VERSION=0.1.0
ARG VCS_REF=local
LABEL org.opencontainers.image.title="PocketTally Frontend" \
      org.opencontainers.image.description="PocketTally Nuxt frontend" \
      org.opencontainers.image.source="https://github.com/LouisLiuNova/PocketTally" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.licenses="MIT"

ENV HOME=/tmp \
    NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=3000 \
    NUXT_API_BASE=http://backend:8000

WORKDIR /app
COPY --from=build --chown=bun:bun /app/.output ./.output

USER bun
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD ["bun", "-e", "fetch('http://127.0.0.1:3000/api/v1/health').then(async response => { const data = await response.json(); process.exit(response.ok && data.ready ? 0 : 1) }).catch(() => process.exit(1))"]

CMD ["bun", ".output/server/index.mjs"]
