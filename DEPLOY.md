# Deploy WhyBot publicly

WhyBot is two parts:
- **Web app** (Next.js): the pages people see.
- **Engine** (FastAPI): talks to HydraDB and the LLM, and keeps the graph, cache and rate limits in memory.

The engine needs to be a long-running server, so it can't live on Vercel's serverless functions: they forget in-memory state between requests and time out on long HydraDB calls. Pick one of the two setups below.

| Setup | Cost | URL | Best for |
|---|---|---|---|
| **A. Everything on Render** (recommended) | Free | `whybot.onrender.com` | Fastest path; one service, one URL |
| **B. Web on Vercel + engine on Render** | Free | `whybot.vercel.app` | Vercel's global CDN for the pages |

Free Render services sleep after 15 minutes without visitors; the first visit after that takes about a minute to wake up. Open the URL a few minutes before a demo, or use a paid instance ($7/month) to keep it awake.

---

## A. Everything on Render (about 5 minutes)

1. Sign in at https://dashboard.render.com with GitHub.
2. **New → Blueprint** → choose the `SVAI-HACK` repo → **Apply**. Render reads `render.yaml`.
3. When asked, paste your two secret keys:
   - `HYDRA_DB_API_KEY`: from your HydraDB dashboard.
   - `OPENAI_API_KEY`: your Groq key (`gsk_…`) from https://console.groq.com/keys.
4. Wait for the first build (about 5–8 minutes). Open the URL Render shows, e.g. `https://whybot.onrender.com`.
5. Check: `https://<your-url>/api/health` should say `"mode": "hydradb"` and `"llm": "groq"`.

Every push to `main` redeploys automatically.

## B. Web on Vercel + engine on Render

1. Do **A** first; that Render service is your engine. Note its URL, e.g. `https://whybot.onrender.com`.
2. Sign in at https://vercel.com with GitHub → **Add New → Project** → import `SVAI-HACK`.
3. Set **Root Directory** to `web` (the framework is detected as Next.js).
4. Add an environment variable **before** the first deploy (it's baked in at build time):
   - `BACKEND_URL` = `https://whybot.onrender.com/api`
5. **Deploy**. Your app is at `https://<project>.vercel.app`; all `/api/*` calls are proxied to Render.

If you change `BACKEND_URL` later, redeploy on Vercel for it to take effect.

---

## Public-mode guardrails (on by default in the Docker image)

| Setting | Default | What it does |
|---|---|---|
| `PUBLIC_MODE` | `1` | Turns on the protections below |
| `RATE_AI_PER_MIN` | `12` | Questions + impact checks per visitor per minute |
| `RATE_INGEST_PER_HOUR` | `20` | Uploads / URLs / profile saves per visitor per hour |
| `MAX_UPLOAD_MB` | `10` | Largest file a visitor can upload |
| `ADMIN_TOKEN` | generated | Only requests with header `X-Admin-Token` can reset the brain |
| `AUTO_SAMPLE` | `1` | Reloads the starter brain whenever the server restarts |
| `HYDRA_DATABASE` | `whybotpublic` | Keeps public uploads separate from your local demo brain |

Everyone who visits shares **one** brain and **one** free Groq quota (about 8,000 tokens a minute). When Groq is busy, visitors get the evidence summary with a "try again in a minute" note instead of an error.

Reset the public brain yourself:

```bash
curl -X POST https://<your-url>/api/reset -H "X-Admin-Token: <ADMIN_TOKEN from Render → Environment>"
```

## Run the production image locally

```bash
docker build -t whybot .
docker run -p 3000:3000 --env-file backend/.env -e HYDRA_DATABASE=whybot whybot
# open http://localhost:3000
```

The same image runs on Railway, Fly.io, Google Cloud Run or Hugging Face Spaces (Docker); each sets `$PORT`, and the image listens on it.
