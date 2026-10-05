import json
import subprocess
from pathlib import Path

from models.finding import Finding


class JavaScriptAnalyzer:

    def __init__(self):
        self.name = "eslint"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path)
        language = (
            "typescript"
            if file.suffix.lower() in {".ts", ".tsx"}
            else "javascript"
        )

        result = subprocess.run(
            [
                "npx",
                "eslint",
                str(file),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
        )

        if not result.stdout.strip():
            return []

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return []

        findings = []

        for file_result in data:
            for issue in file_result["messages"]:

                findings.append(
                    Finding(
                        language=language,
                        file=str(file),
                        line=issue["line"],
                        column=issue["column"],
                        category=issue["ruleId"] or "unknown",
                        severity=self._get_severity(
                            issue["severity"]
                        ),
                        message=issue["message"],
                        analyzer=self.name,
                        confidence=0.95,
                    )
                )

        return findings

    def _get_severity(self, severity: int) -> str:
        if severity == 2:
            return "high"

        if severity == 1:
            return "medium"

        return "low"
