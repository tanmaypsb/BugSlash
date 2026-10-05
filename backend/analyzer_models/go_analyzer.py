import re
import subprocess
from pathlib import Path

from models.finding import Finding


class GoAnalyzer:

    def __init__(self):
        self.name = "staticcheck"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path)

        result = subprocess.run(
            [
                "staticcheck",
                str(file),
            ],
            capture_output=True,
            text=True,
        )

        findings = []

        for line in result.stdout.splitlines():

            match = re.match(
                r"(.+):(\d+):(\d+): (.+) \((SA\d+)\)",
                line,
            )

            if not match:
                continue

            file_name = match.group(1)
            line_number = int(match.group(2))
            column_number = int(match.group(3))
            message = match.group(4)
            category = match.group(5)

            findings.append(
                Finding(
                    language="go",
                    file=file_name,
                    line=line_number,
                    column=column_number,
                    category=category,
                    severity=self._get_severity(category),
                    message=message,
                    analyzer=self.name,
                    confidence=0.95,
                )
            )

        return findings

    def _get_severity(self, category: str) -> str:

        if category.startswith("SA"):
            return "high"

        return "medium"
