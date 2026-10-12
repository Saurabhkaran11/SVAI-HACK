"""Personas & memory: roles, the signed-in user's profile, and 'remember this about me'."""
from __future__ import annotations

import hashlib
import logging

from .. import hydra
from ..config import settings
from ..state import state
from ..text import clean, slug

log = logging.getLogger("whybot.personas")


def _push(key: str, memories: list[str]) -> None:
    if settings.mock or not memories:
        return
    try:
        hydra.ingest_memories(key, memories)
    except Exception as e:  # memory sync failure shouldn't block the UI
        log.warning("memory sync for %s failed: %s", key, e)


def all_personas() -> dict[str, dict]:
    with state.lock:
        return {k: {"label": v["label"], "memories": list(v["memories"])} for k, v in state.personas.items()}


def labels() -> dict[str, str]:
    return {k: v["label"] for k, v in all_personas().items()}


def create(label: str, memories: list[str]) -> str:
    label = clean(label)
    if not label:
        raise ValueError("Give the persona a name.")
    key = slug(label, 40, "")
    with state.lock:
        existing = state.personas.get(key) if key else None
    if not key or key == "me" or (existing and existing["label"] != label):
        # symbol-only labels or clashes ("!!!" vs "???") get a stable, unique suffix
        key = f"{key or 'persona'}_{hashlib.sha1(label.encode()).hexdigest()[:6]}"
    mems = list(dict.fromkeys(m for m in (clean(x) for x in memories) if m))
    state.set_persona(key, label, mems)
    _push(key, mems)
    return key


def remember(persona: str, text: str) -> None:
    text, persona = clean(text), clean(persona)
    if not text:
        raise ValueError("Nothing to remember.")
    if not persona:
        raise ValueError("Choose a persona.")
    _push(persona, state.add_memory(persona, text))


def set_profile(name: str, role: str, team: str, about: str) -> str:
    name, role, team, about = clean(name), clean(role), clean(team), clean(about)
    mems = [m for m in (f"My name is {name}." if name else "", f"My role is {role}." if role else "",
                        f"I work on the {team} team." if team else "", about) if m]
    state.set_persona("me", f"Me ({name})" if name else "Me", mems)
    _push("me", mems)
    return "me"


def sync_all() -> None:
    for key, p in all_personas().items():
        _push(key, p["memories"])
