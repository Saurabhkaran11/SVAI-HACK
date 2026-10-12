"""Fault injection: live-mode HydraDB via a fake SDK, LLM failures, network failures, corrupt state.

The fake mirrors the hydra_db SDK surface WhyBot uses (verified against hydradb-sdk 2.x signatures).
"""
import json
from types import SimpleNamespace as NS

import pytest

from whybot import hydra, llm
from whybot import config as config_mod


# ---- a fake HydraDB SDK ------------------------------------------------------------------
class FakeHydra:
    def __init__(self, fail_query=0, fail_ingest=0, empty=False, malformed=False):
        self.fail_query, self.fail_ingest, self.empty, self.malformed = fail_query, fail_ingest, empty, malformed
        self.ingested, self.queries = [], []
        self.context = NS(ingest=self._ingest, status=self._status)
        self.databases = NS(create=lambda **k: None,
                            status=lambda **k: NS(data=NS(infra=NS(ready_for_ingestion=True))))

    def _ingest(self, **kw):
        if self.fail_ingest:
            self.fail_ingest -= 1
            raise ConnectionError("hydra down")
        self.ingested.append(kw)
        if kw.get("type") == "memory":
            ids = [m["id"] for m in json.loads(kw["memories"])]
        else:
            ids = [m["id"] for m in json.loads(kw["document_metadata"])]
        return NS(data=NS(results=[NS(id=i) for i in ids]))

    def _status(self, database, collection=None, ids=None, **kw):
        return NS(data=NS(statuses=[NS(indexing_status="completed") for _ in ids]))

    def query(self, **kw):
        self.queries.append(kw)
        if self.fail_query:
            self.fail_query -= 1
            raise TimeoutError("query timeout")
        if self.empty:
            return NS(data=NS(chunks=None, graph_context=None))
        if self.malformed:  # missing fields, None everywhere
            return NS(data=NS(chunks=[NS(source_title=None, id=None, chunk_content=None, relevancy_score=None)],
                              graph_context=NS(query_paths=[NS(triplets=[NS(source=None, relation=None, target=None)])])))
        chunk = NS(source_title="ADR-007", id="adr", chunk_content="billing-service depends on payments-api-v1",
                   relevancy_score=0.91)
        trip = NS(source={"name": "billing-service"}, relation={"canonical_predicate": "DEPENDS_ON"},
                  target={"name": "payments-api-v1"})
        gc = NS(query_paths=[NS(triplets=[trip])]) if kw.get("graph_context") else None
        return NS(data=NS(chunks=[chunk], graph_context=gc))


@pytest.fixture()
def live(client, monkeypatch):
    """Switch the running app into live mode backed by a FakeHydra."""
    fake = FakeHydra()
    s = config_mod.settings
    new = config_mod.Settings(**{**s.__dict__, "hydra_key": "test-key", "force_mock": False})
    for mod in ("whybot.config", "whybot.retrieval", "whybot.hydra", "whybot.services.knowledge",
                "whybot.services.personas", "whybot.services.impact", "whybot.api.routes"):
        monkeypatch.setattr(f"{mod}.settings", new, raising=False)
    monkeypatch.setattr(hydra, "client", lambda: fake)
    monkeypatch.setattr("hydra_db.helpers.build_string", lambda res: "billing-service depends on payments-api-v1", raising=False)
    from whybot.services import knowledge
    knowledge._ensure_db_once.done = False
    return client, fake


def test_live_ask_uses_hydradb(live):
    client, fake = live
    r = client.post("/ask", json={"question": "what breaks", "persona": "engineer"}).json()
    assert r["mode"] == "hydradb" and r["paths"] == ["billing-service --[DEPENDS_ON]--> payments-api-v1"]
    q = fake.queries[-1]
    assert q["type"] == "all" and q["collections"]["engineer"] == 1.0 and q["graph_context"] is True
    assert q["mode"] == "thinking"


def test_live_plain_query_uses_fast_mode_and_shared_collection(live):
    client, fake = live
    client.post("/ask", json={"question": "plain please", "graph": False})
    q = fake.queries[-1]
    assert q["mode"] == "fast" and q["type"] == "knowledge" and q["collection"] == "company_knowledge"


