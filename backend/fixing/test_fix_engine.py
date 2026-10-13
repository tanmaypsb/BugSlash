import hashlib
import tempfile
import unittest
from pathlib import Path

from fixing.fix_engine import FixEngine, FindingNotFoundError
from fixing.llm_assistance import (
    ProposalValidationError,
    explain_finding,
    propose_finding_fix,
    verify_proposal_source,
)


class FakeClient:
    model = "fake-local-model"
    provider_name = "Ollama"

    def __init__(self, data):
        self.data = data

    def generate_json(self, _system, _user):
        return self.data


class FixEngineTests(unittest.TestCase):
    def test_multiple_safe_fixes_are_reanalyzed_and_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("import sys\nimport os\n\ndef run():\n    return 1\n", encoding="utf-8")
            result = FixEngine().fix_file(str(path))
            self.assertEqual(result["status"], "FIX_VERIFIED")
            self.assertEqual(result["verification_status"], "VERIFIED")
            self.assertGreaterEqual(result["resolved_count"], 2)
            self.assertEqual(result["resolved_count"], len(result["resolved_findings"]))
            self.assertEqual(result["introduced_count"], len(result["introduced_findings"]))
            self.assertEqual(result["remaining_count"], 0)

    def test_safe_and_nonfixable_findings_report_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("import os\n\ndef run():\n    unused = 1\n    return 2\n", encoding="utf-8")
            result = FixEngine().fix_file(str(path))
            self.assertEqual(result["status"], "PARTIALLY_FIXED")
            self.assertGreater(result["resolved_count"], 0)
            self.assertGreater(result["remaining_count"], 0)
            self.assertEqual(result["remaining_count"], len(result["remaining_findings"]))
            self.assertEqual(result["resolved_count"], len(result["resolved_findings"]))

    def test_no_findings_is_not_misreported_as_a_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            original = "def run():\n    return 2\n"
            path.write_text(original, encoding="utf-8")
            result = FixEngine().fix_file(str(path))
            self.assertEqual(result["status"], "NO_CHANGES")
            self.assertFalse(result["fixed"])
            self.assertEqual(result["verification_status"], "NOT_NEEDED")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_finding_fix_targets_selected_rule_and_keeps_unrelated_finding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("import os\n\ndef run():\n    unused = 1\n    return 2\n", encoding="utf-8")
            before = FixEngine._analyze(path)
            selected = next(item for item in before if item["code"] == "F401")
            target = {
                "language": "python", "analyzer": "ruff", "category": selected["code"],
                "line": selected["location"]["row"], "column": selected["location"]["column"],
                "message": selected["message"],
            }
            result = FixEngine().fix_finding(str(path), target)
            self.assertTrue(result["selected_resolved"])
            self.assertTrue(any(item["code"] == "F841" for item in result["remaining_findings"]))
            self.assertIn("multiple instances", result["scope_note"])

    def test_stale_finding_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("print('clean')\n", encoding="utf-8")
            stale = {"language": "python", "analyzer": "ruff", "category": "F401", "line": 1, "column": 8, "message": "missing"}
            with self.assertRaises(FindingNotFoundError):
                FixEngine().fix_finding(str(path), stale)

    def test_duplicate_rule_counts_and_line_shifts(self):
        finding = {"code": "F401", "message": "unused import", "location": {"row": 1}}
        shifted = {"code": "F821", "message": "undefined name", "location": {"row": 3}}
        count, codes = FixEngine._resolved_findings(
            [finding, finding, shifted], [shifted],
            ["import os", "import sys", "print(missing)"],
            ["# moved", "# comment", "print(missing)"],
        )
        self.assertEqual(count, 2)
        self.assertEqual(codes, ["F401"])

    def test_unsupported_language_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.rb"
            path.write_text("const value = 1;\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                FixEngine().fix_file(str(path))

    def test_explanation_uses_structured_output(self):
        data = {
            "meaning": "Unused import.", "why_reported": "Ruff found no references.",
            "impact": "Adds clutter.", "suggested_correction": "Remove the import.",
            "correction_kind": "deterministic",
        }
        result = explain_finding({"line": 1, "category": "F401"}, "import os\n", FakeClient(data))
        self.assertEqual(result["meaning"], data["meaning"])
        self.assertIn("1: import os", result["source_context"])

    def test_malformed_explanation_is_rejected(self):
        with self.assertRaises(ProposalValidationError):
            explain_finding({"line": 1}, "print(1)\n", FakeClient({"meaning": "incomplete"}))

    def test_proposal_is_review_only_and_source_bound(self):
        original = "def run():\n    return 1\n"
        proposed = "def run():\n    return 2\n"
        result = propose_finding_fix(
            {"line": 2, "category": "TEST"}, original,
            FakeClient({"summary": "Change the return value.", "proposed_code": proposed, "risks": ["Behavior changes."]}),
        )
        self.assertTrue(result["review_required"])
        self.assertEqual(result["status"], "PROPOSAL_READY")
        verify_proposal_source(original, proposed, result["source_sha256"], {"line": 2})
        with self.assertRaises(ProposalValidationError):
            verify_proposal_source(original + "# changed\n", proposed, result["source_sha256"], {"line": 2})


if __name__ == "__main__":
    unittest.main()
