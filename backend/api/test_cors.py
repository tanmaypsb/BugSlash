import asyncio
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@127.0.0.1:5432/test")

from api.main import app


class CorsOriginTests(unittest.TestCase):
    def request(self, origin):
        messages = []
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/health",
            "raw_path": b"/health",
            "query_string": b"",
            "headers": [(b"host", b"testserver"), (b"origin", origin.encode())],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(app(scope, receive, send))
        response = next(message for message in messages if message["type"] == "http.response.start")
        return response["status"], {key.decode().lower(): value.decode() for key, value in response["headers"]}

    def test_local_and_production_origins_are_allowed_and_unrelated_origin_is_rejected(self):
        for origin in ("http://localhost:5173", "https://bug-slash.vercel.app"):
            with self.subTest(origin=origin):
                status, headers = self.request(origin)
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("access-control-allow-origin"), origin)
                self.assertEqual(headers.get("access-control-allow-credentials"), "true")

        status, headers = self.request("https://unrelated.example")
        self.assertEqual(status, 200)
        self.assertNotIn("access-control-allow-origin", headers)


if __name__ == "__main__":
    unittest.main()
