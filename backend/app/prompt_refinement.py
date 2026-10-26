"""
Prompt linter and deterministic autofixer (Mask Machine v2 static path).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple


@dataclass
class Diagnostic:
    code: str
    category: str
    message: str
    severity: str
    fixable: bool = False


class AutoFixer:
    """Applies deterministic fixes to prompts based on Diagnostic codes."""

    def __init__(self):
        self.fix_registry: Dict[str, Callable[[str], str]] = {
            "W002": self._fix_filler_words,
            "S002": self._fix_unclosed_tags,
        }

    def fix(self, prompt: str, diagnostics: List[Diagnostic]) -> Tuple[str, List[str]]:
        current_prompt = prompt
        applied_fixes: List[str] = []
        active_codes = {d.code for d in diagnostics if d.fixable}

        for code, fixer_func in self.fix_registry.items():
            if code in active_codes:
                new_prompt = fixer_func(current_prompt)
                if new_prompt != current_prompt:
                    current_prompt = new_prompt
                    applied_fixes.append(code)

        return current_prompt, applied_fixes

    def _fix_filler_words(self, prompt: str) -> str:
        fillers = [
            r"Please\s+",
            r"I want you to\s+",
            r"Could you\s+",
            r"If possible,\s+",
            r"I need a\s+",
            r"Can you help me\s+",
        ]
        cleaned = prompt
        for pattern in fillers:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned.strip()

    def _fix_unclosed_tags(self, prompt: str) -> str:
        tags = re.findall(r"<([a-zA-Z0-9_-]+)>", prompt)
        closing_tags = re.findall(r"</([a-zA-Z0-9_-]+)>", prompt)
        fixed_prompt = prompt
        for tag in tags:
            if tag not in closing_tags and f"</{tag}>" not in prompt:
                fixed_prompt += f"\n</{tag}>"
        return fixed_prompt


class PromptLinter:
    """Static analysis for prompts."""

    WEAK_WORDS = {
        "want",
        "create",
        "service",
        "thing",
        "stuff",
        "something",
        "anything",
        "maybe",
        "perhaps",
        "kinda",
        "sort of",
        "like",
        "you know",
        "um",
        "good",
        "better",
    }

    REQUIRED_SECTIONS = ["Context", "Task", "Format"]

    def lint(self, prompt: str) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        diagnostics.extend(self._check_ambiguity(prompt))
        diagnostics.extend(self._check_structure(prompt))
        diagnostics.extend(self._check_filler(prompt))
        diagnostics.extend(self._check_tag_matching(prompt))
        return diagnostics

    def _check_ambiguity(self, prompt: str) -> List[Diagnostic]:
        words = re.findall(r"\b\w+\b", prompt.lower())
        if not words:
            return []
        weak_found = [word for word in words if word in self.WEAK_WORDS]
        if len(weak_found) > len(words) * 0.2:
            return [
                Diagnostic(
                    code="W001",
                    category="Weakness",
                    message=(
                        "High ambiguity: Found weak words like "
                        f'{", ".join(set(weak_found[:3]))}.'
                    ),
                    severity="warning",
                    fixable=False,
                )
            ]
        return []

    def _check_structure(self, prompt: str) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        prompt_lower = prompt.lower()
        missing = [s for s in self.REQUIRED_SECTIONS if s.lower() not in prompt_lower]
        if missing:
            diagnostics.append(
                Diagnostic(
                    code="S001",
                    category="Structure",
                    message=f'Missing core sections: {", ".join(missing)}.',
                    severity="error",
                    fixable=False,
                )
            )

        for section in self.REQUIRED_SECTIONS:
            pattern = rf"<{section}>(.*?)</{section}>"
            match = re.search(pattern, prompt, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if len(content.split()) < 3:
                    diagnostics.append(
                        Diagnostic(
                            code="S004",
                            category="Structure",
                            message=f"Section <{section}> is too thin or empty.",
                            severity="error",
                            fixable=False,
                        )
                    )
        return diagnostics

    def _check_filler(self, prompt: str) -> List[Diagnostic]:
        fillers = ["please", "could you", "i want you to", "if possible"]
        prompt_lower = prompt.lower()
        found = [f for f in fillers if f in prompt_lower]
        if found:
            return [
                Diagnostic(
                    code="W002",
                    category="Weakness",
                    message=f'Conversational filler detected: "{found[0]}".',
                    severity="info",
                    fixable=True,
                )
            ]
        return []

    def _check_tag_matching(self, prompt: str) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        tags = re.findall(r"<(/?[a-zA-Z0-9_-]+)>", prompt)
        stack: List[str] = []

        for tag in tags:
            if not tag.startswith("/"):
                stack.append(tag)
                continue
            if not stack or stack[-1] != tag[1:]:
                diagnostics.append(
                    Diagnostic(
                        code="S003",
                        category="Structure",
                        message=f"Improperly nested tag: <{tag}>",
                        severity="error",
                        fixable=False,
                    )
                )
            else:
                stack.pop()

        for leftover in stack:
            diagnostics.append(
                Diagnostic(
                    code="S002",
                    category="Structure",
                    message=f"Unclosed tag: <{leftover}>",
                    severity="error",
                    fixable=True,
                )
            )
        return diagnostics
