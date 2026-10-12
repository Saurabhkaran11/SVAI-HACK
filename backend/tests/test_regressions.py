"""One test per defect found during the test campaign, so none can come back silently.

D1  validation errors were raw lists (UI showed "[object Object]")
D2  binary junk named .txt was accepted as a document
D3  UTF-16 files decoded into garbage
D4  blast radius on a meaningless change still listed people (wrapper words matched docs)
D5  persona labels like "!!!" / "???" collided on one key and overwrote each other
D6  zero-width / control characters (NUL) were stored and treated as content
D7  /ask persona had no length limit
D8  a document with no line breaks became one 300k-character chunk
D9  re-uploading a file leaked index entries (memory grew forever)
D10 a corrupt-but-valid-JSON state file (nulls / wrong shapes) crashed startup
D11 HydraDB outage during upload returned a raw 500
D12 an empty LLM reply produced an empty answer
D13 URL redirects were followed without re-checking for private addresses (SSRF)
"""
import io

import pytest


def test_d1_validation_errors_are_readable_strings(client):
    for path, body in [("/ask", {"question": 123}), ("/ask", {}), ("/impact", {"change": None}),
                       ("/persona", {"label": "x", "memories": ["ok", None]})]:
        r = client.post(path, json=body)
        assert r.status_code == 422
        assert isinstance(r.json()["detail"], str) and r.json()["detail"]


