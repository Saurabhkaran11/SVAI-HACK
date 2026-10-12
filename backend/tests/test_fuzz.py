"""Property-based fuzzing (Hypothesis): random text, graphs and API payloads."""
import os
import string

from hypothesis import HealthCheck, given, settings, strategies as st

from whybot.graph import Graph, format_edge, parse_edge
from whybot.text import html_to_text, paragraphs, slug, tokens

ANY_TEXT = st.one_of(
    st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=3000),
    st.text(alphabet="abc xyz-", min_size=1000, max_size=6000),          # long single lines
    st.lists(st.sampled_from(["\n", "\r\n", "\u2028", " ", "x", "word "]), max_size=2000).map("".join),  # odd breaks
)
NAME = st.text(alphabet=string.ascii_letters + string.digits + "-_. ", min_size=1, max_size=30).map(str.strip).filter(bool)
DEEP = int(os.getenv("FUZZ_EXAMPLES", "300"))
FUZZ = settings(max_examples=DEEP, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])


@FUZZ
@given(ANY_TEXT)
def test_slug_always_safe(s):
    out = slug(s)
    assert out and len(out) <= 60 and set(out) <= set(string.ascii_lowercase + string.digits + "_")


@FUZZ
@given(ANY_TEXT)
def test_tokens_never_crash(s):
    assert all(t and t.isalnum() for t in tokens(s))


@FUZZ
@given(ANY_TEXT)
def test_paragraphs_bounded_and_lossless_enough(s):
    parts = paragraphs(s)
    assert all(p.strip() and len(p) <= 1500 for p in parts)
    if s.strip():
        assert parts  # non-empty text never vanishes


@FUZZ
@given(ANY_TEXT)
def test_html_to_text_never_crashes(s):
    title, text = html_to_text(s)
    assert isinstance(title, str) and isinstance(text, str)


@FUZZ
@given(NAME, st.sampled_from(["DEPENDS_ON", "OWNED_BY", "REPLACES", "REFERENCES"]), NAME)
def test_edge_roundtrip(a, rel, b):
    e = parse_edge(format_edge(a, rel, b))
    assert e is not None and e.relation == rel
    assert (e.source, e.target) == (a, b) or "--[" in a + b


@FUZZ
@given(st.lists(st.tuples(NAME, st.sampled_from(["DEPENDS_ON", "OWNED_BY", "CALLS"]), NAME), max_size=80),
       st.integers(min_value=0, max_value=6))
def test_graph_bfs_invariants(triples, max_hops):
    g = Graph([format_edge(*t) for t in triples])
    seeds = set(list(g.entities)[:2])
    hop, via = g.blast_radius(seeds, max_hops)
    assert all(0 <= h <= max_hops for h in hop.values())
    assert all(hop[s] == 0 for s in seeds)
    for node, h in hop.items():  # every non-seed has a parent exactly one hop closer
        if h:
            parent = via[node].split(" ", 1)[1]
            assert hop[parent] == h - 1
    owners = g.owners_of(set(hop))
    assert all(items for items in owners.values())


@FUZZ
@given(ANY_TEXT)
def test_graph_match_never_crashes(s):
    g = Graph(["billing-service --[DEPENDS_ON]--> payments-api-v1", "x --[OWNED_BY]--> team"])
    assert g.match(s) <= g.entities


@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(q=st.text(min_size=1, max_size=400), persona=st.one_of(st.none(), st.sampled_from(["engineer", "manager", "nope"])),
       graph=st.booleans())
def test_api_ask_fuzz(sample, q, persona, graph):
    r = sample.post("/ask", json={"question": q, "persona": persona, "graph": graph})
    assert r.status_code in (200, 400, 422), r.text[:200]
    if r.status_code == 200:
        body = r.json()
        assert body["answer"].strip() and isinstance(body["chunks"], list)


@settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(change=st.text(min_size=1, max_size=300))
def test_api_impact_fuzz(sample, change):
    r = sample.post("/impact", json={"change": change})
    assert r.status_code in (200, 400, 422), r.text[:200]
    if r.status_code == 200:
        b = r.json()
        assert 0 <= b["risk"]["score"] <= 100 and b["risk"]["level"] in {"Low", "Medium", "High"}
        assert len(b["notify"]) == len(b["owners"])


@settings(max_examples=80, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(name=st.text(max_size=120), body=st.binary(max_size=4000))
def test_api_upload_fuzz(client, name, body):
    r = client.post("/upload", files={"file": (name or "f.txt", body, "application/octet-stream")})
    assert r.status_code in (200, 400, 422), r.text[:200]
