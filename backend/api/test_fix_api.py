import asyncio
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

from fastapi import HTTPException, UploadFile
from api import main


class FixApiTests(unittest.TestCase):
    def upload(self, name: str, source: bytes) -> UploadFile:
        return UploadFile(file=BytesIO(source), filename=name)

    def test_global_fix_uses_isolated_source_and_returns_complete_code(self):
        original = b"import os\n\ndef run():\n    return 1\n"
        upload = self.upload("sample.py", original)
        result = asyncio.run(main.fix_file(upload))
        self.assertEqual(result["status"], "FIX_VERIFIED")
        self.assertIn("fixed_code", result)
        self.assertNotIn("import os", result["fixed_code"])
        self.assertEqual(upload.file.getvalue(), original)

    def test_temporary_file_is_removed_after_fix(self):
        seen = {}
        original_call = main.fix_engine.fix_file

        def recording_call(path):
            seen["path"] = Path(path)
            return original_call(path)

        with patch.object(main.fix_engine, "fix_file", side_effect=recording_call):
            asyncio.run(main.fix_file(self.upload("sample.py", b"import os\n")))
        self.assertIn("path", seen)
        self.assertFalse(seen["path"].exists())

    def test_finding_fix_addresses_the_selected_issue(self):
        original = b"import os\n\ndef run():\n    unused = 1\n    return 2\n"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.py"
            source.write_bytes(original)
            selected = next(item for item in main.fix_engine._analyze(source) if item["code"] == "F401")
        context = {
            "language": "python", "file": "sample.py", "line": selected["location"]["row"],
            "column": selected["location"]["column"], "category": selected["code"],
            "severity": "high", "message": selected["message"], "analyzer": "ruff", "confidence": 0.95,
        }
        result = asyncio.run(main.fix_one_finding(self.upload("sample.py", original), json.dumps(context)))
        self.assertTrue(result["selected_resolved"])
        self.assertTrue(any(item["code"] == "F841" for item in result["remaining_findings"]))

    def test_global_typescript_fix_uses_the_original_extension_and_keeps_upload_unchanged(self):
        original = b'const value: string = "text";\nconsole.log(value);\n'
        upload = self.upload("sample.ts", original)
        result = asyncio.run(main.fix_file(upload))
        self.assertEqual(result["status"], "FIX_VERIFIED")
        self.assertEqual(result["filename"], "sample.ts")
        self.assertIn("value: string = 'text'", result["fixed_code"])
        self.assertEqual(upload.file.getvalue(), original)

    def test_unsupported_deterministic_file_is_rejected(self):
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(main.fix_file(self.upload("sample.rb", b"const value = 1;")))
        self.assertEqual(raised.exception.status_code, 400)

    def test_analyzer_timeout_is_not_reported_as_success(self):
        timeout = subprocess.TimeoutExpired("ruff", 30)
        with patch.object(main.fix_engine, "fix_file", side_effect=timeout):
            with self.assertRaises(HTTPException) as raised:
                asyncio.run(main.fix_file(self.upload("sample.py", b"import os\n")))
        self.assertEqual(raised.exception.status_code, 504)

    def test_local_provider_unavailable_is_explicit_and_does_not_affect_analysis(self):
        context = {
            "language": "python", "file": "sample.py", "line": 1, "column": 1,
            "category": "F401", "severity": "high", "message": "unused import", "analyzer": "ruff",
        }
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(main.explain_one_finding(self.upload("sample.py", b"import os\n"), json.dumps(context)))
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(main.engine.analyze_file.__name__, "analyze_file")

    def test_reviewed_proposal_is_hash_bound_and_verified(self):
        original = b"import os\nprint('ok')\n"
        candidate = "print('ok')\n"
        context = {
            "language": "python", "file": "sample.py", "line": 1, "column": 8,
            "category": "F401", "severity": "high", "message": "`os` imported but unused", "analyzer": "ruff",
        }
        result = asyncio.run(main.apply_reviewed_proposal(
            self.upload("sample.py", original), json.dumps(context), candidate,
            hashlib.sha256(original.decode("utf-8").encode("utf-8")).hexdigest(),
        ))
        self.assertEqual(result["status"], "FIX_VERIFIED")
        self.assertEqual(result["fixed_code"], candidate)
        self.assertEqual(original, b"import os\nprint('ok')\n")


if __name__ == "__main__":
    unittest.main()
