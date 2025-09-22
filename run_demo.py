"""Run both the customer API and the MCP wrapper in the same process.

This helper is convenient for local demos, unit tests or to record screenshots.
"""

from __future__ import annotations

import signal
import threading
import time
from contextlib import contextmanager
from typing import Iterator

from customer_api.server import application as customer_app
from mcp_platform.server import DEFAULT_PORT, application as mcp_app


@contextmanager
def _serve(app, port: int) -> Iterator[None]:
    from wsgiref.simple_server import make_server

    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def main() -> None:
    customer_port = 8001
    mcp_port = DEFAULT_PORT

    print("Starting demo services...\n")
    with _serve(customer_app, customer_port), _serve(mcp_app, mcp_port):
        print("Customer API available at http://127.0.0.1:8001/api/orders")
        print("MCP platform available at http://127.0.0.1:8010/tools/orders")
        print("Press Ctrl+C to stop.")

        stop = threading.Event()

        def _handle_signal(signum, frame):
            print("\nShutting down...")
            stop.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        while not stop.is_set():
            time.sleep(0.2)


if __name__ == "__main__":
    main()
