"""Simple customer-facing API implemented with only the Python standard library.

The module exposes a WSGI application so it can be served by ``wsgiref.simple_server``
for local demos or unit tests.  It mimics a small portion of a customer system
that will later be wrapped by the MCP platform.
"""

from __future__ import annotations

import json
import time
from typing import Callable, Iterable, Tuple

Headers = list[Tuple[str, str]]
StartResponse = Callable[[str, Headers], Callable[[bytes], object]]


def _json_response(status: str, payload: dict) -> Tuple[str, Headers, bytes]:
    body = json.dumps(payload).encode("utf-8")
    headers: Headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    return status, headers, body


def _not_found(path: str) -> Tuple[str, Headers, bytes]:
    return _json_response(
        "404 Not Found",
        {
            "error": "not_found",
            "message": f"The resource {path!r} does not exist in the customer API.",
        },
    )


def _orders() -> dict:
    """Return a deterministic payload for the ``/api/orders`` endpoint."""

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "generated_at": now,
        "orders": [
            {
                "order_id": "A1001",
                "status": "processing",
                "total": 512.43,
                "currency": "CNY",
                "items": [
                    {"sku": "SKU-1", "quantity": 2, "unit_price": 199.0},
                    {"sku": "SKU-5", "quantity": 1, "unit_price": 114.43},
                ],
            },
            {
                "order_id": "A1002",
                "status": "shipped",
                "total": 79.99,
                "currency": "CNY",
                "items": [
                    {"sku": "SKU-8", "quantity": 4, "unit_price": 19.99},
                ],
            },
        ],
    }


def _order(order_id: str) -> dict | None:
    for order in _orders()["orders"]:
        if order["order_id"] == order_id:
            return order
    return None


def application(environ: dict, start_response: StartResponse) -> Iterable[bytes]:
    """WSGI entry point for the demo API."""

    path = environ.get("PATH_INFO") or "/"

    if path == "/" or path == "/health":
        status, headers, body = _json_response(
            "200 OK",
            {"status": "healthy", "service": "customer-api"},
        )
    elif path == "/api/orders":
        status, headers, body = _json_response("200 OK", _orders())
    elif path.startswith("/api/orders/"):
        order_id = path.rsplit("/", 1)[-1]
        order = _order(order_id)
        if order is None:
            status, headers, body = _not_found(path)
        else:
            status, headers, body = _json_response("200 OK", order)
    else:
        status, headers, body = _not_found(path)

    write = start_response(status, headers)
    write(body)
    return []


def run(host: str = "127.0.0.1", port: int = 8001) -> None:
    """Run the server using ``wsgiref.simple_server`` for local testing."""

    from wsgiref.simple_server import make_server

    with make_server(host, port, application) as httpd:
        print(f"Customer API listening on http://{host}:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    run()
