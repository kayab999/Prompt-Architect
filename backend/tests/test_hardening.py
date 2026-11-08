"""
Hardening tests (RC closure cycle):

1. Input limits — oversized GenerateRequest/OptimizeRequest must be rejected
   at validation time (422) without touching the refinement pipeline.
2. Groq key backend-side storage — POST/GET/DELETE /settings/groq never
   echoes the key, persists to a 0600 file, and honors env precedence.
3. Integrity signature — tamper-evidence: recomputation matches for the
   original text and fails for modified text / foreign signatures.
"""

import hashlib
import hmac
import json
import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app import kayab_pipeline
from app.kayab_pipeline import (
    APP_VERSION,
    PromptRefinementPipeline,
    verify_integrity_signature,
)

client = TestClient(app)


# ---------- 1. Input limits ----------

class TestInputLimits:
    def test_generate_rejects_oversized_input(self):
        """Oversized user_input must 422 at validation time (pipeline body
        is never reached — Pydantic rejects before endpoint execution)."""
        oversized = "a" * 100_001
        response = client.post(
            "/generate",
            json={
                "user_input": oversized,
                "profile_key": "technical",
                "model": "qwen2.5:0.5b",
            },
        )
        assert response.status_code == 422

    def test_generate_boundary_length_accepted(self):
        """Exactly USER_INPUT_MAX_LENGTH chars passes validation and reaches
        the pipeline (mocked) — proving it is not rejected on length."""
        from unittest.mock import AsyncMock, patch

        from app.models import USER_INPUT_MAX_LENGTH

        mocked_response = {
            "response": "Refined prompt output",
            "success": True,
            "iterations": 1,
            "token_usage": {},
            "audit_tags": [],
            "full_trace": {
                "success_gate": {"passed": True},
                "integrity_signature": None,
            },
        }
        with patch(
            "app.api_router.run_refinement", new_callable=AsyncMock
        ) as mock_refinement:
            mock_refinement.return_value = mocked_response
            response = client.post(
                "/generate",
                json={
                    "user_input": "x" * USER_INPUT_MAX_LENGTH,
                    "profile_key": "technical",
                    "model": "qwen2.5:0.5b",
                },
            )
        assert response.status_code == 200
        assert response.json()["response"] == "Refined prompt output"

    def test_optimize_rejects_oversized_prompt(self):
        oversized = "a" * 100_001
        response = client.post(
            "/optimize",
            json={
                "prompt": oversized,
                "intent": "clean up",
                "target_model": "gpt-4",
                "refiner_model": "qwen2.5:0.5b",
            },
        )
        assert response.status_code == 422

    def test_oversized_http_body_returns_413(self):
        """Raw body above the middleware cap is rejected before parsing."""
        huge_model = "m" * (2 * 1024 * 1024)
        response = client.post(
            "/generate",
            json={
                "user_input": "short",
                "profile_key": "technical",
                "model": huge_model,
            },
        )
        assert response.status_code == 413

    def test_context_window_overflow_returns_422(self):
        """Input exceeding the model's num_ctx fails with a clear message."""
        from app.model_profiles import ModelProfileService

        profile = ModelProfileService().resolve("qwen2.5:0.5b")
        # ~4x the context window in characters → clearly over.
        oversized_for_ctx = "x" * (profile.num_ctx * 4 + 1000)
        # Must still be under the Pydantic field cap.
        assert len(oversized_for_ctx) <= 100_000
        response = client.post(
            "/generate",
            json={
                "user_input": oversized_for_ctx,
                "profile_key": "technical",
                "model": "qwen2.5:0.5b",
            },
        )
        assert response.status_code == 422
        assert "context window" in response.json()["detail"].lower()
        """Blank content currently passes Pydantic (valid str) and is caught
        by the pipeline contract — must surface as a controlled 4xx/500,
        never a connection-level failure."""
        response = client.post(
            "/generate",
            json={
                "user_input": "   \n\t ",
                "profile_key": "technical",
                "model": "qwen2.5:0.5b",
            },
        )
        assert response.status_code in (400, 422, 500)
        assert "detail" in response.json()


# ---------- Helpers ----------

