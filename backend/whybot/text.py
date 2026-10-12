"""Text utilities: cleaning, tokenizing, ids, decoding and extracting text from files and web pages."""
from __future__ import annotations

import html
import io
import re
import unicodedata

STOPWORDS = frozenset(
    "the a an to of we if is and or what who why how i on for should in it this that with be are was by "
    "as at from do does did can will would me my our you your they them their".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")
# zero-width + bidi controls + C0/C1 controls except \t \n \r
_INVISIBLE = re.compile(r"[​-‏‪-‮⁠-⁤﻿\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
MAX_UNIT = 1000  # max characters per retrieval unit


def clean(text: str | None) -> str:
    """Normalize user/file text: NFC, strip invisible/control characters, trim. None -> ''."""
    if not text:
        return ""
    return _INVISIBLE.sub("", unicodedata.normalize("NFC", str(text))).strip()


def tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower())) - STOPWORDS


def slug(text: str, limit: int = 60, default: str = "doc") -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_")
    return s[:limit].strip("_") or default


def decode_bytes(content: bytes) -> str:
    """Decode text files robustly: BOMs, UTF-16 without BOM, UTF-8, then Windows-1252."""
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return content.decode("utf-16", errors="replace")
    if content.startswith(b"\xef\xbb\xbf"):
        return content[3:].decode("utf-8", errors="replace")
    sample = content[:4000]
    if sample and sample.count(b"\x00") > len(sample) // 4:  # UTF-16 without BOM
        even_nulls = sample[0::2].count(b"\x00")
        return content.decode("utf-16-be" if even_nulls > len(sample) // 4 else "utf-16-le", errors="replace")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace")


def is_binary(content: bytes) -> bool:
    """Byte-level check before decoding: many control bytes (and not UTF-16) means binary."""
    if content.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf")):
        return False
    sample = content[:8000]
    if not sample:
        return False
    if sample.count(b"\x00") > len(sample) // 4:  # UTF-16 text
        return False
    ctrl = sum(1 for b in sample if b < 0x20 and b not in (9, 10, 13))
    return ctrl / len(sample) > 0.05


def looks_like_text(text: str) -> bool:
    """Reject binary garbage that slipped in as .txt: mostly printable characters required."""
    if not text:
        return False
    sample = text[:20000]
    printable = sum(1 for ch in sample if ch.isprintable() or ch in "\n\r\t")
    return printable / len(sample) >= 0.85 and sample.count("�") / len(sample) < 0.05


def extract_file_text(filename: str, content: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    return decode_bytes(content)


def html_to_text(raw: str) -> tuple[str, str]:
    """Return (title, readable text) from an HTML page."""
    m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
    title = clean(html.unescape(m.group(1))) if m else ""
    raw = re.sub(r"(?is)<(script|style|nav|footer|svg|noscript|header)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr)[^>]*>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    lines = (re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())
    return title, "\n".join(line for line in lines if len(line) > 2)


def _window(text: str, size: int = MAX_UNIT) -> list[str]:
    """Split long text on whitespace near `size`; hard-cut only words longer than `size`."""
    out, start, n = [], 0, len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            cut = text.rfind(" ", start + size // 2, end)
            if cut == -1:
                cut = text.rfind("\n", start + size // 2, end)
            end = cut if cut != -1 else end
        piece = text[start:end].strip()
        if piece:
            out.append(piece)
        start = end
    return out


def paragraphs(text: str) -> list[str]:
    """Retrieval units: blank-line paragraphs; long ones packed by line, then windowed."""
    out: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= MAX_UNIT:
            out.append(para)
            continue
        buf = ""
        for line in para.splitlines():
            if len(line) > MAX_UNIT:
                if buf.strip():
                    out.append(buf.strip())
                buf = ""
                out.extend(_window(line))
                continue
            if len(buf) + len(line) + 1 > MAX_UNIT and buf.strip():
                out.append(buf.strip())
                buf = ""
            buf += line + "\n"
        if buf.strip():
            out.append(buf.strip())
    return out
