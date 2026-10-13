import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fixing.fix_engine import FixEngine

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "test_code" / "autofix_reliability"
CASES = {
    "python": ("python_unused_import.py", (".venv/bin/ruff",), "FIX_VERIFIED", 2, 2, 0, 0),
    "javascript": ("autofix_stress.js", (str(BACKEND / "node_modules/.bin/eslint"),), "PARTIALLY_FIXED", 11, 6, 5, 0),
    "typescript": ("typescript_remaining_unused.ts", (str(BACKEND / "node_modules/.bin/eslint"),), "PARTIALLY_FIXED", 2, 1, 1, 0),
    "c": ("c_braces.c", ("clang-tidy", "clang-format"), "FIX_VERIFIED", 1, 1, 0, 0),
    "cpp": ("cpp_braces.cpp", ("clang-tidy", "clang-format"), "PARTIALLY_FIXED", 2, 1, 1, 0),
    "java": ("java_null_deref.java", ("mvn", "clang-format"), "REVIEW_REQUIRED", 1, 0, 1, 0),
    "go": ("autofix_stress.go", ("go", "gofmt", "staticcheck"), "PARTIALLY_FIXED", 3, 2, 1, 0),
    "rust": ("rust_let_return.rs", ("cargo", "rustfmt"), "FIX_VERIFIED", 1, 1, 0, 0),
}


class AutofixReliabilityTests(unittest.TestCase):
    def test_language_fixture_matrix_counts_and_source_preservation(self):
        engine = FixEngine()
        tested = set()
        for language, (filename, tools, status, before, resolved, remaining, introduced) in CASES.items():
            if any(
                not (Path(tool).exists() if "/" in tool else shutil.which(tool))
                for tool in tools
            ):
                continue
            fixture = BACKEND / "test_code" / filename if filename.startswith("autofix_stress") else FIXTURES / filename
            original = fixture.read_bytes()
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                uploaded = Path(directory) / fixture.name
                uploaded.write_bytes(original)
                result = engine.fix_file(str(uploaded))
                self.assertEqual(result["status"], status, result["message"])
                self.assertEqual(result["original_count"], before)
                self.assertEqual(result["resolved_count"], resolved)
                self.assertEqual(result["remaining_count"], remaining)
                self.assertEqual(result["introduced_count"], introduced)
                self.assertEqual(len(result["original_findings"]), before)
                self.assertEqual(len(result["resolved_findings"]), resolved)
                self.assertEqual(len(result["remaining_findings"]), remaining)
                self.assertEqual(len(result["introduced_findings"]), introduced)
                self.assertEqual(uploaded.read_bytes(), original)
                if status == "FIX_VERIFIED":
                    self.assertEqual(result["verification_status"], "VERIFIED")
                else:
                    self.assertNotEqual(result["verification_status"], "VERIFIED")
                tested.add(language)
        self.assertTrue({"python", "javascript", "typescript", "c", "cpp", "java", "go", "rust"} <= tested)

    def test_javascript_loose_equality_is_detected_and_fixed(self):
        fixture = BACKEND / "test_code" / "autofix_stress.js"
        with tempfile.TemporaryDirectory() as directory:
            uploaded = Path(directory) / fixture.name
            uploaded.write_bytes(fixture.read_bytes())
            result = FixEngine().fix_file(str(uploaded))
        self.assertTrue(any(item["code"] == "eqeqeq" for item in result["remaining_findings"]))
        self.assertIn('age == \'18\'', result["fixed_code"])

    def test_javascript_undefined_name_stays_remaining_after_quote_fixes(self):
        fixture = BACKEND / "test_code" / "autofix_stress.js"
        original = fixture.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            uploaded = Path(directory) / fixture.name
            uploaded.write_bytes(original)
            result = FixEngine().fix_file(str(uploaded))
            self.assertEqual(uploaded.read_bytes(), original)
        self.assertEqual(result["status"], "PARTIALLY_FIXED")
        self.assertIsNotNone(result["fixed_code"])
        self.assertIn("userName", result["fixed_code"])
        self.assertTrue(any(
            item["code"] == "no-undef" and "userName" in item["message"]
            for item in result["remaining_findings"]
        ))
        self.assertEqual(result["introduced_count"], 0)

    def test_duplicate_findings_match_after_line_and_column_shifts(self):
        before_lines = [
            'const unused = "x";',
            'const unused = "x";',
        ]
        after_lines = [
            "// formatter inserted a comment",
            "    const unused = 'x';",
            "    const unused = 'x';",
        ]
        before = [
            {"code": "no-unused-vars", "message": "'unused' is assigned a value but never used.", "location": {"row": row, "column": 7}}
            for row in (1, 2)
        ]
        after = [
            {"code": "no-unused-vars", "message": "'unused' is assigned a value but never used.", "location": {"row": row, "column": 11}}
            for row in (2, 3)
        ]
        resolved, introduced = FixEngine._finding_differences(
            before, after, before_lines, after_lines, "javascript"
        )
        self.assertEqual((len(resolved), len(introduced)), (0, 0))

    def test_malformed_rust_analyzer_output_is_not_treated_as_clean(self):
        import subprocess

        from analyzer_models.rust_analyzer import RustAnalyzer
        from models.analyzer_error import AnalyzerExecutionError

        fixture = FIXTURES / "rust_let_return.rs"
        completed = subprocess.CompletedProcess(["cargo"], 0, "{malformed json}\\n", "")
        with patch("analyzer_models.rust_analyzer.run_analyzer", return_value=completed), self.assertRaises(AnalyzerExecutionError):
            RustAnalyzer().analyze(str(fixture))

    def test_genuinely_new_same_rule_finding_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.js"
            original = "console.log(oldName);\n"
            source.write_text(original, encoding="utf-8")
            before = {"code": "no-undef", "message": "'oldName' is not defined.", "filename": source.name, "location": {"row": 1, "column": 13}}
            after = {"code": "no-undef", "message": "'newName' is not defined.", "filename": source.name, "location": {"row": 1, "column": 13}}

            def introduce(_language, copied, _cwd, selected_code=None):
                copied.write_text("console.log(newName);\n", encoding="utf-8")

            engine = FixEngine()
            with patch.object(engine, "_analyze_language", side_effect=[[before], [after]]), \
                    patch.object(engine, "_apply", side_effect=introduce), \
                    patch.object(engine, "_verify"):
                result = engine.fix_file(str(source))
            self.assertEqual(result["status"], "FIX_FAILED")
            self.assertEqual(result["verification_status"], "FAILED")
            self.assertEqual(result["resolved_count"], 1)
            self.assertEqual(result["introduced_count"], 1)
            self.assertIsNone(result["fixed_code"])
            self.assertEqual(source.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
