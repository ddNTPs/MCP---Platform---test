"""Minimal MCP-like wrapper around the customer API.

The goal of this module is to demonstrate how an organisation might wrap its
internal/customer API with a layer that provides:

* Normalised output format and metadata that is friendly to LLM tooling.
* Lightweight authentication using an API key in the ``X-MCP-Key`` header.
* Request logging to make it easy to audit calls coming from the AI platform.

The implementation uses only the Python standard library so it can run in the
execution environment provided for the kata.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from typing import Callable, Iterable, Tuple

Headers = list[Tuple[str, str]]
StartResponse = Callable[[str, Headers], Callable[[bytes], object]]

DEFAULT_PORT = 8010


class RequestLogger:
    """Thread-safe, in-memory request logger used for the demo."""

    def __init__(self) -> None:
        self._entries: list[str] = []
        self._lock = threading.Lock()

    def log(self, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        line = f"[{timestamp}] {message}"
        with self._lock:
            self._entries.append(line)
        print(line, file=sys.stderr)

    def as_dict(self) -> dict:
        with self._lock:
            return {"entries": list(self._entries)}


LOGGER = RequestLogger()


def _json_response(status: HTTPStatus, payload: dict) -> Tuple[str, Headers, bytes]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers: Headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    return f"{status.value} {status.phrase}", headers, body


def _error(status: HTTPStatus, message: str, *, code: str) -> Tuple[str, Headers, bytes]:
    return _json_response(status, {"error": code, "message": message})


def _require_api_key(environ: dict) -> bool:
    expected_key = os.environ.get("MCP_API_KEY", "mcp-demo-key")
    provided = environ.get("HTTP_X_MCP_KEY")
    return provided == expected_key


def _call_customer_api(path: str) -> Tuple[int, dict]:
    base_url = os.environ.get("CUSTOMER_API_BASE", "http://127.0.0.1:8001")
    url = f"{base_url}{path}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            charset = response.headers.get_content_charset("utf-8")
            payload = json.loads(response.read().decode(charset))
            return response.status, payload
    except urllib.error.HTTPError as exc:  # Customer API returned error
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:  # pragma: no cover - defensive
            payload = {"error": "customer_api_error", "message": str(exc)}
        return exc.code, payload
    except urllib.error.URLError as exc:
        return 503, {
            "error": "unreachable",
            "message": f"Failed to reach customer API at {url}: {exc.reason}",
        }


def application(environ: dict, start_response: StartResponse) -> Iterable[bytes]:
    path = environ.get("PATH_INFO") or "/"

    if path == "/" or path == "/health":
        status, headers, body = _json_response(
            HTTPStatus.OK,
            {
                "status": "healthy",
                "service": "mcp-platform",
                "customer_api": os.environ.get("CUSTOMER_API_BASE", "http://127.0.0.1:8001"),
            },
        )
    elif path == "/logs":
        status, headers, body = _json_response(HTTPStatus.OK, LOGGER.as_dict())
    elif path.startswith("/tools/orders"):
        if not _require_api_key(environ):
            status, headers, body = _error(
                HTTPStatus.UNAUTHORIZED,
                "Missing or invalid X-MCP-Key header.",
                code="unauthorised",
            )
        else:
            LOGGER.log(f"orders endpoint requested: path={path}")
            customer_path = "/api/orders"
            if path != "/tools/orders":
                suffix = path[len("/tools") :]
                customer_path = suffix.replace("/tools", "")
                customer_path = customer_path.replace("/orders", "/api/orders", 1)
            status_code, payload = _call_customer_api(customer_path)
            metadata = {
                "source": "customer-api",
                "transformed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            try:
                status_enum = HTTPStatus(status_code)
            except ValueError:  # pragma: no cover - defensive
                status_enum = HTTPStatus.BAD_GATEWAY
            status, headers, body = _json_response(
                status_enum,
                {"metadata": metadata, "data": payload},
            )
    else:
        status, headers, body = _error(
            HTTPStatus.NOT_FOUND,
            f"Unknown resource {path!r} on MCP platform.",
            code="not_found",
        )

    writer = start_response(status, headers)
    writer(body)
    return []


def run(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    from wsgiref.simple_server import make_server

    with make_server(host, port, application) as httpd:
        print(f"MCP platform listening on http://{host}:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    run()
