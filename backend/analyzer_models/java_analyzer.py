import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from models.finding import Finding


class JavaAnalyzer:

    def __init__(self):
        self.name = "spotbugs"

    def analyze(self, file_path: str) -> list[Finding]:
        file = Path(file_path)

        # Make sure the Java source is available to Maven
        maven_file = Path("src/main/java") / file.name
        maven_file.parent.mkdir(parents=True, exist_ok=True)

        maven_file.write_text(
            file.read_text()
        )

        # Compile Java and run SpotBugs
        result = subprocess.run(
            [
                "mvn",
                "clean",
                "compile",
                "spotbugs:spotbugs",
                "-q",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return []

        xml_file = Path("target/spotbugsXml.xml")

        if not xml_file.exists():
            return []

        try:
            root = ET.parse(xml_file).getroot()
        except ET.ParseError:
            return []

        findings = []

        for bug in root.findall("BugInstance"):

            bug_type = bug.get("type", "unknown")
            priority = bug.get("priority", "3")

            short_message = bug.findtext(
                "ShortMessage",
                default="Unknown Java issue"
            )

            long_message = bug.findtext(
                "LongMessage",
                default=short_message
            )

            source_line = bug.find(
                ".//SourceLine[@role='SOURCE_LINE_DEREF']"
            )

            if source_line is None:
                source_line = bug.find(".//SourceLine")

            if source_line is None:
                continue

            source_file = source_line.get(
                "sourcefile",
                file.name
            )

            line = int(
                source_line.get("start", "1")
            )

            severity = self._get_severity(priority)

            findings.append(
                Finding(
                    language="java",
                    file=source_file,
                    line=line,
                    column=0,
                    category=bug_type,
                    severity=severity,
                    message=long_message,
                    analyzer=self.name,
                    confidence=0.95,
                )
            )

        return findings

    def _get_severity(self, priority: str) -> str:

        if priority == "1":
            return "high"

        if priority == "2":
            return "medium"

        return "low"
