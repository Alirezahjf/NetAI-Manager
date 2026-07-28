"""Central registry for platform accounts and their live clients."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, PlatformType


class AccountManager:
    """Keeps track of all connected platform instances."""

    def __init__(self) -> None:
        # key: "{platform}:{account_id}"
        self._clients: Dict[str, BasePlatform] = {}

    def _key(self, platform: PlatformType | str, account_id: str) -> str:
        return f"{platform}:{account_id}"

    def register(self, client: BasePlatform) -> None:
        key = self._key(client.platform, client.account_id)
        self._clients[key] = client
        logger.info(f"Registered account {key}")

    def unregister(self, platform: PlatformType | str, account_id: str) -> None:
        key = self._key(platform, account_id)
        if key in self._clients:
            del self._clients[key]
            logger.info(f"Unregistered account {key}")

    def get(self, platform: PlatformType | str, account_id: str) -> Optional[BasePlatform]:
        return self._clients.get(self._key(platform, account_id))

    def list_accounts(self, platform: Optional[PlatformType | str] = None) -> List[dict]:
        result = []
        for key, client in self._clients.items():
            if platform and str(client.platform) != str(platform):
                continue
            result.append(
                {
                    "key": key,
                    "platform": str(client.platform),
                    "account_id": client.account_id,
                    "display_name": client.display_name,
                    "is_connected": client.is_connected,
                }
            )
        return result

    def all_clients(self) -> List[BasePlatform]:
        return list(self._clients.values())

    async def disconnect_all(self) -> None:
        for client in list(self._clients.values()):
            try:
                await client.disconnect()
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Error disconnecting {client}: {exc}")
        self._clients.clear()


account_manager = AccountManager()
