"""Shared sample data used by the customer API and the MCP wrapper."""

from __future__ import annotations

import time
from typing import Any

_SAMPLE_ORDERS: list[dict[str, Any]] = [
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
    {
        "order_id": "A1003",
        "status": "ready_for_pickup",
        "total": 1499.0,
        "currency": "CNY",
        "items": [
            {"sku": "SKU-9", "quantity": 1, "unit_price": 1499.0},
        ],
    },
]


def list_orders_payload() -> dict[str, Any]:
    """Return the payload used for ``/api/orders``."""

    generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {"generated_at": generated_at, "orders": list(_SAMPLE_ORDERS)}


def get_order_payload(order_id: str) -> dict[str, Any] | None:
    """Return a single order dict if it exists."""

    for order in _SAMPLE_ORDERS:
        if order["order_id"] == order_id:
            return dict(order)
    return None
