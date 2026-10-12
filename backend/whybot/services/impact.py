"""Blast Radius: what breaks, who to tell, and what went wrong last time — for a planned change."""
from __future__ import annotations

import re
import time

from .. import llm
from ..cache import answers
from ..config import settings
from ..graph import Graph
from ..models import Retrieval
from ..retrieval import retrieve
from ..state import state
from ..text import clean, tokens

INCIDENT_WORDS = ("incident", "postmortem", "sev-", "outage", "root cause", "rollback")
_NAME = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
_NOT_NAMES = {"The", "Incident", "Architecture", "Service", "Status", "Date", "Root", "Permanent", "New", "All",
              "Highest", "Deprecate", "Migration", "Review", "Summary", "Resolution", "Context", "Decision",
              "Consequences", "Release", "Engineer", "Onboarding"}


def _risk(affected: int, incidents: int, owners: int, matched: bool) -> dict:
    """Transparent heuristic: reach dominates, incident history and coordination cost add risk."""
    score = min(100, 15 * affected + 20 * incidents + 8 * owners + (10 if matched else 0))
    level = "High" if score >= 60 else "Medium" if score >= 30 else "Low"
    return {"score": score, "level": level}


def _people(chunks) -> list[str]:
    found = {m for c in chunks for m in _NAME.findall(c.content)
             if m.split()[0] not in _NOT_NAMES and m.split()[1] not in _NOT_NAMES and m not in c.title}
    return sorted(found)[:8]


def _compute(change: str, persona: str | None) -> dict:
    t0 = time.perf_counter()
    # Retrieve on the change itself: wrapper words ("depends", "owned") would match unrelated docs.
    r = retrieve(change, persona, graph=True) if tokens(change) else Retrieval([], [], "", settings.mode)
    g = state.graph()
    if any(p not in g.edge_set for p in r.paths):  # only rebuild when retrieval found new relationships
        g = Graph(state.all_edges() + r.paths)

    seeds = g.match(change)
    hop, via = g.blast_radius(seeds, settings.max_hops)
    affected = [{"name": n, "hop": h, "via": via.get(n, "the change itself")}
                for n, h in sorted(hop.items(), key=lambda kv: (kv[1], kv[0]))]
    owners = g.owners_of(set(hop))
    incidents = list(dict.fromkeys(c.title for c in r.chunks
                                   if any(w in (c.title + " " + c.content).lower() for w in INCIDENT_WORDS)))
    risk = _risk(len([a for a in affected if a["hop"] > 0]), len(incidents), len(owners), bool(seeds))

    facts = ("\n\nAffected (hop distance): " + ", ".join(f'{a["name"]}({a["hop"]})' for a in affected)
             + "\nOwners: " + "; ".join(f"{o}: {', '.join(v)}" for o, v in owners.items())
             + "\nPast incidents: " + ", ".join(incidents) + f"\nComputed risk: {risk['level']} ({risk['score']}/100)")
    brief = llm.generate(llm.IMPACT_SYSTEM, f"Planned change: {change}", r.context + facts, state.memories(persona))

    phrase = change.strip().rstrip(".")
    phrase = phrase[:1].lower() + phrase[1:]
    notify = [{"to": owner, "message": f"Heads-up: we're planning to {phrase}. It affects {', '.join(items)}, "
                                        f"which your team owns. Can you review the impact before we proceed?"}
              for owner, items in owners.items()]

    features = ["Context graph traversal", "Thinking mode", f"Multi-hop dependency walk (≤{settings.max_hops} hops)"]
    if state.sample_loaded:
        features.append("Bring-your-own-graph (graph_payload)")
    if persona:
        features.append(f"Persona memory ({persona})")

    return {
        "change": change, "seeds": sorted(seeds), "affected": affected, "owners": owners,
        "people": _people(r.chunks), "incidents": incidents, "risk": risk, "brief": brief, "notify": notify,
        "paths": g.edges_among([a["name"] for a in affected], limit=40),
        "chunks": [c.__dict__ for c in r.chunks], "features": features, "mode": r.mode,
        "latency_ms": int((time.perf_counter() - t0) * 1000),
        "_new_paths": r.paths,
    }


def blast_radius(change: str, persona: str | None = None) -> dict:
    change, persona = clean(change), (clean(persona) or None)
    if not change:
        raise ValueError("Describe the change you're planning.")
    t0 = time.perf_counter()
    result, hit = answers.get_or_set(("impact", change.lower(), persona, state.version), lambda: _compute(change, persona))
    out = {k: v for k, v in result.items() if not k.startswith("_")}
    if hit:
        out["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    state.add_edges(result["_new_paths"])
    state.count_question()
    return out
