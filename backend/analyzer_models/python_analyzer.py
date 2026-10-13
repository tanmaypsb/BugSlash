import json
from pathlib import Path

from .finding import Finding
from models.analyzer_error import parse_json_output, run_analyzer


class PythonAnalyzer:

    def __init__(self):
        self.name = "ruff"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path)

        result = run_analyzer(
            self.name,
            ["ruff", "check", str(file), "--output-format", "json"],
            timeout=30,
            expected=(0, 1),
        )
        issues = parse_json_output(self.name, result.stdout, expected_type=list)

        findings = []

        for issue in issues:
            code = issue.get("code") or "unknown"
            findings.append(
                Finding(
                    language="python",
                    file=str(file),
                    line=issue.get("location", {}).get("row", 1),
                    column=issue.get("location", {}).get("column", 1),
                    category=code,
                    severity=self._get_severity(code),
                    message=issue.get("message") or "Unknown Ruff finding",
                    analyzer=self.name,
                    confidence=0.95,
                )
            )

        return findings

    def _get_severity(self, code: str) -> str:
        if code.startswith(("E", "F")):
            return "high"

        if code.startswith(("W", "I")):
            return "low"

        return "medium"
