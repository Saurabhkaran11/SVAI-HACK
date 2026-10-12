"""Domain objects shared across layers (plain dataclasses, no web concerns)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Chunk:
    title: str
    content: str
    score: float | None = None


@dataclass
class Retrieval:
    chunks: list[Chunk]
    paths: list[str]
    context: str
    mode: str  # "hydradb" | "mock" | "mock-fallback"


@dataclass
class Answer:
    answer: str
    chunks: list[Chunk] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    mode: str = "mock"
    latency_ms: int = 0
    features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
