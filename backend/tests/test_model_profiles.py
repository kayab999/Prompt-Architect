"""Model profile resolution + profile-aware pipeline contracts."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.kayab_pipeline import PromptRefinementPipeline
from app.mcp_adapter import _build_architect, run_refinement
from app.model_profiles import ModelProfileService
from app.prompt_refinement import PromptLinter
from app.services import MaskService, SpecValidator

SERVICE = ModelProfileService()

GOOD_OUTPUT = (
    "<Context>Project background and constraints go here.</Context>\n"
    "<Task>Produce a clear actionable summary for engineers.</Task>\n"
    "<Format>Markdown with bullet points only.</Format>"
)


def test_family_detection_by_pattern():
    assert (
        SERVICE.resolve("deepseek-r1-distill-qwen-7b-q4_k_m:latest").family
        == "deepseek_r1"
    )
    assert SERVICE.resolve("qwen2.5-coder:3b").family == "qwen25_coder"
    assert SERVICE.resolve("qwen2.5:0.5b").family == "qwen25"
    assert SERVICE.resolve("qwen3:8b").family == "qwen3"
    assert SERVICE.resolve("smollm2-1.7b:latest").family == "smollm2"
    assert SERVICE.resolve("synapse-bonsai-8b:latest").family == "bonsai"
    assert (
        SERVICE.resolve("prism-ml_bonsai-8b-unpacked-q2_k:latest").family == "bonsai"
    )
    assert SERVICE.resolve("minicpm5-fable5-q4:latest").family == "fable"
    assert SERVICE.resolve("synapse-deepseek-local:latest").family == "deepseek_ft"
    assert SERVICE.resolve("totally-unknown-model:1b").family == "generic"


def test_deepseek_r1_matches_official_card():
    p = SERVICE.resolve("deepseek-r1:7b")
    assert p.temperature == 0.6
    assert p.top_p == 0.95
    assert p.use_system_role is False
    assert p.experimental is False
    assert any("think" in q.lower() for q in p.quirks)


def test_experimental_flag_for_local_finetunes():
    for mid in (
        "synapse-bonsai-8b:latest",
        "prism-ml_bonsai-8b-unpacked-q2_k:latest",
        "synapse-deepseek-local:latest",
        "minicpm5-fable5-q4:latest",
    ):
        assert SERVICE.resolve(mid).experimental is True, mid


def test_smollm2_low_temperature():
    p = SERVICE.resolve("smollm2-1.7b:latest")
    assert p.temperature == 0.2
    assert p.top_p == 0.9


def test_ollama_options_shape():
    opts = SERVICE.resolve("qwen3:8b").ollama_options()
    assert opts["temperature"] == 0.7
    assert opts["top_k"] == 20
    assert "num_ctx" in opts
    assert "num_predict" in opts


def test_groq_options_shape():
    opts = SERVICE.resolve("qwen2.5-coder:7b").groq_options()
    assert opts["temperature"] == 0.7
    assert opts["max_tokens"] > 0


def test_clamp_on_low_ram_machine(monkeypatch):
    """6 GB-class machines: KV cache options must be capped or Ollama
    refuses the model load entirely (HTTP 500 'unable to load model')."""
    import psutil

    class FakeVM:
        total = 6 * 1024**3

    monkeypatch.setattr(psutil, "virtual_memory", lambda: FakeVM())
    p = SERVICE.resolve("qwen3:8b")
    assert p.num_ctx == 2048
    assert p.num_predict == 1024


def test_no_clamp_on_large_ram_machine(monkeypatch):
    import psutil

    class FakeVM:
        total = 32 * 1024**3

    monkeypatch.setattr(psutil, "virtual_memory", lambda: FakeVM())
    p = SERVICE.resolve("deepseek-r1:7b")
    assert p.num_ctx == 4096  # YAML default preserved
    assert p.num_predict == 4096  # R1 family value preserved


def test_build_architect_groq_by_prefix():
    from app.groq_architect import GroqArchitect

    arch = _build_architect("openai/gpt-oss-120b", "test-key")
    assert isinstance(arch, GroqArchitect)


def test_pipeline_uses_system_role_for_qwen3():
    captured = {}

    async def fake_generate(context, *, system="", options=None):
        captured["system"] = system
        captured["options"] = options
        return {
            "raw_text": GOOD_OUTPUT,
            "token_usage": {"prompt": 5, "completion": 15, "total": 20},
            "error": None,
        }

    arch = MagicMock()
    arch.generate = fake_generate
    pipeline = PromptRefinementPipeline(
        arch,
        PromptLinter(),
        SpecValidator(),
        MaskService(),
        {"max_iterations": 1, "model_profile": SERVICE.resolve("qwen3:8b")},
    )
    result = asyncio.run(pipeline.process("write a summary prompt"))

    assert result["success_gate"]["passed"] is True
    assert "Prompt Architect" in captured["system"]
    assert "/no_think" in captured["system"]
    assert captured["options"]["top_k"] == 20


def test_pipeline_embeds_system_for_deepseek_r1():
    captured = {}

    async def fake_generate(context, *, system="", options=None):
        captured["context"] = context
        captured["system"] = system
        return {
            "raw_text": GOOD_OUTPUT,
            "token_usage": {"prompt": 5, "completion": 15, "total": 20},
            "error": None,
        }

    arch = MagicMock()
    arch.generate = fake_generate
    pipeline = PromptRefinementPipeline(
        arch,
        PromptLinter(),
        SpecValidator(),
        MaskService(),
        {
            "max_iterations": 1,
            "model_profile": SERVICE.resolve("deepseek-r1:1.5b"),
            "rules": [
                {
                    "id": "R006_MODEL_DECLARED_SUCCESS",
                    "severity": "HIGH",
                    "description": "Model should not claim success in the output text",
                    "check_type": "regex",
                    "pattern": "(?i)(i have succeeded|here is the refined)",
                }
            ],
        },
    )
    result = asyncio.run(pipeline.process("write a summary prompt"))

    assert result["success_gate"]["passed"] is True
    assert captured["system"] == ""  # R1 family: no system role
    assert "Prompt Architect" in captured["context"]
    assert "Begin your reply with <think>" in captured["context"]


def test_pipeline_generic_profile_is_backward_compatible():
    captured = {}

    async def fake_generate(context, *, system="", options=None):
        captured["context"] = context
        captured["system"] = system
        captured["options"] = options
        return {
            "raw_text": GOOD_OUTPUT,
            "token_usage": {"prompt": 5, "completion": 15, "total": 20},
            "error": None,
        }

    arch = MagicMock()
    arch.generate = fake_generate
    pipeline = PromptRefinementPipeline(
        arch, PromptLinter(), SpecValidator(), MaskService(), {"max_iterations": 1}
    )
    result = asyncio.run(pipeline.process("write a summary prompt"))

    assert result["success_gate"]["passed"] is True
    # No profile → base template still goes via the system role, no sampling
    # options injected (pre-profiles behavior).
    assert "Prompt Architect" in captured["system"]
    assert captured["options"] is None


def test_flavor_resolution_maps_unknown_flavors():
    from app.mcp_adapter import _resolve_flavor

    assert _resolve_flavor("technical") == "technical"
    assert _resolve_flavor("creative") == "creative"
    # Persona keys / UI intents are not rule flavors → mapped to technical
    assert _resolve_flavor("prompt_engineer") == "technical"
    assert _resolve_flavor("senior_dev") == "technical"
    assert _resolve_flavor("concise") == "technical"


@pytest.mark.asyncio
async def test_run_refinement_carries_rules_and_generic_profile(monkeypatch):
    mock_arch = MagicMock()
    mock_arch.generate = AsyncMock(
        return_value={
            "raw_text": GOOD_OUTPUT,
            "token_usage": {"prompt": 5, "completion": 15, "total": 20},
            "error": None,
        }
    )
    monkeypatch.setattr("app.mcp_adapter._build_architect", lambda *a, **k: mock_arch)

    result = await run_refinement(
        user_input="please write a short summary prompt",
        model="mock-model",
        flavor="technical",
        max_iterations=2,
    )

    assert result["success"] is True
    assert any(tag.startswith("rules_") for tag in result["audit_tags"])
    assert "experimental_model" not in result["audit_tags"]