def test_d1_validation_error_with_binary_body_is_not_500(client):
    r = client.post("/ask", content=b"\xff\xfe\x00garbage", headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_d2_binary_txt_rejected(client):
    r = client.post("/upload", files={"file": ("bin.txt", bytes(range(256)) * 50, "text/plain")})
    assert r.status_code == 400 and "binary" in r.json()["detail"]


def test_d3_utf16_decoded_correctly(client):
    for enc in ("utf-16", "utf-16-le", "utf-16-be"):
        client.post("/reset")
        assert client.post("/upload", files={"file": ("u.txt", "Zoë owns the ledger-service.".encode(enc), "text/plain")}).status_code == 200
        r = client.post("/ask", json={"question": "who owns the ledger-service"}).json()
        assert any("Zoë owns" in c["content"] for c in r["chunks"]), enc


def test_d3_windows_1252_decoded(client):
    client.post("/upload", files={"file": ("w.txt", "Café team owns billing".encode("cp1252"), "text/plain")})
    r = client.post("/ask", json={"question": "who owns billing"}).json()
    assert any("Café" in c["content"] for c in r["chunks"])


@pytest.mark.parametrize("change", ["???", "the a of", "!!!", "​ x"])
def test_d4_meaningless_change_has_no_people_or_incidents(sample, change):
    r = sample.post("/impact", json={"change": change})
    if r.status_code == 200:
        b = r.json()
        assert b["people"] == [] and b["incidents"] == [] and b["affected"] == [] and b["risk"]["level"] == "Low"


def test_d4_relevant_change_still_finds_people(sample):
    b = sample.post("/impact", json={"change": "Deprecate payments-api-v1 next month"}).json()
    assert "James Wright" in b["people"] and b["incidents"]


def test_d5_symbol_labels_get_distinct_keys(client):
    k1 = client.post("/persona", json={"label": "!!!"}).json()["key"]
    k2 = client.post("/persona", json={"label": "???"}).json()["key"]
    assert k1 != k2
    labels = client.get("/personas").json()
    assert labels[k1] == "!!!" and labels[k2] == "???"


def test_d5_clash_with_different_label_does_not_overwrite(client):
    k1 = client.post("/persona", json={"label": "Support Lead"}).json()["key"]
    k2 = client.post("/persona", json={"label": "support-lead"}).json()["key"]
    assert k1 != k2
    k3 = client.post("/persona", json={"label": "Support Lead", "memories": ["update"]}).json()["key"]
    assert k3 == k1  # same label updates in place


def test_d5_cannot_hijack_profile_key(client):
    client.post("/profile", json={"name": "Vik"})
    k = client.post("/persona", json={"label": "me"}).json()["key"]
    assert k != "me" and client.get("/personas").json()["me"] == "Me (Vik)"


def test_d6_invisible_and_control_chars_stripped(client):
    assert client.post("/ask", json={"question": "​​"}).status_code == 400
    assert client.post("/impact", json={"change": "​"}).status_code == 400
    assert client.post("/memory", json={"persona": "engineer", "text": "\x00\x01"}).status_code == 400
    client.post("/memory", json={"persona": "engineer", "text": "I\x00 own​ CI"})
    assert "I own CI" in client.get("/personas/full").json()["engineer"]["memories"]


def test_d6_duplicate_memory_not_stored_twice(client):
    for _ in range(3):
        client.post("/memory", json={"persona": "engineer", "text": "I like dashboards"})
    mems = client.get("/personas/full").json()["engineer"]["memories"]
    assert mems.count("I like dashboards") == 1


def test_d7_persona_length_limited(client):
    for path, body in [("/ask", {"question": "q"}), ("/compare", {"question": "q"}), ("/impact", {"change": "c"})]:
        assert client.post(path, json={**body, "persona": "x" * 81}).status_code == 422


def test_d8_no_giant_chunks(client):
    client.post("/upload", files={"file": ("line.txt", ("needle haystack " * 20000).encode(), "text/plain")})
    chunks = client.post("/ask", json={"question": "needle"}).json()["chunks"]
    assert chunks and max(len(c["content"]) for c in chunks) <= 1000


def test_d9_reupload_compacts_index(client):
    from whybot.state import state
    for i in range(300):
        client.post("/upload", files={"file": ("same.md", f"rev {i}\n\ntwo\n\nthree".encode(), "text/plain")})
    assert len(state.index.units) < 200 and sum(1 for u in state.index.units if u[1]) == 3
    r = client.post("/ask", json={"question": "rev 299"}).json()
    assert r["chunks"][0]["content"] == "rev 299"


@pytest.mark.parametrize("content", ["null", "[]", '"text"', "42", '{"docs": "nope"}', '{"docs": {"a": {"title": 1}}}',
                                     '{"docs": {"a": null}}', '{"personas": {"x": {"label": null, "memories": "a"}}}',
                                     '{"personas": null, "edges": null, "stats": null}', '{"edges": [1, null, "a --[R]--> b"]}',
                                     '{"stats": {"questions": -5}}', '{"stats": {"questions": "many"}}'])
def test_d10_corrupt_state_shapes(tmp_path, content):
    from whybot.state import BrainState
    p = tmp_path / "state.json"
    p.write_text(content)
    s = BrainState(p)
    assert isinstance(s.docs, dict) and "engineer" in s.personas and s.stats["questions"] >= 0
    assert all(isinstance(e, str) for e in s.edges)


def test_d10_valid_parts_survive_partial_corruption(tmp_path):
    from whybot.state import BrainState
    p = tmp_path / "state.json"
    p.write_text('{"docs": {"good": {"title": "G", "text": "Mia owns infra", "type": "doc"}, "bad": 5},'
                 ' "personas": {"qa": {"label": "QA", "memories": ["ok"]}, "broken": 1}}')
    s = BrainState(p)
    assert list(s.docs) == ["good"] and s.personas["qa"]["memories"] == ["ok"] and "broken" not in s.personas
    assert s.index.search("infra")[0].title == "G"


def test_d12_empty_llm_output_falls_back(sample, monkeypatch):
    from whybot import llm
    for out in ("", "   ", None):
        monkeypatch.setattr(llm, "complete", lambda s, u, o=out: o)
        r = sample.post("/ask", json={"question": f"billing-service fallback {out!r}"}).json()
        assert r["answer"].strip()


def test_d13_redirect_to_private_ip_blocked(client, monkeypatch):
    import urllib.error

    from whybot.services import knowledge

    def resolve(host, port):
        return [(2, 1, 6, "", ("10.0.0.5" if host == "internal.example.com" else "93.184.216.34", 0))]
    monkeypatch.setattr("socket.getaddrinfo", resolve)

    class Opener:
        def open(self, req, timeout):
            raise urllib.error.HTTPError(req.full_url, 302, "Found", {"Location": "http://internal.example.com/admin"}, None)
    monkeypatch.setattr(knowledge, "_opener", Opener())
    r = client.post("/url", json={"url": "https://public.example.com/start"})
    assert r.status_code == 400 and "private network" in r.json()["detail"]


def test_d13_redirect_loop_is_bounded(client, monkeypatch):
    import urllib.error

    from whybot.services import knowledge
    monkeypatch.setattr("socket.getaddrinfo", lambda h, p: [(2, 1, 6, "", ("93.184.216.34", 0))])
    calls = []

    class Opener:
        def open(self, req, timeout):
            calls.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 302, "Found", {"Location": "/again"}, None)
    monkeypatch.setattr(knowledge, "_opener", Opener())
    r = client.post("/url", json={"url": "https://loop.example.com/"})
    assert r.status_code == 400 and "redirects" in r.json()["detail"] and len(calls) <= 5


