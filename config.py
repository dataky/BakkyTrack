"""config.py — Constantes, Config, chemins, contexte SSL, helpers partagés."""
import os, sys, json, ssl as _ssl

# ── Chemins ──────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH  = os.path.join(BASE_DIR, "config.json")
OVERLAY_PORT = 49124
REFRESH_MS   = 2000

PLAYLIST_NAMES = {
    "1v1": "Ranked Duel 1v1",
    "2v2": "Ranked Doubles 2v2",
    "3v3": "Ranked Standard 3v3",
}

# ── Rangs Rocket League (source unique — importé par mmr.py, sound.py) ────
RANKS = [
    "Unranked",
    "Bronze I", "Bronze II", "Bronze III",
    "Silver I", "Silver II", "Silver III",
    "Gold I", "Gold II", "Gold III",
    "Platinum I", "Platinum II", "Platinum III",
    "Diamond I", "Diamond II", "Diamond III",
    "Champion I", "Champion II", "Champion III",
    "Grand Champion I", "Grand Champion II", "Grand Champion III",
    "Supersonic Legend",
]

# ── Headers HTTP tracker.gg (source unique) ───────────────────────────────
TRACKER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://rocketleague.tracker.network/",
    "Origin": "https://rocketleague.tracker.network",
    "Connection": "keep-alive",
    "sec-fetch-site": "same-site",
    "sec-fetch-mode": "cors",
    "sec-fetch-dest": "empty",
}

# ── Mapping plateforme ↔ slug tracker.gg ──────────────────────────────────
PLATFORM_SLUGS = {
    "epic": "epic", "steam": "steam",
    "ps4": "psn", "xbox": "xbl", "switch": "switch",
}

# ── Préfixes PrimaryId → plateforme ───────────────────────────────────────
_PLAT_PREFIX_MAP = {
    "Steam|": "steam", "Epic|": "epic", "PS4|": "ps4",
    "XboxOne|": "xbox", "Switch|": "switch",
}


def platform_from_id(primary_id: str) -> str:
    """Déduit la plateforme depuis un PrimaryId (ex: 'Steam|123' → 'steam')."""
    for prefix, plat in _PLAT_PREFIX_MAP.items():
        if primary_id.startswith(prefix):
            return plat
    return "epic"


def id_from_primary_id(primary_id: str) -> str:
    """Extrait l'ID utilisateur depuis un PrimaryId (ex: 'Steam|123' → '123')."""
    parts = primary_id.split("|")
    return parts[1] if len(parts) >= 2 else primary_id

# ── Contexte SSL — embarque certifi si disponible (fix PyInstaller) ───────
try:
    import certifi as _certifi
    SSL_CTX = _ssl.create_default_context(cafile=_certifi.where())
except Exception:
    try:
        SSL_CTX = _ssl.create_default_context()
    except Exception:
        SSL_CTX = None

SSL_CTX_NOVERIFY = _ssl.create_default_context()
SSL_CTX_NOVERIFY.check_hostname = False
SSL_CTX_NOVERIFY.verify_mode    = _ssl.CERT_NONE

# ── Icône par défaut (base64) ────────────────────────────────────────────
DEFAULT_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAB4ElEQVR4nO2bXVLDMAyEVYZzwDXhBHBNuEh5asd47FiKtdIm8ffYyY92tbYzaSyyuDa3yJu9fdzvmuN+v29hdUFvpBU8AmmI+4W9RPfwNsPtYmjhNV5GTF8kWnjNrBEvMydni/eoYbd7XuJ/vsbHvH+Oj9mbhFfrCQxdb/Goy2qEaQh4i/fqfom1RrUBrJ1vYalVZQBCvKb7M2hrnloF0Fjjv4ehAUeKfo2m9k0DUOLR8S8ZaegakN15z/hvaaGeAyJoGoDsPmLt19DTtBJQ/5DdfSQtbXQJiFj7S+gMiOafAWeO/4NaI1UCouMvEmQAS/dbUCUgg6cBZ3r0HVFqNb8Ss6KNf9YT4mGGACohhzEABdQAr9kfOT/QJwA9OcIMYF77S6gTELE0wpbBUfGjhEQ9F6QkgGl4PA2I/CxlBLr7pVbqOSACOgNO/0Zoa/ynvw9gmgdQ1BpphkBG90VIDMgSL9IwADkMstf/lrb0BGR2X6RjQNRkGCm+pyksAdnx79E1AJ0Chu6LDBKAMoFFvIhiCBz54UhTe/g/Q9mzfo3KgCOmQFuzOgEeJkR131KraQjMmMAoXiTgc/nH+I98y2Nh9yRouSGreJG1ZWZtmlrb5jwvVnPJjZNbMG6dXVydP/yruvfRgdsmAAAAAElFTkSuQmCC"

