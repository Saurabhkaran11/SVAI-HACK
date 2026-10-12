"""Thread-safe brain state + local search index, persisted atomically to JSON.

Design notes
- One re-entrant lock guards all mutations (FastAPI runs sync handlers in a thread pool).
- `version` bumps on knowledge/memory changes and is part of the answer-cache key.
- Writes are *debounced*: mutations mark the state dirty and a background thread flushes
  at most every SAVE_DELAY_S, so hot paths (asking questions) never serialize every document.
  Structural changes (new docs, personas, reset) flush immediately.
- Loading validates every field's shape, so a corrupt or hand-edited file can never crash startup.
"""
from __future__ import annotations

import atexit
import copy
import json
import logging
import os
import tempfile
import threading
from collections import defaultdict
from pathlib import Path

from . import sample_data as sd
from .config import settings
from .graph import Graph, manifest_edges
from .models import Chunk
from .text import paragraphs, tokens

log = logging.getLogger("whybot.state")
SAVE_DELAY_S = 1.0


class LocalIndex:
    """Inverted index over paragraphs: query cost scales with matches, not corpus size."""

    def __init__(self) -> None:
        self.units: list[tuple[str, str, frozenset[str]]] = []  # (doc_id, para, tokens); para "" = tombstone
        self.by_doc: dict[str, list[int]] = defaultdict(list)
        self.postings: dict[str, set[int]] = defaultdict(set)
        self.titles: dict[str, str] = {}
        self.dead = 0

    def add(self, doc_id: str, title: str, text: str) -> None:
        self.remove(doc_id)
        self.titles[doc_id] = title
        title_toks = tokens(title)
        for para in paragraphs(text):
            toks = frozenset(tokens(para) | title_toks)
            i = len(self.units)
            self.units.append((doc_id, para, toks))
            self.by_doc[doc_id].append(i)
            for t in toks:
                self.postings[t].add(i)

    def remove(self, doc_id: str) -> None:
        for i in self.by_doc.pop(doc_id, []):
            _, _, toks = self.units[i]
            for t in toks:
                bucket = self.postings.get(t)
                if bucket is not None:
                    bucket.discard(i)
                    if not bucket:
                        del self.postings[t]
            self.units[i] = (doc_id, "", frozenset())
            self.dead += 1
        self.titles.pop(doc_id, None)
        if self.dead > 64 and self.dead > len(self.units) // 2:
            self._compact()

    def _compact(self) -> None:
        """Drop tombstones and renumber (keeps memory flat under repeated re-uploads)."""
        live = [(d, p, t) for d, p, t in self.units if p]
        self.units, self.by_doc, self.postings, self.dead = [], defaultdict(list), defaultdict(set), 0
        for d, p, t in live:
            i = len(self.units)
            self.units.append((d, p, t))
            self.by_doc[d].append(i)
            for tok in t:
                self.postings[tok].add(i)

    def search(self, query: str, k: int = 6) -> list[Chunk]:
        q = tokens(query)
        if not q:
            return []
        hits: dict[int, int] = defaultdict(int)
        for t in q:
            for i in self.postings.get(t, ()):
                hits[i] += 1
        ranked = sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return [Chunk(self.titles.get(self.units[i][0], self.units[i][0]), self.units[i][1], round(n / len(q), 3))
                for i, n in ranked]


def _valid_doc(d: object) -> bool:
    return isinstance(d, dict) and isinstance(d.get("title"), str) and isinstance(d.get("text"), str)


def _valid_persona(p: object) -> bool:
    return (isinstance(p, dict) and isinstance(p.get("label"), str) and isinstance(p.get("memories"), list)
            and all(isinstance(m, str) for m in p["memories"]))


