"""Request/response contracts (also drive the OpenAPI docs at /docs)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---- requests ------------------------------------------------------------------
class AskIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, examples=["Who owns billing-service?"])
    persona: str | None = Field(None, max_length=80, examples=["new_hire"])
    graph: bool = True


class CompareIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    persona: str | None = Field(None, max_length=80)


class ImpactIn(BaseModel):
    change: str = Field(..., min_length=1, max_length=1000, examples=["Deprecate payments-api-v1 next month"])
    persona: str | None = Field(None, max_length=80)


class UrlIn(BaseModel):
    url: str = Field(..., min_length=8, max_length=2000, examples=["https://docs.hydradb.com/"])


class MemoryIn(BaseModel):
    persona: str = Field(..., min_length=1, max_length=80)
    text: str = Field(..., min_length=1, max_length=2000)


class PersonaIn(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)
    memories: list[str] = Field(default_factory=list, max_length=50)


class ProfileIn(BaseModel):
    name: str = Field("", max_length=120)
    role: str = Field("", max_length=120)
    team: str = Field("", max_length=120)
    about: str = Field("", max_length=2000)


# ---- responses -----------------------------------------------------------------
class ChunkOut(BaseModel):
    title: str
    content: str
    score: float | None = None


class AnswerOut(BaseModel):
    answer: str
    chunks: list[ChunkOut]
    paths: list[str]
    memories: list[str]
    mode: str
    latency_ms: int
    features: list[str]


class CompareOut(BaseModel):
    without_graph: AnswerOut
    with_graph: AnswerOut


class AffectedOut(BaseModel):
    name: str
    hop: int
    via: str


class RiskOut(BaseModel):
    score: int
    level: Literal["Low", "Medium", "High"]


class NotifyOut(BaseModel):
    to: str
    message: str


class ImpactOut(BaseModel):
    change: str
    seeds: list[str]
    affected: list[AffectedOut]
    owners: dict[str, list[str]]
    people: list[str]
    incidents: list[str]
    risk: RiskOut
    brief: str
    notify: list[NotifyOut]
    paths: list[str]
    chunks: list[ChunkOut]
    features: list[str]
    mode: str
    latency_ms: int


class IngestOut(BaseModel):
    ingested: list[str]


class InventoryRowOut(BaseModel):
    id: str
    title: str
    type: str
    status: str | None = None


class PersonaOut(BaseModel):
    label: str
    memories: list[str]


class HealthOut(BaseModel):
    ok: bool
    mode: str
    database: str
    docs: int
    sample_loaded: bool
    questions: int
    edges: int
    llm: str
    version: str
    cache: dict
    starter_questions: list[str]
    sample_questions: list[str]
    public: bool = False


class Ok(BaseModel):
    ok: bool = True
