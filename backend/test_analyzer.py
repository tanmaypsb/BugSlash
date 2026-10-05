from analyzer_models.python_analyzer import PythonAnalyzer


analyzer = PythonAnalyzer()

findings = analyzer.analyze("test_code/example.py")

for finding in findings:
    print(finding)
