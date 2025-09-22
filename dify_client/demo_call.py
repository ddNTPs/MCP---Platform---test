"""Demo script that exercises the MCP HTTP service using urllib."""

from __future__ import annotations

import json
import os
import urllib.request

MCP_BASE = os.environ.get("MCP_BASE", "http://127.0.0.1:8010")
API_KEY = os.environ.get("MCP_API_KEY")


def main() -> None:
    url = f"{MCP_BASE}/mcp/tools/orders"
    request = urllib.request.Request(url, method="POST")
    body = json.dumps({"order_id": "A1001"}).encode("utf-8")
    request.data = body
    request.add_header("Content-Type", "application/json")
    if API_KEY:
        request.add_header("X-MCP-Key", API_KEY)

    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    print("Response from MCP platform:\n")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
