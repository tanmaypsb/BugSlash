import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from models.finding import Finding
from models.analyzer_error import AnalyzerExecutionError, run_analyzer


class JavaAnalyzer:
    def __init__(self):
        self.name = "spotbugs"

    def analyze(self, file_path: str) -> list[Finding]:
        source = Path(file_path).resolve()
        backend = Path(__file__).resolve().parents[1]
        if shutil.which("mvn") is None:
            raise AnalyzerExecutionError(self.name, "required executable 'mvn' is unavailable")

        with tempfile.TemporaryDirectory(prefix="bugslash-java-analysis-") as temp_dir:
            workspace = Path(temp_dir)
            shutil.copyfile(backend / "pom.xml", workspace / "pom.xml")
            java_dir = workspace / "src" / "main" / "java"
            java_dir.mkdir(parents=True)
            copied = java_dir / source.name
            shutil.copyfile(source, copied)
            run_analyzer(
                self.name,
                ["mvn", "-q", "-f", str(workspace / "pom.xml"), "clean", "compile", "spotbugs:spotbugs"],
                cwd=workspace,
                timeout=180,
            )
            report = workspace / "target" / "spotbugsXml.xml"
            if not report.is_file():
                raise AnalyzerExecutionError(self.name, "SpotBugs did not produce its XML report")
            try:
                root = ET.parse(report).getroot()
            except ET.ParseError as exc:
                raise AnalyzerExecutionError(self.name, "SpotBugs produced malformed XML") from exc

        findings = []
        for bug in root.findall("BugInstance"):
            code = bug.get("type", "unknown")
            priority = bug.get("priority", "3")
            short = bug.findtext("ShortMessage", default="Unknown Java issue")
            message = bug.findtext("LongMessage", default=short)
            source_line = bug.find(".//SourceLine[@role='SOURCE_LINE_DEREF']")
            if source_line is None:
                source_line = bug.find(".//SourceLine")
            findings.append(
                Finding(
                    language="java",
                    file=str(source),
                    line=int(source_line.get("start", "1")) if source_line is not None else 1,
                    column=0,
                    category=code,
                    severity=self._get_severity(priority),
                    message=message,
                    analyzer=self.name,
                    confidence=0.95,
                )
            )
        return findings

    def _get_severity(self, priority: str) -> str:
        return {"1": "high", "2": "medium"}.get(priority, "low")
