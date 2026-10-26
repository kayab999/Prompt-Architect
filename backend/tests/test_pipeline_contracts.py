"""Contract tests for prompt pipeline (architect mocked only)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.kayab_pipeline import PromptRefinementPipeline
from app.mcp_adapter import _build_architect, run_refinement
from app.ollama_architect import OllamaArchitect, _extract_models, _model_id_from_entry
from app.prompt_refinement import PromptLinter
from app.services import MaskService, SpecValidator


def test_mask_sanitize_contract():
    mask = MaskService()
    result = mask.sanitize(
        {"raw_text": "<think>secret</think>Hello user@example.com"}
    )
    assert "secret" not in result["clean_text"]
    assert "[REDACTED_EMAIL]" in result["clean_text"]
    assert result["metadata"]["think_tags_removed"] == 1


def test_spec_get_default():
    validator = SpecValidator()
    spec = validator.get_spec()
    assert "required_fields" in spec
    result = validator.validate({"raw_text": "context task format"}, spec)
    assert result.schema_valid is True


def test_build_architect_ollama():
    arch = _build_architect("tinyllama:latest")
    assert isinstance(arch, OllamaArchitect)


def test_model_id_from_entry_variants():
    class Obj:
        model = "qwen3:8b"

    assert _model_id_from_entry(Obj()) == "qwen3:8b"
    assert _model_id_from_entry({"name": "llama3.2:latest"}) == "llama3.2:latest"
    assert _model_id_from_entry({"model": "x:latest"}) == "x:latest"


def test_extract_models_from_list_like():
    class Model:
        def __init__(self, model):
            self.model = model

    class Resp:
        models = [Model("a:latest"), Model("b:latest")]

    assert _extract_models(Resp()) == ["a:latest", "b:latest"]
    assert _extract_models({"models": [{"model": "c:1"}]}) == ["c:1"]


@pytest.mark.asyncio
async def test_run_refinement_with_mocked_architect(monkeypatch):
    mock_arch = MagicMock()
    mock_arch.generate = AsyncMock(
        return_value={
            "raw_text": (
                "<Context>Project background and constraints go here.</Context>\n"
                "<Task>Produce a clear actionable summary for engineers.</Task>\n"
                "<Format>Markdown with bullet points only.</Format>"
            ),
            "token_usage": {"prompt": 5, "completion": 15, "total": 20},
            "error": None,
        }
    )

    monkeypatch.setattr(
        "app.mcp_adapter._build_architect", lambda *a, **k: mock_arch
    )

    result = await run_refinement(
        user_input="please write a short summary prompt",
        model="mock-model",
        flavor="technical",
        max_iterations=2,
    )

    assert result["success"] is True
    assert "Context" in result["response"] or "summary" in result["response"].lower()
    assert mock_arch.generate.called
    assert result["full_trace"]["success_gate"]["passed"] is True


def test_pipeline_empty_input():
    arch = MagicMock()
    arch.generate = AsyncMock()
    pipeline = PromptRefinementPipeline(
        arch, PromptLinter(), SpecValidator(), MaskService(), {"max_iterations": 1}
    )
    result = asyncio.run(pipeline.process(""))
    assert result["success_gate"]["passed"] is False
    assert not arch.generate.called
