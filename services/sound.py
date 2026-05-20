"""services/sound.py — SoundService + cache in-game tracker.gg."""
import os, time, threading, urllib.parse, urllib.request, urllib.error, json
from concurrent.futures import ThreadPoolExecutor
from config import BASE_DIR, SSL_CTX, SSL_CTX_NOVERIFY, RANKS, TRACKER_HEADERS
from signals import AppSignals

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

_PLAT_TO_SLUG = {
    "Epic": "epic", "Steam": "steam",
    "PS4": "psn", "XboxOne": "xbl", "Switch": "switch",
}

_INGAME_CACHE_TTL = 120  # cache rafraîchi toutes les 2 min au lieu de 5
_ingame_fetch_lock = threading.Lock()
_ingame_fetch_last = 0.0
_INGAME_FETCH_GAP  = 0.0  # plus de gap forcé — parallélisation via ThreadPool
_INGAME_POOL_SIZE  = 6
_ingame_executor   = ThreadPoolExecutor(max_workers=_INGAME_POOL_SIZE)


def _fetch_player_for_ingame(primary_id: str, display_name: str, cache: dict, smurf_enabled: bool = True):
    global _ingame_fetch_last
    parts = primary_id.split("|")
    if len(parts) < 2:
        cache[primary_id] = {"status": "error", "http_code": 0, "playlists": {}, "timestamp": time.time()}
        return
    plat_raw = parts[0]
    user_id  = parts[1]
    slug     = _PLAT_TO_SLUG.get(plat_raw, "epic")
    target   = user_id if slug == "steam" else urllib.parse.quote(display_name, safe="")
    if not target:
        cache[primary_id] = {"status": "error", "http_code": 0, "playlists": {}, "timestamp": time.time()}
        return
    # Pas de lock global — les appels sont parallélisés par le ThreadPoolExecutor
    url = (f"https://api.tracker.gg/api/v2/rocket-league/standard/profile"
           f"/{slug}/{target}")
    _MAX_ATTEMPTS = 2
    _RETRY_WAIT   = 1
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers=TRACKER_HEADERS)
            ctx = SSL_CTX if SSL_CTX is not None else SSL_CTX_NOVERIFY
            try:
                with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
                    raw = resp.read().decode("utf-8")
            except Exception:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data.get("data"), dict):
                raise ValueError("No profile data")
            playlists = {}
            total_wins = 0
            trn_score = 0
            for seg in data["data"].get("segments", []):
                if seg.get("type") == "overview":
                     wins_val = seg.get("stats", {}).get("wins", {}).get("value")
                     if wins_val is not None:
                         total_wins = int(wins_val)
                     score_val = seg.get("stats", {}).get("score", {}).get("value")
                     if score_val is not None:
                         trn_score = float(score_val)
                if seg.get("type") != "playlist":
                    continue
                pid_val   = seg.get("attributes", {}).get("playlistId")
                s         = seg.get("stats", {})
                tier_name = s.get("tier", {}).get("metadata", {}).get("name", "Unranked")
                mmr_val   = s.get("rating", {}).get("value", 0)
                try:
                    tier_id = RANKS.index(tier_name)
                except ValueError:
                    tier_id = 0
                playlists[pid_val] = {
                    "mmr": int(mmr_val) if mmr_val else 0,
                    "tier_name": tier_name, "tier_id": tier_id,
                }
            for seg in data["data"].get("segments", []):
                if seg.get("type") != "peak-rating":
                    continue
                pid_val  = seg.get("attributes", {}).get("playlistId")
                peak_val = seg.get("stats", {}).get("peakRating", {}).get("value")
                if pid_val is not None and peak_val:
                    if pid_val in playlists:
                        playlists[pid_val]["peak_mmr"] = int(peak_val)
                    else:
                        playlists[pid_val] = {"mmr": 0, "tier_name": "Unranked",
                                              "tier_id": 0, "peak_mmr": int(peak_val)}
            
            is_smurf = False
            max_tier = max([p.get("tier_id", 0) for p in playlists.values()] + [0])
            if smurf_enabled:
                if max_tier >= 16:  # Champion or above
                    if (0 < trn_score < 150000) or (0 < total_wins < 250):
                        is_smurf = True
                elif 10 <= max_tier <= 15:  # Diamond & Platinum
                    if (0 < trn_score < 80000) or (0 < total_wins < 120):
                        is_smurf = True
                
            cache[primary_id] = {"status": "ok", "playlists": playlists, "wins": total_wins, "is_smurf": is_smurf, "timestamp": time.time()}
            return
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_WAIT * attempt)
                continue
            old = cache.get(primary_id, {})
            cache[primary_id] = {
                "status": "error", "http_code": e.code,
                "playlists": old.get("playlists", {}), "timestamp": time.time(),
            }
            return
        except Exception:
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_WAIT * attempt)
                continue
            old = cache.get(primary_id, {})
            cache[primary_id] = {
                "status": "error", "http_code": 0,
                "playlists": old.get("playlists", {}), "timestamp": time.time(),
            }


