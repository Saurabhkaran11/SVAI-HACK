"""LLM layer: Claude, or any OpenAI-compatible provider (OpenAI, Groq, Gemini, Ollama, LM Studio…),
or a clean evidence summary when no LLM is configured."""
from __future__ import annotations

import logging
import re
from functools import lru_cache

from .config import settings

log = logging.getLogger("whybot.llm")

ANSWER_SYSTEM = (
    "You are WhyBot, a company brain. Answer ONLY from the provided context. "
    "Use graph relationships to connect services, owners, incidents and decisions. "
    "Tailor depth and format to the user's memories/persona. Cite sources by name in square brackets, e.g. [ADR-007]. "
    "Be concise: short bullets, max ~150 words. If context is insufficient, say so."
)
IMPACT_SYSTEM = (
    "You are WhyBot's change-impact analyst. Using ONLY the context, write a crisp markdown brief: "
    "**Verdict** (one line with the risk level), **What breaks** (bullets, cite sources in [brackets]), "
    "**Who to notify**, **Lessons from past incidents**, **Safe rollout checklist** (3-5 steps). Max ~220 words."
)
_ODD_CITES = re.compile(r"【[^】]{0,40}】")  # e.g. 【1†L13-L15】 from some open models
EMPTY = "I don't have anything on that yet. Add docs, notes or a URL to your brain and ask again."


@lru_cache(maxsize=1)
def _anthropic():
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_key, timeout=settings.llm_timeout_s)


@lru_cache(maxsize=1)
def _openai():
    from openai import OpenAI

    # Local servers (Ollama, LM Studio) accept any key; the SDK just needs a non-empty string.
    return OpenAI(api_key=settings.openai_key or "not-needed", base_url=settings.openai_base_url or None,
                  timeout=settings.llm_timeout_s)


def _openai_enabled() -> bool:
    return bool(settings.openai_key or settings.openai_base_url)


def provider() -> str:
    if settings.anthropic_key:
        return "claude"
    if not _openai_enabled():
        return "none"
    url = settings.openai_base_url.lower()
    for name in ("groq", "generativelanguage", "openrouter", "11434", "1234", "together", "mistral"):
        if name in url:
            return {"generativelanguage": "gemini", "11434": "ollama", "1234": "lm-studio"}.get(name, name)
    return "openai-compatible" if url else "openai"


def extractive(context: str) -> str:
    """No LLM configured: a tidy evidence summary grouped by source, plus key relationships."""
    if not context.strip():
        return EMPTY
    sources: dict[str, list[str]] = {}
    relations: list[str] = []
    facts: list[str] = []
    current = "Notes"
    section = "sources"
    for raw in context.splitlines():
        line = raw.strip().strip("-•* ").strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        low = line.lower()
        if low.startswith("graph relationships") or low.startswith("relationships"):
            section = "relations"
            continue
        if "--[" in line and "]-->" in line:
            relations.append(line)
            continue
        if low.startswith(("affected (hop", "owners:", "past incidents:", "computed risk:")):
            facts.append(line)
            continue
        if line.startswith("[") and line.endswith("]") and len(line) < 140:
            current, section = line.strip("[]"), "sources"
            continue
        if section == "sources" and len(sources.get(current, [])) < 3:
            sources.setdefault(current, []).append(line[:220])
    out = ["**Here's what your brain found**"]
    for title, lines in list(sources.items())[:4]:
        out.append(f"- **{title}** — " + " ".join(lines)[:300])
    if facts:
        out.append("\n**Impact facts**")
        out += [f"- {f}" for f in facts]
    if relations:
        out.append("\n**How it's connected**")
        out += [f"- {r.replace('--[', '→ ').replace(']-->', ' →')}" for r in relations[:6]]
    out.append("\n_Evidence summary. Add a free LLM (see backend/.env) for a written, cited answer._")
    return "\n".join(out)


def complete(system: str, user: str) -> str | None:
    try:
        if settings.anthropic_key:
            msg = _anthropic().messages.create(model=settings.anthropic_model, max_tokens=settings.llm_max_tokens,
                                               system=system, messages=[{"role": "user", "content": user}])
            return "".join(getattr(b, "text", "") for b in msg.content).strip()
        if _openai_enabled():
            r = _openai().chat.completions.create(model=settings.openai_model,
                                                  messages=[{"role": "system", "content": system},
                                                            {"role": "user", "content": user}])
            return (r.choices[0].message.content or "").strip()
    except Exception as e:
        log.warning("LLM call failed: %s", e)
        return f"(LLM unavailable: {type(e).__name__})"
    return None


def generate(system: str, question: str, context: str, memories: list[str]) -> str:
    if not context.strip():
        return EMPTY
    user = f"User memories:\n{chr(10).join(memories) or 'none'}\n\nContext:\n{context}\n\nQuestion: {question}"
    out = complete(system, user)
    if not out or not out.strip():
        return extractive(context)
    if out.startswith("(LLM unavailable"):
        return out + "\n\n" + extractive(context)
    return _ODD_CITES.sub("", out).replace(" \n", "\n").strip()
