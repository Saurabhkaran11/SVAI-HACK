"""Relationship graph engine.

Edges are stored as human-readable strings "source --[RELATION]--> target" (the same
format the UI renders). `Graph` indexes them for O(1) neighbour lookups, used by
multi-hop blast-radius traversal and by offline graph retrieval.
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from dataclasses import dataclass

_EDGE = re.compile(r"^(.+?) --\[(.+?)\]--> (.+)$")
_WORDS = re.compile(r"[a-z0-9]+")
_GENERIC = frozenset({"api", "service", "config", "team", "app", "the", "a", "of", "and", "to"})
OWNER_RELATIONS = frozenset({"OWNED_BY", "OWNS", "OWNER", "MANAGED_BY", "MAINTAINED_BY", "RESPONSIBLE_FOR"})


@dataclass(frozen=True)
class Edge:
    source: str
    relation: str
    target: str

    def __str__(self) -> str:
        return format_edge(self.source, self.relation, self.target)

    @property
    def is_ownership(self) -> bool:
        return self.relation.upper() in OWNER_RELATIONS


def format_edge(source: str, relation: str, target: str) -> str:
    return f"{source} --[{relation}]--> {target}"


def parse_edge(text: str) -> Edge | None:
    m = _EDGE.match(text.strip())
    return Edge(*m.groups()) if m else None


def manifest_edges(manifest: dict) -> list[str]:
    """Convert a bring-your-own-graph payload into edge strings."""
    ents = manifest["entities"]
    return [format_edge(ents[r["source"]]["name"], r["predicate"], ents[r["target"]]["name"])
            for r in manifest["relations"]]


class Graph:
    def __init__(self, edge_strings: list[str]):
        seen: set[str] = set()
        self.edge_set = seen
        self.edges: list[Edge] = []
        for raw in edge_strings:
            if raw in seen:
                continue
            seen.add(raw)
            e = parse_edge(raw)
            if e:
                self.edges.append(e)
        self.incoming: dict[str, list[Edge]] = defaultdict(list)   # target -> edges pointing at it
        self.outgoing: dict[str, list[Edge]] = defaultdict(list)
        self.touching: dict[str, list[Edge]] = defaultdict(list)   # node -> every edge it is on
        self.owners: dict[str, list[str]] = defaultdict(list)      # entity -> owning teams/people
        for e in self.edges:
            self.touching[e.source].append(e)
            if e.target != e.source:
                self.touching[e.target].append(e)
            if e.is_ownership:
                if e.target not in self.owners[e.source]:
                    self.owners[e.source].append(e.target)
            else:
                self.incoming[e.target].append(e)
                self.outgoing[e.source].append(e)
        self.owner_nodes = {o for os_ in self.owners.values() for o in os_}
        self.nodes = set(self.touching)
        self.entities = self.nodes - self.owner_nodes  # things that can break
        self._name_tokens = {n: set(_WORDS.findall(n.lower())) - _GENERIC for n in self.nodes}

    # ---- entity matching -------------------------------------------------
    def match(self, text: str, candidates: set[str] | None = None) -> set[str]:
        """Entities named in free text (exact name first, then shared distinctive tokens)."""
        pool = candidates if candidates is not None else self.entities
        low = text.lower()
        if not low.strip() or not pool:
            return set()
        exact = {n for n in pool if len(n) > 1 and n.lower() in low}
        if exact:
            return exact
        words = set(_WORDS.findall(low)) - _GENERIC
        if not words:
            return set()
        return {n for n in pool if words & self._name_tokens.get(n, set())}

    # ---- traversal ---------------------------------------------------------
    def blast_radius(self, seeds: set[str], max_hops: int = 3) -> tuple[dict[str, int], dict[str, str]]:
        """BFS against dependency direction: anything pointing at an affected node is affected."""
        hop = {s: 0 for s in seeds}
        via: dict[str, str] = {}
        queue = deque(seeds)
        while queue:
            cur = queue.popleft()
            if hop[cur] >= max_hops:
                continue
            for e in self.incoming.get(cur, ()):
                if e.source not in hop:
                    hop[e.source] = hop[cur] + 1
                    via[e.source] = f"{e.relation} {cur}"
                    queue.append(e.source)
        return hop, via

    def neighbourhood(self, seeds: set[str], hops: int = 2) -> list[str]:
        """Undirected expansion around seeds, returned as edge strings (offline graph context)."""
        frontier, seen, out = set(seeds), set(seeds), {}
        for _ in range(hops):
            nxt = set()
            for node in frontier:
                for e in self.touching.get(node, ()):
                    out.setdefault(str(e), None)
                    for n in (e.source, e.target):
                        if n not in seen:
                            seen.add(n)
                            nxt.add(n)
            frontier = nxt
            if not frontier:
                break
        return list(out)

    def edges_among(self, nodes, limit: int = 40) -> list[str]:
        """Edges touching any of `nodes` (evidence for an answer), closest first."""
        out: dict[str, None] = {}
        for n in nodes:
            for e in self.touching.get(n, ()):
                out.setdefault(str(e), None)
                if len(out) >= limit:
                    return list(out)
        return list(out)

    def owners_of(self, nodes: set[str]) -> dict[str, list[str]]:
        result: dict[str, list[str]] = defaultdict(list)
        for n in sorted(nodes):
            for owner in self.owners.get(n, ()):
                if n not in result[owner]:
                    result[owner].append(n)
        return dict(result)
