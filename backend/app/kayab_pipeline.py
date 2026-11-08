"""
Prompt refinement pipeline (RC primary path).

SovereignCodePipeline remains as a public alias for API compatibility.
Firecracker/Tribunal is never constructed on this hot path.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import settings
from .prompt_refinement import AutoFixer, Diagnostic, PromptLinter

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.2"

# ---------- Integrity signing (local tamper-evidence) ----------
# The signature proves: (a) the text was not modified after signing at this
# installation (HMAC with the local system key + sha256 of the exact text).
# It does NOT prove authorship or origin against an attacker who also
# controls the machine. The UI must present it as such.


def _integrity_payload_json(payload: Dict[str, Any]) -> str:
    cert = {
        "timestamp": payload["timestamp"],
        "text_hash": payload["text_hash"],
        "version": payload["version"],
    }
    return json.dumps(cert, sort_keys=True)


def verify_integrity_signature(payload: Optional[Dict[str, Any]], text: str) -> bool:
    """
    True iff the payload is a well-formed signed record whose HMAC matches the
    given text under the current local system key, i.e. the text is bit-identical
    to what this installation signed.
    """
    if not isinstance(payload, dict):
        return False
    required = {"timestamp", "text_hash", "version", "signature"}
    if not required.issubset(payload.keys()):
        return False

    expected_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(str(payload["text_hash"]), expected_hash):
        return False

    recert_json = _integrity_payload_json(payload)
    key = (settings.SYSTEM_KEY or "").encode("utf-8")
    expected_sig = hmac.new(key, recert_json.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(payload["signature"]), expected_sig)

REFINE_SYSTEM_TEMPLATE = """You are Prompt Architect, a professional prompt engineer.
Refine the user's request into a clear, structured prompt optimized for an LLM.

Flavor: {flavor}
Rules:
- Prefer explicit Context, Task, and Format sections when useful.
- Remove filler and vague language.
- Do not include <think> or internal chain-of-thought tags.
- Output ONLY the refined prompt text, no preamble.

