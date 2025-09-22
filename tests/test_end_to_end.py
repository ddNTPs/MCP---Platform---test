from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.request
from contextlib import contextmanager

from customer_api.server import application as customer_app
from mcp_platform.server import DEFAULT_PORT, application as mcp_app


@contextmanager
def serve(app, port: int):
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


class EndToEndTestCase(unittest.TestCase):
    def test_orders_flow(self) -> None:
        with serve(customer_app, 8001), serve(mcp_app, DEFAULT_PORT):
            time.sleep(0.1)  # allow servers to bind
            request = urllib.request.Request(
                f"http://127.0.0.1:{DEFAULT_PORT}/tools/orders",
                headers={"X-MCP-Key": "mcp-demo-key"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))

        self.assertIn("metadata", data)
        self.assertIn("data", data)
        self.assertIn("orders", data["data"])
        self.assertGreater(len(data["data"]["orders"]), 0)


if __name__ == "__main__":
    unittest.main()
