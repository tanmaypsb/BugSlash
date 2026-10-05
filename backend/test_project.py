from engine import BugslashEngine


engine = BugslashEngine()

findings = engine.analyze_project("test_code")

for finding in findings:
    print(finding)