class BrainState:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.default_personas = copy.deepcopy(sd.PERSONAS)
        self._dirty = threading.Event()
        self._timer: threading.Timer | None = None
        self._graph_cache: tuple[tuple, Graph] | None = None
        self._clear()
        self.load()
        atexit.register(self.flush)

    def _clear(self) -> None:
        self.docs: dict[str, dict] = {}
        self.personas: dict[str, dict] = copy.deepcopy(self.default_personas)
        self.sample_loaded = False
        self.edges: list[str] = []
        self._edge_set: set[str] = set()
        self.stats = {"questions": 0}
        self.version = 0
        self.index = LocalIndex()
        self._graph_cache = None

    # ---- persistence ------------------------------------------------------------
    def load(self) -> None:
        try:
            if not self.path.exists():
                return
            data = json.loads(self.path.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:  # unreadable/corrupt file should never stop the app
            log.warning("state load skipped: %s", e)
            return
        if not isinstance(data, dict):
            log.warning("state load skipped: top level is %s", type(data).__name__)
            return
        with self.lock:
            docs = data.get("docs")
            for doc_id, d in (docs.items() if isinstance(docs, dict) else ()):
                if isinstance(doc_id, str) and _valid_doc(d):
                    self._put_doc(doc_id, d)
            personas = data.get("personas")
            for k, p in (personas.items() if isinstance(personas, dict) else ()):
                if isinstance(k, str) and _valid_persona(p):
                    self.personas[k] = {"label": p["label"], "memories": list(p["memories"])}
            self.sample_loaded = data.get("sample") is True
            edges = data.get("edges")
            if isinstance(edges, list):
                self._add_edges_unlocked([e for e in edges if isinstance(e, str)])
            stats = data.get("stats")
            if isinstance(stats, dict) and isinstance(stats.get("questions"), int) and stats["questions"] >= 0:
                self.stats["questions"] = stats["questions"]

    def flush(self) -> None:
        """Write now (atomic). Safe to call any time; no-op when clean."""
        with self.lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if not self._dirty.is_set():
                return
            self._dirty.clear()
            payload = {"docs": self.docs, "personas": self.personas, "sample": self.sample_loaded,
                       "edges": self.edges, "stats": self.stats}
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".state-", suffix=".json")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False)
                os.replace(tmp, self.path)  # atomic: never leaves a half-written file
            except Exception as e:
                log.warning("state save skipped: %s", e)

    def _touch(self, now: bool = False) -> None:
        self._dirty.set()
        if now:
            self.flush()
        elif self._timer is None:
            self._timer = threading.Timer(SAVE_DELAY_S, self.flush)
            self._timer.daemon = True
            self._timer.start()

    # ---- mutations ------------------------------------------------------------------
    def _put_doc(self, doc_id: str, doc: dict) -> None:
        self.docs[doc_id] = doc
        self.index.add(doc_id, doc["title"], doc["text"])

    def add_doc(self, doc_id: str, title: str, text: str, doc_type: str, source: str | None = None) -> None:
        with self.lock:
            self._put_doc(doc_id, {"title": title, "type": doc_type, "text": text, **({"source": source} if source else {})})
            self.version += 1
            self._touch()  # debounced: bulk uploads write the file once, not once per document

    def _add_edges_unlocked(self, edges: list[str]) -> int:
        added = 0
        for e in edges:
            if e not in self._edge_set:
                self._edge_set.add(e)
                self.edges.append(e)
                added += 1
        return added

    def add_edges(self, edges: list[str]) -> int:
        # discovered edges don't bump `version`: they come *from* answers and must not invalidate the cache
        with self.lock:
            added = self._add_edges_unlocked(edges)
            if added:
                self._touch()
            return added

    def set_persona(self, key: str, label: str, memories: list[str]) -> None:
        with self.lock:
            self.personas[key] = {"label": label, "memories": memories}
            self.version += 1
            self._touch(now=True)

    def add_memory(self, key: str, text: str) -> list[str]:
        with self.lock:
            p = self.personas.setdefault(key, {"label": key, "memories": []})
            if text not in p["memories"]:
                p["memories"].append(text)
            self.version += 1
            self._touch(now=True)
            return list(p["memories"])

    def count_question(self) -> None:
        with self.lock:
            self.stats["questions"] += 1
            self._touch()

    def reset(self) -> None:
        with self.lock:
            self._clear()
            self.version += 1
            self._touch(now=True)

    # ---- reads ----------------------------------------------------------------------
    def memories(self, persona: str | None) -> list[str]:
        if not persona:
            return []
        with self.lock:
            p = self.personas.get(persona)
            return list(p["memories"]) if p else []

    def all_edges(self) -> list[str]:
        with self.lock:
            edges = list(self.edges)
            if self.sample_loaded:
                edges += [e for e in manifest_edges(sd.MANIFEST_GRAPH) if e not in self._edge_set]
            return edges

    def graph(self) -> Graph:
        """Graph over all known edges, rebuilt only when the edge set changes."""
        with self.lock:
            key = (len(self.edges), self.sample_loaded, self.version)
            if self._graph_cache and self._graph_cache[0] == key:
                return self._graph_cache[1]
            g = Graph(self.all_edges())
            self._graph_cache = (key, g)
            return g


state = BrainState(settings.state_file)
