"""
Core services for prompt processing and validation.
Kept lean so importing MaskService / SpecValidator does not pull MicroVM code.
"""

from __future__ import annotations

import logging
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class RulesLoadError(Exception):
    """Raised when critical rules fail to load."""


class RuleLoader:
    """Loads and merges rule sets based on flavors."""

    BASE_PATH = str(Path(__file__).resolve().parent.parent / "rules")

    @staticmethod
    def get_safe_mode_rules() -> List[Dict]:
        return [
            {
                "id": "R004_INTEGRITY_SIGNED",
                "check_type": "post_flight",
                "severity": "CRITICAL",
                "action_on_fail": "ABORT_REFINEMENT",
            },
            {
                "id": "R002_SECTION_COMPLETENESS",
                "check_type": "spec_kit",
                "severity": "HIGH",
                "action_on_fail": "FAIL_SILENT",
            },
        ]

    @staticmethod
    def load_rules(flavor: str = "technical") -> List[Dict]:
        base_path = f"{RuleLoader.BASE_PATH}/base.toml"
        try:
            base_rules = RuleLoader._load_toml(base_path)
            if not base_rules:
                logger.warning(
                    "Base rules empty from %s. Entering Safe Mode.", base_path
                )
                return RuleLoader.get_safe_mode_rules()
        except RulesLoadError as exc:
            logger.warning("Failed to load base rules: %s. Entering Safe Mode.", exc)
            return RuleLoader.get_safe_mode_rules()

        flavor_path = f"{RuleLoader.BASE_PATH}/flavors/{flavor}.toml"
        flavor_rules: List[Dict] = []
        if os.path.exists(flavor_path):
            try:
                flavor_rules = RuleLoader._load_toml(flavor_path)
            except Exception as exc:
                logger.warning("Flavor '%s' failed to load: %s", flavor, exc)

        rule_map = {r["id"]: r for r in base_rules}
        for rule in flavor_rules:
            rule_map[rule["id"]] = rule
        return list(rule_map.values())

    @staticmethod
    def _load_toml(path: str) -> List[Dict]:
        try:
            with open(path, "rb") as handle:
                data = tomllib.load(handle)
                if not data or "rules" not in data:
                    return []
                return data.get("rules", [])
        except FileNotFoundError as exc:
            raise RulesLoadError(f"Rule file {path} not found.") from exc
        except Exception as exc:
            raise RulesLoadError(f"Error parsing rule file {path}: {exc}") from exc


class MaskService:
    """PII redaction and think-tag stripping."""

    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        "phone": r"\+?\d{1,3}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{3,4}[-.\s]?\d{4}",
    }

    def redact(self, text: str) -> tuple[str, list[str]]:
        redacted_text = text
        found_types: list[str] = []
        for pii_type, pattern in self.PII_PATTERNS.items():
            if re.search(pattern, redacted_text):
                found_types.append(pii_type)
                redacted_text = re.sub(
                    pattern, f"[REDACTED_{pii_type.upper()}]", redacted_text
                )
        return redacted_text, found_types

    def sanitize(self, draft: Dict) -> Dict:
        """
        Sanitize draft text.

        Contract: draft must be a mapping with key ``raw_text`` (str).
        Returns ``{"clean_text": str, "metadata": dict}``.
        """
        text = draft.get("raw_text", "") if isinstance(draft, dict) else ""
        clean_text, n_subs = re.subn(
            r"<think>.*?</think>", "", text, flags=re.DOTALL
        )
        # Truncated generations (num_predict cap mid-think) leave an unclosed
        # opener; without this fallback its content leaks into the output.
        clean_text, n_unclosed = re.subn(
            r"<think>.*\Z", "", clean_text, flags=re.DOTALL
        )
        clean_text = clean_text.strip()
        redacted_text, redacted_types = self.redact(clean_text)
        return {
            "clean_text": redacted_text,
            "metadata": {
                "think_tags_removed": n_subs + n_unclosed,
                "pii_redacted": len(redacted_types) > 0,
                "redacted_types": redacted_types,
                "sections_masked": [],
            },
        }


class SpecValidator:
    """Lightweight structural spec checks for refined prompts."""

    def __init__(self):
        self.specs = {
            "default": {
                "output_format": "json",
                "version": "1.0.0",
                "required_fields": ["context", "task", "format"],
            }
        }
        self._cache: Dict[str, Dict] = {}

    def get_spec(self, template_id: str = "default") -> Dict:
        if template_id in self._cache:
            return self._cache[template_id]
        spec = self.specs.get(template_id, self.specs["default"])
        self._cache[template_id] = spec
        return spec

    @dataclass
    class SpecResult:
        schema_valid: bool
        missing_fields: List[str]
        type_errors: List[str]

    def validate(self, draft: Dict, spec: Dict) -> SpecResult:
        text = (draft.get("raw_text", "") if isinstance(draft, dict) else "").lower()
        missing = [
            field for field in spec.get("required_fields", []) if field not in text
        ]
        return self.SpecResult(
            schema_valid=len(missing) == 0,
            missing_fields=missing,
            type_errors=[],
        )


__all__ = [
    "RulesLoadError",
    "RuleLoader",
    "MaskService",
    "SpecValidator",
]
