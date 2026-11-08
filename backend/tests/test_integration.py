"""
Integration tests for the REST API endpoints.

Tests the full flow: Request → Router → MCP Adapter → Kayab Pipeline → Response.
Uses FastAPI TestClient for HTTP-level testing.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


class TestHealthEndpoints:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_status(self):
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["version"] == "1.0.2"


class TestModelsEndpoint:
    def test_list_models_returns_non_empty(self):
        """GET /models must never return an empty list."""
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0

    def test_list_models_contains_defaults(self):
        """Models list contains llama-named entries (Ollama or Groq)."""
        response = client.get("/models")
        data = response.json()
        models = data["models"]
        assert isinstance(models, list)
        assert len(models) > 0
        # Models are objects with id/provider
        ids = [
            (m.get("id") if isinstance(m, dict) else str(m)).lower() for m in models
        ]
        assert any("llama" in mid for mid in ids)


class TestProfilesEndpoint:
    def test_list_profiles(self):
        """GET /profiles returns profiles from profiles.yml."""
        response = client.get("/profiles")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert len(data["profiles"]) > 0
        profile = data["profiles"][0]
        assert "key" in profile
        assert "name" in profile
        assert "description" in profile


class TestLibraryEndpoint:
    def test_library_returns_list(self):
        """GET /library returns a list (may be empty if no prompts seeded)."""
        response = client.get("/library")
        assert response.status_code == 200
        data = response.json()
        assert "library" in data
        assert isinstance(data["library"], list)


class TestPresetsEndpoint:
    def test_presets_default_model(self):
        """GET /presets returns presets for default model."""
        response = client.get("/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert "model_id" in data
        assert data["model_id"] == "nano-banana-pro"

    def test_presets_specific_model(self):
        response = client.get("/presets?model_id=nano-banana-pro")
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "nano-banana-pro"


class TestCompileVisualEndpoint:
    def test_compile_visual(self):
        """POST /compile-visual compiles visual components."""
        response = client.post(
            "/compile-visual",
            json={
                "subject": "A modern cabin",
                "environment": "Forest",
                "lighting": "Morning sun",
                "camera": "24mm wide",
                "render_style": "Photorealistic",
                "text_content": "",
                "model_id": "nano-banana-pro",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "compiled_prompt" in data
        assert "A modern cabin" in data["compiled_prompt"]


class TestVitalSignsEndpoint:
    def test_vital_signs(self):
        """GET /vital-signs returns system metrics."""
        response = client.get("/vital-signs")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "ram_percent" in data
        assert "tier_id" in data
        assert "tier_name" in data


class TestGenerateEndpoint:
    @patch("app.api_router.run_refinement", new_callable=AsyncMock)
    def test_generate_success(self, mock_refinement):
        """POST /generate returns refined prompt with success flag."""
        mock_refinement.return_value = {
            "response": "Refined prompt output",
            "success": True,
            "iterations": 2,
            "token_usage": {"total": 500},
            "audit_tags": ["flavor_technical"],
            "full_trace": {
                "success_gate": {"passed": True},
                "integrity_signature": {"signature": "abc"},
            },
        }

        response = client.post(
            "/generate",
            json={
                "user_input": "Write a prompt about AI ethics",
                "profile_key": "technical",
                "model": "deepseek-r1:1.5b",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Refined prompt output"
        assert data["success"] is True
        assert data["iterations"] == 2
        assert data["integrity_signature"] == {"signature": "abc"}

    @patch("app.api_router.run_refinement", new_callable=AsyncMock)
    def test_generate_hard_fail_empty(self, mock_refinement):
        """Empty failed refinement returns 422."""
        mock_refinement.return_value = {
            "response": "",
            "success": False,
            "iterations": 1,
            "token_usage": {},
            "audit_tags": [],
            "full_trace": {
                "success_gate": {"passed": False, "reason": "Architect error: boom"},
                "reason": "Architect error: boom",
            },
        }

        response = client.post(
            "/generate",
            json={
                "user_input": "x",
                "profile_key": "technical",
                "model": "deepseek-r1:1.5b",
            },
        )
        assert response.status_code == 422
        assert "boom" in response.json()["detail"]

    @patch("app.api_router.run_refinement", new_callable=AsyncMock)
    def test_generate_soft_fail_partial(self, mock_refinement):
        """Failed gate with partial text still returns 200 + success=false."""
        mock_refinement.return_value = {
            "response": "Partial refined prompt",
            "success": False,
            "iterations": 3,
            "token_usage": {},
            "audit_tags": [],
            "full_trace": {
                "success_gate": {
                    "passed": False,
                    "reason": "Max iterations reached",
                },
                "reason": "Max iterations reached",
            },
        }

        response = client.post(
            "/generate",
            json={
                "user_input": "please improve this",
                "profile_key": "technical",
                "model": "deepseek-r1:1.5b",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["response"] == "Partial refined prompt"
        assert "Max iterations" in (data.get("reason") or "")


class TestMetadataValidation:
    """DT-008: Metadata JSON validation tests."""

    def test_parse_prompt_row_validates_metadata(self):
        """Corrupted metadata should be sanitized, not crash."""
        from app.db import parse_prompt_row

        row = {
            "id": 1,
            "name": "Test Prompt",
            "prompt": "Test content",
            "category": "General",
            "version": 1,
            "metadata": "not valid json{{{",
            "created_at": "2024-01-01",
        }

        result = parse_prompt_row(row)
        assert result["template"] == "Test Prompt"
        assert result["model_specifics"] == {}
        assert result["variables"] == []

    def test_parse_prompt_row_valid_metadata(self):
        """Valid metadata should pass through correctly."""
        import json
        from app.db import parse_prompt_row

        meta = json.dumps(
            {
                "model_specifics": {"temperature": 0.7},
                "variables": ["topic", "tone"],
                "guidelines": "Be concise",
                "timestamp": "2024-01-01",
                "signature": {
                    "input_variables": ["topic"],
                    "output_format": "text",
                    "constraints": [],
                },
            }
        )

        row = {
            "id": 1,
            "name": "Test Prompt",
            "prompt": "Test content",
            "category": "General",
            "version": 1,
            "metadata": meta,
            "created_at": "2024-01-01",
        }

        result = parse_prompt_row(row)
        assert result["model_specifics"] == {"temperature": 0.7}
        assert result["variables"] == ["topic", "tone"]
        assert result["guidelines"] == "Be concise"
