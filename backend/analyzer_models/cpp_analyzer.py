import re
from pathlib import Path

from models.finding import Finding
from models.analyzer_error import AnalyzerExecutionError, run_analyzer


class CppAnalyzer:
    def __init__(self):
        self.name = "clang-tidy"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path).resolve()
        is_c = file.suffix.lower() in {".c", ".h"}
        language = "c" if is_c else "cpp"
        flags = ["-x", "c", "-std=c11"] if is_c else ["-x", "c++", "-std=c++17"]
        result = run_analyzer(
            self.name,
            ["clang-tidy", str(file), "--checks=clang-analyzer-*,bugprone-*,performance-*,readability-*", "--", *flags],
            timeout=90,
            expected=(0, 1),
        )

        findings = []
        diagnostics = (result.stdout + "\n" + result.stderr).splitlines()
        pattern = re.compile(r"^(.+):(\d+):(\d+): (warning|error): (.*?)(?: \[([^\]]+)\])?$")
        for line in diagnostics:
            match = pattern.match(line.strip())
            if not match:
                continue
            filename, row, column, level, message, category = match.groups()
            findings.append(
                Finding(
                    language=language,
                    file=filename,
                    line=int(row),
                    column=int(column),
                    category=category or ("clang-diagnostic-error" if level == "error" else "unknown"),
                    severity="high" if level == "error" else "medium",
                    message=message.strip(),
                    analyzer=self.name,
                    confidence=0.90,
                )
            )
        if result.returncode != 0 and not findings:
            detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
            raise AnalyzerExecutionError(self.name, detail[:1000])
        return findings
