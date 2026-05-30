"""
services/mmr_fetcher_rlapi.py - Récupération MMR via le serveur BakkyTrack Render
Optimisé : connexion keep-alive, timeout réduit, singleton.
"""
import os
import sys
import json
import threading
import http.client
import urllib.parse
from typing import Dict, Optional, List

from config import RANKS
from signals import AppSignals

PLAYLIST_ID_MAP = {10: "1v1", 11: "2v2", 13: "3v3"}
RENDER_URL = "https://bakkytrack-server.onrender.com"
RENDER_HOST = urllib.parse.urlparse(RENDER_URL).netloc
RENDER_USE_HTTPS = urllib.parse.urlparse(RENDER_URL).scheme == "https"


class ConnectionPool:
    """Pool de connexions HTTP persistantes (keep-alive)."""
    
    def __init__(self, host: str, use_https: bool = True, max_connections: int = 4):
        self._host = host
        self._use_https = use_https
        self._lock = threading.Lock()
        self._connections: List[http.client.HTTPConnection] = []
        self._max_connections = max_connections
    
    def _create_connection(self) -> http.client.HTTPConnection:
        if self._use_https:
            conn = http.client.HTTPSConnection(self._host, timeout=8)
        else:
            conn = http.client.HTTPConnection(self._host, timeout=8)
        return conn
    
    def acquire(self) -> http.client.HTTPConnection:
        with self._lock:
            if self._connections:
                conn = self._connections.pop()
                try:
                    conn.sock
                    return conn
                except Exception:
                    pass
            return self._create_connection()
    
    def release(self, conn: http.client.HTTPConnection):
        with self._lock:
            if len(self._connections) < self._max_connections:
                self._connections.append(conn)
            else:
                try:
                    conn.close()
                except Exception:
                    pass


class RLAPIMmrFetcher:
    """
    Récupère le MMR via le serveur Render.
    Utilise un pool de connexions persistantes (keep-alive).
    Pas de cache : chaque appel va chercher les données fraîches.
    """
    
    def __init__(self, config, signals: AppSignals):
        self.config = config
        self.signals = signals
        self._lock = threading.Lock()
        self._render_url = RENDER_URL
        self._timeout = 8  # secondes (réduit de 20 → 8)
        
        # Pool de connexions persistantes (partagé entre toutes les instances)
        if not hasattr(RLAPIMmrFetcher, '_pool'):
            RLAPIMmrFetcher._pool = ConnectionPool(RENDER_HOST, RENDER_USE_HTTPS)
        self._pool = RLAPIMmrFetcher._pool

    def _api_call(self, epic_id: str) -> Optional[Dict]:
        """Appelle le serveur Render avec une connexion persistante (keep-alive).
        Si la connexion persistante échoue (ex: fermée par le serveur),
        on retente automatiquement avec une connexion fraîche.
        """
        url = f"/mmr/{epic_id}"
        errored_conn = False
        
        for attempt in range(2):  # max 2 tentatives
            conn = self._pool.acquire()
            try:
                conn.request("GET", url, headers={
                    "Accept": "application/json",
                    "Connection": "keep-alive",
                    "User-Agent": "BakkyTrack/1.0",
                })
                resp = conn.getresponse()
                raw = resp.read().decode()
                data = json.loads(raw)
                
                if data.get("success"):
                    return data["mmr"]
                else:
                    self.signals.log_event.emit(
                        f"[Render] Erreur pour {epic_id}: {data.get('error', 'inconnue')}"
                    )
                    return None
            except (http.client.HTTPException, ConnectionError, OSError) as e:
                err_str = str(e)
                # Si la connexion persistante est morte, on la jette et on retente
                if "closed" in err_str.lower() or "reset" in err_str.lower() or "refused" in err_str.lower():
                    errored_conn = True
                    # Ne pas remettre la connexion dans le pool (elle est morte)
                    try: conn.close()
                    except: pass
                    if attempt == 0:
                        self.signals.log_event.emit(
                            f"[Render] Connexion perdue, nouvelle tentative...")
                        continue
                self.signals.log_event.emit(f"[Render] HTTP erreur pour {epic_id}: {e}")
                return None
            except Exception as e:
                self.signals.log_event.emit(f"[Render] Erreur pour {epic_id}: {e}")
                return None
            finally:
                if not errored_conn:
                    self._pool.release(conn)
        
        return None

    def _batch_api_call(self, epic_ids: List[str]) -> Dict:
        """Appelle le serveur Render pour un batch MMR (avec keep-alive)."""
        url = "/mmr/batch"
        body = json.dumps({"epic_ids": epic_ids}).encode()
        conn = self._pool.acquire()
        try:
            conn.request("POST", url, body=body, headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connection": "keep-alive",
                "User-Agent": "BakkyTrack/1.0",
            })
            resp = conn.getresponse()
            raw = resp.read().decode()
            data = json.loads(raw)
            return data.get("results", {})
        except Exception as e:
            self.signals.log_event.emit(f"[Render] Erreur batch : {e}")
            return {}
        finally:
            self._pool.release(conn)

    def fetch_sync(self, username: str, platform: str, user_id: Optional[str] = None) -> Dict[str, Dict]:
        """
        Récupère le MMR d'un joueur.
        
        - username: pseudo ou Epic ID
        - platform: "epic" uniquement supporté
        - user_id: Epic ID (UUID 32 caractères)
        """
        target_id = user_id or username
        if not target_id:
            raise Exception("Aucun ID fourni")

        self.signals.log_event.emit(f"[Render] Fetch MMR pour {target_id}")
        data = self._api_call(target_id)
        
        if data is None:
            raise Exception("Impossible de récupérer le MMR depuis le serveur Render")

        # Normalise les playlists au format attendu par BakkyTrack
        result = {}
        for playlist_key, mmr_data in data.items():
            playlist_id = {"1v1": 10, "2v2": 11, "3v3": 13}.get(playlist_key)
            if playlist_id:
                result[playlist_key] = mmr_data
        
        return result

    def fetch_players_batch_sync(self, epic_ids: List[str]) -> Dict[str, Dict]:
        """Récupère le MMR de plusieurs joueurs en une seule requête."""
        if not epic_ids:
            return {}
        
        self.signals.log_event.emit(f"[Render] Batch MMR pour {len(epic_ids)} joueurs")
        results = self._batch_api_call(epic_ids)
        
        # Normalise les données
        normalized = {}
        for epic_id, data in results.items():
            if data:
                normalized[epic_id] = data
        return normalized