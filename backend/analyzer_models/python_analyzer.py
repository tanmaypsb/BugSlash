import json
import subprocess
from pathlib import Path

from .finding import Finding


class PythonAnalyzer:

    def __init__(self):
        self.name = "ruff"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path)

        result = subprocess.run(
            [
                "ruff",
                "check",
                str(file),
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
        )

        if not result.stdout.strip():
            return []

        try:
            issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

        findings = []

        for issue in issues:
            findings.append(
                Finding(
                    language="python",
                    file=str(file),
                    line=issue["location"]["row"],
                    column=issue["location"]["column"],
                    category=issue["code"],
                    severity=self._get_severity(issue["code"]),
                    message=issue["message"],
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
