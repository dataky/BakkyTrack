"""Authentication module for PsyNet."""
from typing import List, Optional
from dataclasses import dataclass
import logging

import websockets

from .psynet import PsyNet, FEATURE_SET, PSY_BUILD_ID, GAME_VERSION
from .psynetrpc import PsyNetRPC
from .playerid import PlayerID, Platform, new_player_id


@dataclass
class AuthPlayerRequest:
    """Authentication request for a player."""

    Platform: str
    PlayerName: str
    PlayerID: str
    Language: str
    AuthTicket: str
    BuildRegion: str
    FeatureSet: str
    Device: str
    LocalFirstPlayerID: str
    bSkipAuth: bool
    bSetAsPrimaryAccount: bool
    EpicAuthTicket: str
    EpicAccountID: str


@dataclass
class AuthPlayerResponse:
    """Authentication response for a player."""

    IsLastChanceAuthBan: bool
    SessionID: str
    VerifiedPlayerName: str
    UseWebSocket: bool
    PerConURL: str
    PerConURLv2: str
    PsyToken: str
    CountryRestrictions: List[str]


async def auth_player(
    psy_net: PsyNet,
    auth_token: str,
    account_id: str,
    account_name: str,
) -> PsyNetRPC:
    """Authenticate with PsyNet via EGS and return a WebSocket connection.

    Args:
        psy_net: PsyNet client instance
        auth_token: EOS authentication token
        account_id: Epic account ID
        account_name: Account display name

    Returns:
        Authenticated PsyNetRPC WebSocket client

    Raises:
        Exception: If authentication fails
    """
    local_player_id = new_player_id(Platform.EPIC, account_id)

    req_data = {
        "Platform": Platform.EPIC.value,
        "PlayerName": account_name,
        "PlayerID": account_id,
        "Language": "INT",
        "AuthTicket": auth_token,
        "BuildRegion": "",
        "FeatureSet": FEATURE_SET,
        "Device": "PC",
        "LocalFirstPlayerID": str(local_player_id),
        "bSkipAuth": False,
        "bSetAsPrimaryAccount": True,
        "EpicAuthTicket": auth_token,
        "EpicAccountID": account_id,
    }

    result = psy_net._post_json(["Auth", "AuthPlayer", "v2"], req_data, dict)

    psy_token = result["PsyToken"]
    session_id = result["SessionID"]
    ws_url = result["PerConURLv2"]

    rpc = await establish_socket(
        ws_url,
        local_player_id,
        psy_token,
        session_id,
        psy_net.request_id,
        psy_net.logger,
    )

    return rpc


async def auth_player_steam(
    psy_net: PsyNet,
    auth_token: str,
    epic_account_id: str,
    steam_account_id: str,
    account_name: str,
) -> PsyNetRPC:
    """Authenticate with PsyNet via Steam and return a WebSocket connection.

    Args:
        psy_net: PsyNet client instance
        auth_token: EOS authentication token
        epic_account_id: Epic account ID
        steam_account_id: Steam account ID
        account_name: Account display name

    Returns:
        Authenticated PsyNetRPC WebSocket client

    Raises:
        Exception: If authentication fails
    """
    local_player_id = new_player_id(Platform.STEAM, steam_account_id)

    req_data = {
        "Platform": Platform.STEAM.value,
        "PlayerName": account_name,
        "PlayerID": steam_account_id,
        "Language": "INT",
        "AuthTicket": auth_token,
        "BuildRegion": "",
        "FeatureSet": FEATURE_SET,
        "Device": "PC",
        "bSkipAuth": False,
        "bSetAsPrimaryAccount": True,
        "EpicAuthTicket": auth_token,
        "EpicAccountID": epic_account_id,
    }

    result = psy_net._post_json(["Auth", "AuthPlayer", "v2"], req_data, dict)

    psy_token = result["PsyToken"]
    session_id = result["SessionID"]
    ws_url = result["PerConURLv2"]

    rpc = await establish_socket(
        ws_url,
        local_player_id,
        psy_token,
        session_id,
        psy_net.request_id,
        psy_net.logger,
    )

    return rpc


async def establish_socket(
    url: str,
    player_id: PlayerID,
    psy_token: str,
    session_id: str,
    request_id,
    logger: Optional[logging.Logger] = None,
) -> PsyNetRPC:
    """Establish a WebSocket connection to PsyNet.

    Args:
        url: WebSocket URL
        player_id: Player ID
        psy_token: PsyNet authentication token
        session_id: Session ID
        request_id: Request ID counter
        logger: Optional logger instance

    Returns:
        PsyNetRPC client instance

    Raises:
        Exception: If connection fails
    """
    if logger:
        logger.debug(f"Establishing WebSocket connection to {url}")

    extra_headers = {
        "PsyBuildID": PSY_BUILD_ID,
        "User-Agent": f"RL Win/{GAME_VERSION} gzip",
        "PsyEnvironment": "Prod",
        "PsyToken": psy_token,
        "PsySessionID": session_id,
    }

    ws_conn = await websockets.connect(
        url,
        additional_headers=extra_headers,
        max_size=16 * 1024 * 1024,  # 16 Mo — les réponses lourdes dépassent la limite de 1 Mo par défaut
    )

    rpc = PsyNetRPC(
        ws_conn=ws_conn,
        local_player_id=player_id,
        psy_token=psy_token,
        session_id=session_id,
        request_id=request_id,
        logger=logger,
    )

    # Start background tasks
    rpc.start_background_tasks()

    return rpc