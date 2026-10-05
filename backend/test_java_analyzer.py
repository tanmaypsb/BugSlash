from analyzer_models.java_analyzer import JavaAnalyzer


analyzer = JavaAnalyzer()

findings = analyzer.analyze(
    "test_code/java/Example.java"
)

for finding in findings:
    print(finding)
