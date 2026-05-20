import asyncio
import json
import websockets
from .playerid import PlayerID, Platform, new_player_id
from .requestid import RequestIDCounter
from .signing import make_ws_signature, HMAC_KEY_WS
from .ranks import tier_name, division_name, playlist_name

BUILD_ID    = "151471783"
WS_URL      = "wss://ws.rlpp.psynet.gg/ws/gc2"
USER_AGENT  = "RL Win/250811.43331.492665 gzip"


class PsyNetClient:
    def __init__(self, token: str, session_id: str):
        self.token      = token
        self.session_id = session_id
        self._counter   = RequestIDCounter()
        self._ws        = None

    async def connect(self):
        headers = {
            "PsyToken":       self.token,
            "PsySessionID":   self.session_id,
            "PsyBuildID":     BUILD_ID,
            "PsyEnvironment": "Prod",
            "User-Agent":     USER_AGENT,
        }
        self._ws = await websockets.connect(
            WS_URL,
            additional_headers=headers,
            max_size=16 * 1024 * 1024,  # 16 Mo — les réponses lourdes (Wallet, MatchHistory, Shops…) dépassent 1 Mo
        )

    async def close(self):
        if self._ws:
            await self._ws.close()

    def _build_message(self, service: str, version: int, body: dict) -> str:
        """
        Format PsyNet WebSocket :
          Header1: value\r\n
          Header2: value\r\n
          \r\n
          {json body}
        """
        body_bytes  = json.dumps(body).encode()
        request_id  = self._counter.get_id()
        sig         = make_ws_signature(HMAC_KEY_WS, service, body_bytes)

        headers = "\r\n".join([
            f"PsyService: {service} v{version}",
            f"PsyRequestID: {request_id}",
            f"PsyToken: {self.token}",
            f"PsySessionID: {self.session_id}",
            f"PsySig: {sig}",
            f"PsyBuildID: {BUILD_ID}",
        ])
        return headers + "\r\n\r\n" + body_bytes.decode()

    async def _send_recv(self, service: str, version: int, body: dict) -> dict:
        msg = self._build_message(service, version, body)
        await self._ws.send(msg)
        raw = await self._ws.recv()

        # La réponse est aussi header\r\n\r\nbody
        _, _, json_part = raw.partition("\r\n\r\n")
        return json.loads(json_part)

    # ── Rank ────────────────────────────────────────────────────────────────

    async def get_player_skill(self, player_id: PlayerID) -> dict:
        """Récupère les skills d'un joueur (son propre compte)."""
        return await self._send_recv(
            service="Skills/GetPlayerSkill",
            version=1,
            body={"PlayerID": str(player_id)},
        )

    async def get_players_skills(self, player_ids: list[PlayerID]) -> dict:
        """Récupère les skills de plusieurs joueurs (endpoint public)."""
        return await self._send_recv(
            service="Skills/GetPlayersSkills",
            version=1,
            body={"PlayerIDs": [str(p) for p in player_ids]},
        )