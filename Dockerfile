# WhyBot — one container: FastAPI engine (internal :8000) + Next.js web app (public $PORT).
# Works on Render, Railway, Fly.io, Google Cloud Run, Hugging Face Spaces (Docker) or any Docker host.

# ---------- 1) build the web app ----------
FROM node:20-bookworm-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
# /api/* is proxied to the engine inside the same container
ENV BACKEND_URL=http://127.0.0.1:8000 NEXT_TELEMETRY_DISABLED=1
RUN npm run build && npm prune --omit=dev

# ---------- 2) runtime ----------
FROM python:3.12-slim-bookworm
COPY --from=web /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=web /app/web /app/web
COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh && useradd -m whybot && chown -R whybot /app
USER whybot

ENV PORT=3000 \
    PYTHONUNBUFFERED=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    STATE_FILE=/tmp/whybot_state.json \
    PUBLIC_MODE=1 \
    TRUSTED_PROXY_HOPS=1 \
    HYDRA_DATABASE=whybotpublic \
    MAX_UPLOAD_MB=10 \
    AUTO_SAMPLE=1
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD node -e "fetch('http://127.0.0.1:'+process.env.PORT+'/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["/app/start.sh"]
