"""Simple customer-facing API implemented with only the Python standard library."""

from __future__ import annotations

import json
from typing import Callable, Iterable, Tuple

from . import data

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


def application(environ: dict, start_response: StartResponse) -> Iterable[bytes]:
    """WSGI entry point for the demo API."""

    path = environ.get("PATH_INFO") or "/"

    if path == "/" or path == "/health":
        status, headers, body = _json_response(
            "200 OK",
            {"status": "healthy", "service": "customer-api"},
        )
    elif path == "/api/orders":
        status, headers, body = _json_response("200 OK", data.list_orders_payload())
    elif path.startswith("/api/orders/"):
        order_id = path.rsplit("/", 1)[-1]
        order = data.get_order_payload(order_id)
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
