from engine import BugslashEngine


engine = BugslashEngine()

result = engine.analyze_file("test_code/example.py")

print("File:", result["file"])
print("Language:", result["language"])

print("\nFindings:")

for finding in result["findings"]:
    print(finding)

print("\nVerification Evidence:")
print(result["verification"])

print("\nVerification Results:")

for verification in result["verification_results"]:
    print(verification)
