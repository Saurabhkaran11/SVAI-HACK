from whybot.graph import Graph, parse_edge

EDGES = [
    "web --[DEPENDS_ON]--> api",
    "api --[DEPENDS_ON]--> db",
    "worker --[DEPENDS_ON]--> db",
    "api --[OWNED_BY]--> team-core",
    "web --[OWNED_BY]--> team-ui",
]


def test_parse_edge():
    e = parse_edge("a b --[REL]--> c")
    assert (e.source, e.relation, e.target) == ("a b", "REL", "c")
    assert parse_edge("garbage") is None


def test_blast_radius_hops_and_owners():
    g = Graph(EDGES)
    hop, via = g.blast_radius({"db"}, max_hops=3)
    assert hop == {"db": 0, "api": 1, "worker": 1, "web": 2}
    assert via["web"] == "DEPENDS_ON api"
    assert g.owners_of(set(hop)) == {"team-core": ["api"], "team-ui": ["web"]}


def test_max_hops_respected():
    hop, _ = Graph(EDGES).blast_radius({"db"}, max_hops=1)
    assert "web" not in hop


def test_match_excludes_owner_teams():
    g = Graph(EDGES)
    assert g.match("migrate the db") == {"db"}
    assert "team-core" not in g.match("team-core reorg")