def test_live_transient_failure_is_retried(live):
    client, fake = live
    fake.fail_query = 1
    r = client.post("/ask", json={"question": "retry me"}).json()
    assert r["mode"] == "hydradb" and len(fake.queries) == 2


def test_live_hard_failure_falls_back_locally(live):
    client, fake = live
    client.post("/sample")
    fake.fail_query = 99
    r = client.post("/ask", json={"question": "who owns billing-service"})
    assert r.status_code == 200 and r.json()["mode"] == "mock-fallback" and r.json()["chunks"]


def test_live_empty_and_malformed_responses(live):
    client, fake = live
    fake.empty = True
    r = client.post("/ask", json={"question": "empty?"})
    assert r.status_code == 200 and r.json()["chunks"] == []
    fake.empty, fake.malformed = False, True
    r = client.post("/ask", json={"question": "malformed?"})
    assert r.status_code == 200
    assert r.json()["chunks"][0]["title"] == "source" and r.json()["chunks"][0]["content"] == ""


def test_live_upload_sends_document_and_metadata(live):
    client, fake = live
    r = client.post("/upload", files={"file": ("plan.md", b"Ravi owns the plan.", "text/plain")})
    assert r.status_code == 200 and r.json() == {"ingested": ["plan"]}
    kw = fake.ingested[-1]
    meta = json.loads(kw["document_metadata"])[0]
    assert kw["type"] == "knowledge" and meta["id"] == "plan"
    assert "title" not in meta and meta["additional_metadata"]["title"] == "plan.md"  # live API rejects top-level title
    assert isinstance(kw["documents"], list)  # SDK expects a list of files


def test_live_upload_failure_is_clean_error(live):
    client, fake = live
    fake.fail_ingest = 5
    r = client.post("/upload", files={"file": ("x.md", b"content here", "text/plain")})
    assert r.status_code in (502, 503) and "HydraDB" in r.json()["detail"]


def test_live_sample_sends_byo_graph(live):
    client, fake = live
    client.post("/sample")
    manifest = [k for k in fake.ingested if "graph_payload" in k]
    assert manifest and "service_manifest" in json.loads(manifest[0]["graph_payload"])


def test_live_memory_and_profile_sync(live):
    client, fake = live
    client.post("/memory", json={"persona": "engineer", "text": "I own CI"})
    client.post("/profile", json={"name": "Vik", "role": "EM"})
    mem_calls = [k for k in fake.ingested if k.get("type") == "memory"]
    assert {k["collection"] for k in mem_calls} >= {"engineer", "me"}


def test_live_memory_sync_failure_does_not_break_ui(live):
    client, fake = live
    fake.fail_ingest = 99
    assert client.post("/memory", json={"persona": "engineer", "text": "x"}).status_code == 200


def test_live_inventory_shows_index_status(live):
    client, _ = live
    client.post("/upload", files={"file": ("s.md", b"status test", "text/plain")})
    assert client.get("/inventory").json()[0]["status"] == "completed"


# ---- LLM ----------------------------------------------------------------------------------
def test_llm_success_path(sample, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda system, user: "**Billing** depends on v1 [ADR-007]")
    r = sample.post("/ask", json={"question": "llm success billing-service"}).json()
    assert r["answer"].startswith("**Billing**")


def test_llm_receives_memories_and_context(sample, monkeypatch):
    seen = {}
    monkeypatch.setattr(llm, "complete", lambda system, user: seen.setdefault("u", user) and "ok")
    sample.post("/ask", json={"question": "memory check billing-service", "persona": "manager"})
    assert "I am a manager" in seen["u"] and "Context:" in seen["u"]


def test_llm_exception_degrades_gracefully(sample, monkeypatch):
    class Boom:
        class messages:
            @staticmethod
            def create(**k):
                raise RuntimeError("rate limited")
    monkeypatch.setattr(llm, "_anthropic", lambda: Boom)
    monkeypatch.setattr("whybot.llm.settings", config_mod.Settings(**{**config_mod.settings.__dict__, "anthropic_key": "k"}))
    r = sample.post("/ask", json={"question": "llm failure billing-service"})
    assert r.status_code == 200 and llm.BUSY in r.json()["answer"] and "what your brain found" in r.json()["answer"]


