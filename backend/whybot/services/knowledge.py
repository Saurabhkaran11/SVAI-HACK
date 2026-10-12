"""Knowledge: ingest files, web pages and starter data; report inventory and indexing status."""
from __future__ import annotations

import ipaddress
import logging
import socket
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

from .. import hydra
from .. import sample_data as sd
from ..cache import answers
from ..config import settings
from ..state import state
from ..text import clean, extract_file_text, html_to_text, is_binary, looks_like_text, slug

log = logging.getLogger("whybot.knowledge")
ALLOWED_EXT = {".pdf", ".md", ".txt", ".csv", ".json", ".markdown"}
MAX_REDIRECTS = 4
MAX_PAGE_BYTES = 8 * 1024 * 1024


class IngestError(ValueError):
    """User-facing ingestion problem (bad type, too big, unreachable URL)."""


def _ensure_db_once() -> None:
    if not settings.mock and not getattr(_ensure_db_once, "done", False):
        try:
            hydra.ensure_database()
        except Exception as e:
            raise hydra.UpstreamError(f"HydraDB database isn't ready ({type(e).__name__})") from e
        _ensure_db_once.done = True  # type: ignore[attr-defined]


def _store(doc_id: str, title: str, text: str, doc_type: str, source: str | None = None) -> list[str]:
    text = clean(text)[: settings.max_doc_chars]
    if not text:
        raise IngestError(f"No readable text found in {title}.")
    if not looks_like_text(text):
        raise IngestError(f"{title} looks like a binary file, not text.")
    # Saved locally first: if HydraDB is down, answers still work from the local copy.
    state.add_doc(doc_id, title, text, doc_type, source)
    if settings.mock:
        return [doc_id]
    _ensure_db_once()
    body = f"Source: {source}\n\n{text}" if source else text
    return hydra.ingest_text(doc_id, title, body, doc_type)


def _safe_name(filename: str | None) -> str:
    name = clean(filename or "").replace("\\", "/").rsplit("/", 1)[-1]  # drop any path components
    return name[:160] or "upload.txt"


def upload(filename: str | None, content: bytes) -> list[str]:
    name = _safe_name(filename)
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise IngestError(f"Unsupported file type '{ext or name}'. Use PDF, Markdown, TXT, CSV or JSON.")
    if not content:
        raise IngestError(f"{name} is empty.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise IngestError(f"{name} is larger than {settings.max_upload_mb} MB.")
    if ext != ".pdf" and is_binary(content):
        raise IngestError(f"{name} looks like a binary file, not text.")
    try:
        text = extract_file_text(name, content)
    except Exception as e:
        raise IngestError(f"Couldn't read {name}: {type(e).__name__}") from e
    return _store(slug(name.rsplit(".", 1)[0], default="upload"), name, text, "upload")


# ---- URLs ------------------------------------------------------------------------------
def _check_url(url: str) -> None:
    """Allow only public http(s) hosts (SSRF guard) — this server may run inside a company network."""
    u = urlparse(url)
    if u.scheme not in {"http", "https"} or not u.hostname:
        raise IngestError("Enter a full http(s) URL.")
    try:
        infos = socket.getaddrinfo(u.hostname, None)
    except (socket.gaierror, UnicodeError) as e:
        raise IngestError(f"Couldn't resolve {u.hostname}.") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if not ip.is_global or ip.is_multicast:
            raise IngestError("That address is on a private network and can't be fetched.")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # we follow redirects ourselves, re-checking each hop
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def _fetch(url: str) -> str:
    for _ in range(MAX_REDIRECTS + 1):
        _check_url(url)
        req = urllib.request.Request(url, headers={"User-Agent": "WhyBot/2.0 (+company-brain)"})
        try:
            with _opener.open(req, timeout=settings.fetch_timeout_s) as resp:
                ctype = (resp.headers.get("Content-Type") or "text/html") if getattr(resp, "headers", None) else "text/html"
                if not any(t in ctype for t in ("text", "html", "xml", "json")):
                    raise IngestError(f"That URL is not a web page ({ctype.split(';')[0]}).")
                return resp.read(MAX_PAGE_BYTES).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers and e.headers.get("Location"):
                url = urljoin(url, e.headers["Location"])
                continue
            raise IngestError(f"The page returned HTTP {e.code}.") from e
    raise IngestError("Too many redirects.")


def ingest_url(url: str) -> list[str]:
    url = clean(url)
    _check_url(url)
    try:
        raw = _fetch(url)
    except IngestError:
        raise
    except Exception as e:
        raise IngestError(f"Couldn't fetch the page ({type(e).__name__}).") from e
    title, text = html_to_text(raw)
    return _store(slug(url.split("://", 1)[-1]), (title or url)[:120], text, "web", source=url)


# ---- sample / inventory / reset ----------------------------------------------------------------
def load_sample() -> list[str]:
    with state.lock:
        state.sample_loaded = True
    for doc_id, d in sd.SAMPLE_DOCS.items():
        state.add_doc(doc_id, d["title"], d["text"], d["type"])
    answers.clear()
    if settings.mock:
        return list(sd.SAMPLE_DOCS)
    _ensure_db_once()
    ids: list[str] = []
    for doc_id, d in sd.SAMPLE_DOCS.items():
        ids += hydra.ingest_text(doc_id, d["title"], d["text"], d["type"])
    ids += hydra.ingest_text(sd.MANIFEST_ID, "Service Dependency Manifest", sd.MANIFEST_TEXT, "manifest",
                             graph=sd.MANIFEST_GRAPH)
    return ids


def inventory() -> list[dict]:
    with state.lock:
        rows = [{"id": k, "title": d["title"], "type": d.get("type", "doc")} for k, d in state.docs.items()]
    if not settings.mock and rows:
        try:
            statuses = hydra.indexing_status([r["id"] for r in rows])
            for r in rows:
                r["status"] = statuses.get(r["id"], "unknown")
        except Exception as e:
            for r in rows:
                r["status"] = f"n/a ({type(e).__name__})"
    return rows


def reset() -> None:
    """Clear the local registry (HydraDB data is left untouched)."""
    state.reset()
    answers.clear()
