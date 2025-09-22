"""Utility script that demonstrates how Dify (or any HTTP client) can call the
wrapped MCP endpoint.

The script sends a GET request with the required ``X-MCP-Key`` header and
prints the transformed response in a human-friendly way.  It uses only the
standard library so it can run in this execution environment.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

MCP_BASE = os.environ.get("MCP_BASE", "http://127.0.0.1:8010")
API_KEY = os.environ.get("MCP_API_KEY", "mcp-demo-key")


def main() -> None:
    url = f"{MCP_BASE}/tools/orders"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "X-MCP-Key": API_KEY,
            "User-Agent": "dify-demo-client/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode(response.headers.get_content_charset("utf-8")))
    except urllib.error.URLError as exc:  # pragma: no cover - demo script
        raise SystemExit(f"Failed to call MCP endpoint {url}: {exc}") from exc

    print("Response from MCP platform:\n")
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