DEFAULT_CONFIG = {
    "platform":           "epic",
    "username":           "",
    "statsapi_port":      49123,
    "overlay_mode":       "compact",
    "mmr_display_mode":   "both",
    "auto_skip_replay":   False,
    "auto_queue":         False,
    "auto_freeplay":      False,
    "skip_replay_key":    "key:k",
    "skip_replay_delay":  4.0,
    "queue_key":          "key:m",
    "queue_delay":        2.0,
    "freeplay_key":       "key:l",
    "freeplay_delay":     3.0,
    "players_overlay_key": "key:f7",
    "sound_goal_scored":   False,
    "sound_goal_conceded": False,
    "sound_crossbar":      False,
    "sound_demo_me":       False,
    "sound_demo_opponent": False,
    "sound_epic_save":     False,
    "sound_save":          False,
    "snd_file_goal_scored":   "",
    "snd_file_goal_conceded": "",
    "snd_file_crossbar":      "",
    "snd_file_demo_me":       "",
    "snd_file_demo_opponent": "",
    "snd_file_epic_save":     "",
    "snd_file_save":          "",
    "result_overlay_enabled": True,
    "result_overlay_theme":   "auto",
    "overlay_hotkey_type":           "key",
    "overlay_hotkey_key":            "key:tab",
    "overlay_hotkey_controller_btn": 0,
    "tab_rank_mode":                 "2v2",
    "tab_show_peak":                 True,
    "controller_overlay_enabled":    False,
    "controller_overlay_mode":       "with_bg",
    "streamer_mode":                 False,
    "streamer_mute_audio":           True,
    "auto_gg":                       False,
    "auto_gg_key":                   "key:t",
    "auto_gg_text":                  "gg",
    "auto_gg_delay":                 4.0,
    "obs_ws_enabled":                False,
    "obs_ws_host":                   "localhost",
    "obs_ws_port":                   4455,
    "obs_ws_password":               "",
    "obs_scene_ingame":              "In-Game",
    "obs_scene_outgame":             "Lobby",
    "webhook_enabled":               False,
    "webhook_url":                   "",
}


class Config:
    _AUTOSAVE_DELAY = 2.0  # seconds

    def __init__(self):
        self._d = dict(DEFAULT_CONFIG)
        self._save_timer = None
        self._load()

    def _load(self):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                self._d.update(json.load(f))
        except Exception:
            pass

    def save(self) -> bool:
        # Cancel any pending auto-save since we're saving now
        if self._save_timer is not None:
            self._save_timer.cancel()
            self._save_timer = None
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._d, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config] save error: {e}")
            return False

    def _schedule_save(self):
        """Debounced auto-save: reschedule on every change, save after idle."""
        if self._save_timer is not None:
            self._save_timer.cancel()
        import threading
        self._save_timer = threading.Timer(self._AUTOSAVE_DELAY, self.save)
        self._save_timer.daemon = True
        self._save_timer.start()

    def __getitem__(self, k):    return self._d[k]
    def __setitem__(self, k, v):
        self._d[k] = v
        self._schedule_save()
    def get(self, k, d=None):   return self._d.get(k, d)