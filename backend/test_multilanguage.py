from engine import BugslashEngine


engine = BugslashEngine()

files = [
    "test_code/example.py",
    "test_code/javascript/example.js",
]

for file in files:
    print("\n" + "=" * 60)
    print("Analyzing:", file)
    print("=" * 60)

    result = engine.analyze_file(file)

    print("Language:", result["language"])

    print("\nFindings:")

    for finding in result["findings"]:
        print(finding)
