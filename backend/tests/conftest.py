import os
import sys
import tempfile
from pathlib import Path

# Offline, isolated state for every test run — set before the app is imported.
os.environ["MOCK_MODE"] = "1"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_BASE_URL"] = ""
os.environ["STATE_FILE"] = str(Path(tempfile.mkdtemp()) / "state.json")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        c.post("/reset")
        yield c


@pytest.fixture()
def sample(client):
    client.post("/sample")
    return client
