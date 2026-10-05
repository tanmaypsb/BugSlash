from analyzer_models.go_analyzer import GoAnalyzer


analyzer = GoAnalyzer()

findings = analyzer.analyze(
    "test_code/go/example.go"
)

for finding in findings:
    print(finding)
