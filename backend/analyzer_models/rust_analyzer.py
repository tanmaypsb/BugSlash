import json
import subprocess
from pathlib import Path

from models.finding import Finding


class RustAnalyzer:

    def __init__(self):
        self.name = "clippy"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path)

        cargo_toml = self._find_cargo_project(file)

        if cargo_toml is None:
            return []

        result = subprocess.run(
            [
                "cargo",
                "clippy",
                "--manifest-path",
                str(cargo_toml),
                "--message-format=json",
            ],
            capture_output=True,
            text=True,
        )

        findings = []

        for line in result.stdout.splitlines():

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            if data.get("reason") != "compiler-message":
                continue

            message = data.get("message", {})

            level = message.get("level")

            if level not in ("error", "warning"):
                continue

            spans = message.get("spans", [])

            primary_span = None

            for span in spans:
                if span.get("is_primary"):
                    primary_span = span
                    break

            if primary_span is None and spans:
                primary_span = spans[0]

            if primary_span is None:
                continue

            code_info = message.get("code") or {}

            category = code_info.get(
                "code",
                "unknown"
            )

            findings.append(
                Finding(
                    language="rust",
                    file=primary_span.get(
                        "file_name",
                        str(file)
                    ),
                    line=primary_span.get(
                        "line_start",
                        1
                    ),
                    column=primary_span.get(
                        "column_start",
                        1
                    ),
                    category=category,
                    severity=self._get_severity(level),
                    message=message.get(
                        "message",
                        "Unknown Rust issue"
                    ),
                    analyzer=self.name,
                    confidence=0.95,
                )
            )

        return findings

    def _find_cargo_project(
        self,
        file: Path
    ) -> Path | None:

        current = file.resolve()

        if current.is_file():
            current = current.parent

        for directory in [current, *current.parents]:

            cargo_toml = directory / "Cargo.toml"

            if cargo_toml.exists():
                return cargo_toml

        return None

    def _get_severity(self, level: str) -> str:

        if level == "error":
            return "high"

        if level == "warning":
            return "medium"

        return "low"
