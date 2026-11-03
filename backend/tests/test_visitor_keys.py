"""Visitors bring their own AI key: it's used for that request only and never leaks."""
import logging

import pytest
from fastapi.testclient import TestClient

from whybot import config as config_mod
from whybot import llm

KEY = "sk-visitor-key-1234567890"
HEADERS = {"X-LLM-Provider": "openai", "X-LLM-Key": KEY}


@pytest.fixture()
def fake_llm(monkeypatch):
    calls = []

    def fake(provider, key, system, user):
        calls.append((provider, key))
        return "Written answer [ADR-007]"

    monkeypatch.setattr(llm, "_visitor_complete", fake)
    return calls


def public(monkeypatch, **extra):
    s = config_mod.Settings(**{**config_mod.settings.__dict__, "public_mode": True, **extra})
    monkeypatch.setattr("whybot.llm.settings", s)


def test_without_a_key_you_get_an_evidence_summary_and_are_told_how_to_add_one(sample, fake_llm):
    r = sample.post("/ask", json={"question": "key test billing-service none"}).json()
    assert "Add your own AI key in Settings" in r["answer"] and fake_llm == []


def test_visitor_key_reaches_the_provider(sample, fake_llm):
    r = sample.post("/ask", json={"question": "key test billing-service one"}, headers=HEADERS)
    assert r.status_code == 200 and r.json()["answer"].startswith("Written answer")
    assert fake_llm == [("openai", KEY)]


def test_key_works_on_impact_and_across_compare_threads(sample, fake_llm):
    assert sample.post("/impact", json={"change": "key test deprecate billing-service"}, headers=HEADERS).status_code == 200
    r = sample.post("/compare", json={"question": "key test billing-service compare"}, headers=HEADERS).json()
    assert r["with_graph"]["answer"].startswith("Written answer")
    assert [c[1] for c in fake_llm] == [KEY, KEY]


def test_a_key_does_not_carry_over_to_the_next_visitor(sample, fake_llm):
    sample.post("/ask", json={"question": "key test billing-service first"}, headers=HEADERS)
    fake_llm.clear()
    r = sample.post("/ask", json={"question": "key test billing-service second"}).json()
    assert fake_llm == [] and "Add your own AI key" in r["answer"]


def test_evidence_and_written_answers_are_cached_separately(sample, fake_llm):
    q = {"question": "key test billing-service cached"}
    assert "Add your own AI key" in sample.post("/ask", json=q).json()["answer"]
    assert sample.post("/ask", json=q, headers=HEADERS).json()["answer"].startswith("Written answer")
    assert "Add your own AI key" in sample.post("/ask", json=q).json()["answer"]


def test_public_mode_never_spends_the_owner_key(sample, monkeypatch):
    public(monkeypatch, openai_key="sk-owner-key", anthropic_key="sk-ant-owner")

    def boom(*_):
        raise AssertionError("owner key used")

    monkeypatch.setattr(llm, "_openai", boom)
    monkeypatch.setattr(llm, "_anthropic", boom)
    r = sample.post("/ask", json={"question": "key test billing-service owner"})
    assert r.status_code == 200 and "Add your own AI key" in r.json()["answer"]
    assert sample.get("/health").json()["llm"] in ("visitor-key", "none")


def test_unknown_provider_is_rejected_so_keys_cannot_be_redirected(sample, fake_llm):
    r = sample.post("/ask", json={"question": "x"}, headers={"X-LLM-Provider": "https://evil.example", "X-LLM-Key": KEY})
    assert r.status_code == 400 and fake_llm == []
    assert "http" not in " ".join(llm.PROVIDERS)
    assert all(p.get("base_url") is None or p["base_url"].startswith("https://") for p in llm.PROVIDERS.values())


def test_rejected_key_is_explained_not_cached_and_not_logged(sample, monkeypatch, caplog):
    class Rejected(Exception):
        status_code = 401

    def fail(provider, key, system, user):
        raise Rejected(f"bad key {key}")

    monkeypatch.setattr(llm, "_visitor_complete", fail)
    q = {"question": "key test billing-service rejected"}
    with caplog.at_level(logging.DEBUG):
        r = sample.post("/ask", json=q, headers=HEADERS)
    assert r.status_code == 200 and llm.KEY_REJECTED in r.json()["answer"]
    assert KEY not in r.text and KEY not in caplog.text
    monkeypatch.setattr(llm, "_visitor_complete", lambda *a: "Written answer")
    assert sample.post("/ask", json=q, headers=HEADERS).json()["answer"] == "Written answer"


def test_key_is_only_read_on_ai_routes(sample, fake_llm):
    sample.post("/memory", json={"persona": "engineer", "text": "likes bullets"}, headers=HEADERS)
    assert fake_llm == []
