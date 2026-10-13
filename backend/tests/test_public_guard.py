"""PUBLIC_MODE guardrails: per-visitor rate limits and a locked reset."""
import dataclasses

import pytest

from whybot import config as config_mod
from whybot.api import guard


@pytest.fixture()
def public(monkeypatch):
    s = dataclasses.replace(config_mod.settings, public_mode=True, admin_token="secret", trusted_proxy_hops=1)
    monkeypatch.setattr(guard, "settings", s)
    monkeypatch.setattr(guard, "ai_limit", guard.SlidingWindow(3, 60))
    monkeypatch.setattr(guard, "ingest_limit", guard.SlidingWindow(2, 3600))
    return s


def test_sliding_window_allows_then_blocks_then_recovers():
    w = guard.SlidingWindow(2, 10)
    assert w.hit("a", 0) == 0 and w.hit("a", 1) == 0
    assert w.hit("a", 2) == pytest.approx(8)
    assert w.hit("b", 2) == 0          # other visitors unaffected
    assert w.hit("a", 10.5) == 0       # window slid


def test_ai_calls_are_rate_limited_per_ip(sample, public):
    h = {"X-Forwarded-For": "1.2.3.4"}
    for _ in range(3):
        assert sample.post("/ask", json={"question": "Who owns billing-service?"}, headers=h).status_code == 200
    r = sample.post("/ask", json={"question": "Who owns billing-service?"}, headers=h)
    assert r.status_code == 429 and "Try again" in r.json()["detail"] and int(r.headers["Retry-After"]) >= 1
    other = sample.post("/ask", json={"question": "Who owns billing-service?"}, headers={"X-Forwarded-For": "5.6.7.8"})
    assert other.status_code == 200


def test_ingest_is_rate_limited(sample, public):
    h = {"X-Forwarded-For": "9.9.9.9"}
    for _ in range(2):
        assert sample.post("/upload", files={"file": ("n.md", b"# note\nhello")}, headers=h).status_code == 200
    assert sample.post("/upload", files={"file": ("n.md", b"# note\nhello")}, headers=h).status_code == 429


def test_reset_needs_admin_token(sample, public):
    assert sample.post("/reset").status_code == 403
    assert sample.post("/reset", headers={"X-Admin-Token": "wrong"}).status_code == 403
    assert sample.post("/reset", headers={"X-Admin-Token": "secret"}).status_code == 200


def test_reads_are_never_limited(sample, public):
    for _ in range(20):
        assert sample.get("/health").status_code == 200


def test_private_mode_is_unchanged(sample):
    for _ in range(15):
        assert sample.post("/ask", json={"question": "Who owns billing-service?"}).status_code == 200
    assert sample.post("/reset").status_code == 200


def test_forged_forwarded_for_cannot_dodge_the_limit(sample, monkeypatch):
    """Render edge + Next.js each append one address; the visitor is 2 from the right. Forged prefixes are ignored."""
    s = dataclasses.replace(config_mod.settings, public_mode=True, trusted_proxy_hops=2)
    monkeypatch.setattr(guard, "settings", s)
    monkeypatch.setattr(guard, "ai_limit", guard.SlidingWindow(2, 60))
    q = {"question": "Who owns billing-service?"}
    hdr = lambda forged: {"X-Forwarded-For": f"{forged}, 7.7.7.7, 10.0.0.1"}
    assert sample.post("/ask", json=q, headers=hdr("1.1.1.1")).status_code == 200
    assert sample.post("/ask", json=q, headers=hdr("2.2.2.2")).status_code == 200
    assert sample.post("/ask", json=q, headers=hdr("3.3.3.3")).status_code == 429   # same real visitor
    assert sample.post("/ask", json=q, headers={"X-Forwarded-For": "8.8.8.8, 10.0.0.1"}).status_code == 200


def test_health_reports_public_mode(client):
    assert client.get("/health").json()["public"] is False
