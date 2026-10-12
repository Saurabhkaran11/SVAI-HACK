"""HydraDB adapter: the only module that talks to the HydraDB SDK."""
from __future__ import annotations

import io
import json
import logging
import time
from functools import lru_cache
from typing import Any, Callable

from .config import settings
from .models import Chunk

log = logging.getLogger("whybot.hydra")


class UpstreamError(RuntimeError):
    """HydraDB could not be reached or rejected the request (mapped to HTTP 503)."""


@lru_cache(maxsize=1)
def client():
    from hydra_db import HydraDB

    return HydraDB(token=settings.hydra_key)


def _retry(fn: Callable[[], Any], attempts: int = 2, delay: float = 0.5) -> Any:
    """Retry transient failures once; conflicts and validation errors surface immediately."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            name = type(e).__name__
            if i == attempts - 1 or name in {"ConflictError", "BadRequestError", "UnprocessableEntityError"}:
                raise UpstreamError(f"HydraDB request failed ({name})") from e
            log.warning("HydraDB call failed (%s), retrying", name)
            time.sleep(delay * (i + 1))


def _f(obj: Any, key: str, default: Any = "") -> Any:
    if obj is None:
        return default
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def _file(name: str, text: str):
    return (name, io.BytesIO(text.encode("utf-8")), "text/plain")


# ---- database ---------------------------------------------------------------
def ensure_database(timeout_s: int = 180) -> None:
    from hydra_db.errors import ConflictError

    c = client()
    try:
        c.databases.create(database=settings.database)
        log.info("created database %s", settings.database)
    except ConflictError:
        pass
    start = time.time()
    while time.time() - start < timeout_s:
        if c.databases.status(database=settings.database).data.infra.ready_for_ingestion:
            return
        time.sleep(3)
    raise TimeoutError("HydraDB database was not ready in time")


# ---- ingestion --------------------------------------------------------------
def ingest_text(doc_id: str, title: str, text: str, doc_type: str = "doc", graph: dict | None = None) -> list[str]:
    kwargs: dict[str, Any] = dict(
        database=settings.database, collection=settings.shared_collection, type="knowledge",
        documents=[_file(f"{doc_id}.md", text)],
        # Live API (v2.0.1) rejects a top-level "title"; it belongs in additional_metadata.
        document_metadata=json.dumps([{"id": doc_id, "additional_metadata": {"title": title, "document_type": doc_type}}]),
        upsert="true",
    )
    if graph:
        kwargs["graph_payload"] = json.dumps({doc_id: graph})
    res = _retry(lambda: client().context.ingest(**kwargs))
    return [r.id for r in res.data.results]


def ingest_memories(collection: str, texts: list[str]) -> list[str]:
    if not texts:
        return []
    mems = [{"id": f"{collection}_{i}", "text": t, "infer": False} for i, t in enumerate(texts)]
    res = _retry(lambda: client().context.ingest(
        database=settings.database, collection=collection, type="memory", memories=json.dumps(mems), upsert="true"))
    return [r.id for r in res.data.results]


def indexing_status(ids: list[str], collection: str | None = None) -> dict[str, str]:
    if not ids:
        return {}
    st = client().context.status(database=settings.database, collection=collection or settings.shared_collection, ids=ids)
    return {i: s.indexing_status for i, s in zip(ids, st.data.statuses)}


def wait_for_indexing(ids: list[str], timeout_s: int = 600) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        states = indexing_status(ids)
        log.info("indexing: %s", states)
        if all(s == "completed" for s in states.values()):
            return
        if any(s in ("errored", "failed") for s in states.values()):
            raise RuntimeError(f"Indexing failed: {states}")
        time.sleep(5)
    raise TimeoutError("Indexing did not finish in time")


# ---- retrieval --------------------------------------------------------------
def query(question: str, persona: str | None, graph: bool) -> tuple[list[Chunk], list[str], str]:
    from hydra_db.helpers import build_string

    kwargs: dict[str, Any] = dict(
        database=settings.database, query=question, query_by="hybrid", graph_context=graph,
        query_apps=True, mode="thinking" if graph else "fast", max_results=10,
    )
    if persona:
        kwargs.update(type="all", collections={settings.shared_collection: 1.0, persona: 1.0})
    else:
        kwargs.update(type="knowledge", collection=settings.shared_collection)
    res = _retry(lambda: client().query(**kwargs))

    chunks = [Chunk(_f(c, "source_title") or _f(c, "id") or "source", _f(c, "chunk_content") or "",
                    _f(c, "relevancy_score", None)) for c in (res.data.chunks or [])]
    paths: list[str] = []
    if graph:
        gc = _f(res.data, "graph_context", None)
        for p in _f(gc, "query_paths", None) or []:
            for t in _f(p, "triplets", None) or []:
                s = _f(_f(t, "source", None), "name", "?")
                r = _f(_f(t, "relation", None), "canonical_predicate", "RELATED_TO")
                o = _f(_f(t, "target", None), "name", "?")
                paths.append(f"{s} --[{r}]--> {o}")
    return chunks, list(dict.fromkeys(paths)), build_string(res)
