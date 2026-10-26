import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.kayab_pipeline import PromptRefinementPipeline, SovereignCodePipeline
from app.prompt_refinement import AutoFixer, Diagnostic, PromptLinter


class TestMaskMachineV2(unittest.TestCase):
    def setUp(self):
        self.linter = PromptLinter()
        self.fixer = AutoFixer()

    def test_linter_filler_words(self):
        prompt = "Please I want you to create a list."
        diagnostics = self.linter.lint(prompt)
        w002 = [d for d in diagnostics if d.code == "W002"]
        self.assertTrue(len(w002) > 0, "Should detect filler words")
        self.assertTrue(w002[0].fixable, "W002 should be fixable")

    def test_autofixer_filler_words(self):
        prompt = "Please create a list."
        diagnostics = [Diagnostic("W002", "Weakness", "Filler detected", "info", True)]
        fixed, applied = self.fixer.fix(prompt, diagnostics)
        self.assertEqual(fixed, "Create a list.", "Should strip 'Please ' and capitalize.")
        self.assertIn("W002", applied)

    def test_linter_unclosed_tags(self):
        prompt = "<Context>Some context"
        diagnostics = self.linter.lint(prompt)
        s002 = [d for d in diagnostics if d.code == "S002"]
        self.assertTrue(len(s002) > 0, "Should detect unclosed tag")
        self.assertEqual(s002[0].message, "Unclosed tag: <Context>")

    def test_autofixer_unclosed_tags(self):
        prompt = "<Context>Some context"
        diagnostics = [
            Diagnostic("S002", "Structure", "Unclosed tag: <Context>", "error", True)
        ]
        fixed, applied = self.fixer.fix(prompt, diagnostics)
        self.assertEqual(
            fixed,
            "<Context>Some context\n</Context>",
            "Should append closing tag",
        )
        self.assertIn("S002", applied)

    def test_refinement_loop_flow(self):
        """Full prompt pipeline with mocked Architect only (no tribunal)."""
        mock_architect = MagicMock()
        mock_architect.generate = AsyncMock(
            return_value={
                "raw_text": (
                    "<Context>Here is the required context for the job.</Context>\n"
                    "<Task>We need to produce a structured list now.</Task>\n"
                    "<Format>Output format is JSON dictionary only.</Format>"
                ),
                "token_usage": {"prompt": 10, "completion": 20, "total": 30},
                "error": None,
            }
        )
        mock_architect.model_id = "mock-model"

        mock_spec = MagicMock()
        mock_spec.get_spec.return_value = {
            "output_format": "json",
            "version": "1.0.0",
            "required_fields": ["context", "task", "format"],
        }
        mock_spec.validate.return_value = MagicMock(
            schema_valid=True, missing_fields=[], type_errors=[]
        )

        from app.services import MaskService

        mask = MaskService()
        config = {
            "flavor": "technical",
            "max_iterations": 2,
            "service_key": "test-signing-key-not-for-prod",
        }

        pipeline = SovereignCodePipeline(
            mock_architect, self.linter, mock_spec, mask, config
        )
        self.assertIsInstance(pipeline, PromptRefinementPipeline)

        result = asyncio.run(
            pipeline.process(
                "i want a list",
                template_id="default",
                requester={"id": "test"},
            )
        )

        self.assertTrue(
            result["success_gate"]["passed"],
            f"Should pass success gate. Reason: {result.get('reason')}",
        )
        self.assertTrue(mock_architect.generate.called)
        self.assertIn("rendered_prompt", result["final_output"])
        self.assertTrue(len(result["final_output"]["rendered_prompt"]) > 0)
        self.assertIsNotNone(result.get("integrity_signature"))


if __name__ == "__main__":
    unittest.main()
