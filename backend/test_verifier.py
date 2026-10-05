from verification.python_verifier import PythonVerifier


verifier = PythonVerifier()

result = verifier.verify("test_code/example.py")

print(result)
