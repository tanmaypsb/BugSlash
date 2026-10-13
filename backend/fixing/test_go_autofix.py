import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analyzer_models.go_analyzer import GoAnalyzer
from fixing.fix_engine import FixEngine, FixVerificationError
from models.analyzer_error import AnalyzerExecutionError
from models.go_source_fixes import GoFixError, remove_safe_unused

FIXTURE = Path(__file__).resolve().parents[1] / "test_code" / "autofix_stress.go"


class GoAutofixRegressionTests(unittest.TestCase):
    def test_stress_reproduction_reports_compile_and_format_findings(self):
        findings = GoAnalyzer().analyze(str(FIXTURE))
        self.assertEqual([item.category for item in findings].count("compile"), 2)
        format_findings = [item for item in findings if item.category == "SA5009"]
        self.assertEqual(len(format_findings), 1)
        self.assertIn("%s", format_findings[0].message)
        self.assertIn("int", format_findings[0].message)

    def test_stress_reproduction_fixes_safe_items_and_preserves_remaining_finding(self):
        with tempfile.TemporaryDirectory() as directory:
            uploaded = Path(directory) / "autofix_stress.go"
            original = FIXTURE.read_bytes()
            uploaded.write_bytes(original)

            result = FixEngine().fix_file(str(uploaded))

            self.assertEqual(result["status"], "PARTIALLY_FIXED")
            self.assertEqual(result["verification_status"], "PARTIAL")
            self.assertEqual(result["original_count"], 3)
            self.assertEqual(result["resolved_count"], 2)
            self.assertEqual(result["remaining_count"], 1)
            self.assertEqual(result["introduced_count"], 0)
            self.assertEqual(len(result["resolved_findings"]), 2)
            self.assertEqual([f["code"] for f in result["remaining_findings"]], ["SA5009"])
            self.assertNotIn('"os"', result["fixed_code"])
            self.assertNotIn("unused := 100", result["fixed_code"])
            self.assertIn('fmt.Printf("Score: %s\\n", score)', result["fixed_code"])
            self.assertIn("divide(10, 0)", result["fixed_code"])
            self.assertEqual(uploaded.read_bytes(), original)

    def test_safe_import_and_literal_local_fixes_can_be_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.go"
            source.write_text(
                'package main\nimport (\n"fmt"\n"os"\n)\n'
                'func main() {\n    unused := 100\n    fmt.Println("ok")\n}\n',
                encoding="utf-8",
            )
            result = FixEngine().fix_file(str(source))
            self.assertEqual(result["status"], "FIX_VERIFIED")
            self.assertEqual(result["verification_status"], "VERIFIED")
            self.assertEqual(result["original_count"], 2)
            self.assertEqual(result["resolved_count"], 2)
            self.assertEqual(result["remaining_count"], 0)
            self.assertEqual(result["introduced_count"], 0)
            self.assertNotIn('"os"', result["fixed_code"])
            self.assertNotIn("unused", result["fixed_code"])

    def test_side_effecting_unused_local_is_not_removed_or_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.go"
            source.write_text(
                'package main\nfunc sideEffect() int { return 1 }\n'
                'func main() {\n    unused := sideEffect()\n    _ = 1\n}\n',
                encoding="utf-8",
            )
            result = FixEngine().fix_file(str(source))
            self.assertEqual(result["status"], "VERIFICATION_INCOMPLETE")
            self.assertEqual(result["verification_status"], "INCOMPLETE")
            self.assertIn("unused := sideEffect()", result["fixed_code"])

    def test_failed_go_build_verification_is_never_marked_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.go"
            source.write_text("package main\nfunc main() {}\n", encoding="utf-8")
            engine = FixEngine()
            finding = {"code": "MOCK", "message": "mock", "filename": source.name, "location": {"row": 1, "column": 1}}
            with patch.object(engine, "_analyze_language", side_effect=[[finding], []]), \
                    patch.object(engine, "_apply", side_effect=lambda _lang, path, _cwd, selected_code=None: path.write_text("package main\nfunc main( {\n")), \
                    patch.object(engine, "_verify", side_effect=FixVerificationError("go build failed")):
                result = engine.fix_file(str(source))
            self.assertEqual(result["status"], "FIX_FAILED")
            self.assertEqual(result["verification_status"], "FAILED")
            self.assertIsNone(result["fixed_code"])

    def test_malformed_staticcheck_output_is_a_failure(self):
        completed = subprocess.CompletedProcess(["staticcheck"], 0, "not json\n", "")
        with patch("analyzer_models.go_analyzer.run_analyzer", return_value=completed), \
                self.assertRaises(AnalyzerExecutionError):
            GoAnalyzer().analyze(str(FIXTURE))

    def test_missing_staticcheck_is_an_analyzer_failure(self):
        with patch("analyzer_models.go_analyzer.shutil.which", return_value=None), \
                self.assertRaises(AnalyzerExecutionError):
            GoAnalyzer().analyze(str(FIXTURE))

    def test_missing_gofmt_is_not_reported_as_zero_findings(self):
        with tempfile.TemporaryDirectory() as directory:
            uploaded = Path(directory) / "autofix_stress.go"
            uploaded.write_bytes(FIXTURE.read_bytes())
            with patch.object(FixEngine, "_run", side_effect=FileNotFoundError("gofmt missing")):
                result = FixEngine().fix_file(str(uploaded))
            self.assertEqual(result["status"], "VERIFICATION_INCOMPLETE")
            self.assertEqual(result["verification_status"], "INCOMPLETE")
            self.assertEqual(result["original_count"], 3)
            self.assertEqual(result["remaining_count"], 3)
            self.assertIn("gofmt missing", result["message"])

    def test_unknown_or_unsafe_compile_diagnostic_fails_closed(self):
        with self.assertRaises(GoFixError):
            remove_safe_unused(
                "package main\nfunc main() { unused := sideEffect() }\n",
                "./sample.go:2:14: declared and not used: unused",
            )


if __name__ == "__main__":
    unittest.main()