Diagnostics to address:
{diagnostics}
"""


class PromptRefinementPipeline:
    """
    Orchestrates: sanitize → lint/autofix → LLM refine → re-lint → mask → sign.
    """

    def __init__(
        self,
        architect: Any,
        linter: Any,
        spec_validator: Any,
        mask: Any,
        config: Dict[str, Any],
    ):
        self.architect = architect
        self.linter = linter if linter is not None else PromptLinter()
        self.spec_validator = spec_validator
        self.mask = mask
        self.config = config or {}
        self.max_iterations = int(self.config.get("max_iterations", 3))
        self.flavor = self.config.get("flavor", "technical")
        self.service_key = self.config.get("service_key") or settings.SYSTEM_KEY
        self.autofixer = AutoFixer()

    async def process(
        self,
        user_input: str,
        template_id: str = "default",
        requester: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return await self.run(
            user_intent=user_input,
            template_id=template_id,
            requester=requester or {},
        )

    async def run(
        self,
        user_intent: str,
        template_id: str = "default",
        requester: Optional[Dict[str, str]] = None,
        quest_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        del quest_id  # reserved for optional SQLog integration
        requester = requester or {}
        audit_tags: List[str] = [f"flavor_{self.flavor}", f"version_{APP_VERSION}"]

        profile = self.config.get("model_profile")
        rules = self.config.get("rules") or []
        governance = self._governance_text(rules)
        if rules:
            audit_tags.append(f"rules_{len(rules)}")
        if profile is not None and profile.experimental:
            audit_tags.append("experimental_model")

        if not user_intent or not str(user_intent).strip():
            return self._fail("Empty user input", audit_tags=audit_tags)

        # 1. Input sanitize
        sanitized = self.mask.sanitize({"raw_text": user_intent})
        working = sanitized.get("clean_text", "") or ""
        if sanitized.get("metadata", {}).get("pii_redacted"):
            audit_tags.append("input_pii_redacted")

        # 2. Deterministic lint + autofix on input
        diagnostics = self.linter.lint(working)
        working, applied_fixes = self.autofixer.fix(working, diagnostics)
        if applied_fixes:
            audit_tags.append(f"autofix_{'+'.join(applied_fixes)}")

        remaining = [
            d for d in self.linter.lint(working) if not d.fixable or d.severity == "error"
        ]

        token_usage_total = {"prompt": 0, "completion": 0, "total": 0}
        last_raw = working
        iterations_used = 0

        for iteration in range(1, self.max_iterations + 1):
            iterations_used = iteration
            diag_text = (
                "\n".join(f"- [{d.code}] {d.message}" for d in remaining)
                if remaining
                else "- None"
            )
            system = self._build_system_text(diag_text, governance)
            opts = profile.ollama_options() if profile is not None else None

            if profile is not None and not profile.use_system_role:
                # DeepSeek-R1 family: no system role — instructions go in the
                # user message (official model-card guidance).
                context = f"{system}\n\nUser request:\n{working}"
                draft = await self.architect.generate(context, options=opts)
            else:
                draft = await self.architect.generate(
                    working, system=system, options=opts
                )
            if draft.get("error"):
                logger.error("Architect error: %s", draft.get("error"))
                return self._fail(
                    f"Architect error: {draft.get('error')}",
                    audit_tags=audit_tags,
                    iterations=iterations_used,
                )

            last_raw = draft.get("raw_text") or ""
            usage = draft.get("token_usage") or {}
            for key in ("prompt", "completion", "total"):
                token_usage_total[key] = token_usage_total.get(key, 0) + int(
                    usage.get(key, 0) or 0
                )

            # Output sanitize
            out_sanitized = self.mask.sanitize({"raw_text": last_raw})
            candidate = out_sanitized.get("clean_text", "") or ""
            if out_sanitized.get("metadata", {}).get("think_tags_removed"):
                audit_tags.append("think_tags_stripped")
            if out_sanitized.get("metadata", {}).get("pii_redacted"):
                audit_tags.append("output_pii_redacted")

            # Deterministic fixes on model output
            out_diags = self.linter.lint(candidate)
            candidate, out_fixes = self.autofixer.fix(candidate, out_diags)
            if out_fixes:
                audit_tags.append(f"out_autofix_{'+'.join(out_fixes)}")

            # Governance regex rules on the model output
            rule_diags = self._apply_regex_rules(candidate, rules)
            blocked = [d for d in rule_diags if d.severity == "error"]
            advisory = [d for d in rule_diags if d.severity != "error"]

            remaining = [
                d
                for d in self.linter.lint(candidate)
                if d.code in ("S001", "S004") and d.severity == "error"
            ]
            remaining.extend(blocked)
            # Advisory rule hits steer the next iteration; they do not block.
            if advisory and iteration < self.max_iterations:
                remaining.extend(advisory)

            # Soft spec check
            if self.spec_validator is not None:
                spec = self.spec_validator.get_spec(template_id)
                spec_result = self.spec_validator.validate(
                    {"raw_text": candidate}, spec
                )
                if not spec_result.schema_valid and iteration < self.max_iterations:
                    remaining.append(
                        Diagnostic(
                            code="SPEC",
                            category="Spec",
                            message=f"Missing: {spec_result.missing_fields}",
                            severity="error",
                            fixable=False,
                        )
                    )
                    working = candidate
                    continue

            if not remaining or iteration == self.max_iterations:
                signature = self._sign_output(candidate)
                passed = True
                # Prefer success if we have non-empty cleaned output
                if not candidate.strip():
                    passed = False
                    return self._fail(
                        "Empty refined output",
                        audit_tags=audit_tags,
                        iterations=iterations_used,
                    )

                return {
                    "final_output": {
                        "rendered_prompt": candidate,
                        "token_usage": token_usage_total,
                    },
                    "success_gate": {
                        "passed": passed,
                        "iterations_used": iterations_used,
                    },
                    "integrity_signature": signature,
                    "audit_tags": list(dict.fromkeys(audit_tags)),
                    "requester": requester,
                    "control_log": [],
                }

            working = candidate

        return self._fail(
            "Max iterations reached without convergence",
            audit_tags=audit_tags,
            iterations=iterations_used,
            last_raw=last_raw,
        )

    def _governance_text(self, rules: List[Dict[str, Any]]) -> str:
        """Surface CRITICAL/HIGH governance rules as prompt guidance."""
        relevant = [
            r
            for r in rules
            if r.get("severity") in ("CRITICAL", "HIGH") and r.get("description")
        ][:8]
        if not relevant:
            return ""
        lines = "\n".join(f"- {r['description']}" for r in relevant)
        return f"Governance rules (must hold for the final output):\n{lines}"

    def _build_system_text(
        self, diag_text: str, governance: str
    ) -> str:
        """Compose the system/instruction text: base template + governance +
        model-family directives and quirks."""
        parts = [REFINE_SYSTEM_TEMPLATE.format(flavor=self.flavor, diagnostics=diag_text)]
        profile = self.config.get("model_profile")
        if governance:
            parts.append(governance.strip())
        if profile is not None:
            if profile.extra_system_directives:
                parts.append(profile.extra_system_directives.strip())
            if profile.quirks:
                quirks = "\n".join(f"- {q}" for q in profile.quirks)
                parts.append(f"Model quirks:\n{quirks}")
            if profile.experimental:
                parts.append(
                    "Note: this model is experimental; keep instructions explicit "
                    "and verify the result."
                )
        return "\n\n".join(parts)

    def _apply_regex_rules(
        self, text: str, rules: List[Dict[str, Any]]
    ) -> List[Diagnostic]:
        """Evaluate regex-type governance rules against candidate output.

        CRITICAL violations become error diagnostics (iterate); the rest are
        advisory guidance for the next pass.
        """
        diags: List[Diagnostic] = []
        for rule in rules:
            if rule.get("check_type") != "regex":
                continue
            pattern = rule.get("pattern")
            if not pattern:
                continue
            try:
                if re.search(pattern, text):
                    diags.append(
                        Diagnostic(
                            code=str(rule.get("id", "RULE")),
                            category="Rule",
                            message=str(
                                rule.get("description", "Governance rule violated")
                            ),
                            severity="error"
                            if rule.get("severity") == "CRITICAL"
                            else "warning",
                            fixable=False,
                        )
                    )
            except re.error as exc:
                logger.warning(
                    "Invalid governance pattern for %s: %s", rule.get("id"), exc
                )
        return diags

    def _sign_output(self, text: str) -> Dict[str, str]:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "version": APP_VERSION,
        }
        cert_json = _integrity_payload_json(payload)
        key = (self.service_key or settings.SYSTEM_KEY or "").encode("utf-8")
        payload["signature"] = hmac.new(
            key, cert_json.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return payload

    def _fail(
        self,
        reason: str,
        audit_tags: Optional[List[str]] = None,
        iterations: int = 0,
        last_raw: str = "",
    ) -> Dict[str, Any]:
        logger.warning("Pipeline failed: %s", reason)
        return {
            "final_output": {
                "rendered_prompt": last_raw or "",
                "token_usage": {},
            },
            "success_gate": {
                "passed": False,
                "iterations_used": iterations,
                "reason": reason,
            },
            "integrity_signature": None,
            "audit_tags": audit_tags or [],
            "control_log": [],
            "reason": reason,
        }


# Backward-compatible name used by mcp_adapter and tests
SovereignCodePipeline = PromptRefinementPipeline