def test_non_html_url_rejected(client, monkeypatch):
    from whybot.services import knowledge
    monkeypatch.setattr("socket.getaddrinfo", lambda h, p: [(2, 1, 6, "", ("93.184.216.34", 0))])

    class Resp(io.BytesIO):
        headers = {"Content-Type": "application/zip"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class Opener:
        def open(self, req, timeout):
            return Resp(b"PK\x03\x04")
    monkeypatch.setattr(knowledge, "_opener", Opener())
    r = client.post("/url", json={"url": "https://files.example.com/a.zip"})
    assert r.status_code == 400 and "not a web page" in r.json()["detail"]


def test_writes_are_debounced_and_flushed(client, tmp_path):
    """Many uploads -> one deferred write; the file is complete after the debounce window."""
    import json
    import time

    from whybot.state import SAVE_DELAY_S, state
    for i in range(20):
        client.post("/upload", files={"file": (f"b{i}.md", f"doc {i} owner".encode(), "text/plain")})
    time.sleep(SAVE_DELAY_S + 0.5)
    data = json.loads(state.path.read_text())
    assert all(f"b{i}" in data["docs"] for i in range(20))


# ---- LLM providers (added when switching away from Anthropic-only) ------------------------
def test_openai_compatible_provider_used_without_key(sample, monkeypatch):
    """Ollama/LM Studio style: base URL set, no API key -> LLM is still called."""
    from types import SimpleNamespace as NS

    from whybot import config, llm
    s = config.Settings(**{**config.settings.__dict__, "openai_key": "", "anthropic_key": "",
                           "openai_base_url": "http://localhost:11434/v1", "openai_model": "llama3.2"})
    monkeypatch.setattr("whybot.llm.settings", s)
    seen = {}

    class Fake:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    seen.update(kw)
                    return NS(choices=[NS(message=NS(content="Billing depends on v1 [ADR-007]"))])
    monkeypatch.setattr(llm, "_openai", lambda: Fake)
    r = sample.post("/ask", json={"question": "ollama path billing-service"}).json()
    assert r["answer"] == "Billing depends on v1 [ADR-007]" and seen["model"] == "llama3.2"
    assert llm.provider() == "ollama"


def test_provider_names(monkeypatch):
    from whybot import config, llm
    for url, name in [("https://api.groq.com/openai/v1", "groq"),
                      ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini"),
                      ("http://localhost:1234/v1", "lm-studio"), ("", "openai")]:
        s = config.Settings(**{**config.settings.__dict__, "anthropic_key": "", "openai_key": "k", "openai_base_url": url})
        monkeypatch.setattr("whybot.llm.settings", s)
        assert llm.provider() == name


def test_no_llm_answer_is_clean_summary(sample):
    a = sample.post("/ask", json={"question": "What would break if we deprecated the v1 payments API?"}).json()["answer"]
    assert a.startswith("**Here's what your brain found**") and "How it's connected" in a
    assert "No LLM key" not in a and "[ADR-007" not in a.split("\n")[1][:3]
    b = sample.post("/impact", json={"change": "Deprecate payments-api-v1 next month"}).json()["brief"]
    assert "Impact facts" in b and "Computed risk: High" in b


def test_odd_model_citations_removed(sample, monkeypatch):
    from whybot import llm
    monkeypatch.setattr(llm, "complete", lambda s, u: "- billing breaks【1†L13-L15】【4†L2-L3】 [ADR-007]")
    a = sample.post("/ask", json={"question": "citation cleanup billing-service"}).json()["answer"]
    assert a == "- billing breaks [ADR-007]"


def test_impact_verdict_matches_computed_risk():
    from whybot.services.impact import align_verdict
    b = "**Verdict**\n⚠️ **Medium\u2011risk** – deprecation touches billing\n\n**What breaks**\n- low-risk path stays"
    out = align_verdict(b, "High")
    assert "High\u2011risk" in out and "Medium" not in out.split("\n\n")[0]
    assert "low-risk path stays" in out  # only the verdict is touched
    assert align_verdict("**Verdict:** Low risk overall.", "Medium") == "**Verdict:** Medium risk overall."
