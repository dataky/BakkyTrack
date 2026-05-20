"""Player API endpoints."""
from typing import List, Dict, Any, Optional

from .types import PlayerData, PlayerXPInfo
from .playerid import PlayerID


class PlayersAPI:
    """Player-related API endpoints mixin."""

    async def get_ban_status(self, player_ids: List[PlayerID], timeout: Optional[float] = None) -> List[Any]:
        """Retrieve ban status information for given players.

        Args:
            player_ids: List of player IDs to check
            timeout: Optional request timeout in seconds

        Returns:
            List of ban messages
        """
        request = {"Players": [str(pid) for pid in player_ids]}
        result = await self.send_request_sync("Players/GetBanStatus v3", request, timeout)
        return result.get("BanMessages", [])

    async def get_profiles(self, player_ids: List[PlayerID], timeout: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve profile information for given players.

        Args:
            player_ids: List of player IDs
            timeout: Optional request timeout in seconds

        Returns:
            List of player data
        """
        request = {"PlayerIDs": [str(pid) for pid in player_ids]}
        result = await self.send_request_sync("Players/GetProfile v1", request, timeout)
        return result.get("PlayerData", [])

    async def get_xp(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Retrieve XP information for the authenticated player.

        Args:
            timeout: Optional request timeout in seconds

        Returns:
            Player XP information
        """
        request = {"PlayerID": str(self.local_player_id)}
        result = await self.send_request_sync("Players/GetXP v1", request, timeout)
        return result.get("XPInfoResponse", {})

    async def get_creator_code(self, timeout: Optional[float] = None) -> Any:
        """Retrieve creator code information for the authenticated player.

        Args:
            timeout: Optional request timeout in seconds

        Returns:
            Creator code information
        """
        result = await self.send_request_sync("Players/GetCreatorCode v1", {}, timeout)
        return result.get("CreatorCode")

    async def report_player(
        self,
        offender: PlayerID,
        reason_ids: List[int],
        game_id: str,
        timeout: Optional[float] = None,
    ) -> None:
        """Report a player.

        Args:
            offender: Player ID of the offender
            reason_ids: List of reason IDs for the report
            game_id: Game ID where the offense occurred
            timeout: Optional request timeout in seconds
        """
        request = {
            "Reports": [
                {
                    "Reporter": str(self.local_player_id),
                    "Offender": str(offender),
                    "ReasonIDs": reason_ids,
                    "ReportTimestamp": 0.0,
                }
            ],
            "GameID": game_id,
        }
        await self.send_request_sync("Players/Report v4", request, timeout)