def test_llm_empty_or_none_output(sample, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda system, user: "")
    r = sample.post("/ask", json={"question": "empty llm billing-service"}).json()
    assert r["answer"].strip()  # never an empty answer bubble


def test_llm_not_called_when_no_context(client, monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "complete", lambda s, u: calls.append(1) or "x")
    client.post("/ask", json={"question": "nothing indexed yet"})
    assert calls == []


# ---- URL fetch ---------------------------------------------------------------------------
class FakeResp:
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def __init__(self, body: bytes):
        self.body = body

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _public_dns(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0))])


def test_url_ingest_html(client, monkeypatch):
    _public_dns(monkeypatch)
    html = b"<html><head><title>Docs &amp; Guides</title><script>evil()</script></head><body><nav>menu</nav>" \
           b"<h1>Memories</h1><p>Memories are per-user context.</p></body></html>"
    monkeypatch.setattr("whybot.services.knowledge._opener", type("O", (), {"open": lambda self, req, timeout: FakeResp(html)})())
    assert client.post("/url", json={"url": "https://docs.example.com/x"}).status_code == 200
    row = client.get("/inventory").json()[0]
    assert row["title"] == "Docs & Guides"
    r = client.post("/ask", json={"question": "what are memories"}).json()
    assert any("per-user context" in c["content"] for c in r["chunks"])
    assert not any("evil()" in c["content"] for c in r["chunks"])


def test_url_ingest_network_error(client, monkeypatch):
    _public_dns(monkeypatch)

    def boom(req, timeout):
        raise TimeoutError("slow")
    monkeypatch.setattr("whybot.services.knowledge._opener", type("O", (), {"open": lambda self, req, timeout: boom(req, timeout)})())
    r = client.post("/url", json={"url": "https://slow.example.com"})
    assert r.status_code == 400 and "Couldn't fetch" in r.json()["detail"]


def test_url_ingest_empty_page(client, monkeypatch):
    _public_dns(monkeypatch)
    monkeypatch.setattr("whybot.services.knowledge._opener", type("O", (), {"open": lambda self, req, timeout: FakeResp(b"<html><script>x</script></html>")})())
    r = client.post("/url", json={"url": "https://empty.example.com"})
    assert r.status_code == 400 and "No readable text" in r.json()["detail"]


def test_url_redirect_to_private_ip_blocked(client, monkeypatch):
    """A public URL that redirects to an internal address must not be followed."""
    _public_dns(monkeypatch)
    import urllib.error

    def redirecting(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 302, "Found", {"Location": "http://169.254.169.254/"}, None)
    monkeypatch.setattr("whybot.services.knowledge._opener", type("O", (), {"open": lambda self, req, timeout: redirecting(req, timeout)})())
    r = client.post("/url", json={"url": "https://redirect.example.com"})
    assert r.status_code == 400


# ---- persistence --------------------------------------------------------------------------
@pytest.mark.parametrize("content", ["", "{", "null", "[]", '{"docs": "nope"}', '{"docs": {"a": {"title": 1}}}',
                                     '{"personas": null, "edges": null, "stats": null}', "\x00\x01"])
def test_corrupt_state_file_never_crashes(tmp_path, content):
    from whybot.state import BrainState

    p = tmp_path / "state.json"
    p.write_text(content)
    s = BrainState(p)
    assert isinstance(s.docs, dict) and "engineer" in s.personas and s.stats["questions"] >= 0


def test_unwritable_state_dir_does_not_break_requests(client, monkeypatch, tmp_path):
    from whybot.state import state

    monkeypatch.setattr(state, "path", tmp_path / "missing" / "\x00bad" / "s.json")
    r = client.post("/upload", files={"file": ("w.md", b"still works", "text/plain")})
    assert r.status_code == 200
