import pytest
import os
import re
from unittest.mock import MagicMock
from app.services import MaskService, RuleLoader, RulesLoadError

# --- 1. MaskService Tests (Real PII Redaction) ---


def test_mask_service_pii_redaction():
    mask = MaskService()
    text = "Contact me at user@example.com or 555-555-0199. My SSN is 123-45-6789. Card: 4111 1111 1111 1111."

    redacted_text, redacted_types = mask.redact(text)

    assert "[REDACTED_EMAIL]" in redacted_text
    assert "[REDACTED_PHONE]" in redacted_text
    assert "[REDACTED_SSN]" in redacted_text
    assert "[REDACTED_CREDIT_CARD]" in redacted_text
    assert "email" in redacted_types
    assert "phone" in redacted_types
    assert "ssn" in redacted_types
    assert "credit_card" in redacted_types


def test_mask_service_sanitize_think_tags():
    mask = MaskService()
    text = "<think>I should be hidden</think>Final Output"
    draft = {"raw_text": text}

    result = mask.sanitize(draft)

    assert "I should be hidden" not in result["clean_text"]
    assert "Final Output" in result["clean_text"]
    assert result["metadata"]["think_tags_removed"] == 1


# --- 2. RuleLoader Tests (Fallo Ruidoso) ---


def test_rule_loader_critical_failure():
    # Attempting to load rules from non-existent flavor should still load base,
    # but base MUST exist.
    # We test with a dummy non-existent flavor to verify the fallback logic works if base is ok.
    rules = RuleLoader.load_rules("non_existent_flavor_for_testing")
    assert len(rules) > 0  # Should have at least base rules


def test_rule_loader_invalid_toml(tmp_path):
    # Mocking a corrupted base.toml
    bad_toml = tmp_path / "bad_rules.toml"
    bad_toml.write_text("this is not [toml] syntax")

    with pytest.raises(RulesLoadError):
        RuleLoader._load_toml(str(bad_toml))


# --- 3. CI Gates Verification (Internal Code Check) ---


def test_no_prints_in_backend():
    # Simple check that we haven't missed any prints in app
    # (Excludes this test file)
    backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")

    for path in [backend_path]:
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    with open(os.path.join(root, file), "r") as f:
                        content = f.read()
                        # Allow print in comments or logger-like names
                        # This regex is a bit naive but good for a gate check
                        for line in content.split("\n"):
                            if "print(" in line and not line.lstrip().startswith("#"):
                                assert False, (
                                    f"Print statement found in {os.path.join(root, file)}: {line}"
                                )


def test_security_keys_not_hardcoded():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "app", "config.py"
    )
    with open(config_path, "r") as f:
        content = f.read()
        assert "dev_key" not in content
        assert "default_key" not in content
