"""HTTP MCP wrapper that exposes the customer API as MCP tools."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from customer_api import data as sample_data

DEFAULT_PORT = 8010
_MANIFEST_SCHEMA_VERSION = "2024-05-24"


class RequestLog:
    """Thread-safe request log for demo observability."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def record(self, *, method: str, path: str, status: int, metadata: dict[str, Any] | None) -> None:
        entry = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": method,
            "path": path,
            "status": status,
        }
        if metadata:
            entry["metadata"] = metadata
        with self._lock:
            self._entries.append(entry)

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return {"entries": list(self._entries)}


REQUEST_LOG = RequestLog()


def _customer_api_base() -> str:
    return os.environ.get("CUSTOMER_API_BASE", "http://127.0.0.1:8001")


def _expected_api_key() -> str | None:
    key = os.environ.get("MCP_API_KEY")
    return key or None


def _fallback_from_sample(order_id: str | None) -> tuple[int, dict[str, Any]]:
    if order_id:
        order = sample_data.get_order_payload(order_id)
        if order is None:
            return HTTPStatus.NOT_FOUND, {
                "error": "not_found",
                "message": f"Order {order_id} was not found in sample data.",
            }
        return HTTPStatus.OK, order
    return HTTPStatus.OK, sample_data.list_orders_payload()


def _fetch_orders(order_id: str | None) -> tuple[int, dict[str, Any], dict[str, Any]]:
    path = "/api/orders" + (f"/{order_id}" if order_id else "")
    base_url = _customer_api_base()
    url = f"{base_url}{path}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            charset = response.headers.get_content_charset("utf-8")
            payload = json.loads(response.read().decode(charset))
            metadata = {"source": "customer-api", "url": url}
            return response.status, payload, metadata
    except urllib.error.HTTPError as exc:
        try:
            charset = exc.headers.get_content_charset("utf-8")
            payload = json.loads(exc.read().decode(charset or "utf-8"))
        except Exception:  # pragma: no cover - defensive
            payload = {"error": "customer_api_error", "message": str(exc)}
        metadata = {
            "source": "customer-api",
            "url": url,
            "status": exc.code,
        }
        return exc.code, payload, metadata
    except urllib.error.URLError as exc:
        status, payload = _fallback_from_sample(order_id)
        reason = getattr(exc, "reason", exc)
        metadata = {
            "source": "sample-data",
            "url": url,
            "customer_api_error": str(reason),
        }
        return status, payload, metadata


def _manifest() -> dict[str, Any]:
    return {
        "schema_version": _MANIFEST_SCHEMA_VERSION,
        "name": "demo-orders-mcp",
        "version": "1.0.0",
        "description": "Expose customer orders via the Model Context Protocol.",
        "tools": [
            {
                "name": "orders",
                "description": "List all orders or fetch a single order when `order_id` is provided.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "Optional order identifier. When set the tool returns only that order.",
                        }
                    },
                },
            }
        ],
    }


class MCPRequestHandler(BaseHTTPRequestHandler):
    server_version = "DemoMCP/1.0"

    def _send_json(self, status: int, payload: dict[str, Any], *, metadata: dict[str, Any] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        REQUEST_LOG.record(method=self.command, path=self.path, status=status, metadata=metadata)

    def _require_api_key(self) -> bool:
        expected = _expected_api_key()
        if expected is None:
            return True
        provided = self.headers.get("X-MCP-Key")
        if provided == expected:
            return True
        self._send_json(
            HTTPStatus.UNAUTHORIZED,
            {
                "error": "unauthorised",
                "message": "Missing or invalid X-MCP-Key header.",
            },
            metadata={"reason": "invalid_api_key"},
        )
        return False

    def do_OPTIONS(self) -> None:  # pragma: no cover - simple boilerplate
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-MCP-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/mcp/health":
            self._send_json(HTTPStatus.OK, {"status": "healthy", "service": "mcp-platform"})
        elif parsed.path == "/.well-known/mcp.json":
            self._send_json(HTTPStatus.OK, _manifest())
        elif parsed.path == "/mcp/logs":
            self._send_json(HTTPStatus.OK, REQUEST_LOG.as_dict())
        elif parsed.path == "/mcp/tools/orders":
            if not self._require_api_key():
                return
            params = parse_qs(parsed.query)
            order_id = params.get("order_id", [None])[0]
            self._handle_orders(order_id)
        else:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "error": "not_found",
                    "message": f"Unknown resource {parsed.path!r} on the MCP platform.",
                },
            )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/mcp/tools/orders":
            if not self._require_api_key():
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "invalid_length", "message": "Invalid Content-Length header."},
                )
                return

            raw_body = self.rfile.read(length) if length else b"{}"
            if not raw_body:
                body: dict[str, Any] = {}
            else:
                try:
                    body = json.loads(raw_body.decode("utf-8"))
                except json.JSONDecodeError:
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {
                            "error": "invalid_json",
                            "message": "Request body must be valid JSON.",
                        },
                    )
                    return
            order_id = body.get("order_id")
            if order_id is not None and not isinstance(order_id, str):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {
                        "error": "invalid_order_id",
                        "message": "order_id must be a string when provided.",
                    },
                )
                return
            self._handle_orders(order_id)
        else:
            self._send_json(
                HTTPStatus.NOT_FOUND,
                {
                    "error": "not_found",
                    "message": f"Unknown resource {parsed.path!r} on the MCP platform.",
                },
            )

    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - suppress default logging
        return

    def _handle_orders(self, order_id: str | None) -> None:
        status, payload, metadata = _fetch_orders(order_id)
        if status >= 400:
            response = {
                "error": payload.get("error", "customer_api_error"),
                "message": payload.get("message", "Customer API returned an error."),
                "data": payload,
            }
            self._send_json(status, response, metadata=metadata)
            return

        response = {
            "tool": "orders",
            "metadata": metadata,
            "data": payload,
        }
        self._send_json(status, response, metadata=metadata)


def make_server(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    """Create a ThreadingHTTPServer instance for embedding or tests."""

    return ThreadingHTTPServer((host, port), MCPRequestHandler)


def run(host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    server = make_server(host, port)
    try:
        print(f"MCP platform listening on http://{host}:{port}")
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - interactive use
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
