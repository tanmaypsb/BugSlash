class AnalyzerExecutionError(RuntimeError):
    """Raised when analysis could not complete reliably for a source file."""

    def __init__(self, analyzer: str, message: str):
        self.analyzer = analyzer
        self.message = message
        super().__init__(f"{analyzer} analysis failed: {message}")


def run_analyzer(analyzer: str, command: list[str], *, cwd=None, timeout=60, expected=(0,)):
    import subprocess
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise AnalyzerExecutionError(analyzer, f"required executable '{command[0]}' is unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise AnalyzerExecutionError(analyzer, f"timed out after {timeout} seconds") from exc
    if result.returncode not in expected:
        detail = (result.stderr or result.stdout or f"exit code {result.returncode}").strip()
        raise AnalyzerExecutionError(analyzer, detail[:1000])
    return result


def parse_json_output(analyzer: str, output: str, *, expected_type):
    import json
    try:
        value = json.loads(output)
    except json.JSONDecodeError as exc:
        raise AnalyzerExecutionError(analyzer, f"returned malformed JSON: {exc.msg}") from exc
    if not isinstance(value, expected_type):
        raise AnalyzerExecutionError(analyzer, "returned JSON in an unexpected format")
    return value
