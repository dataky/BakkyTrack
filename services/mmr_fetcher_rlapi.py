"""
services/mmr_fetcher_rlapi.py - Récupération MMR via l'API Rocket League (Psynet)
Utilise un compte bot configuré dans les paramètres (refresh_token stocké).
"""
import os
import sys
import asyncio
import time
import threading
from typing import Dict, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RLAPI_PATH = os.path.join(BASE_DIR, "rlapi-py-main")
if os.path.exists(RLAPI_PATH) and RLAPI_PATH not in sys.path:
    sys.path.insert(0, RLAPI_PATH)

from rlapi.egs import EGS
from rlapi.psynet import PsyNet, PsyNetError
from rlapi.auth import auth_player
from rlapi.playerid import Platform, new_player_id
from rlapi.client import RocketLeagueClient

from config import PLAYLIST_NAMES, RANKS
from signals import AppSignals

PLAYLIST_ID_MAP = {10: "1v1", 11: "2v2", 13: "3v3"}

class RLAPIMmrFetcher:
    def __init__(self, config, signals: AppSignals):
        self.config = config
        self.signals = signals
        self._lock = threading.Lock()

    def _get_bot_tokens(self):
        """Récupère les infos du compte bot depuis la config."""
        refresh = self.config.get("bot_refresh_token", "")
        account_id = self.config.get("bot_account_id", "")
        account_name = self.config.get("bot_account_name", "")
        if not refresh or not account_id:
            return None
        return {"refresh_token": refresh, "account_id": account_id, "account_name": account_name}

    def _refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Utilise le refresh_token pour obtenir un nouvel access_token."""
        egs = EGS()
        try:
            new_token = egs.refresh_eos_token(refresh_token)
            # Mise à jour du refresh_token (rotation possible)
            if new_token.refresh_token:
                self.config["bot_refresh_token"] = new_token.refresh_token
                self.config.save()
            return new_token.access_token
        except Exception as e:
            self.signals.log_event.emit(f"[RLAPI] Échec refresh token bot : {e}")
            return None
        finally:
            egs.close()

    async def _fetch_async(self, target_id: str) -> Dict[str, Dict]:
        # Récupère les infos du bot
        bot = self._get_bot_tokens()
        if not bot:
            raise Exception("Aucun compte bot configuré. Veuillez lier un compte dans les paramètres.")
        refresh_token = bot["refresh_token"]
        account_id = bot["account_id"]
        account_name = bot["account_name"]

        # Obtenir un access_token valide
        access_token = self._refresh_access_token(refresh_token)
        if not access_token:
            raise Exception("Impossible d'obtenir un token d'accès pour le compte bot.")

        # Connexion PsyNet
        psy = PsyNet()
        try:
            rpc = await auth_player(psy, access_token, account_id, account_name)
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

            target = new_player_id(Platform.EPIC, target_id)
            skills_raw = await client.get_players_skills([target], timeout=15.0)

            result = {}
            if skills_raw and isinstance(skills_raw, list) and len(skills_raw) > 0:
                for player_skills in skills_raw:
                    skills_list = player_skills.get("Skills", [])
                    for skill in skills_list:
                        playlist_id = skill.get("Playlist")
                        if playlist_id in PLAYLIST_ID_MAP:
                            key = PLAYLIST_ID_MAP[playlist_id]
                            tier = skill.get("Tier", 0)
                            division = skill.get("Division", 0)
                            mu = skill.get("Mu", 0.0)
                            mmr = int(mu * 20 + 100) if mu else 0
                            rank_name = RANKS[tier] if 0 <= tier < len(RANKS) else "Unranked"
                            result[key] = {
                                "mmr": mmr,
                                "rank": rank_name,
                                "tier_id": tier,
                                "div_id": division,
                                "peak_mmr": None,
                            }
            await client.close()
            if not result:
                raise Exception("Aucune donnée MMR trouvée")
            return result
        except PsyNetError as e:
            raise Exception(f"Erreur PsyNet: {e}")
        finally:
            psy.close()

    def fetch_sync(self, username: str, platform: str, user_id: Optional[str] = None) -> Dict[str, Dict]:
        target_id = user_id or username
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._fetch_async(target_id))
        except Exception as e:
            raise e
        finally:
            loop.close()

    async def _fetch_batch_async(self, target_ids: List[str]) -> Dict[str, Dict]:
        """Fetch MMR pour plusieurs joueurs Epic en une seule connexion PsyNet."""
        bot = self._get_bot_tokens()
        if not bot:
            raise Exception("Aucun compte bot configuré.")
        refresh_token = bot["refresh_token"]
        account_id = bot["account_id"]
        account_name = bot["account_name"]

        access_token = self._refresh_access_token(refresh_token)
        if not access_token:
            raise Exception("Impossible d'obtenir un token d'accès.")

        psy = PsyNet()
        try:
            rpc = await auth_player(psy, access_token, account_id, account_name)
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

            targets = [new_player_id(Platform.EPIC, tid) for tid in target_ids if tid]
            if not targets:
                return {}

            skills_raw = await client.get_players_skills(targets, timeout=20.0)

            results = {}
            if skills_raw and isinstance(skills_raw, list):
                for player_skills in skills_raw:
                    skills_list = player_skills.get("Skills", [])
                    player_data = {}
                    for skill in skills_list:
                        playlist_id = skill.get("Playlist")
                        if playlist_id in PLAYLIST_ID_MAP:
                            key = PLAYLIST_ID_MAP[playlist_id]
                            tier = skill.get("Tier", 0)
                            division = skill.get("Division", 0)
                            mu = skill.get("Mu", 0.0)
                            mmr = int(mu * 20 + 100) if mu else 0
                            rank_name = RANKS[tier] if 0 <= tier < len(RANKS) else "Unranked"
                            player_data[key] = {
                                "mmr": mmr,
                                "rank": rank_name,
                                "tier_id": tier,
                                "div_id": division,
                                "peak_mmr": None,
                            }
                    # Utiliser l'ID Epic comme clé dans le résultat
                    results[target_ids[skills_raw.index(player_skills)] if len(target_ids) > skills_raw.index(player_skills) else "unknown"] = player_data

            await client.close()
            return results
        except PsyNetError as e:
            raise Exception(f"Erreur PsyNet batch: {e}")
        finally:
            psy.close()

    def fetch_players_batch_sync(self, epic_ids: List[str]) -> Dict[str, Dict]:
        """Fetch MMR pour plusieurs joueurs Epic en une seule connexion PsyNet (synchrone)."""
        if not epic_ids:
            return {}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._fetch_batch_async(epic_ids))
        except Exception as e:
            raise e
        finally:
            loop.close()