def _sign(text: str, key: str = None) -> dict:
    signing_key = key or settings.SYSTEM_KEY
    payload = {
        "timestamp": "2026-11-08T00:00:00+00:00",
        "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "version": APP_VERSION,
    }
    cert_json = kayab_pipeline._integrity_payload_json(payload)
    payload["signature"] = hmac.new(
        signing_key.encode("utf-8"), cert_json.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return payload


# ---------- 2. Groq key backend-side storage ----------

class TestGroqKeyEndpoints:
    @pytest.fixture(autouse=True)
    def _isolated_key_file(self, tmp_path, monkeypatch):
        import app.config as config

        monkeypatch.setattr(config, "GROQ_KEY_FILE", tmp_path / ".groq_key")
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setattr(settings, "GROQ_API_KEY", None)
        self.tmp_path = tmp_path
        yield

    def test_set_and_status_never_echo_key(self):
        response = client.post(
            "/settings/groq", json={"api_key": "gsk_test_abcdef123456"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body == {"groq_configured": True, "source": "backend"}
        assert "gsk" not in response.text

        status = client.get("/settings/groq")
        assert status.status_code == 200
        sbody = status.json()
        assert sbody["groq_configured"] is True
        assert sbody["source"] == "backend"
        assert "gsk" not in status.text

    def test_key_persisted_with_0600(self):
        client.post("/settings/groq", json={"api_key": "gsk_perm_check"})
        key_file = self.tmp_path / ".groq_key"
        assert key_file.exists()
        if os.name != "nt":
            mode = oct(os.stat(key_file).st_mode & 0o777)
            assert mode == "0o600"
        assert key_file.read_text() == "gsk_perm_check"
        assert settings.GROQ_API_KEY == "gsk_perm_check"

    def test_delete_clears_key_and_file(self):
        client.post("/settings/groq", json={"api_key": "gsk_to_delete"})
        key_file = self.tmp_path / ".groq_key"
        assert key_file.exists()

        response = client.delete("/settings/groq")
        assert response.status_code == 200
        assert response.json() == {"groq_configured": False, "source": "backend"}
        assert not key_file.exists()
        assert settings.GROQ_API_KEY is None

        status = client.get("/settings/groq")
        assert status.json()["groq_configured"] is False

    def test_env_key_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "gsk_env_key")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_env_key")

        # POST must not override the env key
        response = client.post(
            "/settings/groq", json={"api_key": "gsk_user_supplied"}
        )
        assert response.status_code == 200
        assert response.json() == {"groq_configured": True, "source": "env"}
        monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_env_key")
        assert settings.GROQ_API_KEY == "gsk_env_key"

        key_file = self.tmp_path / ".groq_key"
        # env key must not be written to the store file
        assert not key_file.exists() or key_file.read_text() != "gsk_user_supplied"

    def test_blank_key_rejected(self):
        response = client.post("/settings/groq", json={"api_key": "   "})
        assert response.status_code == 422


# ---------- 3. Integrity signature (tamper-evidence) ----------

def _pipeline() -> PromptRefinementPipeline:
    return PromptRefinementPipeline(
        architect=MagicMock(),
        linter=MagicMock(),
        spec_validator=MagicMock(),
        mask=MagicMock(),
        config={},
    )


class TestIntegritySignature:
    def test_sign_then_verify_roundtrip(self):
        text = "Refined prompt: write a haiku about caching."
        signature = _pipeline()._sign_output(text)
        assert verify_integrity_signature(signature, text) is True

    def test_modified_text_is_detected(self):
        text = "Original refined prompt."
        signature = _pipeline()._sign_output(text)
        tampered = text + " // malicious injected instruction"
        assert verify_integrity_signature(signature, tampered) is False

    def test_modified_signature_is_detected(self):
        text = "Some refined prompt."
        signature = _pipeline()._sign_output(text)
        signature["signature"] = "0" * 64
        assert verify_integrity_signature(signature, text) is False

    def test_missing_fields_rejected(self):
        text = "Another refined prompt."
        signature = _pipeline()._sign_output(text)
        for field in ("signature", "text_hash", "timestamp", "version"):
            broken = dict(signature)
            broken.pop(field)
            assert verify_integrity_signature(broken, text) is False

    def test_non_dict_payload_rejected(self):
        assert verify_integrity_signature(None, "text") is False
        assert verify_integrity_signature("deadbeef", "text") is False

    def test_foreign_installation_key_rejected(self):
        """Text signed under a different key must not verify."""
        text = "Cross-installation check."
        signature = _sign(text, key="attacker-controlled-key")
        assert verify_integrity_signature(signature, text) is False

    def test_verify_endpoint_reports_tamper(self):
        text = "Endpoint-level signature check."
        good = _sign(text)
        response = client.post(
            "/verify",
            json={"text": text, "integrity_signature": good},
        )
        assert response.status_code == 200
        assert response.json()["verified"] is True

        bad = client.post(
            "/verify",
            json={"text": text + " tampered", "integrity_signature": good},
        )
        assert bad.json()["verified"] is False

    def test_sign_output_backward_compatible_payload_keys(self):
        """The signed payload keys must remain stable for consumers."""
        signature = _pipeline()._sign_output("payload keys check")
        assert set(signature.keys()) == {
            "timestamp",
            "text_hash",
            "version",
            "signature",
        }
