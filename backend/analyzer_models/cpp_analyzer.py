import json
import subprocess
from pathlib import Path

from models.finding import Finding


class CppAnalyzer:

    def __init__(self):
        self.name = "clang-tidy"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path)

        result = subprocess.run(
            [
                "clang-tidy",
                str(file),
                "--checks=clang-analyzer-*,bugprone-*,performance-*,readability-*",
                "--",
                "-std=c++17",
            ],
            capture_output=True,
            text=True,
        )

        findings = []

        for line in result.stdout.splitlines():

            if ": warning:" not in line:
                continue

            try:
                location, message = line.split(": warning:", 1)

                parts = location.split(":")

                file_name = ":".join(parts[:-2])
                line_number = int(parts[-2])
                column_number = int(parts[-1])

                if "[" in message and "]" in message:
                    message_text = message.split("[", 1)[0].strip()
                    category = message.split("[", 1)[1].split("]", 1)[0]
                else:
                    message_text = message.strip()
                    category = "unknown"

                findings.append(
                    Finding(
                        language="cpp",
                        file=file_name,
                        line=line_number,
                        column=column_number,
                        category=category,
                        severity="medium",
                        message=message_text,
                        analyzer=self.name,
                        confidence=0.90,
                    )
                )

            except (ValueError, IndexError):
                continue

        return findings
