# 🧠 WhyBot — know the blast radius before you ship

**Problem:** Teams make changes — deprecate an API, reorganise a team, flip a config, someone goes on leave — without seeing what depends on it. The knowledge exists, but it's scattered across docs, Slack, tickets and postmortems, so incidents repeat and the wrong people find out last.

**What makes WhyBot different:** most "company brain" tools answer questions. WhyBot also answers the question nobody asks until it's too late: **"If we change this, what breaks, who do we tell, and what went wrong last time?"** It walks a HydraDB knowledge graph hop by hop, scores the risk, and drafts the heads-up messages to every owning team.

## Features
| Feature | What it does | HydraDB features used |
|---|---|---|
| **Blast Radius** ⭐ | Planned change → affected systems by hop, owners to notify, past incidents, risk score, drafted messages, animated shockwave | Context graph, multi-hop traversal, bring-your-own-graph, memories |
| Ask the Brain | Cited answers with relationship map; plain-search vs WhyBot comparison | Hybrid search, context graph, thinking mode, `type="all"` |
| Knowledge | Drag-drop PDF/MD/TXT/CSV/JSON or any docs URL; live indexing status | Ingestion, auto graph extraction, status API |
| Personas & Memory | Roles + your own profile; "remember this about me" | Per-persona memory collections |
| Graph Explorer | Every discovered relationship, searchable and draggable | Context graphs, BYO graph |
| API & Integrations | Try every endpoint live; cURL + Slack bot snippets | REST API (App-Starter ready) |

Top-right: **profile** (saved as your personal HydraDB memory) and **settings** (accent, glass blur, reduce motion, defaults, engine status, reset).

## Setup (one time, ~5 min)
Requires Python 3.10+ and Node 18+.
```bash
cd whybot
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env                  # add HYDRA_DB_API_KEY + ANTHROPIC_API_KEY
cd web && npm install && npm run build && cd ..
```
Keys: HydraDB → https://app.hydradb.com · Claude → https://console.anthropic.com (or set `OPENAI_API_KEY`).

## Run
```bash
./start.sh          # Windows: start.bat     (./start.sh dev for hot reload)
```
Open **http://localhost:3000**. Engine API docs: http://localhost:8000/docs

Load real docs early (graph indexing takes a few minutes):
```bash
cd backend
python ingest.py --folder ./my_docs
python ingest.py --url https://docs.hydradb.com/
```
No wifi on stage? Set `MOCK_MODE=1` in `backend/.env` and restart.

Run the tests: `cd backend && pytest -q` (248 tests, offline, ~13s). Full report and browser tests: see **TESTING.md**.

## Deploy (free tiers)
- Engine → [Render](https://render.com): root directory `backend`, start command `uvicorn main:app --host 0.0.0.0 --port $PORT`, add `.env` values.
- Web → [Vercel](https://vercel.com): root directory `web`, env `BACKEND_URL=https://<your-render-url>`.

## Architecture
```
Next.js (glass UI, motion) ──/api──► FastAPI engine ──► HydraDB  (hybrid search · context graph · BYO graph · memories)
                                          │
                                          └──► Claude / GPT → cited answers, impact briefs, heads-up drafts
```

### Backend layout (`backend/`)
```
main.py                  uvicorn entrypoint (create_app)
ingest.py                CLI bulk loader
whybot/
  config.py              all settings from env (.env), mock/live mode
  models.py              Chunk, Retrieval, Answer
  text.py                tokenizing, PDF + HTML extraction, paragraph splitting
  graph.py               Edge/Graph: adjacency index, BFS blast radius, ownership, entity matching
  state.py               thread-safe brain state + inverted search index, atomic JSON persistence
  cache.py               TTL answer cache keyed on state version
  hydra.py               the only HydraDB SDK adapter (ingest, memories, query, status, retry)
  retrieval.py           HydraDB first, local index + graph fallback
  llm.py                 Claude → OpenAI → extractive fallback, prompts
  services/              one module per feature: ask, impact, knowledge, personas
  api/                   app factory (middleware, errors), pydantic schemas, routers by feature
  sample_data.py         opt-in starter docs, default personas, suggested questions
tests/                   248 tests: API, edge inputs, scale, faults, fuzzing, regressions + bench.py
```

### Performance & hardening
- `/compare` runs plain and graph answers **in parallel** (2.0s → 1.0s with a 1s LLM).
- **Answer cache**: repeat questions return in <1 ms; it is invalidated automatically when docs or memories change.
- **Inverted index** for offline search and an **adjacency-indexed graph** for O(edges) multi-hop traversal.
- **Thread-safe state** with atomic writes (no corrupt state file on crash).
- Input validation (400/422 with readable messages), upload type/size limits, **SSRF guard** on URL ingestion.
- HydraDB calls retry once on transient errors; failures fall back to local retrieval so the demo never dies.
- Gzip responses and an `X-Response-Time-ms` header on every request.

## Business model
Free (personal, 100 docs) · Team $15/seat/mo (Slack, Jira, Notion connectors; change-review in PRs) · Enterprise (SSO, private HydraDB, audit logs).
