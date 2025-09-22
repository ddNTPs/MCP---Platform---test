"""Run both the customer API and the MCP wrapper in the same process."""

from __future__ import annotations

import threading
import time

from customer_api import server as customer_server
from mcp_platform import server as mcp_server


class ServerThread(threading.Thread):
    def __init__(self, target, name: str) -> None:
        super().__init__(daemon=True)
        self._target = target
        self._stopped = threading.Event()
        self.name = name

    def run(self) -> None:  # pragma: no cover - simple orchestration
        try:
            self._target()
        finally:
            self._stopped.set()

    def wait_until_stopped(self) -> None:
        self._stopped.wait()


def main() -> None:  # pragma: no cover - convenience script
    customer = ServerThread(lambda: customer_server.run(port=8001), name="customer-api")
    mcp = ServerThread(lambda: mcp_server.run(port=8010), name="mcp-platform")

    customer.start()
    time.sleep(0.3)
    mcp.start()

    print("Customer API available at http://127.0.0.1:8001/api/orders")
    print("MCP service manifest at http://127.0.0.1:8010/.well-known/mcp.json")
    print("Orders tool endpoint http://127.0.0.1:8010/mcp/tools/orders")

    try:
        while customer.is_alive() and mcp.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping demo...")


if __name__ == "__main__":
    main()
