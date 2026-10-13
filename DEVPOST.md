# Devpost submission (copy-paste)

**Name:** WhyBot
**Tagline:** Know the blast radius before you ship — a company brain that tells you what breaks, who to tell, and what went wrong last time.

## Inspiration
Most outages and bad surprises don't come from missing knowledge. They come from not connecting it in time. The ADR, the Slack thread, the postmortem and the service owner all exist, in four different places, and nobody puts them together before the change ships.

## What it does
- **Blast Radius (our signature feature):** describe a planned change ("deprecate payments-api-v1", "Priya goes on leave"). WhyBot walks the HydraDB knowledge graph hop by hop to find every affected system, the teams that own them, and past incidents involving them. It scores the risk, writes an impact brief with a rollout checklist, and drafts a heads-up message for each owner. An animated shockwave shows the ripple.
- **Ask the Brain:** cited answers with an interactive relationship map, side by side with plain search.
- **Personas & profile:** your profile and role live in HydraDB memory, so the same question gets the depth you need.
- **Bring your own knowledge:** drag in PDFs and exports or paste any docs URL; live indexing status.
- **Graph Explorer and a REST API** ready for Slack bots and an App-Starter SaaS frontend.

## How we built it
- **HydraDB:** knowledge ingestion with auto graph extraction, bring-your-own-graph (`graph_payload`) for structured topology, per-persona memory collections, `type="all"` hybrid + graph queries in thinking mode, indexing-status polling. Every answer shows exactly which HydraDB features fired.
- **Claude** for impact briefs, cited answers and heads-up drafts.
- **FastAPI** engine + **Next.js** frontend with a glassmorphism design and Motion animations.

## Challenges
Async indexing (graph queries need `completed`), stacking contexts with glass blur, and making multi-hop traversal useful on messy real documents.

## What we learned
Vector search returns a reading list. A graph returns a map, and a map is what you need before you change something.

## What's next
Run Blast Radius automatically on every pull request and change ticket; Slack, Jira and Notion live connectors; App-Starter billing and workspaces.

**Built with:** hydradb, groq, nextjs, fastapi, python, typescript, motion

## Try it
- **Live demo:** https://whybot-ytcu.onrender.com
- **Code:** https://github.com/Saurabhkaran11/SVAI-HACK
- **Run locally (macOS):** right-click `WhyBot.command` → Open. First run installs everything, then opens http://localhost:3000
- **Keys:** `backend/.env` — HydraDB key + any OpenAI-compatible LLM (we used Groq `openai/gpt-oss-120b`); works offline with `MOCK_MODE=1`
- **Verified live:** Blast Radius on "Deprecate payments-api-v1" → High risk, 6 systems, 3 teams, past incident found, in ~4 s on HydraDB + Groq
- **Quality:** 252 backend tests (edge cases, fuzzing, fault injection) + browser regression suite — see TESTING.md
