"""All runtime configuration, read once from the environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()  # also honour a .env in the working directory


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(int(default))).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    hydra_key: str = os.getenv("HYDRA_DB_API_KEY", "")
    database: str = os.getenv("HYDRA_DATABASE", "whybot")
    shared_collection: str = os.getenv("HYDRA_COLLECTION", "company_knowledge")
    force_mock: bool = _bool("MOCK_MODE")

    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    openai_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    # Any OpenAI-compatible endpoint: Groq, Google Gemini, Ollama/LM Studio (local, no key), OpenRouter…
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "")
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "700"))
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "20"))
    # Free LLM tiers are rate-limited by tokens/minute: cap the context we send per answer.
    llm_context_chars: int = int(os.getenv("LLM_CONTEXT_CHARS", "6000"))

    state_file: Path = Path(os.getenv("STATE_FILE", str(BACKEND_DIR / "brain_state.json")))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "20"))
    max_doc_chars: int = int(os.getenv("MAX_DOC_CHARS", "300000"))
    fetch_timeout_s: float = float(os.getenv("FETCH_TIMEOUT_S", "20"))
    cache_ttl_s: int = int(os.getenv("CACHE_TTL_S", "600"))
    max_hops: int = int(os.getenv("MAX_HOPS", "3"))
    # Public deployment guardrails (see whybot/api/guard.py)
    public_mode: bool = _bool("PUBLIC_MODE")
    admin_token: str = os.getenv("ADMIN_TOKEN", "")
    # How many proxies append to X-Forwarded-For in front of the engine (Render: 1, verified live; the Next.js proxy does not append).
    # The visitor's real address is that many entries from the RIGHT; anything left of it is client-forgeable.
    trusted_proxy_hops: int = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))
    rate_ai_per_min: int = int(os.getenv("RATE_AI_PER_MIN", "12"))
    rate_ingest_per_hour: int = int(os.getenv("RATE_INGEST_PER_HOUR", "20"))
    auto_sample: bool = _bool("AUTO_SAMPLE")
    cors_origins: tuple[str, ...] = tuple(os.getenv("CORS_ORIGINS", "*").split(","))

    @property
    def mock(self) -> bool:
        """Offline mode: no HydraDB key, or explicitly forced for stage safety."""
        return self.force_mock or not self.hydra_key

    @property
    def mode(self) -> str:
        return "mock" if self.mock else "hydradb"


settings = Settings()
