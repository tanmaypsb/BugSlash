import py_compile


class PythonVerifier:

    def verify(self, file_path: str) -> dict:
        try:
            py_compile.compile(
                file_path,
                doraise=True
            )

            return {
                "verified": True,
                "status": "valid",
                "message": "Python syntax is valid."
            }

        except py_compile.PyCompileError as error:
            return {
                "verified": False,
                "status": "invalid",
                "message": str(error)
            }
