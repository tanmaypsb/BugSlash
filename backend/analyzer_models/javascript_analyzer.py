from pathlib import Path

from models.finding import Finding
from models.analyzer_error import parse_json_output, run_analyzer


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

        backend = Path(__file__).resolve().parents[1]
        eslint = backend / "node_modules" / ".bin" / "eslint"
        executable = str(eslint) if eslint.exists() else "eslint"
        result = run_analyzer(
            self.name,
            [executable, str(file), "--config", str(backend / "eslint.config.js"), "--format", "json"],
            cwd=backend,
            timeout=45,
            expected=(0, 1),
        )
        data = parse_json_output(self.name, result.stdout, expected_type=list)

        findings = []

        for file_result in data:
            for issue in file_result["messages"]:

                findings.append(
                    Finding(
                        language=language,
                        file=str(file),
                        line=issue.get("line") or 1,
                        column=issue.get("column") or 1,
                        category=issue.get("ruleId") or "unknown",
                        severity=self._get_severity(
                            issue.get("severity", 1)
                        ),
                        message=issue.get("message") or "Unknown ESLint finding",
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
