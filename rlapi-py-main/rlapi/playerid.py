"""PlayerID module for Rocket League API."""
from enum import Enum
from typing import Tuple


class Platform(str, Enum):
    """Gaming platform enumeration."""

    EPIC = "Epic"
    STEAM = "Steam"
    PS4 = "PS4"
    XBOX = "XboxOne"
    SWITCH = "Switch"


class PlayerID(str):
    """PlayerID represents a unique player identifier in the format 'Platform|ID|0'."""

    def __new__(cls, value: str):
        """Create a new PlayerID instance."""
        return super().__new__(cls, value)

    @classmethod
    def create(cls, platform: Platform, player_id: str) -> "PlayerID":
        """Create a PlayerID for the specified platform and ID.

        Args:
            platform: The gaming platform
            player_id: The player's unique ID on that platform

        Returns:
            A PlayerID instance
        """
        return cls(f"{platform.value}|{player_id}|0")

    def parse(self) -> Tuple[Platform, str]:
        """Parse a PlayerID string and return its components.

        Returns:
            Tuple of (platform, id)

        Raises:
            ValueError: If the PlayerID format is invalid
        """
        parts = str(self).split("|")
        if len(parts) != 3:
            raise ValueError(f"Invalid PlayerID format: {self}")

        return Platform(parts[0]), parts[1]


def new_player_id(platform: Platform, player_id: str) -> PlayerID:
    """Create a PlayerID for the specified platform and ID.

    Args:
        platform: The gaming platform
        player_id: The player's unique ID on that platform

    Returns:
        A PlayerID instance
    """
    return PlayerID.create(platform, player_id)


def parse_player_id(player_id: str) -> Tuple[Platform, str]:
    """Parse a PlayerID string and return its components.

    Args:
        player_id: The PlayerID string to parse

    Returns:
        Tuple of (platform, id)

    Raises:
        ValueError: If the PlayerID format is invalid
    """
    return PlayerID(player_id).parse()
