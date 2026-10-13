import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from typing import Any


class LLMProviderError(RuntimeError):
    def __init__(self, message: str, *, unavailable: bool = True):
        super().__init__(message)
        self.unavailable = unavailable


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class OllamaClient:
    """Optional loopback-only Ollama JSON client using the Python standard library."""

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int = 60):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.timeout = timeout
        parsed = urlparse(self.base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise LLMProviderError("Ollama must use a plain local HTTP origin (localhost or loopback IP).")
        if not self.model.strip():
            raise LLMProviderError("OLLAMA_MODEL must name an installed Ollama model.")

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = json.dumps({
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode("utf-8")
        request = Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with build_opener(_RejectRedirects()).open(request, timeout=self.timeout) as response:
                raw_body = response.read(1_000_001)
                if len(raw_body) > 1_000_000:
                    raise LLMProviderError("Ollama response exceeded the 1 MB size limit.")
                body = json.loads(raw_body.decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                raise LLMProviderError("Ollama is running, but the configured model is not installed.") from error
            raise LLMProviderError(f"Ollama returned HTTP {error.code}.") from error
        except (URLError, TimeoutError, socket.timeout) as error:
            raise LLMProviderError("Ollama is unavailable or timed out. Local code analysis still works.") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LLMProviderError("Ollama returned malformed response data.") from error

        try:
            content = body["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise LLMProviderError("Ollama returned malformed structured output.") from error
        if not isinstance(parsed, dict):
            raise LLMProviderError("Ollama response must be a JSON object.")
        return parsed

    @property
    def provider_name(self) -> str:
        return "Ollama"
