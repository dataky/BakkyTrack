"""Rocket League API client for Python.

This package provides a complete Python client for the Rocket League PsyNet API,
allowing you to interact with player data, shops, matches, clubs, and more.

Example:
    ```python
    import asyncio
    from rlapi import EGS, create_client

    async def main():
        # Authenticate with Epic Games Store
        egs = EGS()
        auth_url = egs.get_auth_url()
        print(f"Visit: {auth_url}")
        auth_code = input("Enter auth code: ")

        auth = egs.authenticate_with_code(auth_code)
        exchange_code = egs.get_exchange_code(auth.access_token)
        eos_token = egs.exchange_eos_token(exchange_code)

        # Create authenticated client
        client = await create_client(
            eos_token.access_token,
            eos_token.account_id,
            auth.display_name
        )

        # Get item shop data
        shops = await client.get_standard_shops()
        catalogue = await client.get_shop_catalogue([s["ID"] for s in shops["Shops"]])
        print(catalogue)

        # Clean up
        await client.close()

    asyncio.run(main())
    ```
"""

__version__ = "1.0.0"
__author__ = "Converted from github.com/dank/rlapi"

from .egs import EGS, TokenResponse, EOSTokenResponse, new_egs
from .psynet import PsyNet, PsyNetError, new_psy_net
from .psynetrpc import PsyNetRPC, Event, EventType
from .playerid import PlayerID, Platform, new_player_id, parse_player_id
from .client import RocketLeagueClient, create_client
from .auth import auth_player, auth_player_steam
from .types import (
    ShopID,
    ClubID,
    ChallengeID,
    PlaylistID,
    TournamentID,
    PartyID,
    PlayerData,
    PlayerXPInfo,
    Product,
    Shop,
    ShopCatalogue,
    Match,
    MatchEntry,
    Skill,
    ClubDetails,
)

__all__ = [
    # Version
    "__version__",
    "__author__",
    # Main client
    "RocketLeagueClient",
    "create_client",
    # Authentication
    "EGS",
    "TokenResponse",
    "EOSTokenResponse",
    "new_egs",
    "auth_player",
    "auth_player_steam",
    # Core classes
    "PsyNet",
    "PsyNetRPC",
    "PsyNetError",
    "new_psy_net",
    # Player ID
    "PlayerID",
    "Platform",
    "new_player_id",
    "parse_player_id",
    # Events
    "Event",
    "EventType",
    # Type aliases
    "ShopID",
    "ClubID",
    "ChallengeID",
    "PlaylistID",
    "TournamentID",
    "PartyID",
    # Common types
    "PlayerData",
    "PlayerXPInfo",
    "Product",
    "Shop",
    "ShopCatalogue",
    "Match",
    "MatchEntry",
    "Skill",
    "ClubDetails",
]
