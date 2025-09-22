import json
import threading
import time
import unittest
import urllib.request
from contextlib import contextmanager

from customer_api.server import application as customer_app
from mcp_platform import server as mcp_server


@contextmanager
def serve_customer(port: int):
    from wsgiref.simple_server import make_server

    server = make_server("127.0.0.1", port, customer_app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@contextmanager
def serve_mcp(port: int):
    server = mcp_server.make_server("127.0.0.1", port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class EndToEndTestCase(unittest.TestCase):
    def test_manifest_and_orders_flow(self) -> None:
        with serve_customer(8001), serve_mcp(mcp_server.DEFAULT_PORT):
            time.sleep(0.2)

            with urllib.request.urlopen(
                f"http://127.0.0.1:{mcp_server.DEFAULT_PORT}/.well-known/mcp.json", timeout=5
            ) as response:
                manifest = json.loads(response.read().decode("utf-8"))

            self.assertIn("tools", manifest)
            self.assertEqual(manifest["tools"][0]["name"], "orders")

            with urllib.request.urlopen(
                f"http://127.0.0.1:{mcp_server.DEFAULT_PORT}/mcp/tools/orders", timeout=5
            ) as response:
                list_payload = json.loads(response.read().decode("utf-8"))

            self.assertEqual(list_payload["tool"], "orders")
            self.assertIn("orders", list_payload["data"])

            url = f"http://127.0.0.1:{mcp_server.DEFAULT_PORT}/mcp/tools/orders"
            body = json.dumps({"order_id": "A1001"}).encode("utf-8")
            request = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                detail_payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(detail_payload["metadata"]["source"], "customer-api")
        self.assertEqual(detail_payload["data"]["order_id"], "A1001")

    def test_orders_fallback_when_customer_api_unavailable(self) -> None:
        with serve_mcp(mcp_server.DEFAULT_PORT):
            time.sleep(0.2)
            with urllib.request.urlopen(
                f"http://127.0.0.1:{mcp_server.DEFAULT_PORT}/mcp/tools/orders", timeout=5
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(payload["metadata"]["source"], "sample-data")
        self.assertGreater(len(payload["data"]["orders"]), 0)


if __name__ == "__main__":
    unittest.main()
