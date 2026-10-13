import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fixing.fix_engine import FixEngine


CASES = {
    "python": (".py", "import os\n\ndef run():\n    return 1\n"),
    "javascript": (".js", 'const value = "text";\nconsole.log(value);\n'),
    "typescript": (".ts", 'const value: string = "text";\nconsole.log(value);\n'),
    "c": (".c", "int main(){return 0;}\n"),
    "cpp": (".cpp", "int main(){return 0;}\n"),
    "java": (".java", "class Sample{public static void main(String[] args){System.out.println(1);}}\n"),
    "go": (".go", "package main\nfunc main(){x:=1;_=x}\n"),
    "rust": (".rs", "pub fn value()->i32{let x=1;x}\n"),
}
TOOLS = {
    "python": ["ruff"],
    "javascript": [FixEngine._eslint()],
    "typescript": [FixEngine._eslint()],
    "c": ["clang-tidy", "clang-format"],
    "cpp": ["clang-tidy", "clang-format"],
    "java": ["mvn", "clang-format"],
    "go": ["go", "gofmt", "staticcheck"],
    "rust": ["cargo", "rustfmt"],
}


class MultiLanguageFixerTests(unittest.TestCase):
    def test_real_language_fixers_modify_isolated_copies_and_verify(self):
        for lang, (extension, source) in CASES.items():
            if any(Path(tool).is_absolute() and not Path(tool).exists() or not Path(tool).is_absolute() and shutil.which(tool) is None for tool in TOOLS[lang]):
                continue
            with self.subTest(language=lang), tempfile.TemporaryDirectory() as directory:
                original = Path(directory) / ("sample" + extension)
                original.write_text(source, encoding="utf-8")
                before = original.read_bytes()
                result = FixEngine().fix_file(str(original))
                self.assertTrue(result["fixed"], result["message"])
                self.assertEqual(result["verification_status"], "VERIFIED", result["message"])
                self.assertEqual(result["status"], "FIX_VERIFIED", result["message"])
                self.assertEqual(result["original_count"], len(result["original_findings"]))
                self.assertEqual(result["remaining_count"], len(result["remaining_findings"]))
                self.assertGreaterEqual(result["resolved_count"], 0)
                self.assertNotEqual(result["fixed_code"], source)
                self.assertEqual(original.read_bytes(), before)

    def test_clean_unresolved_and_verification_failure_contract_for_each_language(self):
        for lang, (extension, _source) in CASES.items():
            with self.subTest(language=lang):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / ("sample" + extension)
                    path.write_text("original source\n", encoding="utf-8")
                    clean_engine = FixEngine()
                    with patch.object(clean_engine, "_analyze_language", return_value=[]), patch.object(clean_engine, "_apply"), patch.object(clean_engine, "_verify"):
                        clean = clean_engine.fix_file(str(path))
                    self.assertEqual(clean["status"], "NO_CHANGES")
                    self.assertEqual(clean["verification_status"], "NOT_NEEDED")
                    self.assertEqual(path.read_text(), "original source\n")

                    finding = {"code": "MOCK1", "message": "mock unresolved issue", "filename": path.name, "location": {"row": 1, "column": 1}}
                    unresolved_engine = FixEngine()
                    with patch.object(unresolved_engine, "_analyze_language", side_effect=[[finding], [finding]]), patch.object(unresolved_engine, "_apply"), patch.object(unresolved_engine, "_verify"):
                        unresolved = unresolved_engine.fix_file(str(path))
                    self.assertEqual(unresolved["status"], "REVIEW_REQUIRED")
                    self.assertEqual(unresolved["remaining_count"], 1)
                    self.assertEqual(unresolved["original_count"], 1)

                    failure_engine = FixEngine()
                    def changed_copy(language, copied, cwd, selected_code=None):
                        copied.write_text("modified only in temp\n", encoding="utf-8")
                    with patch.object(failure_engine, "_analyze_language", return_value=[finding]), patch.object(failure_engine, "_apply", side_effect=changed_copy), patch.object(failure_engine, "_verify", side_effect=RuntimeError("mock verification failure")):
                        failed = failure_engine.fix_file(str(path))
                    self.assertEqual(failed["status"], "VERIFICATION_INCOMPLETE")
                    self.assertEqual(failed["verification_status"], "INCOMPLETE")
                    self.assertEqual(path.read_text(), "original source\n")

    def test_failed_verification_is_distinct_from_incomplete_verification(self):
        from fixing.fix_engine import FixVerificationError
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("import os\n")
            engine = FixEngine()
            finding = {"code": "F401", "message": "unused import", "filename": path.name, "location": {"row": 1, "column": 1}}
            with patch.object(engine, "_analyze_language", return_value=[finding]), patch.object(engine, "_apply"), patch.object(engine, "_verify", side_effect=FixVerificationError("mock check failed")):
                result = engine.fix_file(str(path))
            self.assertEqual(result["status"], "FIX_FAILED")
            self.assertEqual(result["verification_status"], "FAILED")
            self.assertIsNone(result["fixed_code"])
            self.assertEqual(path.read_text(), "import os\n")

    def test_new_post_fix_finding_fails_and_withholds_modified_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("import os\n", encoding="utf-8")
            engine = FixEngine()
            introduced = {"code": "NEW", "message": "new issue", "filename": path.name, "location": {"row": 1, "column": 1}}
            with patch.object(engine, "_analyze_language", side_effect=[[], [introduced]]), patch.object(engine, "_apply", side_effect=lambda _lang, copied, _cwd, selected_code=None: copied.write_text("# changed\n", encoding="utf-8")), patch.object(engine, "_verify"):
                result = engine.fix_file(str(path))
            self.assertEqual(result["status"], "FIX_FAILED")
            self.assertEqual(result["verification_status"], "FAILED")
            self.assertIsNone(result["fixed_code"])
            self.assertEqual(path.read_text(encoding="utf-8"), "import os\n")

    def test_unsupported_extension_and_invalid_utf8_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            unsupported = Path(directory) / "sample.rb"
            unsupported.write_text("puts 1")
            with self.assertRaises(ValueError):
                FixEngine().fix_file(str(unsupported))
            invalid = Path(directory) / "sample.py"
            invalid.write_bytes(b"\xff")
            with self.assertRaises(ValueError):
                FixEngine().fix_file(str(invalid))


if __name__ == "__main__":
    unittest.main()
