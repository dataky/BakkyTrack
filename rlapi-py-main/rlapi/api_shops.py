"""Shop API endpoints."""
from typing import List, Dict, Any, Optional

from .types import ShopID


class ShopsAPI:
    """Shop-related API endpoints mixin."""

    async def get_standard_shops(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve the list of available shops.

        Args:
            timeout: Optional request timeout in seconds

        Returns:
            Dictionary with 'Shops' key containing list of shops
        """
        return await self.send_request_sync("Shops/GetStandardShops v1", {}, timeout)

    async def get_shop_catalogue(self, shop_ids: List[ShopID], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve detailed information about items available in specified shops.

        Args:
            shop_ids: List of shop IDs
            timeout: Optional request timeout in seconds

        Returns:
            Dictionary with 'Catalogues' key containing shop catalogues
        """
        request = {"ShopIDs": shop_ids}
        return await self.send_request_sync("Shops/GetShopCatalogue v2", request, timeout)

    async def get_player_wallet(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve the authenticated player's wallet information.

        Args:
            timeout: Optional request timeout in seconds

        Returns:
            Dictionary with 'Currencies' key containing wallet currencies
        """
        request = {"PlayerID": str(self.local_player_id)}
        return await self.send_request_sync("Shops/GetPlayerWallet v1", request, timeout)

    async def get_shop_notifications(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve current shop notifications.

        Args:
            timeout: Optional request timeout in seconds

        Returns:
            Dictionary with 'ShopNotifications' key containing notifications
        """
        return await self.send_request_sync("Shops/GetShopNotifications v1", {}, timeout)
