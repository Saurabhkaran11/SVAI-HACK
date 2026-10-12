"""Large inputs, scale and latency budgets (offline mode, no LLM)."""
import random
import time

import pytest

from whybot.graph import Graph
from whybot.text import paragraphs


def timed(fn):
    t = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t) * 1000


# ---- size limits ---------------------------------------------------------------------
def test_question_length_boundary(sample):
    assert sample.post("/ask", json={"question": "a" * 2000}).status_code == 200
    assert sample.post("/ask", json={"question": "a" * 2001}).status_code == 422


def test_change_length_boundary(sample):
    assert sample.post("/impact", json={"change": "b" * 1000}).status_code == 200
    assert sample.post("/impact", json={"change": "b" * 1001}).status_code == 422


def test_upload_over_limit_rejected(client):
    from whybot.config import settings
    big = b"x" * (settings.max_upload_mb * 1024 * 1024 + 1)
    r = client.post("/upload", files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 400 and "larger than" in r.json()["detail"]


def test_huge_doc_truncated_and_searchable(client):
    words = ["alpha", "beta", "gamma", "delta", "owner", "service", "deploy", "incident"]
    body = "\n\n".join(" ".join(random.choice(words) for _ in range(80)) for _ in range(2000)).encode()  # ~1MB
    _, ms = timed(lambda: client.post("/upload", files={"file": ("huge.md", body, "text/plain")}))
    assert ms < 3000, f"ingest took {ms:.0f}ms"
    r, ms = timed(lambda: client.post("/ask", json={"question": "incident owner"}).json())
    assert r["chunks"] and ms < 300, f"ask took {ms:.0f}ms"


def test_single_giant_line_is_windowed():
    """A 300k-char document with no newlines must not become one giant chunk."""
    text = ("word " * 60000).strip()
    parts = paragraphs(text)
    assert len(parts) > 100 and max(len(p) for p in parts) <= 1500


def test_giant_line_upload_returns_small_chunks(client):
    text = ("needle haystack " * 20000).encode()
    client.post("/upload", files={"file": ("line.txt", text, "text/plain")})
    r = client.post("/ask", json={"question": "needle"}).json()
    assert r["chunks"] and max(len(c["content"]) for c in r["chunks"]) <= 1500


def test_answer_payload_stays_bounded(client):
    """Even with huge docs, an answer response must stay small enough for the UI."""
    body = ("\n\n".join(f"Team {i} owns service-{i}. " * 30 for i in range(500))).encode()
    client.post("/upload", files={"file": ("teams.md", body, "text/plain")})
    r = client.post("/compare", json={"question": "who owns service-42"})
    assert r.status_code == 200 and len(r.content) < 200_000


# ---- many documents ----------------------------------------------------------------
def test_thousand_docs_search_latency(client):
    from whybot.state import state

    with state.lock:
        for i in range(1000):
            state.index.add(f"d{i}", f"doc {i}", f"Service svc-{i} is owned by team-{i % 37}.\n\n"
                                                    f"It depends on db-{i % 11} and cache-{i % 7}.")
            state.docs[f"d{i}"] = {"title": f"doc {i}", "type": "doc", "text": "x"}
    _, ms = timed(lambda: [state.index.search("who owns svc-500 db-3") for _ in range(100)])
    assert ms / 100 < 20, f"search avg {ms / 100:.1f}ms"
    _, ms = timed(lambda: client.get("/inventory"))
    assert ms < 500


def test_reupload_does_not_leak_index_memory(client):
    from whybot.state import state

    for i in range(300):
        client.post("/upload", files={"file": ("same.md", f"rev {i}\n\nline two\n\nline three".encode(), "text/plain")})
    live = sum(1 for u in state.index.units if u[1])
    assert live == 3 and len(state.index.units) < 200, f"{len(state.index.units)} units kept for 3 live"


# ---- graph scale & shapes -----------------------------------------------------------------
def test_graph_cycles_and_self_loops_terminate():
    g = Graph(["a --[DEPENDS_ON]--> b", "b --[DEPENDS_ON]--> a", "c --[DEPENDS_ON]--> c", "d --[DEPENDS_ON]--> a"])
    hop, _ = g.blast_radius({"a"}, max_hops=10)
    assert hop == {"a": 0, "b": 1, "d": 1}
    assert g.neighbourhood({"c"}, hops=5) == ["c --[DEPENDS_ON]--> c"]


def test_graph_unknown_seed_and_empty_graph():
    assert Graph([]).blast_radius({"x"}) == ({"x": 0}, {})
    assert Graph([]).match("anything") == set()
    assert Graph([]).owners_of({"x"}) == {}


def test_large_graph_blast_radius_fast():
    edges = [f"s{i} --[DEPENDS_ON]--> s{i // 3}" for i in range(1, 30000)]  # 30k-edge tree
    edges += [f"s{i} --[OWNED_BY]--> team{i % 50}" for i in range(0, 30000, 7)]
    g, build_ms = timed(lambda: Graph(edges))
    (hop, _), ms = timed(lambda: g.blast_radius({"s0"}, max_hops=3))
    assert len(hop) == 1 + 3 + 9 + 27 - 1 or len(hop) > 10
    assert build_ms < 500 and ms < 50, f"build {build_ms:.0f}ms, bfs {ms:.1f}ms"
    _, ms = timed(lambda: g.neighbourhood({"s0"}, hops=2))
    assert ms < 100, f"neighbourhood {ms:.0f}ms"


def test_api_with_many_known_edges_stays_fast(sample):
    from whybot.state import state

    state.add_edges([f"svc{i} --[DEPENDS_ON]--> payments-api-v1" for i in range(3000)])
    _, ms = timed(lambda: sample.post("/impact", json={"change": "Deprecate payments-api-v1"}))
    assert ms < 1500, f"impact took {ms:.0f}ms"
    r = sample.post("/impact", json={"change": "Deprecate payments-api-v1 now"}).json()
    assert len(r["paths"]) <= 40 and len(r["affected"]) > 100
    _, ms = timed(lambda: [sample.post("/ask", json={"question": f"what uses payments-api-v1 {i}"}) for i in range(20)])
    assert ms / 20 < 150, f"ask avg {ms / 20:.0f}ms with 3k edges"


def test_question_does_not_rewrite_entire_state_file(sample):
    """Asking questions must not re-serialize every document each time."""
    from whybot.state import state

    body = ("filler text " * 50_000).encode()
    for i in range(5):
        sample.post("/upload", files={"file": (f"big{i}.txt", body, "text/plain")})
    _, ms = timed(lambda: [sample.post("/ask", json={"question": f"filler question {i}", "graph": False}) for i in range(30)])
    assert ms / 30 < 60, f"ask avg {ms / 30:.0f}ms — state writes are on the hot path"


# ---- concurrency ------------------------------------------------------------------------
def test_mixed_concurrent_workload(sample):
    import concurrent.futures as cf

    def work(i):
        k = i % 5
        if k == 0:
            return sample.post("/upload", files={"file": (f"c{i}.md", f"owner {i} runs svc-{i}".encode(), "text/plain")})
        if k == 1:
            return sample.post("/ask", json={"question": f"who runs svc-{i}", "persona": "engineer"})
        if k == 2:
            return sample.post("/impact", json={"change": f"remove billing-service {i}"})
        if k == 3:
            return sample.post("/memory", json={"persona": "engineer", "text": f"fact {i}"})
        return sample.get("/inventory")

    with cf.ThreadPoolExecutor(12) as ex:
        codes = [r.status_code for r in ex.map(work, range(120))]
    assert set(codes) == {200}
    full = sample.get("/personas/full").json()
    assert len([m for m in full["engineer"]["memories"] if m.startswith("fact ")]) == 24
    assert len([r for r in sample.get("/inventory").json() if r["id"].startswith("c")]) == 24


def test_reset_during_traffic_is_safe(sample):
    import concurrent.futures as cf

    def work(i):
        if i % 10 == 0:
            return sample.post("/reset")
        return sample.post("/ask", json={"question": f"who owns billing-service {i}"})

    with cf.ThreadPoolExecutor(8) as ex:
        assert {r.status_code for r in ex.map(work, range(80))} == {200}
