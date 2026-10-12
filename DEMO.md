# Stage demo script (3 minutes)

## 20+ minutes before
- `.env` has HydraDB + Claude keys; `./start.sh` running; browser at http://localhost:3000 (full screen).
- Load real docs: `cd backend && python ingest.py --url https://docs.hydradb.com/` plus a few of your own files (or starter data from the Knowledge page).
- Knowledge page shows indexing `completed`. Set your profile (top-right avatar).
- Backup: `MOCK_MODE=1` in `backend/.env`, restart, load starter data.

## 0:00 — Hook (20s)
"Every outage starts with a change someone thought was safe. The knowledge to stop it existed — in an ADR, a Slack thread, a postmortem — just not in one place."

## 0:20 — Blast Radius, the money shot (70s)
- Open **Blast Radius**, type a real change (e.g. "Deprecate payments-api-v1 next month").
- Shockwave animates; risk score counts up.
- Walk through: systems affected by hop → teams to notify → "last time this went wrong" → heads-up drafts (click Copy).
- "That's HydraDB's context graph walking dependencies three hops out."

## 1:30 — Why the graph matters (30s)
- **Ask the Brain**, compare mode: plain search (fragments) vs WhyBot (connected answer + map).
- Open **Under the hood**: hybrid search, context graph, thinking mode, memories.

## 2:00 — It's yours (30s)
- **Knowledge**: drag in a real file live. "Any team, any docs."
- Avatar → switch persona Engineer → Manager → same question, different answer.

## 2:30 — Sponsors + close (30s)
- **API & Integrations**: send a live request. "Drops into App-Starter for auth and billing; runs on every PR next."
- "WhyBot: know the blast radius before you ship."
