from pathlib import Path

from language_detector import LanguageDetector

from analyzer_models.python_analyzer import PythonAnalyzer
from analyzer_models.javascript_analyzer import JavaScriptAnalyzer
from analyzer_models.cpp_analyzer import CppAnalyzer
from analyzer_models.java_analyzer import JavaAnalyzer
from analyzer_models.rust_analyzer import RustAnalyzer
from analyzer_models.go_analyzer import GoAnalyzer

from verification.python_verifier import PythonVerifier
from verification.verification_engine import VerificationEngine


class BugslashEngine:

    def __init__(self):
        self.language_detector = LanguageDetector()

        self.analyzers = {
            "python": PythonAnalyzer(),
            "javascript": JavaScriptAnalyzer(),
            "typescript": JavaScriptAnalyzer(),
            "cpp": CppAnalyzer(),
            "java": JavaAnalyzer(),
            "go": GoAnalyzer(),
            "rust": RustAnalyzer(),
        }

        self.verifiers = {
            "python": PythonVerifier(),
        }

        self.verification_engine = VerificationEngine()

    def analyze_file(self, file_path: str):
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        language = self.language_detector.detect(file_path)

        if language is None:
            return []

        analyzer = self.analyzers.get(language)

        if analyzer is None:
            return []

        findings = analyzer.analyze(file_path)

        verifier = self.verifiers.get(language)

        if verifier is None:
            return {
                "file": str(path),
                "language": language,
                "findings": findings,
                "verification": None,
                "verification_results": [],
            }

        verification = verifier.verify(file_path)

        verification_results = self.verification_engine.evaluate(
            findings,
            verification
        )

        return {
            "file": str(path),
            "language": language,
            "findings": findings,
            "verification": verification,
            "verification_results": verification_results,
        }

    def analyze_project(self, project_path: str):
        project = Path(project_path)

        if not project.exists():
            raise FileNotFoundError(
                f"Project not found: {project_path}"
            )

        results = []

        for file_path in project.rglob("*"):

            if not file_path.is_file():
                continue

            language = self.language_detector.detect(
                str(file_path)
            )

            if language is None:
                continue

            analyzer = self.analyzers.get(language)

            if analyzer is None:
                continue

            result = self.analyze_file(
                str(file_path)
            )

            results.append(result)

        return results
