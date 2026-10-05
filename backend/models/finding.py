from dataclasses import dataclass


@dataclass
class Finding:
    language: str
    file: str
    line: int
    column: int
    category: str
    severity: str
    message: str
    analyzer: str
    confidence: float
