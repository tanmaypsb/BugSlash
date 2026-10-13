import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from analyzer_models.cpp_analyzer import CppAnalyzer
from analyzer_models.go_analyzer import GoAnalyzer
from analyzer_models.java_analyzer import JavaAnalyzer
from analyzer_models.javascript_analyzer import JavaScriptAnalyzer
from analyzer_models.python_analyzer import PythonAnalyzer
from analyzer_models.rust_analyzer import RustAnalyzer
from fixing.fix_engine import FixEngine
from models.analyzer_error import AnalyzerExecutionError, parse_json_output

BACKEND = Path(__file__).resolve().parent
ESLINT = BACKEND / "node_modules" / ".bin" / "eslint"


class RealAnalyzerMatrixTests(unittest.TestCase):
    def analyze(self, analyzer, suffix, source):
        with tempfile.TemporaryDirectory(prefix="bugslash-analysis-matrix-", dir=BACKEND) as directory:
            path = Path(directory) / ("sample" + suffix)
            path.write_text(source, encoding="utf-8")
            return analyzer.analyze(str(path))

    def require_tools(self, *tools):
        missing = [tool for tool in tools if not (Path(tool).exists() if "/" in tool else shutil.which(tool))]
        if missing:
            self.skipTest("real tool unavailable: " + ", ".join(missing))

    def test_missing_tool_launch_is_an_explicit_analyzer_failure(self):
        analyzers = [
            (PythonAnalyzer(), ".py"),
            (JavaScriptAnalyzer(), ".js"),
            (JavaScriptAnalyzer(), ".ts"),
            (CppAnalyzer(), ".c"),
            (CppAnalyzer(), ".cpp"),
            (JavaAnalyzer(), ".java"),
            (GoAnalyzer(), ".go"),
            (RustAnalyzer(), ".rs"),
        ]
        with tempfile.TemporaryDirectory(prefix="bugslash-tool-failure-") as directory:
            for analyzer, suffix in analyzers:
                path = Path(directory) / ("sample" + suffix)
                path.write_text("source", encoding="utf-8")
                with self.subTest(analyzer=analyzer.name, extension=suffix):
                    with patch("subprocess.run", side_effect=FileNotFoundError("tool disappeared")):
                        with self.assertRaises(AnalyzerExecutionError):
                            analyzer.analyze(str(path))

    def test_malformed_analyzer_json_is_an_explicit_failure(self):
        with self.assertRaises(AnalyzerExecutionError):
            parse_json_output("ruff", "{invalid", expected_type=list)

    def test_python_clean_issue_and_syntax(self):
        self.require_tools("ruff")
        analyzer = PythonAnalyzer()
        self.assertEqual(self.analyze(analyzer, ".py", "def answer():\n    return 42\n"), [])
        findings = self.analyze(analyzer, ".py", "import os\n")
        self.assertIn("F401", {item.category for item in findings})
        syntax = self.analyze(analyzer, ".py", "def broken(:\n")
        self.assertTrue(syntax)

    def test_javascript_clean_issue_and_parser_error(self):
        self.require_tools(str(ESLINT))
        analyzer = JavaScriptAnalyzer()
        self.assertEqual(self.analyze(analyzer, ".js", "console.log('ok');\n"), [])
        findings = self.analyze(analyzer, ".js", "const unused = 1;\n")
        self.assertIn("no-unused-vars", {item.category for item in findings})
        self.assertTrue(self.analyze(analyzer, ".js", "const = ;\n"))

    def test_typescript_clean_issue_and_parser_error(self):
        self.require_tools(str(ESLINT))
        analyzer = JavaScriptAnalyzer()
        self.assertEqual(self.analyze(analyzer, ".ts", "const answer: number = 42;\nconsole.log(answer);\n"), [])
        findings = self.analyze(analyzer, ".ts", "const unused: number = 1;\n")
        self.assertIn("no-unused-vars", {item.category for item in findings})
        self.assertTrue(self.analyze(analyzer, ".ts", "const answer: = ;\n"))

    def test_c_detectable_issue_and_invalid_source_is_not_clean(self):
        self.require_tools("clang-tidy")
        analyzer = CppAnalyzer()
        self.assertEqual(self.analyze(analyzer, ".c", "int main(void) { return 0; }\n"), [])
        findings = self.analyze(analyzer, ".c", "int main(void) { if (1) return 0; return 1; }\n")
        self.assertTrue(any("braces-around-statements" in item.category for item in findings))
        self.assert_invalid_not_clean(analyzer, ".c", "int main( { return 0; }\n")

    def test_cpp_detectable_issue_and_invalid_source_is_not_clean(self):
        self.require_tools("clang-tidy")
        analyzer = CppAnalyzer()
        self.assertEqual(self.analyze(analyzer, ".cpp", "int main() { return 0; }\n"), [])
        findings = self.analyze(analyzer, ".cpp", "int main() { if (1) return 0; return 1; }\n")
        self.assertTrue(any("braces-around-statements" in item.category for item in findings))
        self.assert_invalid_not_clean(analyzer, ".cpp", "int main( { return 0; }\n")

    def assert_invalid_not_clean(self, analyzer, suffix, source):
        try:
            findings = self.analyze(analyzer, suffix, source)
        except AnalyzerExecutionError:
            return
        self.assertTrue(findings, "invalid input must produce an error finding or an explicit analyzer failure")

    def test_java_real_spotbugs_finding_and_clean_source(self):
        self.require_tools("mvn")
        analyzer = JavaAnalyzer()
        clean = "class Clean { public static void main(String[] args) { System.out.println(\"ok\"); } }\n"
        self.assertEqual(self.analyze(analyzer, ".java", clean), [])
        bug = "class NullDeref { static String value() { String x = null; return x.toString(); } }\n"
        findings = self.analyze(analyzer, ".java", bug)
        self.assertTrue(any("NULL" in item.category for item in findings), findings)

    def test_go_clean_and_compile_errors_are_counted_per_diagnostic(self):
        self.require_tools("staticcheck", "go")
        analyzer = GoAnalyzer()
        self.assertEqual(self.analyze(analyzer, ".go", "package main\nfunc main() {}\n"), [])
        source = "package main\nimport (\n  \"fmt\"\n  \"os\"\n)\nfunc main() { unused := 1; fmt.Println(\"ok\") }\n"
        findings = self.analyze(analyzer, ".go", source)
        compile_errors = [item for item in findings if item.category == "compile"]
        self.assertEqual(len(compile_errors), 2, findings)
        self.assertTrue(all(item.line > 0 and item.column > 0 for item in compile_errors))

    def test_go_fix_reports_remaining_compile_findings_instead_of_clean(self):
        self.require_tools("staticcheck", "go", "gofmt")
        source = "package main\nimport (\n  \"fmt\"\n  \"os\"\n)\nfunc main() { unused := 1; fmt.Println(\"ok\") }\n"
        with tempfile.TemporaryDirectory(prefix="bugslash-go-fix-matrix-") as directory:
            path = Path(directory) / "sample.go"
            path.write_text(source, encoding="utf-8")
            original = path.read_bytes()
            result = FixEngine().fix_file(str(path))
            self.assertEqual(path.read_bytes(), original)
        self.assertEqual(result["original_count"], 2)
        self.assertEqual(result["remaining_count"], len(result["remaining_findings"]))
        self.assertGreater(result["remaining_count"], 0)
        self.assertNotEqual(result["status"], "FIX_VERIFIED")

    def test_rust_real_clippy_finding_clean_and_invalid_not_clean(self):
        self.require_tools("cargo")
        analyzer = RustAnalyzer()
        clean = self.analyze(analyzer, ".rs", "pub fn answer() -> i32 { 42 }\n")
        self.assertEqual(clean, [])
        findings = self.analyze(analyzer, ".rs", "pub fn answer() -> i32 { let value = 1; value }\n")
        self.assertTrue(findings)
        self.assert_invalid_not_clean(analyzer, ".rs", "pub fn broken( {\n")
