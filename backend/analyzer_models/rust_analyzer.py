import json
import re
import shutil
import tempfile
from pathlib import Path

from models.finding import Finding
from models.analyzer_error import AnalyzerExecutionError, run_analyzer


class RustAnalyzer:
    def __init__(self):
        self.name = "clippy"

    def analyze(self, file_path: str) -> list[Finding]:
        source = Path(file_path).resolve()
        if shutil.which("cargo") is None:
            raise AnalyzerExecutionError(self.name, "required executable 'cargo' is unavailable")

        with tempfile.TemporaryDirectory(prefix="bugslash-rust-analysis-") as temp_dir:
            workspace = Path(temp_dir)
            source_dir = workspace / "src"
            source_dir.mkdir()
            is_binary = bool(re.search(r"\bfn\s+main\s*\(", source.read_text(encoding="utf-8")))
            copied = source_dir / ("main.rs" if is_binary else "lib.rs")
            shutil.copyfile(source, copied)
            manifest = workspace / "Cargo.toml"
            manifest.write_text(
                '[package]\nname = "bugslash_upload"\nversion = "0.1.0"\nedition = "2021"\n',
                encoding="utf-8",
            )
            result = run_analyzer(
                self.name,
                ["cargo", "clippy", "--manifest-path", str(manifest), "--message-format=json"],
                cwd=workspace,
                timeout=180,
                expected=(0, 1, 101),
            )

        findings = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AnalyzerExecutionError(self.name, "returned malformed Cargo JSON output") from exc
            if item.get("reason") != "compiler-message":
                continue
            message = item.get("message", {})
            level = message.get("level")
            if level not in {"warning", "error"}:
                continue
            spans = message.get("spans") or []
            primary = next((span for span in spans if span.get("is_primary")), spans[0] if spans else {})
            code = message.get("code") or {}
            findings.append(
                Finding(
                    language="rust",
                    file=str(source),
                    line=primary.get("line_start", 1),
                    column=primary.get("column_start", 1),
                    category=code.get("code") or "rustc-diagnostic",
                    severity=self._get_severity(level),
                    message=message.get("message", "Unknown Rust analyzer finding"),
                    analyzer=self.name,
                    confidence=0.95,
                )
            )
        if result.returncode != 0 and not findings:
            detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
            raise AnalyzerExecutionError(self.name, detail[:1000])
        return findings

    def _get_severity(self, level: str) -> str:
        return "high" if level == "error" else "medium" if level == "warning" else "low"
