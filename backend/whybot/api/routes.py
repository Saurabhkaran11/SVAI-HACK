"""Routers grouped by feature. Handlers only translate HTTP <-> services."""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from .. import __version__, llm
from .. import sample_data as sd
from ..cache import answers
from ..config import settings
from ..services import ask as ask_svc
from ..services import impact as impact_svc
from ..services import knowledge, personas
from ..state import state
from . import schemas as s

# ---- system --------------------------------------------------------------------
system = APIRouter(tags=["System"])


@system.get("/health", response_model=s.HealthOut, summary="Engine status and counts")
def health():
    with state.lock:
        docs, sample, questions = len(state.docs), state.sample_loaded, state.stats["questions"]
    return {
        "ok": True, "mode": settings.mode, "database": settings.database, "docs": docs,
        "sample_loaded": sample, "questions": questions, "edges": len(state.all_edges()),
        "llm": llm.provider(), "version": __version__, "cache": answers.stats(),
        "starter_questions": sd.STARTER_QUESTIONS, "sample_questions": sd.SAMPLE_QUESTIONS,
    }


@system.get("/graph", summary="Every relationship the brain knows so far")
def graph():
    return {"edges": state.all_edges()}


@system.post("/reset", response_model=s.Ok, summary="Clear local registry (HydraDB data untouched)")
def reset():
    knowledge.reset()
    return {"ok": True}


# ---- ask & impact ----------------------------------------------------------------
brain = APIRouter(tags=["Ask & Blast Radius"])


@brain.post("/ask", response_model=s.AnswerOut, summary="Answer a question with graph + persona context")
def ask(body: s.AskIn):
    return ask_svc.ask(body.question, body.persona, body.graph).to_dict()


@brain.post("/compare", response_model=s.CompareOut, summary="Plain search vs graph answer, computed in parallel")
def compare(body: s.CompareIn):
    r = ask_svc.compare(body.question, body.persona)
    return {k: v.to_dict() for k, v in r.items()}


@brain.post("/impact", response_model=s.ImpactOut, summary="Blast radius of a planned change")
def impact(body: s.ImpactIn):
    return impact_svc.blast_radius(body.change, body.persona)


# ---- knowledge -----------------------------------------------------------------------
kb = APIRouter(tags=["Knowledge"])


@kb.post("/upload", response_model=s.IngestOut, summary="Ingest a file (PDF, MD, TXT, CSV, JSON)")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    return {"ingested": knowledge.upload(file.filename or "upload.txt", content)}


@kb.post("/url", response_model=s.IngestOut, summary="Ingest a public web page")
def url(body: s.UrlIn):
    return {"ingested": knowledge.ingest_url(body.url)}


@kb.post("/sample", response_model=s.IngestOut, summary="Load optional starter data")
def sample():
    return {"ingested": knowledge.load_sample()}


@kb.get("/inventory", response_model=list[s.InventoryRowOut], summary="Documents and indexing status")
def inventory():
    return knowledge.inventory()


# ---- personas ----------------------------------------------------------------------
people = APIRouter(tags=["Personas & Memory"])


@people.get("/personas", summary="Persona keys and labels")
def persona_labels():
    return personas.labels()


@people.get("/personas/full", response_model=dict[str, s.PersonaOut], summary="Personas with memories")
def persona_full():
    return personas.all_personas()


@people.post("/persona", summary="Create a persona")
def persona_create(body: s.PersonaIn):
    return {"key": personas.create(body.label, body.memories)}


@people.post("/memory", response_model=s.Ok, summary="Remember a fact for a persona")
def memory(body: s.MemoryIn):
    personas.remember(body.persona, body.text)
    return {"ok": True}


@people.post("/profile", summary="Save the signed-in user's profile as personal memory")
def profile(body: s.ProfileIn):
    return {"persona": personas.set_profile(body.name, body.role, body.team, body.about)}


ROUTERS = [system, brain, kb, people]