class SoundService:
    def __init__(self, config, signals: AppSignals):
        self.config  = config
        self.signals = signals
        self._ingame_stats_cache: dict = {}
        self._saved_system_vol = None

    def play_sound(self, file_str):
        if not PYGAME_AVAILABLE or not file_str:
            return
        def _play(f=file_str):
            try:
                path = f if os.path.isabs(f) else os.path.join(BASE_DIR, f)
                if not os.path.exists(path):
                    self.signals.log_event.emit(f"[Son] Fichier introuvable: {f}")
                    return
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                snd = pygame.mixer.Sound(path)
                vol = self.config.get("sound_volume", 100) / 100.0
                snd.set_volume(max(0.0, min(1.0, vol)))
                snd.play()
                ms = int(snd.get_length() * 1000) + 100
                pygame.time.wait(min(ms, 10000))
            except Exception as e:
                self.signals.log_event.emit(f"[Son] Erreur: {e}")
        threading.Thread(target=_play, daemon=True).start()

    def trigger_sound(self, event_key: str):
        if not self.config.get(f"sound_{event_key}", True):
            return
        f = self.config.get(f"snd_file_{event_key}", "")
        if f:
            self.play_sound(f)

    def fetch_players_for_ingame(self, players: list, my_pid: str,
                                 mmr_to_ingame_entry_fn):
        now = time.time()
        futures = []
        for p in players:
            pid  = p.get("PrimaryId", "")
            name = p.get("Name", "")
            if not pid:
                continue
            # Vérification du cache
            entry = self._ingame_stats_cache.get(pid)
            if pid == my_pid:
                if not entry:
                    self._ingame_stats_cache[pid] = mmr_to_ingame_entry_fn()
                    entry = self._ingame_stats_cache.get(pid)
                if entry and entry.get("status") == "ok":
                    age = now - entry.get("timestamp", 0)
                    if age < _INGAME_CACHE_TTL:
                        continue
            else:
                if entry and entry.get("status") == "ok":
                    age = now - entry.get("timestamp", 0)
                    if age < _INGAME_CACHE_TTL:
                        continue
            
            self._ingame_stats_cache[pid] = {"status": "loading", "playlists": {}, "timestamp": now}
            # Lancement parallélisé via ThreadPoolExecutor (pas de gap de 1.2s)
            futures.append(
                _ingame_executor.submit(
                    _fetch_player_for_ingame,
                    pid, name, self._ingame_stats_cache,
                    self.config.get("smurf_detection_enabled", True)
                )
            )
        # On ne bloque pas — les résultats arrivent de manière asynchrone

    def refresh_own_ingame_cache(self, my_pid: str, entry: dict):
        if my_pid:
            self._ingame_stats_cache[my_pid] = entry

    @property
    def ingame_stats_cache(self):
        return self._ingame_stats_cache

    def mute_system_audio(self):
        import sys as _sys
        if _sys.platform != "win32":
            return
        if not self.config.get("streamer_mute_audio", True):
            return
        try:
            from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
            RL_NAMES = {"rocketleague.exe", "rocket league.exe"}
            sessions = AudioUtilities.GetAllSessions()
            muted_sessions = []
            for session in sessions:
                try:
                    if session.Process and session.Process.name().lower() in RL_NAMES:
                        vol = session._ctl.QueryInterface(ISimpleAudioVolume)
                        if not vol.GetMute():
                            vol.SetMute(1, None)
                            muted_sessions.append(vol)
                except Exception:
                    continue
            if muted_sessions:
                if self._saved_system_vol is None:
                    self._saved_system_vol = ("pycaw_session", muted_sessions)
                self.signals.log_event.emit(
                    f"[Streamer] Son RL coupé ({len(muted_sessions)} session(s))")
            else:
                self.signals.log_event.emit(
                    "[Streamer] RL non trouvé dans les sessions audio")
            return
        except ImportError:
            self.signals.log_event.emit(
                "[Streamer] pycaw absent — pip install pycaw")
        except Exception as e:
            self.signals.log_event.emit(f"[Streamer] Erreur mute session RL : {e}")

    def restore_system_audio(self):
        import sys as _sys
        if _sys.platform != "win32" or self._saved_system_vol is None:
            return
        try:
            method = self._saved_system_vol[0]
            if method == "pycaw_session":
                _, sessions = self._saved_system_vol
                for vol in sessions:
                    try: vol.SetMute(0, None)
                    except Exception: pass
            self._saved_system_vol = None
            self.signals.log_event.emit("[Streamer] Son RL restauré")
        except Exception as e:
            self.signals.log_event.emit(f"[Streamer] Impossible de restaurer le son: {e}")