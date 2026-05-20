"""Main Rocket League API client."""
import logging
from typing import Optional

from .psynet import PsyNet
from .psynetrpc import PsyNetRPC
from .egs import EGS
from .auth import auth_player, auth_player_steam
from .api_players import PlayersAPI
from .api_shops import ShopsAPI
from .api_all import (
    MatchesAPI,
    SkillsAPI,
    StatsAPI,
    ClubsAPI,
    PartyAPI,
    MatchmakingAPI,
    PlaylistsAPI,
    PopulationAPI,
    ProductsAPI,
    MTXAPI,
    RocketPassAPI,
    ChallengesAPI,
    TournamentsAPI,
    TrainingAPI,
    MiscAPI,
)


class RocketLeagueClient(
    PsyNetRPC,
    PlayersAPI,
    ShopsAPI,
    MatchesAPI,
    SkillsAPI,
    StatsAPI,
    ClubsAPI,
    PartyAPI,
    MatchmakingAPI,
    PlaylistsAPI,
    PopulationAPI,
    ProductsAPI,
    MTXAPI,
    RocketPassAPI,
    ChallengesAPI,
    TournamentsAPI,
    TrainingAPI,
    MiscAPI,
):
    """Rocket League API client with all endpoints.

    This class combines PsyNetRPC with all API endpoint mixins to provide
    a complete client for the Rocket League API.
    """

    pass


async def create_client(
    auth_token: str,
    account_id: str,
    account_name: str,
    logger: Optional[logging.Logger] = None,
) -> RocketLeagueClient:
    """Create an authenticated Rocket League API client.

    Args:
        auth_token: EOS authentication token
        account_id: Epic account ID
        account_name: Account display name
        logger: Optional logger instance

    Returns:
        Authenticated RocketLeagueClient instance

    Example:
        ```python
        from rlapi import create_client, EGS

        # Authenticate with Epic Games Store
        egs = EGS()
        auth = egs.authenticate_with_code("your_auth_code")
        exchange_code = egs.get_exchange_code(auth.access_token)
        eos_token = egs.exchange_eos_token(exchange_code)

        # Create client
        client = await create_client(
            eos_token.access_token,
            eos_token.account_id,
            auth.display_name
        )

        # Use the client
        shops = await client.get_standard_shops()
        print(shops)

        # Clean up
        await client.close()
        ```
    """
    psy_net = PsyNet(logger=logger)
    rpc = await auth_player(psy_net, auth_token, account_id, account_name)

    # Convert PsyNetRPC to RocketLeagueClient
    client = RocketLeagueClient(
        ws_conn=rpc.ws_conn,
        local_player_id=rpc.local_player_id,
        psy_token=rpc.psy_token,
        session_id=rpc.session_id,
        request_id=rpc.request_id,
        logger=rpc.logger,
    )
    client._lock = rpc._lock
    client._pending_reqs = rpc._pending_reqs
    client._pong_event = rpc._pong_event
    client._event_queue = rpc._event_queue
    client._connected = rpc._connected
    client._ping_task = rpc._ping_task
    client._read_task = rpc._read_task

    return client
