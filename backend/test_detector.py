from language_detector import LanguageDetector


detector = LanguageDetector()

files = [
    "example.py",
    "app.js",
    "main.cpp",
    "Main.java",
    "server.go",
    "main.rs",
    "unknown.xyz",
]

for file in files:
    language = detector.detect(file)
    print(f"{file} -> {language}")
