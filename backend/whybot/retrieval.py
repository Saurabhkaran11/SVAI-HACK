"""Retrieval: HydraDB when connected, local index + local graph otherwise (or on failure)."""
from __future__ import annotations

import logging

from . import hydra
from .config import settings
from .models import Retrieval
from .state import state

log = logging.getLogger("whybot.retrieval")


def _local(question: str, graph: bool, mode: str = "mock") -> Retrieval:
    with state.lock:
        chunks = state.index.search(question, k=6)
        g = state.graph() if graph else None
    paths: list[str] = []
    if g is not None and g.edges:
        blob = question + " " + " ".join(c.content for c in chunks)
        seeds = g.match(blob, g.nodes)
        paths = g.neighbourhood(seeds, hops=2)[:30]
    context = "\n\n".join(f"[{c.title}]\n{c.content}" for c in chunks)
    if paths:
        context += "\n\nGraph relationships:\n" + "\n".join(paths)
    return Retrieval(chunks, paths, context, mode)


def retrieve(question: str, persona: str | None, graph: bool) -> Retrieval:
    if settings.mock:
        return _local(question, graph)
    try:
        chunks, paths, context = hydra.query(question, persona, graph)
        return Retrieval(chunks, paths, context, "hydradb")
    except Exception as e:  # keep the demo alive on network / indexing issues
        log.warning("HydraDB query failed, using local fallback: %s", e)
        return _local(question, graph, mode="mock-fallback")
