"""Null, missing, wrong-type, malformed and hostile inputs for every endpoint.

Rule under test: bad input must yield a clean 4xx with a readable `detail`,
never a 500, and must never corrupt state for later requests.
"""
import io
import json

import pytest

POST_ENDPOINTS = {
    "/ask": {"question": "Who owns billing?"},
    "/compare": {"question": "Who owns billing?"},
    "/impact": {"change": "Deprecate payments-api-v1"},
    "/url": {"url": "https://example.com"},
    "/memory": {"persona": "engineer", "text": "I like tests"},
    "/persona": {"label": "QA"},
    "/profile": {"name": "Vik"},
}
REQUIRED = {"/ask": "question", "/compare": "question", "/impact": "change", "/url": "url",
            "/memory": "text", "/persona": "label"}


def _no_500(r):
    assert r.status_code < 500, f"{r.status_code}: {r.text[:300]}"


# ---- null / missing / wrong types --------------------------------------------------
@pytest.mark.parametrize("path", sorted(POST_ENDPOINTS))
def test_empty_body(client, path):
    r = client.post(path, json={})
    _no_500(r)
    if path in REQUIRED:
        assert r.status_code == 422


@pytest.mark.parametrize("path", sorted(POST_ENDPOINTS))
def test_null_body(client, path):
    _no_500(client.post(path, content=b"null", headers={"Content-Type": "application/json"}))


@pytest.mark.parametrize("path", sorted(POST_ENDPOINTS))
def test_not_json(client, path):
    r = client.post(path, content=b"{not json", headers={"Content-Type": "application/json"})
    _no_500(r)
    assert r.status_code == 422


@pytest.mark.parametrize("path", sorted(REQUIRED))
def test_required_field_null(client, path):
    body = dict(POST_ENDPOINTS[path], **{REQUIRED[path]: None})
    r = client.post(path, json=body)
    _no_500(r)
    assert r.status_code == 422


@pytest.mark.parametrize("path", sorted(POST_ENDPOINTS))
@pytest.mark.parametrize("bad", [123, 4.5, True, [], {"x": 1}, ["a", "b"]])
def test_wrong_types(client, path, bad):
    key = REQUIRED.get(path, "name")
    _no_500(client.post(path, json=dict(POST_ENDPOINTS[path], **{key: bad})))


@pytest.mark.parametrize("persona", [None, "", "does_not_exist", "../../etc/passwd", "x" * 500])
def test_ask_with_odd_personas(sample, persona):
    r = sample.post("/ask", json={"question": "Who owns billing-service?", "persona": persona})
    _no_500(r)
    if persona is None or len(persona) <= 80:
        assert r.status_code == 200


@pytest.mark.parametrize("q", ["   ", "\n\t", "\u200b\u200b", "?", "!!!", "the a of and"])
def test_blank_or_stopword_questions(sample, q):
    r = sample.post("/ask", json={"question": q})
    _no_500(r)
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        assert isinstance(r.json()["answer"], str) and r.json()["answer"]


@pytest.mark.parametrize("change", ["   ", "\n", "\u200b", "???"])
def test_blank_changes(sample, change):
    r = sample.post("/impact", json={"change": change})
    _no_500(r)
    if r.status_code == 200:
        assert r.json()["risk"]["level"] == "Low"


def test_graph_flag_wrong_type(client):
    _no_500(client.post("/ask", json={"question": "hi", "graph": "maybe"}))


def test_memory_for_unknown_persona_creates_it(client):
    r = client.post("/memory", json={"persona": "ghost", "text": "boo"})
    assert r.status_code == 200
    assert client.get("/personas/full").json()["ghost"]["memories"] == ["boo"]


def test_persona_memories_with_nulls(client):
    r = client.post("/persona", json={"label": "Nully", "memories": ["ok", None, "", "  "]})
    _no_500(r)


def test_persona_label_only_symbols(client):
    r = client.post("/persona", json={"label": "!!!"})
    _no_500(r)
    if r.status_code == 200:
        assert r.json()["key"]  # never an empty key


def test_profile_all_empty(client):
    r = client.post("/profile", json={"name": "", "role": "", "team": "", "about": ""})
    assert r.status_code == 200 and client.get("/personas").json()["me"] == "Me"


# ---- hostile strings ---------------------------------------------------------------------
HOSTILE = [
    "<script>alert(1)</script>", "'; DROP TABLE docs; --", "{{7*7}}", "${jndi:ldap://x}",
    "../../../../etc/passwd", "\x00\x01\x02", "😀🔥🧠" * 50, "مرحبا بالعالم", "日本語のテキスト",
    "a --[DEPENDS_ON]--> b", "--[", "]-->", "((((((((((((((((((((a", "\\" * 100,
]


