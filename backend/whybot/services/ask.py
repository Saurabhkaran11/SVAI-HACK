"""Ask the Brain: graph-aware, persona-aware answers, plus side-by-side comparison."""
from __future__ import annotations

import time
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

from .. import llm
from ..cache import answers
from ..models import Answer
from ..retrieval import retrieve
from ..state import state
from ..text import clean

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="whybot-ask")


def _features(graph: bool, persona: str | None, paths: list[str]) -> list[str]:
    feats = ["Hybrid search (semantic + keyword)"]
    if graph:
        feats += ["Context graph traversal (graph_context=True)", "Thinking mode (multi-query expansion)"]
        if state.sample_loaded and paths:
            feats.append("Bring-your-own-graph (graph_payload)")
    if persona:
        feats.append(f"Persona memory merge (type='all', collection '{persona}')")
    return feats


def _compute(question: str, persona: str | None, graph: bool, write: bool = True) -> Answer:
    t0 = time.perf_counter()
    memories = state.memories(persona)
    r = retrieve(question, persona, graph)
    # write=False: show what retrieval alone returns (used for the "plain search" side of compare).
    text = llm.generate(llm.ANSWER_SYSTEM, question, r.context, memories) if write else llm.extractive(r.context)
    return Answer(text, r.chunks, r.paths, memories, r.mode, int((time.perf_counter() - t0) * 1000),
                  _features(graph, persona, r.paths))


def ask(question: str, persona: str | None = None, graph: bool = True, count: bool = True, write: bool = True) -> Answer:
    question = clean(question)
    if not question:
        raise ValueError("Question is empty.")
    persona = clean(persona) or None
    key = ("ask", question.lower(), persona, graph, write, state.version)
    t0 = time.perf_counter()
    ans, hit = answers.get_or_set(key, lambda: _compute(question, persona, graph, write))
    if not hit and llm.BUSY in ans.answer:  # never cache a degraded answer
        answers.drop(key)
    if hit:  # report real latency for cache hits
        ans = replace(ans, latency_ms=int((time.perf_counter() - t0) * 1000))
    if ans.paths:
        state.add_edges(ans.paths)
    if count:
        state.count_question()
    return ans


def compare(question: str, persona: str | None = None) -> dict[str, Answer]:
    """Plain vs graph answers computed in parallel (≈ half the wall time of running them in sequence)."""
    plain = _pool.submit(ask, question, persona, False, False, False)  # retrieval only: one LLM call per compare
    smart = _pool.submit(ask, question, persona, True, False)
    result = {"without_graph": plain.result(), "with_graph": smart.result()}
    state.count_question()
    return result
