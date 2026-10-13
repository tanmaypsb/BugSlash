import json
import re
import shutil
import tempfile
from pathlib import Path

from models.analyzer_error import AnalyzerExecutionError, run_analyzer
from models.finding import Finding
from models.go_source_fixes import GoFixError, remove_safe_unused


class GoAnalyzer:
    COMPILER_LINE = re.compile(r"(?:\./)?([^:\n]+\.go):(\d+):(\d+):\s*(.*)")

    def __init__(self):
        self.name = "staticcheck"

    def analyze(self, file_path: str) -> list[Finding]:
        source = Path(file_path).resolve()
        if shutil.which("staticcheck") is None:
            raise AnalyzerExecutionError(self.name, "required executable 'staticcheck' is unavailable")

        with tempfile.TemporaryDirectory(prefix="bugslash-go-analysis-") as temp_dir:
            workspace = Path(temp_dir)
            copied = workspace / source.name
            shutil.copyfile(source, copied)
            (workspace / "go.mod").write_text(
                "module bugslash.local/upload\n\ngo 1.20\n", encoding="utf-8"
            )
            initial = run_analyzer(
                self.name, ["staticcheck", "-f", "json", "./..."],
                cwd=workspace, timeout=90, expected=(0, 1),
            )
            findings, compile_messages = self._parse(initial, source)
            if compile_messages:
                try:
                    provisional = remove_safe_unused(
                        copied.read_text(encoding="utf-8"),
                        "\n".join(compile_messages),
                        preserve_lines=True,
                    )
                except GoFixError:
                    # Report compiler findings we do have. Unsafe source transformations
                    # are not used to stage a second analysis.
                    pass
                else:
                    copied.write_text(provisional, encoding="utf-8")
                    followup = run_analyzer(
                        self.name, ["staticcheck", "-f", "json", "./..."],
                        cwd=workspace, timeout=90, expected=(0, 1),
                    )
                    additional, remaining_compile = self._parse(followup, source)
                    if remaining_compile:
                        raise AnalyzerExecutionError(self.name, "compiler errors remained after provisional analysis staging")
                    findings.extend(x for x in additional if x.category != "compile")

        if initial.returncode != 0 and not findings:
            detail = (initial.stderr or initial.stdout or f"exit code {initial.returncode}").strip()
            raise AnalyzerExecutionError(self.name, detail[:1000])
        return findings

    def _parse(self, result, source):
        findings = []
        compile_messages = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AnalyzerExecutionError(self.name, "returned malformed JSON output") from exc
            if not isinstance(item, dict):
                raise AnalyzerExecutionError(self.name, "returned JSON in an unexpected format")
            code = item.get("code") or "staticcheck"
            message = item.get("message") or "Go analyzer finding"
            position = item.get("location") or item.get("position") or {}
            if not isinstance(position, dict):
                raise AnalyzerExecutionError(self.name, "returned a finding with malformed location data")
            if code == "compile":
                compile_messages.append(message)
                diagnostics = list(self.COMPILER_LINE.finditer(message))
                for diagnostic in diagnostics:
                    findings.append(self._finding(
                        source, "compile", diagnostic.group(4),
                        int(diagnostic.group(2)), int(diagnostic.group(3)), "high",
                    ))
                if not diagnostics:
                    raise AnalyzerExecutionError(self.name, message[:1000])
                continue
            row = position.get("line", 1)
            column = position.get("column", 1)
            if not isinstance(row, int) or not isinstance(column, int):
                raise AnalyzerExecutionError(self.name, "returned a finding with invalid source coordinates")
            findings.append(self._finding(
                source, code, message, max(row, 1), max(column, 1), self._get_severity(code),
            ))
        if result.returncode != 0 and not findings:
            detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
            raise AnalyzerExecutionError(self.name, detail[:1000])
        return findings, compile_messages

    def _finding(self, source, category, message, line, column, severity):
        return Finding(
            language="go", file=str(source), line=line, column=column,
            category=category, severity=severity, message=message,
            analyzer=self.name, confidence=0.95,
        )

    def _get_severity(self, category: str) -> str:
        return "high" if category.startswith(("SA", "compile")) else "medium"
