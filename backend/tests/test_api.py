"""End-to-end API tests (offline mode). Run: pytest -q"""
import concurrent.futures as cf


def test_health_starts_empty(client):
    h = client.get("/health").json()
    assert h["ok"] and h["mode"] == "mock" and h["docs"] == 0 and not h["sample_loaded"]
    assert h["starter_questions"] and h["sample_questions"]


def test_empty_brain_answer(client):
    r = client.post("/ask", json={"question": "Who owns billing?"}).json()
    assert "don't have anything" in r["answer"]


def test_upload_and_ask(client):
    doc = b"# Mobile\nRavi Kumar owns the iOS release.\n\nRelease freeze starts Friday."
    assert client.post("/upload", files={"file": ("mobile.md", doc, "text/markdown")}).json() == {"ingested": ["mobile"]}
    r = client.post("/ask", json={"question": "Who owns the iOS release?", "persona": "new_hire"}).json()
    assert r["chunks"][0]["title"] == "mobile.md" and "Ravi" in r["chunks"][0]["content"]
    assert any("Persona memory" in f for f in r["features"])


def test_upload_rejects_bad_type_and_size(client):
    r = client.post("/upload", files={"file": ("virus.exe", b"x", "application/octet-stream")})
    assert r.status_code == 400 and "Unsupported" in r.json()["detail"]
    r = client.post("/upload", files={"file": ("empty.txt", b"   ", "text/plain")})
    assert r.status_code == 400


def test_url_guard(client):
    assert client.post("/url", json={"url": "ftp://example.com/x"}).status_code == 400
    r = client.post("/url", json={"url": "http://127.0.0.1:8000/health"})
    assert r.status_code == 400 and "private" in r.json()["detail"]


def test_validation_errors(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/impact", json={"change": ""}).status_code == 422


def test_compare_graph_beats_plain(sample):
    r = sample.post("/compare", json={"question": "What would break if we deprecated the v1 payments API?",
                                      "persona": "manager"}).json()
    assert len(r["without_graph"]["paths"]) == 0 and len(r["with_graph"]["paths"]) >= 5
    assert sample.get("/health").json()["questions"] == 1  # compare counts once


def test_cache_hit_is_fast_and_invalidates(sample):
    q = {"question": "Why are we migrating to payments v2?", "graph": True}
    first = sample.post("/ask", json=q).json()
    second = sample.post("/ask", json=q).json()
    assert second["answer"] == first["answer"]
    assert sample.get("/health").json()["cache"]["hits"] >= 1
    sample.post("/upload", files={"file": ("new.md", b"payments v2 adds batch settlement", "text/markdown")})
    third = sample.post("/ask", json=q).json()  # new doc -> new state version -> recomputed
    assert any(c["title"] == "new.md" for c in third["chunks"])


def test_blast_radius(sample):
    r = sample.post("/impact", json={"change": "Deprecate payments-api-v1 next month", "persona": "manager"}).json()
    assert r["seeds"] == ["payments-api-v1"]
    hops = {a["name"]: a["hop"] for a in r["affected"]}
    assert hops["billing-service"] == 1 and hops["checkout-service"] == 1 and hops["auth-service"] == 2
    assert set(r["owners"]) == {"payments", "frontend-platform", "platform"}
    assert "Incident Postmortem: INC-0312" in r["incidents"]
    assert r["risk"]["level"] == "High" and len(r["notify"]) == 3
    assert r["notify"][0]["message"].startswith("Heads-up: we're planning to deprecate")


def test_blast_radius_no_match_is_low(sample):
    r = sample.post("/impact", json={"change": "Repaint the office kitchen"}).json()
    assert r["affected"] == [] and r["risk"]["level"] == "Low"


def test_personas_profile_memory_reset(client):
    key = client.post("/persona", json={"label": "Support Lead", "memories": ["I handle escalations", " "]}).json()["key"]
    assert key == "support_lead"
    client.post("/memory", json={"persona": key, "text": "I own Zendesk"})
    full = client.get("/personas/full").json()
    assert full[key]["memories"] == ["I handle escalations", "I own Zendesk"]
    assert client.post("/profile", json={"name": "Vik", "role": "EM"}).json() == {"persona": "me"}
    assert client.get("/personas").json()["me"] == "Me (Vik)"
    client.post("/reset")
    assert set(client.get("/personas").json()) == {"engineer", "manager", "new_hire"}


def test_graph_and_inventory(sample):
    assert len(sample.get("/graph").json()["edges"]) == 13
    rows = sample.get("/inventory").json()
    assert len(rows) == 5 and {"id", "title", "type"} <= set(rows[0])


def test_concurrent_requests_are_safe(sample):
    def hit(i):
        return sample.post("/ask", json={"question": f"Who owns billing-service? #{i}"}).status_code
    with cf.ThreadPoolExecutor(8) as ex:
        assert set(ex.map(hit, range(24))) == {200}
    assert sample.get("/health").json()["questions"] == 24


def test_state_persists_across_restart(client):
    client.post("/upload", files={"file": ("keep.md", b"Asha owns the data warehouse.", "text/markdown")})
    from whybot.config import settings
    from whybot.state import BrainState, state
    state.flush()  # writes are debounced; flush happens automatically within 1s and at exit
    fresh = BrainState(settings.state_file)
    assert "keep" in fresh.docs and fresh.index.search("data warehouse")[0].title == "keep.md"


def test_timing_header(client):
    assert "x-response-time-ms" in client.get("/health").headers
