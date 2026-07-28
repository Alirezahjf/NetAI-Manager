"""WooCommerce REST API helper (orders / products lookup for auto replies)."""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from loguru import logger

from app.core.settings_store import load_settings


class WooCommerceClient:
    def __init__(self) -> None:
        s = load_settings().get("woocommerce", {})
        self.enabled = bool(s.get("enabled"))
        self.base = (s.get("store_url") or "").rstrip("/") + "/"
        self.key = s.get("consumer_key") or ""
        self.secret = s.get("consumer_secret") or ""

    def _auth(self) -> tuple[str, str]:
        return self.key, self.secret

    async def test_connection(self) -> dict[str, Any]:
        if not self.enabled or not self.base or not self.key:
            return {"ok": False, "error": "WooCommerce is not configured"}
        url = urljoin(self.base, "wp-json/wc/v3/system_status")
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(url, auth=self._auth())
                if resp.status_code == 401:
                    # some stores block system_status — try products
                    resp = await client.get(
                        urljoin(self.base, "wp-json/wc/v3/products?per_page=1"),
                        auth=self._auth(),
                    )
                resp.raise_for_status()
                return {"ok": True, "status": resp.status_code}
            except Exception as exc:
                logger.error(f"Woo test failed: {exc}")
                return {"ok": False, "error": str(exc)}

    async def get_order(self, order_id: int | str) -> Optional[dict]:
        if not self.enabled:
            return None
        url = urljoin(self.base, f"wp-json/wc/v3/orders/{order_id}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, auth=self._auth())
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def search_orders_by_phone(self, phone: str) -> list[dict]:
        if not self.enabled:
            return []
        url = urljoin(self.base, "wp-json/wc/v3/orders")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                params={"search": phone, "per_page": 5},
                auth=self._auth(),
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []

    async def format_order_summary(self, order_id: int | str) -> str:
        order = await self.get_order(order_id)
        if not order:
            return f"سفارش {order_id} پیدا نشد."
        status = order.get("status", "?")
        total = order.get("total", "?")
        currency = order.get("currency", "")
        name = f"{order.get('billing', {}).get('first_name', '')} {order.get('billing', {}).get('last_name', '')}".strip()
        return (
            f"سفارش #{order.get('id')}\n"
            f"وضعیت: {status}\n"
            f"مبلغ: {total} {currency}\n"
            f"مشتری: {name or '—'}"
        )


woo = WooCommerceClient
