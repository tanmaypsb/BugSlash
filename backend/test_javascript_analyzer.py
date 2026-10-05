from analyzer_models.javascript_analyzer import JavaScriptAnalyzer


analyzer = JavaScriptAnalyzer()

findings = analyzer.analyze(
    "test_code/javascript/example.js"
)

for finding in findings:
    print(finding)
