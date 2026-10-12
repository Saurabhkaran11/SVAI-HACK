"""Free LLM tiers rate-limit hard. WhyBot must answer fast, never hang, and never cache a degraded answer."""
from whybot import llm
from whybot.cache import answers
import dataclasses

from whybot import config as config_mod
from whybot.config import settings


def _fake_llm(monkeypatch, reply):
    calls = []

    def fake(system, user):
        calls.append(user)
        return reply(len(calls)) if callable(reply) else reply

    monkeypatch.setattr(llm, "complete", fake)
    return calls


def test_rate_limited_answer_falls_back_with_busy_note(sample, monkeypatch):
    _fake_llm(monkeypatch, "(LLM unavailable: RateLimitError)")
    r = sample.post("/ask", json={"question": "Why are we migrating to payments v2?"})
    assert r.status_code == 200
    body = r.json()["answer"]
    assert llm.BUSY in body and "Here's what your brain found" in body
    assert "LLM unavailable" not in body and "Add a free LLM" not in body


def test_degraded_answer_is_not_cached(sample, monkeypatch):
    answers.clear()
    calls = _fake_llm(monkeypatch, lambda n: "(LLM unavailable: RateLimitError)" if n == 1 else "Real answer [ADR-007]")
    q = {"question": "Who owns billing-service?", "graph": True}
    assert llm.BUSY in sample.post("/ask", json=q).json()["answer"]
    assert sample.post("/ask", json=q).json()["answer"] == "Real answer [ADR-007]"
    assert len(calls) == 2


def test_degraded_impact_brief_is_not_cached(sample, monkeypatch):
    answers.clear()
    calls = _fake_llm(monkeypatch, lambda n: "(LLM unavailable: APITimeoutError)" if n == 1 else "**Verdict** High")
    c = {"change": "Deprecate payments-api-v1"}
    assert llm.BUSY in sample.post("/impact", json=c).json()["brief"]
    assert sample.post("/impact", json=c).json()["brief"] == "**Verdict** High"
    assert len(calls) == 2


def test_compare_spends_one_llm_call(sample, monkeypatch):
    answers.clear()
    calls = _fake_llm(monkeypatch, "Graph answer [ADR-007]")
    r = sample.post("/compare", json={"question": "What would break if we deprecated the v1 payments API?"}).json()
    assert len(calls) == 1
    assert r["with_graph"]["answer"] == "Graph answer [ADR-007]"
    plain = r["without_graph"]["answer"]
    assert plain.startswith("**Top matching passages**") and "Add a free LLM" not in plain


def test_context_is_capped_for_token_limits(sample, monkeypatch):
    answers.clear()
    calls = _fake_llm(monkeypatch, "ok")
    monkeypatch.setattr("whybot.llm.settings", dataclasses.replace(config_mod.settings, llm_context_chars=500))
    sample.post("/ask", json={"question": "Tell me everything about payments"})
    ctx = calls[0].split("Context:\n", 1)[1].split("\n\nQuestion:", 1)[0]
    assert len(ctx) <= 502


def test_openai_client_does_not_retry(monkeypatch):
    monkeypatch.setattr("whybot.llm.settings", dataclasses.replace(config_mod.settings, openai_key="x"))
    llm._openai.cache_clear()
    try:
        assert llm._openai().max_retries == 0
    finally:
        llm._openai.cache_clear()


def test_passages_view_dedupes_and_truncates():
    from whybot.models import Chunk
    cs = [Chunk("ADR-007", "x " * 400, 0.9), Chunk("ADR-007", "x " * 400, 0.8), Chunk("", "short note", 0.5)]
    out = llm.passages(cs)
    assert out.count("**ADR-007**") == 1 and "…" in out and "**source** — short note" in out
    assert llm.passages([]) == llm.EMPTY
