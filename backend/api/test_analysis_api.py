import asyncio
import os
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

from api import main
from api.schemas import FileAnalysisResponse, FixResponse
from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from models.analyzer_error import AnalyzerExecutionError


class AnalysisApiFailureTests(unittest.TestCase):
    def upload(self, name, data):
        return UploadFile(file=BytesIO(data), filename=name)

    def test_analyzer_failure_is_http_422_not_a_clean_empty_result(self):
        original = b"package main\\nimport \"os\"\\nfunc main() {}\\n"
        with patch.object(main.engine, "analyze_file", side_effect=AnalyzerExecutionError("staticcheck", "unused import")):
            with self.assertRaises(HTTPException) as raised:
                main.analyze_file(self.upload("example.go", original))
        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn("staticcheck analysis failed", raised.exception.detail)

    def test_go_compiler_diagnostics_reach_the_api_as_findings(self):
        source = Path(__file__).resolve().parents[1] / "test_code" / "go" / "example.go"
        result = main.analyze_file(self.upload("example.go", source.read_bytes()))
        payload = FileAnalysisResponse.model_validate(jsonable_encoder(result)).model_dump()
        compiler_findings = [item for item in payload["findings"] if item["category"] == "compile"]
        self.assertEqual(len(compiler_findings), 2)
        self.assertEqual([item["line"] for item in compiler_findings], [5, 9])
        self.assertTrue(all(item["file"] == "example.go" for item in compiler_findings))

    def test_fix_response_includes_consistent_resolved_and_new_collections(self):
        result = asyncio.run(main.fix_file(self.upload("sample.py", b"import os\n")))
        payload = FixResponse.model_validate(result).model_dump()
        self.assertEqual(payload["resolved_count"], len(payload["resolved_findings"]))
        self.assertEqual(payload["introduced_count"], len(payload["introduced_findings"]))
        self.assertEqual(payload["remaining_count"], len(payload["remaining_findings"]))

    def test_java_upload_keeps_its_filename_in_the_isolated_analysis_copy(self):
        original = b"class Example { public static void main(String[] args) {} }"
        seen = {}
        def inspect_source(path):
            source = Path(path)
            seen["name"] = source.name
            seen["bytes"] = source.read_bytes()
            return {
                "file": str(source), "language": "java", "findings": [],
                "verification": None, "verification_results": [],
            }
        with patch.object(main.engine, "analyze_file", side_effect=inspect_source):
            result = main.analyze_file(self.upload("Example.java", original))
        self.assertEqual(result["file"], "Example.java")
        self.assertEqual(seen, {"name": "Example.java", "bytes": original})


if __name__ == "__main__":
    unittest.main()
