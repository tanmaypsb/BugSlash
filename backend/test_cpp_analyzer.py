from analyzer_models.cpp_analyzer import CppAnalyzer

analyzer = CppAnalyzer()

findings = analyzer.analyze(
    "test_code/cpp/example.cpp"
)

for finding in findings:
    print(finding)
