from analyzer_models.rust_analyzer import RustAnalyzer


analyzer = RustAnalyzer()

findings = analyzer.analyze(
    "test_code/rust_project/src/main.rs"
)

for finding in findings:
    print(finding)