@pytest.mark.parametrize("s", HOSTILE)
def test_hostile_strings_everywhere(sample, s):
    for path, body in [("/ask", {"question": s}), ("/impact", {"change": s}),
                       ("/memory", {"persona": "engineer", "text": s}), ("/persona", {"label": s[:80]}),
                       ("/profile", {"name": s[:120], "about": s})]:
        _no_500(sample.post(path, json=body))
    assert sample.get("/health").status_code == 200
    assert sample.get("/graph").status_code == 200


def test_script_tags_are_returned_as_data_not_executed(client):
    client.post("/upload", files={"file": ("x.md", b"<script>alert('x')</script> owner is Bob", "text/markdown")})
    r = client.post("/ask", json={"question": "who is the owner"}).json()
    assert r["chunks"] and "<script>" in r["chunks"][0]["content"]  # stored verbatim; UI renders as text


# ---- uploads -----------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["", ".md", "noext", "a.MD", "weird name (1).Md", "../../evil.md",
                                  "/abs/path.txt", "C:\\win\\file.txt", "x" * 400 + ".md", "数据.md", "a.md.exe"])
def test_upload_filenames(client, name):
    r = client.post("/upload", files={"file": (name, b"Owner: Lee", "text/plain")})
    _no_500(r)
    if r.status_code == 200:
        doc_id = r.json()["ingested"][0]
        assert "/" not in doc_id and "\\" not in doc_id and ".." not in doc_id and len(doc_id) <= 60


def test_upload_missing_file_field(client):
    r = client.post("/upload", data={"nope": "1"})
    assert r.status_code == 422


def test_upload_binary_garbage_as_txt(client):
    r = client.post("/upload", files={"file": ("bin.txt", bytes(range(256)) * 50, "text/plain")})
    _no_500(r)


def test_upload_utf16_and_bom(client):
    r1 = client.post("/upload", files={"file": ("u16.txt", "Owner: Zoë".encode("utf-16"), "text/plain")})
    r2 = client.post("/upload", files={"file": ("bom.txt", "\ufeffOwner: Ana".encode("utf-8"), "text/plain")})
    _no_500(r1)
    assert r2.status_code == 200


def test_upload_fake_pdf(client):
    r = client.post("/upload", files={"file": ("fake.pdf", b"this is not a pdf", "application/pdf")})
    assert r.status_code == 400 and "Couldn't read" in r.json()["detail"]


def test_upload_empty_pdf(client):
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.showPage()
    c.save()
    r = client.post("/upload", files={"file": ("blank.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 400 and "No readable text" in r.json()["detail"]


def test_upload_real_pdf(client):
    pytest.importorskip("reportlab")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "Kim Lee owns the search-service.")
    c.showPage()
    c.drawString(72, 720, "search-service depends on the index-api.")
    c.save()
    assert client.post("/upload", files={"file": ("team.pdf", buf.getvalue(), "application/pdf")}).status_code == 200
    r = client.post("/ask", json={"question": "who owns search-service"}).json()
    assert any("Kim Lee" in c["content"] for c in r["chunks"])


def test_upload_json_and_csv(client):
    j = json.dumps({"service": "ledger", "owner": "Ravi"}).encode()
    c = b"service,owner\nledger,Ravi\nwallet,Mei\n"
    assert client.post("/upload", files={"file": ("svc.json", j, "application/json")}).status_code == 200
    assert client.post("/upload", files={"file": ("svc.csv", c, "text/csv")}).status_code == 200
    r = client.post("/ask", json={"question": "who owns wallet"}).json()
    assert any("Mei" in ch["content"] for ch in r["chunks"])


def test_same_filename_replaces_not_duplicates(client):
    client.post("/upload", files={"file": ("dup.md", b"version one alpha", "text/plain")})
    client.post("/upload", files={"file": ("dup.md", b"version two beta", "text/plain")})
    assert len([r for r in client.get("/inventory").json() if r["id"] == "dup"]) == 1
    r = client.post("/ask", json={"question": "alpha version"}).json()
    assert not any("alpha" in c["content"] for c in r["chunks"])  # old index entries removed


# ---- URLs --------------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["not a url", "javascript:alert(1)", "file:///etc/passwd", "http://", "https://",
                                 "http://localhost/", "http://127.0.0.1/", "http://10.0.0.1/", "http://192.168.1.1/",
                                 "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "http://0.0.0.0/",
                                 "http://no-such-host.invalid/"])
def test_bad_or_internal_urls(client, url):
    r = client.post("/url", json={"url": url})
    _no_500(r)
    assert r.status_code in (400, 422)


# ---- method / route hygiene -----------------------------------------------------------------
def test_unknown_route_and_wrong_method(client):
    assert client.get("/nope").status_code == 404
    assert client.get("/ask").status_code == 405
    assert client.delete("/health").status_code == 405


def test_openapi_and_docs(client):
    spec = client.get("/openapi.json").json()
    assert {"/ask", "/compare", "/impact", "/upload", "/url", "/memory", "/persona", "/profile"} <= set(spec["paths"])
    assert client.get("/docs").status_code == 200
