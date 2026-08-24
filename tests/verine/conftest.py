import os
import sys
import tempfile
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("VERINE_VAULT_KEY", "test-vault-key-do-not-use-in-prod")

from fastapi.testclient import TestClient  # noqa: E402

from verine.api.app import create_app  # noqa: E402
from verine.api.live_service import get_live_service  # noqa: E402


class MockLLMTransport(httpx.MockTransport):
    """Simulates an OpenAI-compatible provider: /models and /chat/completions."""

    def __init__(self, api_key_required: str | None = "valid-key"):
        self.api_key_required = api_key_required
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "") or request.headers.get("x-api-key", "")
        if self.api_key_required and self.api_key_required not in auth:
            return httpx.Response(401, json={"error": "invalid key"})
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [
                {"id": "demo/model-a", "name": "Demo Model A", "context_length": 128000,
                 "pricing": {"prompt": "0.000001", "completion": "0.000002"}},
            ]})
        if request.url.path.endswith("/chat/completions"):
            # Return a cited IncidentSummary using an evidence id from the prompt.
            import json
            body = json.loads(request.content)
            prompt = body["messages"][-1]["content"]
            ev_id = ""
            for token in prompt.split('"'):
                if token.startswith("ev_") or token.startswith("evidence_"):
                    ev_id = token
                    break
            content = json.dumps({
                "title": "Possible payment capability degradation",
                "what_was_observed": [{"claim": "Provider reports elevated latency.",
                                       "evidence_ids": [ev_id] if ev_id else []}],
                "what_is_inferred": ["Signals may affect configured dependencies."],
                "what_is_simulated": ["Model projects a possible floor breach."],
                "unknowns": ["Actual internal asset exposure is unverified."],
                "alternative_explanations": ["Transient provider blip."],
                "evidence_ids": [ev_id] if ev_id else [],
                "confidence_status": "limited",
            })
            return httpx.Response(200, json={
                "model": body["model"],
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 80},
            })
        return httpx.Response(404, json={"error": "not found"})


@pytest.fixture()
def client(tmp_path):
    app = create_app(data_dir=tmp_path / "data")
    with TestClient(app) as c:
        get_live_service()._llm_transport = MockLLMTransport()
        yield c


@pytest.fixture()
def live(client):
    return get_live_service()
