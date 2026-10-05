from pathlib import Path


class LanguageDetector:

    EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
    }

    def detect(self, file_path: str) -> str | None:
        extension = Path(file_path).suffix.lower()

        return self.EXTENSIONS.get(extension)
