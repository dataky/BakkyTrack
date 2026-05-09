#!/usr/bin/env python3
"""
BakkyTrack — companion Rocket League (StatsAPI / tracker.gg)
  Onglet 1 : Stats     (W/L, MMR, streak)
  Onglet 2 : Match     (joueurs en jeu → tracker.network)
  Onglet 3 : Overlay   (compact / bannière, MMR in-game)
  Onglet 4 : Auto      (skip replay, file, freeplay)
  Onglet 5 : Sons      (événements StatsAPI)
  Onglet 6 : Options
"""

import sys, json, time, threading, os, socket, urllib.parse, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import websocket          # pip install websocket-client
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# Selenium/Chrome supprimé — inutilisé et forçait l'installation de Chrome
SELENIUM_AVAILABLE = False
WEBDRIVER_MANAGER_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from gamepad_state import get_gamepad_state

from PyQt6.QtCore    import Qt, QTimer, pyqtSignal, QObject, QUrl, QPointF, QRectF, QByteArray, QThread, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTabWidget, QLineEdit, QComboBox,
    QTextEdit, QPlainTextEdit, QStackedWidget, QScrollArea, QCheckBox, QDialog,
    QSlider, QStyle, QSizePolicy, QProgressBar,
)
from PyQt6.QtGui import (
    QColor, QCursor, QPainter, QBrush, QPen, QLinearGradient, QRadialGradient, QFont,
    QDesktopServices, QIcon, QPolygonF
)
from PyQt6.QtSvg import QSvgRenderer

# ─────────────────────────────────────────────────────────────────────────────
#  CHEMINS & CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_DEFAULT_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAB4ElEQVR4nO2bXVLDMAyEVYZzwDXhBHBNuEh5asd47FiKtdIm8ffYyY92tbYzaSyyuDa3yJu9fdzvmuN+v29hdUFvpBU8AmmI+4W9RPfwNsPtYmjhNV5GTF8kWnjNrBEvMydni/eoYbd7XuJ/vsbHvH+Oj9mbhFfrCQxdb/Goy2qEaQh4i/fqfom1RrUBrJ1vYalVZQBCvKb7M2hrnloF0Fjjv4ehAUeKfo2m9k0DUOLR8S8ZaegakN15z/hvaaGeAyJoGoDsPmLt19DTtBJQ/5DdfSQtbXQJiFj7S+gMiOafAWeO/4NaI1UCouMvEmQAS/dbUCUgg6cBZ3r0HVFqNb8Ss6KNf9YT4mGGACohhzEABdQAr9kfOT/QJwA9OcIMYF77S6gTELE0wpbBUfGjhEQ9F6QkgGl4PA2I/CxlBLr7pVbqOSACOgNO/0Zoa/ynvw9gmgdQ1BpphkBG90VIDMgSL9IwADkMstf/lrb0BGR2X6RjQNRkGCm+pyksAdnx79E1AJ0Chu6LDBKAMoFFvIhiCBz54UhTe/g/Q9mzfo3KgCOmQFuzOgEeJkR131KraQjMmMAoXiTgc/nH+I98y2Nh9yRouSGreJG1ZWZtmlrb5jwvVnPJjZNbMG6dXVydP/yruvfRgdsmAAAAAElFTkSuQmCC"


CONFIG_PATH  = os.path.join(BASE_DIR, "config.json")
OVERLAY_PORT = 49124
REFRESH_MS   = 2000

PLAYLIST_NAMES = {
    "1v1": "Ranked Duel 1v1",
    "2v2": "Ranked Doubles 2v2",
    "3v3": "Ranked Standard 3v3",
}

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
    # Touche hold-to-show pour l'overlay principal
    "overlay_hotkey_type":           "key",   # "key" | "controller"
    "overlay_hotkey_key":            "key:tab",
    "overlay_hotkey_controller_btn": 0,
    # Overlay manette
    "controller_overlay_enabled":    False,
    "controller_overlay_mode":       "with_bg",   # "with_bg" | "transparent"
    # Mode streamer
    "streamer_mode":                 False,
    "streamer_mute_audio":           True,
}

# ─────────────────────────────────────────────────────────────────────────────
#  COULEURS & STYLE
# ─────────────────────────────────────────────────────────────────────────────
C_BG    = "#0A0C10"
C_BG2   = "#12151C"
C_BG3   = "#1A1E2A"
C_BLUE  = "#1A8CFF"
C_ORG   = "#FF6B00"
C_TEXT  = "#E8ECF4"
C_MUTE  = "#5A6275"
C_GREEN = "#3AE08A"
C_GOLD  = "#FFD700"

APP_STYLE = f"""
QWidget {{ background:transparent; color:{C_TEXT};
           font-family:'Segoe UI','Rajdhani',system-ui,sans-serif; font-size:13px; }}
QMainWindow {{ background:transparent; }}
QToolTip {{ background:{C_BG3}; color:{C_TEXT}; border:none;
            padding:6px 8px; font-size:11px; border-radius:4px; }}
QTabWidget {{ background:transparent; }}
QTabWidget::pane {{ border:none;
                    background:rgba(14,16,22,0.92); border-radius:0 0 8px 8px; }}
QTabBar::tab {{ background:rgba(22,24,32,0.92); color:{C_MUTE};
                padding:10px 12px; min-height:20px; border:none;
                font-size:11px; font-weight:600; letter-spacing:0.3px;
                border-top-left-radius:6px; border-top-right-radius:6px; margin-right:2px; }}
QTabBar::tab:selected {{ background:rgba(32,36,48,0.98); color:{C_TEXT};
                         border-bottom:3px solid {C_BLUE}; padding-bottom:7px; }}
QTabBar::tab:hover:!selected {{ color:{C_TEXT}; background:rgba(28,30,40,0.95); }}
QLineEdit, QComboBox {{ background:{C_BG3}; color:{C_TEXT};
                        border:none; border-radius:4px;
                        padding:5px 9px; font-size:11px; }}
QLineEdit:focus, QComboBox:focus {{ border:none; outline:none; }}
QComboBox::drop-down {{ border:none; padding-right:8px; }}
QComboBox QAbstractItemView {{ background:{C_BG3}; color:{C_TEXT};
                               selection-background-color:{C_BLUE}; outline:none; }}
QTextEdit {{ background:{C_BG3}; color:{C_MUTE}; border:none;
             font-family:'Courier New',monospace; font-size:9px; }}
QScrollBar:vertical {{ background:{C_BG2}; width:5px; border:none; }}
QScrollBar::handle:vertical {{ background:{C_BG3}; border-radius:2px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QCheckBox {{ color:{C_TEXT}; font-size:11px; spacing:8px; }}
QCheckBox::indicator {{ width:16px; height:16px; border-radius:3px;
                        border:none; background:{C_BG3}; }}
QCheckBox::indicator:checked {{ background:{C_BLUE}; border:none; }}
QScrollArea {{ background:transparent; border:none; }}
QScrollArea > QWidget > QWidget {{ background:transparent; }}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS UI
# ─────────────────────────────────────────────────────────────────────────────
def card(parent=None, bg=C_BG2):
    f = QFrame(parent)
    f.setStyleSheet(
        f"QFrame{{background:{bg};border-radius:8px;border:none;}}")
    return f

def lbl(text, color=C_MUTE, size=9, bold=False, parent=None):
    w = QLabel(text, parent)
    weight = "700" if bold else "400"
    # Letter-spacing léger : meilleure lisibilité en français qu’avec 1px partout
    w.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{weight};"
                    f"background:transparent;letter-spacing:0.25px;")
    return w

def btn(text, bg=C_BG3, fg=C_TEXT, size=10, bold=True, parent=None):
    w = QPushButton(text, parent)
    w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    weight = "700" if bold else "400"
    w.setStyleSheet(f"""
        QPushButton{{background:{bg};color:{fg};border:none;border-radius:4px;
                     padding:5px 12px;font-size:{size}px;font-weight:{weight};}}
        QPushButton:hover{{background:{bg}cc;}}
        QPushButton:pressed{{background:{bg}99;}}
    """)
    return w

def hsep(parent=None):
    s = QFrame(parent)
    s.setFrameShape(QFrame.Shape.HLine)
    s.setFixedHeight(1)
    s.setStyleSheet(f"background:{C_BG3};border:none;")
    return s


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
class Config:
    def __init__(self):
        self._d = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                self._d.update(json.load(f))
        except Exception:
            pass

    def save(self) -> bool:
        """Sauvegarde la config sur disque. Retourne True si succès, False sinon."""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._d, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config] save error: {e}")
            return False

    def __getitem__(self, k):    return self._d[k]
    def __setitem__(self, k, v): self._d[k] = v
    def get(self, k, d=None):   return self._d.get(k, d)


# ─────────────────────────────────────────────────────────────────────────────
#  SIGNAUX
# ─────────────────────────────────────────────────────────────────────────────
class AppSignals(QObject):
    status_changed  = pyqtSignal(str, str)
    player_detected = pyqtSignal(str, int)
    match_result    = pyqtSignal(str)
    log_event       = pyqtSignal(str)
    mmr_updated     = pyqtSignal()
    mmr_error       = pyqtSignal(str)
    players_updated = pyqtSignal(list)   # liste joueurs du match courant
    # Signaux inter-services (MatchService → MainApp, sans couplage PyQt UI)
    trigger_sound   = pyqtSignal(str)          # event_key (ex: "goal_scored")
    press_key_sig   = pyqtSignal(str, float)   # key_str, delay_seconds
    game_phase_changed = pyqtSignal(str)       # "lobby" | "ingame"


# ─────────────────────────────────────────────────────────────────────────────
#  BIND WORKER — Détecte la prochaine touche clavier OU bouton manette
# ─────────────────────────────────────────────────────────────────────────────
class BindWorker(QThread):
    """Lance dans un thread : attend la prochaine touche clavier ou bouton manette."""
    finished_bind = pyqtSignal(str, bool, int)   # key_str, is_controller, btn_mask

    def run(self):
        time.sleep(0.4)   # évite de capturer la touche qui a ouvert le dialog

        # Vide l'état courant manette (XInput ou SDL)
        get_gamepad_state()

        while True:
            # ── Clavier (VK scan Windows) ──────────────────────────────────
            if sys.platform == "win32":
                import ctypes
                for vk in list(_VK_MAP.values()):
                    if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
                        # Retrouver le nom depuis la valeur
                        for name, code in _VK_MAP.items():
                            if code == vk:
                                # Ignorer les boutons souris (prefix mouse:)
                                if name.startswith("mouse:"):
                                    continue
                                self.finished_bind.emit(f"key:{name}", False, 0)
                                return
                        # Fallback : lettres A-Z / chiffres
                        if 0x30 <= vk <= 0x39:
                            self.finished_bind.emit(f"key:{chr(vk)}", False, 0)
                            return
                        if 0x41 <= vk <= 0x5A:
                            self.finished_bind.emit(f"key:{chr(vk).lower()}", False, 0)
                            return

            # ── Manette (XInput / SDL) ─────────────────────────────────────
            xi = get_gamepad_state()
            if xi and xi.Gamepad.wButtons != 0:
                btn = xi.Gamepad.wButtons
                # Attendre relâchement
                while True:
                    xi2 = get_gamepad_state()
                    if not xi2 or xi2.Gamepad.wButtons == 0:
                        break
                    time.sleep(0.05)
                self.finished_bind.emit("", True, btn)
                return

            time.sleep(0.02)


# ─────────────────────────────────────────────────────────────────────────────
#  OVERLAY BIND DIALOG — "Appuie sur une touche ou bouton manette"
# ─────────────────────────────────────────────────────────────────────────────
class OverlayBindDialog(QDialog):
    """Fenêtre de capture : attend une touche clavier ou un bouton manette."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurer la touche overlay")
        self.setFixedSize(360, 200)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(
            f"background:{C_BG2};border:2px solid {C_BLUE};border-radius:10px;")
        self.captured_key   = None
        self.is_controller  = False
        self.controller_btn = 0
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 28, 30, 22)
        lay.setSpacing(16)

        title = QLabel("CONFIGURER LA TOUCHE OVERLAY")
        title.setStyleSheet(
            f"color:{C_BLUE};font-size:10px;font-weight:700;"
            f"letter-spacing:2px;background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        self._hint = QLabel(
            "Appuie sur une touche clavier\n"
            "ou maintiens un bouton manette…")
        self._hint.setStyleSheet(
            f"color:{C_TEXT};font-size:13px;background:transparent;")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        lay.addWidget(self._hint)

        row = QHBoxLayout()
        none_btn = QPushButton("Désactiver")
        none_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        none_btn.setStyleSheet(
            f"QPushButton{{background:{C_BG3};color:{C_MUTE};border:none;"
            f"border-radius:4px;padding:6px 14px;font-size:10px;font-weight:700;}}"
            f"QPushButton:hover{{color:{C_TEXT};}}")
        none_btn.clicked.connect(self._disable)
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_btn.setStyleSheet(
            f"QPushButton{{background:{C_BG3};color:{C_MUTE};border:none;"
            f"border-radius:4px;padding:6px 14px;font-size:10px;font-weight:700;}}"
            f"QPushButton:hover{{color:{C_TEXT};}}")
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(none_btn)
        row.addStretch()
        row.addWidget(cancel_btn)
        lay.addLayout(row)

        # Lance le thread de capture
        self._worker = BindWorker()
        self._worker.finished_bind.connect(self._on_bind)
        self._worker.start()

    def _disable(self):
        """Aucune touche — overlay désactivé."""
        self.captured_key   = ""
        self.is_controller  = False
        self.controller_btn = 0
        self._hint.setText("✓  Overlay désactivé (aucune touche)")
        QTimer.singleShot(400, self.accept)

    def _on_bind(self, key_str, is_ctrl, btn):
        if is_ctrl:
            self.is_controller  = True
            self.controller_btn = btn
            self.captured_key   = ""
            self._hint.setText(f"✓  🎮  Bouton manette  0x{btn:04X}")
        else:
            self.is_controller  = False
            self.controller_btn = 0
            self.captured_key   = key_str
            label = key_str[4:].upper() if key_str.startswith("key:") else key_str
            self._hint.setText(f"✓  ⌨  {label}")
        QTimer.singleShot(400, self.accept)

    def closeEvent(self, event):
        if self._worker.isRunning():
            self._worker.terminate()
        super().closeEvent(event)


def _overlay_hotkey_display(cfg: "Config") -> str:
    """Retourne un label lisible pour la touche overlay hold."""
    htype = cfg.get("overlay_hotkey_type", "key")
    if htype == "controller":
        btn = cfg.get("overlay_hotkey_controller_btn", 0)
        if btn == 0:
            return "Désactivée"
        return f"🎮  Bouton 0x{btn:04X}"
    key = cfg.get("overlay_hotkey_key", "key:tab")
    if not key:
        return "Désactivée"
    if key.startswith("key:"):
        return f"⌨  {key[4:].upper()}"
    return f"⌨  {key.upper()}"



# ─────────────────────────────────────────────────────────────────────────────
#  FETCH MMR JOUEURS DU MATCH  (tracker.gg, tous les joueurs en jeu)
# ─────────────────────────────────────────────────────────────────────────────
_PLAT_TO_SLUG = {
    "Epic":    "epic",
    "Steam":   "steam",
    "PS4":     "psn",
    "XboxOne": "xbl",
    "Switch":  "switch",
}

_INGAME_CACHE_TTL = 300   # secondes avant de re-fetcher

# Verrou global pour espacer les fetches in-game et éviter le rate-limit tracker.gg
_ingame_fetch_lock = threading.Lock()
_ingame_fetch_last = 0.0
_INGAME_FETCH_GAP  = 1.2   # secondes minimum entre deux fetches joueurs


def _fetch_player_for_ingame(primary_id: str, display_name: str, cache: dict):
    """Fetche le MMR d'un joueur en background et stocke dans cache[primary_id].

    Utilise exactement la même méthode que MMRService._fetch :
    - _SSL_CTX / _SSL_CTX_NOVERIFY importés depuis overlay_widgets (certifi si dispo)
    - Même headers HTTP
    - Même logique de retry (3 tentatives, backoff linéaire)
    + Espacement global des requêtes pour éviter le rate-limit quand plusieurs
      joueurs sont fetchés en parallèle.
    """
    global _ingame_fetch_last

    # ── Résolution plateforme / identifiant ──────────────────────────────────
    parts = primary_id.split("|")
    if len(parts) < 2:
        cache[primary_id] = {"status": "error", "http_code": 0, "playlists": {}, "timestamp": time.time()}
        return

    plat_raw = parts[0]
    user_id  = parts[1]
    slug     = _PLAT_TO_SLUG.get(plat_raw, "epic")
    # Steam : ID numérique 64-bit — pas d'encodage de pseudo nécessaire
    # Autres : on cherche par display_name (même comportement que MMRService._fetch)
    target   = user_id if slug == "steam" else urllib.parse.quote(display_name, safe="")

    if not target:
        cache[primary_id] = {"status": "error", "http_code": 0, "playlists": {}, "timestamp": time.time()}
        return

    # ── Espacement global : max 1 fetch / _INGAME_FETCH_GAP secondes ─────────
    with _ingame_fetch_lock:
        now  = time.time()
        wait = _INGAME_FETCH_GAP - (now - _ingame_fetch_last)
        if wait > 0:
            time.sleep(wait)
        _ingame_fetch_last = time.time()

    url = (f"https://api.tracker.gg/api/v2/rocket-league/standard/profile"
           f"/{slug}/{target}")

    # Headers identiques à MMRService._fetch
    _HEADERS = {
        "User-Agent":      (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"),
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://rocketleague.tracker.network/",
        "Origin":          "https://rocketleague.tracker.network",
        "Connection":      "keep-alive",
        "sec-fetch-site":  "same-site",
        "sec-fetch-mode":  "cors",
        "sec-fetch-dest":  "empty",
    }

    _MAX_ATTEMPTS  = MMRService._MAX_RETRIES   # même constante (3)
    _RETRY_WAIT    = MMRService._RETRY_WAIT    # même backoff (2 s)

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data.get("data"), dict):
                raise ValueError("No profile data")

            playlists = {}
            for seg in data["data"].get("segments", []):
                if seg.get("type") != "playlist":
                    continue
                pid_val   = seg.get("attributes", {}).get("playlistId")
                s         = seg.get("stats", {})
                tier_name = s.get("tier",   {}).get("metadata", {}).get("name", "Unranked")
                mmr_val   = s.get("rating", {}).get("value", 0)
                try:
                    tier_id = MMRService._RANKS.index(tier_name)
                except (ValueError, AttributeError):
                    tier_id = 0
                playlists[pid_val] = {
                    "mmr":       int(mmr_val) if mmr_val else 0,
                    "tier_name": tier_name,
                    "tier_id":   tier_id,
                }

            cache[primary_id] = {
                "status":    "ok",
                "playlists": playlists,
                "timestamp": time.time(),
            }
            return   # succès

        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < _MAX_ATTEMPTS:
                # Rate-limit tracker.gg — même backoff que MMRService._fetch
                time.sleep(_RETRY_WAIT * attempt)
                continue
            # 403 (profil privé) / 404 (introuvable) / autre → erreur définitive
            old = cache.get(primary_id, {})
            cache[primary_id] = {
                "status":    "error",
                "http_code": e.code,
                "playlists": old.get("playlists", {}),
                "timestamp": time.time(),
            }
            return

        except Exception as e:
            # Erreur réseau / SSL / parsing — on retente comme MMRService._fetch
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_WAIT * attempt)
                continue
            old = cache.get(primary_id, {})
            cache[primary_id] = {
                "status":    "error",
                "http_code": 0,
                "playlists": old.get("playlists", {}),
                "timestamp": time.time(),
            }


from overlay_widgets import *
from overlay_widgets import _CompactCard, _key_to_vk, _VK_MAP, ControllerOverlay, StreamerModeBar

class TrackerTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()
        self._connect_signals()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        # ── Connexion StatsAPI ──────────────────────────────────────────────
        conn = card()
        cl = QVBoxLayout(conn)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(6)
        conn_title = lbl("CONNEXION AU JEU", C_MUTE, 8, True)
        conn_hint = lbl(
            "Les événements du jeu arrivent ici via StatsAPI — le port doit être identique "
            "à celui configuré dans le plugin BakkyTrack (côté Rocket League).",
            C_MUTE, 9)
        conn_hint.setWordWrap(True)
        cl.addWidget(conn_title)
        cl.addWidget(conn_hint)
        row_conn = QHBoxLayout()
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{C_MUTE};font-size:14px;background:transparent;")
        self._status_lbl = lbl("Non connecté")
        port_lbl = lbl("Port :")
        self._port_edit = QLineEdit(str(self.app.config["statsapi_port"]))
        self._port_edit.setFixedWidth(60)
        self._port_edit.setToolTip(
            "Identique au port StatsAPI indiqué dans les réglages du plugin BakkyTrack.")
        reconn_btn = btn("Reconnecter", bg=C_BG3, size=9)
        reconn_btn.setToolTip("Réessaie la connexion au serveur local StatsAPI.")
        reconn_btn.clicked.connect(self.app.reconnect_statsapi)
        row_conn.addWidget(self._dot)
        row_conn.addSpacing(6)
        row_conn.addWidget(self._status_lbl)
        row_conn.addStretch()
        row_conn.addWidget(port_lbl)
        row_conn.addSpacing(4)
        row_conn.addWidget(self._port_edit)
        row_conn.addSpacing(8)
        row_conn.addWidget(reconn_btn)
        cl.addLayout(row_conn)
        root.addWidget(conn)

        # ── Infos joueur + MMR ─────────────────────────────────────────────
        info = card()
        il = QVBoxLayout(info); il.setContentsMargins(14, 12, 14, 12); il.setSpacing(7)

        row_player = QHBoxLayout()
        row_player.addWidget(lbl("COMPTE DÉTECTÉ (EN JEU)", C_MUTE, 8, True))
        self._player_lbl = lbl("--", C_TEXT, 11, True)
        self._player_lbl.setToolTip(
            "Pseudo tel qu’envoyé par le jeu via StatsAPI (plugin BakkyTrack).")
        row_player.addStretch()
        row_player.addWidget(self._player_lbl)
        il.addLayout(row_player); il.addWidget(hsep())

        row_mmr = QHBoxLayout()
        row_mmr.addWidget(lbl("MMR"))
        self._mmr_lbl   = lbl("--",  C_GOLD, 16, True)
        self._delta_lbl = lbl("",    C_GREEN, 10, True)
        self._rank_lbl  = lbl("",    C_MUTE,   9)
        self._rank_icon_lbl = QLabel()
        self._rank_icon_lbl.setFixedSize(28, 28)
        self._rank_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon_lbl.setStyleSheet("background:transparent;")
        # Icône système (évite le glyphe ↻ mal rendu selon la police du thème)
        ref_btn = QPushButton()
        ref_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ref_btn.setFixedSize(26, 26)
        ref_btn.setIcon(
            ref_btn.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        ref_btn.setIconSize(QSize(14, 14))
        ref_btn.setStyleSheet(f"""
            QPushButton{{background:{C_BG3};border:none;border-radius:4px;}}
            QPushButton:hover{{background:{C_BG3}cc;}}
            QPushButton:pressed{{background:{C_BG3}99;}}
        """)
        ref_btn.setToolTip(
            "Met à jour le MMR et les rangs via tracker.gg tout de suite "
            "(contourne le délai entre deux mises à jour automatiques).")
        ref_btn.clicked.connect(lambda: self.app.fetch_mmr_async(force=True))
        row_mmr.addStretch()
        row_mmr.addWidget(self._rank_icon_lbl); row_mmr.addSpacing(4)
        row_mmr.addWidget(self._rank_lbl); row_mmr.addWidget(self._mmr_lbl)
        row_mmr.addWidget(self._delta_lbl); row_mmr.addWidget(ref_btn)
        il.addLayout(row_mmr); il.addWidget(hsep())

        row_pl = QHBoxLayout()
        row_pl.addWidget(lbl("PLAYLIST", C_MUTE, 8)); row_pl.addStretch()
        self._pl_btns = {}
        for key in ("1v1", "2v2", "3v3"):
            b = btn(key, bg=C_BG3, fg=C_MUTE, size=9); b.setFixedWidth(50)
            b.clicked.connect(lambda _, k=key: self.app.select_playlist(k))
            row_pl.addWidget(b); self._pl_btns[key] = b
        il.addLayout(row_pl)
        root.addWidget(info)

        # ── W / L counters ─────────────────────────────────────────────────
        wl = QHBoxLayout(); wl.setSpacing(8)

        for side in ("win", "loss"):
            c_card = card()
            c_card.setFixedHeight(124)
            c_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            color  = C_BLUE if side == "win" else C_ORG
            label  = "VICTOIRES" if side == "win" else "DÉFAITES"
            bar    = QFrame(c_card); bar.setFixedHeight(3)
            bar.setStyleSheet(f"background:{color};border:none;")
            cl2 = QVBoxLayout(c_card); cl2.setContentsMargins(0,0,0,8)
            cl2.setSpacing(2)
            cl2.addWidget(bar)
            cl2.addWidget(lbl(label, color, 9), alignment=Qt.AlignmentFlag.AlignHCenter)
            count_lbl = QLabel("0")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_lbl.setFixedHeight(54)
            count_lbl.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            count_lbl.setStyleSheet(
                f"color:{color};font-size:52px;font-weight:700;"
                f"background:transparent;")
            cl2.addWidget(count_lbl)
            brow = QHBoxLayout(); brow.setSpacing(6); brow.setContentsMargins(10,0,10,0)
            bp = btn("+", bg=C_BG3, size=14); bm = btn("−", bg=C_BG3, size=14)
            bp.clicked.connect(lambda _, s=side: self.app.add(s))
            bm.clicked.connect(lambda _, s=side: self.app.remove(s))
            brow.addWidget(bp); brow.addWidget(bm)
            cl2.addLayout(brow)
            wl.addWidget(c_card, 1)
            if side == "win":
                self._wins_lbl = count_lbl
                wl.addWidget(lbl("VS", C_MUTE, 13))
            else:
                self._losses_lbl = count_lbl
        root.addLayout(wl)

        # ── Win rate bar ────────────────────────────────────────────────────
        wr_card = card()
        wr_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        wrc = QVBoxLayout(wr_card); wrc.setContentsMargins(14, 8, 14, 8); wrc.setSpacing(4)
        wr_top = QHBoxLayout()
        wr_top.addWidget(lbl("WIN RATE", C_MUTE, 9))
        self._wr_lbl = lbl("--", C_TEXT, 13, True)
        wr_top.addStretch(); wr_top.addWidget(self._wr_lbl)
        wrc.addLayout(wr_top)
        # QProgressBar : évite setFixedWidth sur un QFrame enfant (boucle de
        # largeur min / scroll qui pouvait étirer toute la fenêtre quand W+L > 0).
        self._wr_progress = QProgressBar()
        self._wr_progress.setRange(0, 100)
        self._wr_progress.setValue(0)
        self._wr_progress.setTextVisible(False)
        self._wr_progress.setFixedHeight(10)
        self._wr_progress.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._wr_progress.setStyleSheet(f"""
            QProgressBar {{
                border: none; background: #1A0500; border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {C_BLUE}; border-radius: 4px;
            }}
        """)
        wrc.addWidget(self._wr_progress)
        root.addWidget(wr_card)

        # ── Mini stats ──────────────────────────────────────────────────────
        ms = QHBoxLayout(); ms.setSpacing(6)
        self._total_lbl  = QLabel("0")
        self._streak_lbl = QLabel("--")
        self._clock_lbl  = QLabel("0:00")
        for caption, val_ref in [("TOTAL", self._total_lbl),
                                   ("STREAK", self._streak_lbl),
                                   ("DURÉE", self._clock_lbl)]:
            c = card(); cl3 = QVBoxLayout(c); cl3.setContentsMargins(8,8,8,8); cl3.setSpacing(2)
            cl3.addWidget(lbl(caption, C_MUTE, 8), alignment=Qt.AlignmentFlag.AlignHCenter)
            val_ref.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_ref.setStyleSheet(f"color:{C_TEXT};font-size:15px;font-weight:700;background:transparent;")
            cl3.addWidget(val_ref)
            ms.addWidget(c, 1)
        root.addLayout(ms)

        # ── Log StatsAPI ───────────────────────────────────────────────────
        dbg = card()
        dbg.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dl = QVBoxLayout(dbg); dl.setContentsMargins(12, 8, 12, 10); dl.setSpacing(6)
        dl.addWidget(lbl("MESSAGES STATSAPI", C_MUTE, 8))
        # QPlainTextEdit + hauteur fixe : évite l’étirement vertical du layout
        # (QTextEdit a une politique Expanding et peut absorber l’espace du QScrollArea).
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(72)
        self._log.setMaximumBlockCount(400)
        self._log.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._log.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._log.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._log.setStyleSheet(
            f"QPlainTextEdit{{background:{C_BG3};color:{C_MUTE};border:none;"
            f"font-family:'Consolas','Courier New',monospace;font-size:9px;"
            f"padding:4px;border-radius:4px;}}")
        dl.addWidget(self._log)
        root.addWidget(dbg)

        reset_btn = btn("Réinitialiser la session", bg=C_BG, fg=C_MUTE, size=10)
        reset_btn.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        reset_btn.clicked.connect(self.app.reset_session)
        root.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        # Espace résiduel du QScrollArea en bas (évite de l’injecter dans les cartes)
        root.addStretch(1)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _connect_signals(self):
        s = self.app.signals
        s.status_changed.connect(self._on_status)
        s.player_detected.connect(lambda name, _: self._player_lbl.setText(name))
        s.match_result.connect(self._refresh)
        s.log_event.connect(self._on_log)
        s.mmr_updated.connect(self._on_mmr)
        s.mmr_error.connect(self._on_mmr_error)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)

    def _on_status(self, state, msg):
        colors = {"connected": C_GREEN, "error": C_ORG}
        c = colors.get(state, C_MUTE)
        self._dot.setStyleSheet(f"color:{c};font-size:14px;background:transparent;")
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color:{c};font-size:9px;background:transparent;letter-spacing:1px;")

    def _refresh(self, _=None):
        a = self.app
        self._wins_lbl.setText(str(a.wins))
        self._losses_lbl.setText(str(a.losses))
        total = a.wins + a.losses
        self._total_lbl.setText(str(total))
        if total == 0:
            self._wr_lbl.setText("--")
            self._wr_progress.setValue(0)
            self._streak_lbl.setText("--")
        else:
            wr = round(a.wins / total * 100)
            self._wr_lbl.setText(f"{wr}%")
            self._wr_progress.setValue(wr)
            if a.streak > 1:
                self._streak_lbl.setText(f"{a.streak}{'W' if a.streak_type=='win' else 'L'}")
            else:
                self._streak_lbl.setText("--")

    def _on_mmr(self):
        d   = self.app.all_mmr.get(self.app.selected_playlist, {})
        mmr = d.get("mmr")
        self._mmr_lbl.setText(str(mmr) if mmr else "--")
        rank_name = d.get("rank", "")
        self._rank_lbl.setText(rank_name)
        # Icône de rang dans la fenêtre principale
        from overlay_widgets import get_rank_pixmap
        tier_id = d.get("tier_id", 0)
        pm = get_rank_pixmap(tier_id, 26)
        if pm:
            self._rank_icon_lbl.setPixmap(pm)
        else:
            self._rank_icon_lbl.clear()
        chg = d.get("mmr_change", 0)
        if chg != 0 and mmr:
            sign = "+" if chg > 0 else ""
            clr  = C_GREEN if chg > 0 else C_ORG
            self._delta_lbl.setText(f"{sign}{chg}")
            self._delta_lbl.setStyleSheet(f"color:{clr};font-size:9px;font-weight:700;background:transparent;")
        else:
            self._delta_lbl.setText("")
        self.app.highlight_playlist_btns(self._pl_btns)

    def _on_mmr_error(self, msg):
        self._mmr_lbl.setText("ERR")
        self._mmr_lbl.setStyleSheet(f"color:{C_ORG};font-size:16px;font-weight:700;background:transparent;")
        self._delta_lbl.setText("")
        self._rank_lbl.setText(msg[:40])
        self._rank_lbl.setStyleSheet(f"color:{C_ORG};font-size:9px;background:transparent;")

    def _on_log(self, msg):
        self._log.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {msg}")
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _tick_clock(self):
        elapsed = int(time.time() - self.app.session_start)
        m, s = divmod(elapsed, 60)
        self._clock_lbl.setText(f"{m}:{s:02d}")

    def get_port(self):
        return self._port_edit.text().strip()


# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 2 — JOUEURS EN MATCH
# ─────────────────────────────────────────────────────────────────────────────
class PlayersTab(QWidget):
    _PLAYLIST_KEY_TO_ID = {"1v1": 10, "2v2": 11, "3v3": 13}

    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._players = []
        self._build()
        app_ref.signals.players_updated.connect(self._on_players)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_mmr_labels)
        self._refresh_timer.start(1000)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(lbl("JOUEURS EN MATCH", C_MUTE, 9))
        header.addStretch()
        open_all_btn = btn("Ouvrir tous →", bg=C_BG3, size=9)
        open_all_btn.clicked.connect(self._open_all)
        header.addWidget(open_all_btn)
        root.addLayout(header)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidget(self._list_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;border:none;")
        root.addWidget(scroll, 1)

        hint = lbl("Clic sur → pour ouvrir le profil sur tracker.network", C_MUTE, 9)
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._show_empty()

    def _show_empty(self):
        self._clear_list()
        empty = lbl("Aucun match en cours", C_MUTE, 10)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addWidget(empty)
        self._list_layout.addStretch()

    def _refresh_mmr_labels(self):
        if not self._players:
            return
        cache = getattr(self.app, "_ingame_stats_cache", {})
        has_pending = any(
            cache.get(p.get("PrimaryId", ""), {}).get("status") in ("loading", None, "")
            for p in self._players if p.get("PrimaryId")
        )
        if has_pending:
            self._on_players(self._players)

    def _clear_list(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_players(self, players):
        self._players = players
        if not players:
            self._show_empty()
            return

        self._clear_list()
        blues   = [p for p in players if p.get("TeamNum") == 0]
        oranges = [p for p in players if p.get("TeamNum") == 1]

        for team_name, team_color, team_players in [
            ("🔵  BLUE",   C_BLUE, blues),
            ("🟠  ORANGE", C_ORG,  oranges)
        ]:
            if team_players:
                self._list_layout.addWidget(lbl(team_name, team_color, 9, True))
                for p in team_players:
                    self._list_layout.addWidget(self._make_row(p, team_color))

        self._list_layout.addStretch()

    # ── Rate-limit tracker.network : 1 ouverture / 5 min par joueur ──────
    _TRACKER_COOLDOWN_S = 3
    _tracker_last_open: dict = {}

    # Slugs d'URL tracker.network (différents des noms internes)
    _URL_SLUG = {
        "epic":   "epic",
        "steam":  "steam",
        "ps4":    "psn",
        "xbox":   "xbl",
        "switch": "switch",
    }

    def _platform_from_id(self, primary_id):
        if primary_id.startswith("Steam|"):   return "steam"
        if primary_id.startswith("Epic|"):    return "epic"
        if primary_id.startswith("PS4|"):     return "ps4"
        if primary_id.startswith("XboxOne|"): return "xbox"
        if primary_id.startswith("Switch|"):  return "switch"
        return "epic"

    def _id_from_primary_id(self, primary_id):
        """Extrait l'ID utilisateur depuis PrimaryId (ex: 'Steam|76561198...|0' → '76561198...')."""
        parts = primary_id.split("|")
        if len(parts) >= 2:
            return parts[1]
        return primary_id

    def _make_row(self, player, color):
        row = card(bg=C_BG2)
        row.setFixedHeight(58)
        rl = QHBoxLayout(row); rl.setContentsMargins(12, 6, 12, 6)

        primary_id = player.get("PrimaryId", "")
        platform   = self._platform_from_id(primary_id)
        raw_id     = self._id_from_primary_id(primary_id) or player.get("Name", "")
        user_id    = raw_id if platform == "steam" else player.get("Name", raw_id)

        plat_lbl = QLabel(platform.upper())
        plat_lbl.setStyleSheet(
            f"color:{C_MUTE};background:transparent;border-radius:3px;"
            f"padding:2px 5px;font-size:7px;font-weight:700;border:none;")

        name_lbl = lbl(player.get("Name", "?"), color, 12, True)

        cache   = getattr(self.app, "_ingame_stats_cache", {})
        entry   = cache.get(primary_id, {})
        status  = entry.get("status", "")
        pl_key  = getattr(self.app, "selected_playlist", "3v3")
        pid_int = self._PLAYLIST_KEY_TO_ID.get(pl_key, 13)
        pl_data = entry.get("playlists", {}).get(pid_int, {})

        if status == "loading":
            mmr_text, mmr_color, mmr_bold = "⏳ …", C_MUTE, False
        elif status == "ok" and pl_data:
            tier_name = pl_data.get("tier_name", "Unranked")
            mmr_val   = pl_data.get("mmr", 0)
            mmr_text, mmr_color, mmr_bold = f"{tier_name}  {mmr_val}", C_GOLD, True
        elif status == "error":
            mmr_text, mmr_color, mmr_bold = "—", C_MUTE, False
        else:
            mmr_text, mmr_color, mmr_bold = "", C_MUTE, False

        mmr_lbl   = lbl(mmr_text, mmr_color, 9, bold=mmr_bold)
        stats_lbl = lbl(
            f"⚽ {player.get('Goals',0)}   🅰 {player.get('Assists',0)}   🛡 {player.get('Saves',0)}",
            C_MUTE, 9)

        open_btn = btn("→", bg=C_BG3, size=11)
        open_btn.setFixedSize(30, 30)
        open_btn.clicked.connect(
            lambda _, uid=user_id, pl=platform: self._open_profile(uid, pl))

        rl.addWidget(plat_lbl); rl.addSpacing(8)
        vl = QVBoxLayout(); vl.setSpacing(1); vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(name_lbl)
        br = QHBoxLayout(); br.setSpacing(8); br.setContentsMargins(0, 0, 0, 0)
        br.addWidget(stats_lbl); br.addStretch(); br.addWidget(mmr_lbl)
        vl.addLayout(br)
        rl.addLayout(vl); rl.addStretch(); rl.addWidget(open_btn)
        return row

    def _open_profile(self, user_id, platform):
        now = time.time()
        last = self._tracker_last_open.get(user_id, 0)
        remaining = self._TRACKER_COOLDOWN_S - (now - last)
        if remaining > 0:
            # Cooldown actif — on ignore le clic silencieusement
            return
        self._tracker_last_open[user_id] = now
        slug = self._URL_SLUG.get(platform, platform)
        url = (f"https://rocketleague.tracker.network/rocket-league/profile"
               f"/{slug}/{urllib.parse.quote(user_id)}/overview")
        QDesktopServices.openUrl(QUrl(url))

    def _open_all(self):
        for p in self._players:
            primary_id = p.get("PrimaryId", "")
            pl      = self._platform_from_id(primary_id)
            raw_id  = self._id_from_primary_id(primary_id) or p.get("Name", "")
            # Steam utilise l'ID numérique ; toutes les autres plateformes utilisent le pseudo
            user_id = raw_id if pl == "steam" else p.get("Name", raw_id)
            self._open_profile(user_id, pl)


# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 3 — OVERLAY
# ─────────────────────────────────────────────────────────────────────────────
class OverlayTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        # ── Wrapper scrollable ────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;border:none;")

        inner_w = QWidget()
        inner_w.setStyleSheet("background:transparent;")
        root = QVBoxLayout(inner_w)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(12)

        scroll.setWidget(inner_w)
        outer.addWidget(scroll)

        # ── Touche hold-to-show ───────────────────────────────────────────
        hk_card = card()
        hkl = QVBoxLayout(hk_card); hkl.setContentsMargins(16,14,16,16); hkl.setSpacing(10)
        hkl.addWidget(lbl("TOUCHE D'OVERLAY  (maintenir = afficher)", C_MUTE, 9))
        hkl.addWidget(lbl(
            "Maintiens cette touche en jeu pour afficher l'overlay.\n"
            "Supporte clavier (défaut : Tab) et manette (Xbox / PlayStation via XInput ou SDL).",
            C_TEXT, 9))

        hk_row = QHBoxLayout()
        self._hk_display = QLabel(_overlay_hotkey_display(self.app.config))
        self._hk_display.setFixedWidth(170)
        self._hk_display.setStyleSheet(
            f"background:{C_BG3};color:{C_TEXT};border-radius:4px;"
            f"padding:5px 9px;font-size:11px;border:none;")
        hk_bind_btn = QPushButton("🎯  Configurer")
        hk_bind_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        hk_bind_btn.setStyleSheet(
            f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;"
            f"padding:5px 10px;font-size:9px;font-weight:700;}}"
            f"QPushButton:hover{{background:{C_BLUE};color:{C_TEXT};}}")
        hk_bind_btn.clicked.connect(self._reconfigure_hotkey)
        hk_row.addWidget(self._hk_display); hk_row.addWidget(hk_bind_btn); hk_row.addStretch()
        hkl.addLayout(hk_row)
        root.addWidget(hk_card)

        # ── Toggle overlay principal ──────────────────────────────────────
        tog_card = card()
        tl = QVBoxLayout(tog_card); tl.setContentsMargins(16,16,16,16); tl.setSpacing(8)
        tl.addWidget(lbl("OVERLAY", C_MUTE, 9))
        self._toggle_btn = btn("▶  ACTIVER L'OVERLAY", bg=C_BG3, fg=C_TEXT, size=12)
        self._toggle_btn.setFixedHeight(44)
        self._toggle_btn.clicked.connect(self._toggle)
        tl.addWidget(self._toggle_btn)
        tl.addWidget(lbl("Double-clic sur l'overlay pour changer de mode", C_MUTE, 9))
        root.addWidget(tog_card)

        # ── Mode compact/bannière ─────────────────────────────────────────
        mode_card = card()
        ml = QVBoxLayout(mode_card); ml.setContentsMargins(16,14,16,16); ml.setSpacing(10)
        ml.addWidget(lbl("FORMAT", C_MUTE, 9))
        r_mode = QHBoxLayout()
        r_mode.addWidget(lbl("Type d'overlay", C_TEXT, 11))
        self._mode_combo = QComboBox()

        from overlay_widgets import _load_overlay_plugins
        self._available_modes = _load_overlay_plugins()
        self._MODE_MAP = {}
        self._MODE_REVERSE = {}

        for idx, (mode_name, mode_info) in enumerate(sorted(self._available_modes.items())):
            size = mode_info.get("size", (0, 0))
            display_text = f"{mode_name}  ({size[0]}×{size[1]})"
            self._mode_combo.addItem(display_text)
            self._MODE_MAP[idx] = mode_name
            self._MODE_REVERSE[mode_name] = idx

        self._mode_combo.setFixedWidth(200)
        self._mode_combo.currentIndexChanged.connect(
            lambda i: self._set_mode(self._MODE_MAP.get(i, "compact")))
        r_mode.addStretch(); r_mode.addWidget(self._mode_combo)
        ml.addLayout(r_mode)
        root.addWidget(mode_card)

        # ── Mode affichage MMR ────────────────────────────────────────────
        mmr_card = card()
        mml = QVBoxLayout(mmr_card); mml.setContentsMargins(16,14,16,16); mml.setSpacing(8)
        mml.addWidget(lbl("AFFICHAGE MMR", C_MUTE, 9))
        self._mmr_btns = {}
        for mode, label in [
            ("both",  "MMR + Delta  (ex: 1234  +24)"),
            ("mmr",   "MMR uniquement  (ex: 1234)"),
            ("delta", "Delta uniquement  (ex: +24)"),
        ]:
            b = btn(label, bg=C_BG3, fg=C_MUTE, size=10)
            b.setFixedHeight(34)
            b.clicked.connect(lambda _, m=mode: self._set_mmr_mode(m))
            mml.addWidget(b); self._mmr_btns[mode] = b
        root.addWidget(mmr_card)

        # ── Preview ───────────────────────────────────────────────────────
        prev_card = card()
        pl = QVBoxLayout(prev_card); pl.setContentsMargins(16,14,16,16); pl.setSpacing(8)
        pl.addWidget(lbl("APERÇU COMPACT", C_MUTE, 9))
        prev_inner = QHBoxLayout()
        self._preview = _CompactCard(); self._preview.setEnabled(False)
        prev_inner.addStretch(); prev_inner.addWidget(self._preview); prev_inner.addStretch()
        pl.addLayout(prev_inner)
        root.addWidget(prev_card)

        # ── Overlay Manette ───────────────────────────────────────────────
        ctrl_card = card()
        ctl = QVBoxLayout(ctrl_card); ctl.setContentsMargins(16,14,16,16); ctl.setSpacing(10)
        ctl.addWidget(lbl("OVERLAY MANETTE  (XInput / SDL — Xbox & PlayStation)", C_MUTE, 9))

        self._ctrl_toggle_btn = btn(
            "🎮  ACTIVER L'OVERLAY MANETTE", bg=C_BG3, fg=C_TEXT, size=11)
        self._ctrl_toggle_btn.setFixedHeight(40)
        self._ctrl_toggle_btn.clicked.connect(self._toggle_controller)
        ctl.addWidget(self._ctrl_toggle_btn)

        style_row = QHBoxLayout()
        style_row.addWidget(lbl("Style :", C_TEXT, 11))
        style_row.addStretch()
        self._ctrl_style_btns = {}
        for mode_key, mode_label in [("with_bg", "Avec fond"), ("transparent", "Transparent")]:
            b = btn(mode_label, bg=C_BG3, fg=C_MUTE, size=10)
            b.setFixedHeight(30)
            b.clicked.connect(lambda _, m=mode_key: self._set_ctrl_mode(m))
            style_row.addWidget(b)
            self._ctrl_style_btns[mode_key] = b
        ctl.addLayout(style_row)
        ctl.addWidget(lbl(
            "Déplaçable en jeu. Polling 60 Hz — aucun impact sur les perfs.",
            C_MUTE, 8))
        root.addWidget(ctrl_card)

        root.addStretch()

        # ── Init states ───────────────────────────────────────────────────
        self._active = False
        saved_mode = self.app.config.get("overlay_mode", "compact")
        if saved_mode not in self._available_modes:
            saved_mode = next(iter(self._available_modes), "compact")
        self._mode_combo.setCurrentIndex(self._MODE_REVERSE.get(saved_mode, 0))
        self._set_mode(saved_mode)
        self._set_mmr_mode(self.app.config.get("mmr_display_mode", "both"))
        self._ctrl_active = self.app.config.get("controller_overlay_enabled", False)
        self._update_ctrl_btn_style()
        self._set_ctrl_mode(
            self.app.config.get("controller_overlay_mode", "with_bg"), save=False)

    def _toggle_controller(self):
        self._ctrl_active = not self._ctrl_active
        self.app.config["controller_overlay_enabled"] = self._ctrl_active
        self.app.config.save()
        if self._ctrl_active:
            self.app.controller_overlay.show()
        else:
            self.app.controller_overlay.hide()
        self._update_ctrl_btn_style()

    def _update_ctrl_btn_style(self):
        if self._ctrl_active:
            self._ctrl_toggle_btn.setText("🎮  DÉSACTIVER L'OVERLAY MANETTE")
            self._ctrl_toggle_btn.setStyleSheet(f"""
                QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:11px;font-weight:700;}}
                QPushButton:hover{{background:#e06000;}}""")
        else:
            self._ctrl_toggle_btn.setText("🎮  ACTIVER L'OVERLAY MANETTE")
            self._ctrl_toggle_btn.setStyleSheet(f"""
                QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:11px;font-weight:700;}}
                QPushButton:hover{{background:{C_BG3}cc;}}""")

    def _set_ctrl_mode(self, mode, save=True):
        self.app.controller_overlay.set_mode(mode)
        if save:
            self.app.config["controller_overlay_mode"] = mode
            self.app.config.save()
        for m, b in self._ctrl_style_btns.items():
            active = m == mode
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};"
                f"color:{C_TEXT if active else C_MUTE};border:none;border-radius:4px;"
                f"padding:5px 12px;font-size:10px;font-weight:700;}}"
                + ("" if active else f"QPushButton:hover{{color:{C_TEXT};}}")
            )

    def _reconfigure_hotkey(self):
        dlg = OverlayBindDialog(self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.is_controller:
                self.app.config["overlay_hotkey_type"]           = "controller"
                self.app.config["overlay_hotkey_controller_btn"] = dlg.controller_btn
                self.app.config["overlay_hotkey_key"]            = ""
            else:
                self.app.config["overlay_hotkey_type"]           = "key"
                self.app.config["overlay_hotkey_key"]            = dlg.captured_key or ""
                self.app.config["overlay_hotkey_controller_btn"] = 0
            self.app.config.save()
            self._hk_display.setText(_overlay_hotkey_display(self.app.config))

    def _toggle(self):
        self._active = not self._active
        if self._active:
            self.app.overlay_win.show()
            self._toggle_btn.setText("■  DÉSACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(f"""
                QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:12px;font-weight:700;}}
                QPushButton:hover{{background:#e06000;}}""")
        else:
            self.app.overlay_win.hide()
            self._toggle_btn.setText("▶  ACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(f"""
                QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:12px;font-weight:700;}}
                QPushButton:hover{{background:{C_BG3}cc;}}""")

    def _set_mode(self, mode):
        self.app.overlay_win.set_mode(mode)
        self.app.config["overlay_mode"] = mode
        idx = self._MODE_REVERSE.get(mode, 0)
        if self._mode_combo.currentIndex() != idx:
            self._mode_combo.setCurrentIndex(idx)

    def _set_mmr_mode(self, mode):
        self.app.overlay_win.set_mmr_mode(mode)
        self.app.config["mmr_display_mode"] = mode
        for m, b in self._mmr_btns.items():
            active = m == mode
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};"
                f"color:{C_TEXT if active else C_MUTE};border:none;border-radius:4px;"
                f"padding:5px 12px;font-size:10px;font-weight:700;}}"
                + ("" if active else f"QPushButton:hover{{color:{C_TEXT};}}"))

    def refresh_preview(self, stats):
        if hasattr(self._preview, "update_stats"):
            self._preview.update_stats(stats, self.app.config.get("mmr_display_mode", "both"))



# ─────────────────────────────────────────────────────────────────────────────
#  KEY CAPTURE — Dialog + Widget
# ─────────────────────────────────────────────────────────────────────────────

# Mapping Qt key codes → pyautogui key names
_QT_KEY_MAP = {
    Qt.Key.Key_Space:        "space",
    Qt.Key.Key_Return:       "return",
    Qt.Key.Key_Enter:        "return",
    Qt.Key.Key_Escape:       "escape",
    Qt.Key.Key_Tab:          "tab",
    Qt.Key.Key_Backspace:    "backspace",
    Qt.Key.Key_Delete:       "delete",
    Qt.Key.Key_Up:           "up",
    Qt.Key.Key_Down:         "down",
    Qt.Key.Key_Left:         "left",
    Qt.Key.Key_Right:        "right",
    Qt.Key.Key_F1:  "f1",  Qt.Key.Key_F2:  "f2",  Qt.Key.Key_F3:  "f3",
    Qt.Key.Key_F4:  "f4",  Qt.Key.Key_F5:  "f5",  Qt.Key.Key_F6:  "f6",
    Qt.Key.Key_F7:  "f7",  Qt.Key.Key_F8:  "f8",  Qt.Key.Key_F9:  "f9",
    Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
    Qt.Key.Key_Home:    "home",  Qt.Key.Key_End:      "end",
    Qt.Key.Key_PageUp:  "pageup", Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Insert:  "insert",
    # Pavé numérique
    Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2",
    Qt.Key.Key_3: "3", Qt.Key.Key_4: "4", Qt.Key.Key_5: "5",
    Qt.Key.Key_6: "6", Qt.Key.Key_7: "7", Qt.Key.Key_8: "8",
    Qt.Key.Key_9: "9",
    Qt.Key.Key_division:   "num_div",   Qt.Key.Key_multiply: "num_mul",
    Qt.Key.Key_Minus:      "num_minus", Qt.Key.Key_Plus:      "num_plus",
    Qt.Key.Key_Period:     "num_dec",
    # Touches système
    Qt.Key.Key_Print:      "printscreen",
    Qt.Key.Key_ScrollLock: "scrolllock",
    Qt.Key.Key_Pause:      "pause",
    Qt.Key.Key_NumLock:    "numlock",
    Qt.Key.Key_CapsLock:   "capslock",
}


class KeyCaptureDialog(QDialog):
    """Fenêtre de capture : attend un appui clavier ou clic souris."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enregistrer une touche")
        self.setFixedSize(320, 190)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(f"background:{C_BG2};border:2px solid {C_BLUE};border-radius:8px;")
        self.captured_key = None
        self._listening   = True
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 20)
        lay.setSpacing(14)

        title = QLabel("ENREGISTRER UNE TOUCHE")
        title.setStyleSheet(f"color:{C_BLUE};font-size:10px;font-weight:700;"
                            f"letter-spacing:2px;background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        self._hint = QLabel("Appuie sur une touche clavier\nou clique un bouton souris…")
        self._hint.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        lay.addWidget(self._hint)

        cancel_btn = btn("Annuler", bg=C_BG3, fg=C_MUTE, size=10)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

    def mousePressEvent(self, event):
        """Capture les clics souris comme hotkey."""
        if not self._listening:
            return
        btn_map = {
            Qt.MouseButton.LeftButton:   ("mouse:left",  "🖱  Clic gauche"),
            Qt.MouseButton.RightButton:  ("mouse:right", "🖱  Clic droit"),
            Qt.MouseButton.MiddleButton: ("mouse:middle","🖱  Clic milieu"),
            Qt.MouseButton.BackButton:   ("mouse:x1",    "🖱  Bouton retour"),
            Qt.MouseButton.ForwardButton:("mouse:x2",    "🖱  Bouton avant"),
        }
        info = btn_map.get(event.button())
        if info:
            self._captured(*info)

    def keyPressEvent(self, event):
        if not self._listening:
            return
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
                   Qt.Key.Key_Meta, Qt.Key.Key_CapsLock):
            return
        name = _QT_KEY_MAP.get(key)
        if name is None and 0x20 <= key <= 0x7E:
            name = chr(key).lower()
        if name:
            self._captured(f"key:{name}", f"⌨  {name.upper()}")

    def _captured(self, key, label):
        self._listening = False
        self.captured_key = key
        self._hint.setText(f"✓  {label}")
        QTimer.singleShot(300, self.accept)

    def closeEvent(self, event):
        self._listening = False
        super().closeEvent(event)


def _key_display(key_str):
    """Formate une clé pour affichage."""
    if not key_str:
        return "—"
    if key_str.startswith("key:"):
        return f"⌨  {key_str[4:].upper()}"
    if key_str.startswith("mouse:"):
        labels = {"left": "Clic gauche", "right": "Clic droit",
                  "middle": "Clic milieu", "x1": "Btn retour", "x2": "Btn avant"}
        return f"🖱  {labels.get(key_str[6:], key_str[6:].upper())}"
    return f"⌨  {key_str.upper()}"   # legacy


class KeyCaptureWidget(QWidget):
    """Affiche la touche courante + bouton Enregistrer."""
    key_changed = pyqtSignal(str)

    def __init__(self, key_val="", parent=None):
        super().__init__(parent)
        self._key = key_val
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._display = QLabel(_key_display(key_val))
        self._display.setFixedWidth(140)
        self._display.setStyleSheet(
            f"background:{C_BG3};color:{C_TEXT};border-radius:4px;"
            f"padding:5px 9px;font-size:11px;border:none;")

        self._rec_btn = QPushButton("🎯  Enregistrer")
        self._rec_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._rec_btn.setStyleSheet(f"""
            QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;
                         padding:5px 10px;font-size:9px;font-weight:700;}}
            QPushButton:hover{{background:{C_BLUE};color:{C_TEXT};}}
        """)
        self._rec_btn.clicked.connect(self._start_capture)

        lay.addWidget(self._display)
        lay.addWidget(self._rec_btn)

    def _start_capture(self):
        dlg = KeyCaptureDialog(self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.captured_key:
            self._key = dlg.captured_key
            self._display.setText(_key_display(dlg.captured_key))
            self.key_changed.emit(dlg.captured_key)

    def value(self):
        return self._key


# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 4 — AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────
class AutomationTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(12)

        # ── Avertissements dépendances ────────────────────────────────────
        if not PYAUTOGUI_AVAILABLE:
            warn = card(bg="#2A0E00")
            wl = QVBoxLayout(warn); wl.setContentsMargins(16,14,16,14)
            wl.addWidget(lbl("⚠  pyautogui non installé", C_ORG, 11, True))
            wl.addWidget(lbl("pip install pyautogui", C_TEXT, 10))
            root.addWidget(warn)

        def _parse_delay(v, default):
            try:    return float(v.replace(",", "."))
            except: return default

        def _delay_row(label, cfg_key, default):
            """Crée une ligne label + champ délai (sec, virgule acceptée)."""
            row = QHBoxLayout()
            row.addWidget(lbl(label, C_TEXT, 10))
            row.addStretch()
            field = QLineEdit(str(self.app.config.get(cfg_key, default)))
            field.setFixedWidth(70)
            field.setAlignment(Qt.AlignmentFlag.AlignCenter)
            field.textChanged.connect(
                lambda v, k=cfg_key, d=default:
                    self.app.config.__setitem__(k, _parse_delay(v, d)))
            sec_lbl = lbl("sec", C_MUTE, 9)
            row.addWidget(field); row.addWidget(sec_lbl)
            return row

        def _key_row(label, cfg_key, default):
            """Crée une ligne label + KeyCaptureWidget."""
            row = QHBoxLayout()
            row.addWidget(lbl(label, C_TEXT, 10))
            row.addStretch()
            w = KeyCaptureWidget(self.app.config.get(cfg_key, default))
            w.key_changed.connect(lambda v, k=cfg_key: self.app.config.__setitem__(k, v))
            row.addWidget(w)
            return row

        # ── Skip Replay ───────────────────────────────────────────────────
        sr_card = card()
        sl = QVBoxLayout(sr_card); sl.setContentsMargins(16,14,16,16); sl.setSpacing(10)
        sl.addWidget(lbl("SKIP REPLAY AUTO", C_MUTE, 9))

        self._skip_cb = QCheckBox("Activer le skip replay automatique")
        self._skip_cb.setChecked(bool(self.app.config.get("auto_skip_replay", False)))
        self._skip_cb.toggled.connect(lambda v: self.app.config.__setitem__("auto_skip_replay", v))
        sl.addWidget(self._skip_cb)

        sl.addLayout(_key_row("Touche de skip :", "skip_replay_key", "key:space"))
        sl.addLayout(_delay_row("Délai avant skip (3.55 = immédiat) :", "skip_replay_delay", 0))
        sl.addWidget(lbl("Ajuste le délai si le skip est trop tôt ou trop tard.", C_MUTE, 8))
        root.addWidget(sr_card)

        # ── Auto Queue ────────────────────────────────────────────────────
        q_card = card()
        ql = QVBoxLayout(q_card); ql.setContentsMargins(16,14,16,16); ql.setSpacing(10)
        ql.addWidget(lbl("AUTO REJOUER", C_MUTE, 9))

        self._queue_cb = QCheckBox("Lancer une nouvelle partie automatiquement")
        self._queue_cb.setChecked(bool(self.app.config.get("auto_queue", False)))
        self._queue_cb.toggled.connect(lambda v: self.app.config.__setitem__("auto_queue", v))
        ql.addWidget(self._queue_cb)

        ql.addLayout(_key_row("Touche rejouer :", "queue_key", "key:return"))
        ql.addLayout(_delay_row("Délai après fin de match :", "queue_delay", 5))
        root.addWidget(q_card)

        # ── Auto Freeplay ─────────────────────────────────────────────────
        fp_card = card()
        fpl = QVBoxLayout(fp_card); fpl.setContentsMargins(16,14,16,16); fpl.setSpacing(10)
        fpl.addWidget(lbl("AUTO FREEPLAY", C_MUTE, 9))

        self._freeplay_cb = QCheckBox("Lancer le freeplay automatiquement")
        self._freeplay_cb.setChecked(bool(self.app.config.get("auto_freeplay", False)))
        self._freeplay_cb.toggled.connect(lambda v: self.app.config.__setitem__("auto_freeplay", v))
        fpl.addWidget(self._freeplay_cb)

        fpl.addLayout(_key_row("Touche freeplay :", "freeplay_key", "key:f"))
        fpl.addLayout(_delay_row("Délai après fin de match :", "freeplay_delay", 55))
        root.addWidget(fp_card)

        # ── Players Overlay hotkey ────────────────────────────────────────
        po_card = card()
        pol = QVBoxLayout(po_card); pol.setContentsMargins(16,14,16,16); pol.setSpacing(10)
        pol.addWidget(lbl("OVERLAY JOUEURS  (hotkey)", C_MUTE, 9))
        pol.addWidget(lbl(
            "Appuie sur cette touche en jeu pour afficher / masquer\n"
            "le mini-overlay avec les pseudos des joueurs du match.",
            C_TEXT, 9))
        pol.addLayout(_key_row("Touche overlay joueurs :", "players_overlay_key", "key:f7"))
        root.addWidget(po_card)

        save_btn = btn("💾  Sauvegarder", bg=C_BLUE, fg=C_TEXT, size=10)
        save_btn.clicked.connect(self.app.config.save)
        root.addWidget(save_btn)
        root.addStretch()



# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 5 — SONS
# ─────────────────────────────────────────────────────────────────────────────

_SOUND_EVENTS = [
    ("goal_scored",   "🎯  But marqué"),
    ("goal_conceded", "💀  But encaissé"),
    ("crossbar",      "🏐  Poteau / Barre"),
    ("demo_me",       "💥  Démoli (toi)"),
    ("demo_opponent", "🔥  Démolition adverse"),
    ("epic_save",     "🧤  Epic Save"),
    ("save",          "🛡  Save"),
]

class SoundTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(10)

        if not PYGAME_AVAILABLE:
            warn = card(bg="#2A0E00")
            wl = QVBoxLayout(warn); wl.setContentsMargins(16, 12, 16, 12)
            wl.addWidget(lbl("⚠  pygame non installé", C_ORG, 11, True))
            wl.addWidget(lbl("pip install pygame", C_TEXT, 10))
            root.addWidget(warn)

        header = card(bg=C_BG2)
        hl = QVBoxLayout(header); hl.setContentsMargins(14, 10, 14, 10)
        hl.addWidget(lbl("Place tes fichiers .mp3 / .wav dans le meme dossier que l exe.", C_MUTE, 8))
        root.addWidget(header)

        # ── Slider de volume global ───────────────────────────────────────
        vol_card = card()
        vl = QVBoxLayout(vol_card); vl.setContentsMargins(14, 10, 14, 12); vl.setSpacing(6)
        vl.addWidget(lbl("VOLUME GLOBAL", C_MUTE, 9))

        vol_row = QHBoxLayout(); vol_row.setSpacing(10)
        vol_icon = lbl("🔈", C_TEXT, 12)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(int(self.app.config.get("sound_volume", 100)))
        self._vol_slider.setFixedHeight(22)
        self._vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #1A1E2A; border-radius: 4px; height: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #1A8CFF; border-radius: 4px; height: 6px;
            }
            QSlider::handle:horizontal {
                background: #E8ECF4; border-radius: 7px;
                width: 14px; height: 14px; margin: -4px 0;
            }
            QSlider::handle:horizontal:hover { background: #1A8CFF; }
        """)
        self._vol_pct = lbl(f"{self._vol_slider.value()}%", C_TEXT, 10, bold=True)
        self._vol_pct.setFixedWidth(36)

        def _on_vol(v):
            self._vol_pct.setText(f"{v}%")
            self.app.config["sound_volume"] = v

        self._vol_slider.valueChanged.connect(_on_vol)

        vol_row.addWidget(vol_icon)
        vol_row.addWidget(self._vol_slider, 1)
        vol_row.addWidget(lbl("🔊", C_TEXT, 12))
        vol_row.addWidget(self._vol_pct)
        vl.addLayout(vol_row)
        root.addWidget(vol_card)

        for key, label in _SOUND_EVENTS:
            cfg_en  = f"sound_{key}"
            cfg_file = f"snd_file_{key}"

            c = card()
            cl = QVBoxLayout(c); cl.setContentsMargins(14, 12, 14, 12); cl.setSpacing(8)

            # Ligne 1 : checkbox + label
            cb = QCheckBox(label)
            cb.setChecked(bool(self.app.config.get(cfg_en, True)))
            cb.toggled.connect(lambda v, k=cfg_en: self.app.config.__setitem__(k, v))
            cl.addWidget(cb)

            # Ligne 2 : champ fichier + bouton parcourir + test
            file_row = QHBoxLayout(); file_row.setSpacing(6)

            field = QLineEdit(self.app.config.get(cfg_file, ""))
            field.setPlaceholderText("son.wav  ou  chemin complet")
            field.setStyleSheet(
                f"background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;"
                f"padding:4px 8px;font-size:10px;")
            field.textChanged.connect(lambda v, k=cfg_file: self.app.config.__setitem__(k, v.strip()))

            browse_btn = QPushButton("📂")
            browse_btn.setFixedWidth(34)
            browse_btn.setToolTip("Choisir un fichier son")
            browse_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;"
                f"border-radius:4px;padding:4px;font-size:11px;}}"
                f"QPushButton:hover{{background:{C_BLUE};}}")
            browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            browse_btn.clicked.connect(lambda _, f=field, k=cfg_file: self._browse(f, k))

            test_btn = QPushButton("▶")
            test_btn.setFixedWidth(34)
            test_btn.setToolTip("Tester le son")
            test_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_GREEN};border:none;"
                f"border-radius:4px;padding:4px;font-size:11px;}}"
                f"QPushButton:hover{{background:{C_BG3};color:white;}}")
            test_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            test_btn.clicked.connect(lambda _, f=field: self.app._play_sound(f.text().strip()))

            file_row.addWidget(field)
            file_row.addWidget(browse_btn)
            file_row.addWidget(test_btn)
            cl.addLayout(file_row)
            root.addWidget(c)

        save_btn = btn("💾  Sauvegarder", bg=C_BLUE, fg=C_TEXT, size=10)
        save_btn.clicked.connect(self.app.config.save)
        root.addWidget(save_btn)
        root.addStretch(1)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _browse(self, field, cfg_key):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier son", BASE_DIR,
            "Fichiers audio (*.wav *.mp3 *.ogg *.flac);;Tous (*)")
        if path:
            # Stocker le nom de fichier relatif si dans le meme dossier
            rel = os.path.relpath(path, BASE_DIR)
            if not rel.startswith(".."):
                path = rel
            field.setText(path)
            self.app.config[cfg_key] = path
            self.app.config.save()

# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 6 — PARAMÈTRES
# ─────────────────────────────────────────────────────────────────────────────
class SettingsTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(12)

        # ── Mode Streamer ──────────────────────────────────────────────────
        sm_card = card()
        sml = QVBoxLayout(sm_card); sml.setContentsMargins(16, 14, 16, 16); sml.setSpacing(10)
        sml.addWidget(lbl("MODE STREAMER", C_MUTE, 9))
        sml.addWidget(lbl(
            "Active une barre noire en haut de l'écran pour cacher le popup\n"
            "\"Partie Trouvée\" de Rocket League (anti stream-snipe).\n"
            "Coupe également le son système pour ne pas alerter les viewers.",
            C_TEXT, 9))

        self._streamer_btn = btn(
            "🎥  ACTIVER LE MODE STREAMER", bg=C_BG3, fg=C_TEXT, size=11)
        self._streamer_btn.setFixedHeight(42)
        self._streamer_btn.clicked.connect(self._toggle_streamer)
        sml.addWidget(self._streamer_btn)

        mute_row = QHBoxLayout()
        mute_row.addWidget(lbl("Couper le son hors partie (recherche)", C_TEXT, 11))
        self._streamer_mute_chk = QCheckBox()
        self._streamer_mute_chk.setChecked(self.app.config.get("streamer_mute_audio", True))
        self._streamer_mute_chk.stateChanged.connect(self._on_streamer_mute_changed)
        mute_row.addStretch()
        mute_row.addWidget(self._streamer_mute_chk)
        sml.addLayout(mute_row)

        self._streamer_hint = lbl("", C_MUTE, 9)
        sml.addWidget(self._streamer_hint)
        root.addWidget(sm_card)

        # Initialise le style du bouton selon la config sauvegardée
        self._streamer_active = self.app.config.get("streamer_mode", False)
        self._update_streamer_btn()

        # ── Joueur ────────────────────────────────────────────────────────
        jcard = card()
        jl = QVBoxLayout(jcard); jl.setContentsMargins(16,14,16,16); jl.setSpacing(8)
        jl.addWidget(lbl("JOUEUR", C_MUTE, 9))

        r1 = QHBoxLayout()
        r1.addWidget(lbl("Plateforme", C_TEXT, 11))
        self._platform = QComboBox()
        self._platform.addItems(["epic", "steam", "ps4", "xbox", "switch"])
        self._platform.setCurrentText(self.app.config["platform"])
        self._platform.setFixedWidth(110)
        r1.addStretch(); r1.addWidget(self._platform)
        jl.addLayout(r1)

        r2 = QHBoxLayout()
        self._username_lbl = lbl("Pseudo (exact)", C_TEXT, 11)
        r2.addWidget(self._username_lbl)
        self._username = QLineEdit(self.app.config["username"])
        self._username.setFixedWidth(180)
        r2.addStretch(); r2.addWidget(self._username)
        jl.addLayout(r2)
        root.addWidget(jcard)

        # Met à jour le label/placeholder quand la plateforme change
        self._platform.currentTextChanged.connect(self._on_platform_changed)
        self._on_platform_changed(self._platform.currentText())

        # ── Overlay résultat ──────────────────────────────────────────────
        ocard = card()
        ol = QVBoxLayout(ocard); ol.setContentsMargins(16,14,16,16); ol.setSpacing(8)
        ol.addWidget(lbl("OVERLAY VICTOIRE / DÉFAITE", C_MUTE, 9))

        r_on = QHBoxLayout()
        r_on.addWidget(lbl("Activer l'overlay résultat", C_TEXT, 11))
        self._result_overlay_enabled = QCheckBox()
        self._result_overlay_enabled.setChecked(self.app.config.get("result_overlay_enabled", True))
        r_on.addStretch(); r_on.addWidget(self._result_overlay_enabled)
        ol.addLayout(r_on)

        r_th = QHBoxLayout()
        r_th.addWidget(lbl("Thème", C_TEXT, 11))
        self._result_theme = QComboBox()
        self._result_theme.addItems(["auto", "rl_classic", "victory", "defeat", "neon", "dark_minimal"])
        self._result_theme.setCurrentText(self.app.config.get("result_overlay_theme", "auto"))
        self._result_theme.setFixedWidth(130)
        r_th.addStretch(); r_th.addWidget(self._result_theme)
        ol.addLayout(r_th)
        root.addWidget(ocard)

        # ── StatsAPI setup ────────────────────────────────────────────────
        api_card = card(bg="#091409")
        al = QVBoxLayout(api_card); al.setContentsMargins(16,14,16,16); al.setSpacing(8)
        al.addWidget(lbl("⚙  STATSAPI — CONFIGURATION OBLIGATOIRE", C_GREEN, 9, True))
        al.addWidget(lbl("Édite ce fichier AVANT de lancer Rocket League :", C_TEXT, 10))
        al.addWidget(lbl("TAGame\\Config\\DefaultStatsAPI.ini", C_GOLD, 10, True))

        ini_preview = QTextEdit()
        ini_preview.setReadOnly(True); ini_preview.setFixedHeight(62)
        ini_preview.setText("[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123")
        al.addWidget(ini_preview)

        open_btn = btn("📂  Ouvrir le dossier Config de RL", bg=C_BG3, size=10)
        open_btn.clicked.connect(self._open_rl_config)
        al.addWidget(open_btn)

        auto_btn = btn("⚡  Configurer automatiquement le .ini", bg=C_GREEN, fg="#000000", size=10)
        auto_btn.clicked.connect(self._auto_configure_ini)
        al.addWidget(auto_btn)

        self._ini_status = lbl("", C_GREEN, 9)
        self._ini_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(self._ini_status)
        root.addWidget(api_card)

        # ── tracker.gg API ────────────────────────────────────────────────
        tcard = card()
        tl = QVBoxLayout(tcard); tl.setContentsMargins(16,14,16,14); tl.setSpacing(6)
        tl.addWidget(lbl("SOURCE DES DONNÉES MMR & RANG", C_MUTE, 9))
        tl.addWidget(lbl("✓ API tracker.gg — aucune dépendance externe requise", C_GREEN, 9))
        tl.addWidget(lbl("⚠  Le pseudo doit correspondre exactement au profil tracker.gg", C_ORG, 9))
        root.addWidget(tcard)

        save_btn = btn("💾  Sauvegarder les paramètres", bg=C_BLUE, fg=C_TEXT, size=12)
        save_btn.setFixedHeight(42)
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn)

        self._save_lbl = lbl("", C_GREEN, 10)
        self._save_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._save_lbl)
        root.addStretch()

    def _on_streamer_mute_changed(self, state):
        self.app.config["streamer_mute_audio"] = bool(state)
        self.app.config.save()
        self._update_streamer_btn()

    def _toggle_streamer(self):
        self._streamer_active = not self._streamer_active
        self.app.config["streamer_mode"] = self._streamer_active
        saved = self.app.config.save()
        self.app._apply_streamer_mode(self._streamer_active)
        self._update_streamer_btn()
        if not saved:
            # Avertissement visible si le fichier config est en lecture seule
            # (ex: BakkyTrack installé dans Program Files)
            self._streamer_hint.setText(
                "⚠  Config non sauvegardée — vérifier les droits d'accès au dossier")
            self._streamer_hint.setStyleSheet(
                f"color:{C_ORG};font-size:9px;background:transparent;")

    def _update_streamer_btn(self):
        if self._streamer_active:
            self._streamer_btn.setText("🎥  DÉSACTIVER LE MODE STREAMER")
            self._streamer_btn.setStyleSheet(f"""
                QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:11px;font-weight:700;}}
                QPushButton:hover{{background:#e06000;}}""")
            self._streamer_hint.setText("✓  Barre noire active — son coupé" if self.app.config.get("streamer_mute_audio", True) else "✓  Barre noire active")
            self._streamer_hint.setStyleSheet(f"color:{C_GREEN};font-size:9px;background:transparent;")
        else:
            self._streamer_btn.setText("🎥  ACTIVER LE MODE STREAMER")
            self._streamer_btn.setStyleSheet(f"""
                QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:11px;font-weight:700;}}
                QPushButton:hover{{background:{C_BG3}cc;}}""")
            self._streamer_hint.setText("")

    def _on_platform_changed(self, platform):
        if platform == "steam":
            self._username_lbl.setText("Steam ID (64-bit)")
            self._username.setPlaceholderText("ex: 76561198012345678")
        else:
            self._username_lbl.setText("Pseudo (exact)")
            self._username.setPlaceholderText("ex: MonPseudo#1234")

    def _find_rl_config_dirs(self):
        """Cherche tous les dossiers TAGame/Config possibles selon les variantes de noms RL."""
        # Variantes possibles du nom du dossier RL
        rl_variants = ["rocketleague", "Rocket League", "RocketLeague", "rocket-league", "Rocket-League"]
        
        # Dossiers racine à explorer
        base_paths = [
            r"C:\Program Files\Epic Games",
            r"C:\Program Files (x86)\Epic Games",
            r"C:\Program Files (x86)\Steam\steamapps\common",
            r"C:\Program Files\Steam\steamapps\common",
        ]
        
        # Ajouter les chemins Steam personnalisés (via libraryfolders.vdf)
        vdf_paths = [
            r"C:\Program Files (x86)\Steam\config\libraryfolders.vdf",
            r"C:\Program Files\Steam\config\libraryfolders.vdf",
        ]
        for vdf in vdf_paths:
            if os.path.exists(vdf):
                try:
                    for line in open(vdf, encoding="utf-8", errors="replace"):
                        line = line.strip()
                        if '"path"' in line.lower():
                            p = line.split('"')[-2]
                            candidate = os.path.join(p, "steamapps", "common")
                            if os.path.exists(candidate):
                                base_paths.append(candidate)
                except Exception:
                    pass
        
        found = []
        for base in base_paths:
            if not os.path.exists(base):
                continue
            for variant in rl_variants:
                cfg_dir = os.path.join(base, variant, "TAGame", "Config")
                if os.path.exists(cfg_dir):
                    found.append(cfg_dir)
        return found

    def _open_rl_config(self):
        dirs = self._find_rl_config_dirs()
        if dirs:
            QDesktopServices.openUrl(QUrl.fromLocalFile(dirs[0]))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.expanduser("~")))

    def _auto_configure_ini(self):
        """Écrit DefaultStatsAPI.ini automatiquement dans tous les dossiers RL trouvés."""
        ini_content = "[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123\n"
        
        dirs = self._find_rl_config_dirs()
        found = []
        for cfg_dir in dirs:
            ini_path = os.path.join(cfg_dir, "DefaultStatsAPI.ini")
            try:
                with open(ini_path, "w", encoding="utf-8") as f:
                    f.write(ini_content)
                found.append(ini_path)
            except Exception as e:
                self._ini_status.setText(f"Erreur: {e}")
                return

        if found:
            self._ini_status.setStyleSheet(f"color:{C_GREEN};font-size:9px;")
            self._ini_status.setText(f"✓  Configuré dans {len(found)} dossier(s) RL")
        else:
            self._ini_status.setStyleSheet(f"color:{C_ORG};font-size:9px;")
            self._ini_status.setText("⚠  Dossier Rocket League introuvable — configure manuellement")
        QTimer.singleShot(5000, lambda: self._ini_status.setText(""))

    def _save(self):
        self.app.config["platform"]               = self._platform.currentText()
        self.app.config["username"]               = self._username.text().strip()
        self.app.config["result_overlay_enabled"] = self._result_overlay_enabled.isChecked()
        self.app.config["result_overlay_theme"]   = self._result_theme.currentText()
        self.app.config.save()
        self._save_lbl.setText("✓  Sauvegardé !")
        QTimer.singleShot(2500, lambda: self._save_lbl.setText(""))
        self.app.fetch_mmr_async(force=True)




# ── Constantes bytes pour le parser JSON (évite chr() dans la boucle chaude) ──
_B_OPEN      = ord('{')
_B_CLOSE     = ord('}')
_B_QUOTE     = ord('"')
_B_BACKSLASH = ord('\\')

# ─────────────────────────────────────────────────────────────────────────────
#  SERVICE 1 — MATCH  (état de jeu + parsing StatsAPI, zéro PyQt UI)
# ─────────────────────────────────────────────────────────────────────────────
class MatchService:
    """Gère l'état de session (W/L/streak), la connexion TCP StatsAPI
    et le parsing de tous les events du jeu.

    N'importe aucun widget PyQt — communique uniquement via AppSignals.
    """

    def __init__(self, config: "Config", signals: "AppSignals"):
        self.config  = config
        self.signals = signals

        # ── Session ──────────────────────────────────────────────────────
        self.wins          = 0
        self.losses        = 0
        self.streak        = 0
        self.streak_type   = None
        self.history       = []
        self.session_start = time.time()

        # ── Match en cours ───────────────────────────────────────────────
        self.my_team              = None
        self._last_known_my_team  = None   # persiste entre MatchEnded et MatchDestroyed
        self.team_scores          = {}
        self._last_scores         = {}
        self.current_players         = []
        self._current_player_names   = ()   # tuple pour comparaison rapide
        self.detected_player_name    = ""
        self.detected_player_primary_id = ""
        self._goal_counts         = {0: 0, 1: 0}
        self._prev_tgt_stats      = {}
        self._match_result_saved  = False  # True dès que MatchEnded a enregistré un résultat
        self._match_started       = False  # True dès que RoundStarted/CountdownBegin reçu
        self._had_opponent        = False  # True dès qu'on a vu les 2 équipes (pas freeplay)
        self._last_update_log_t   = 0.0   # Throttle du log UpdateState (max 1/s)
        # ── Connexion ────────────────────────────────────────────────────
        self._running  = True
        self._tcp_sock = None

    # ── Session ──────────────────────────────────────────────────────────
    def add(self, t, auto=False):
        if t == "win": self.wins += 1
        else:          self.losses += 1
        if self.streak_type == t: self.streak += 1
        else: self.streak = 1; self.streak_type = t
        self.history.insert(0, (t, time.strftime("%H:%M:%S"), auto))
        self.signals.match_result.emit(t)

    def remove(self, t):
        if t == "win"  and self.wins   > 0: self.wins   -= 1
        elif t == "loss" and self.losses > 0: self.losses -= 1
        else: return
        for i, h in enumerate(self.history):
            if h[0] == t: self.history.pop(i); break
        self._recalc_streak()
        self.signals.match_result.emit(t)

    def _recalc_streak(self):
        if not self.history:
            self.streak = 0; self.streak_type = None; return
        self.streak_type = self.history[0][0]; self.streak = 0
        for h in self.history:
            if h[0] == self.streak_type: self.streak += 1
            else: break

    def reset_session(self, mmr_service=None):
        self.wins = 0; self.losses = 0; self.history = []
        self.streak = 0; self.streak_type = None
        self.session_start = time.time()
        self.signals.match_result.emit("reset")
        if mmr_service:
            mmr_service.reset_deltas()
            self.signals.mmr_updated.emit()

    # ── StatsAPI TCP ──────────────────────────────────────────────────────
    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False
        if self._tcp_sock:
            try: self._tcp_sock.close()
            except: pass
            self._tcp_sock = None

    def restart(self, port=None):
        self.stop()
        time.sleep(0.25)
        if port is not None:
            self.config["statsapi_port"] = port
        self.start()

    def _loop(self):
        port = self.config["statsapi_port"]
        self.signals.status_changed.emit("", f"Connexion StatsAPI port {port}…")
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("127.0.0.1", port))
            sock.settimeout(None)
            self._tcp_sock = sock
            self.signals.status_changed.emit("connected", f"StatsAPI connecté · port {port}")
            buf = b""
            while self._running:
                try:    chunk = sock.recv(4096)
                except OSError: break
                if not chunk: break
                buf += chunk
                while buf:
                    start = buf.find(b"{")
                    if start == -1: buf = b""; break
                    buf = buf[start:]
                    depth = end = 0; in_str = escaped = False
                    for i, bv in enumerate(buf):
                        # Comparaisons directes sur bytes — évite chr() à 30/s
                        if escaped:          escaped = False; continue
                        if bv == _B_BACKSLASH and in_str: escaped = True; continue
                        if bv == _B_QUOTE:   in_str = not in_str; continue
                        if in_str:           continue
                        if bv == _B_OPEN:    depth += 1
                        elif bv == _B_CLOSE:
                            depth -= 1
                            if depth == 0: end = i; break
                    if end == 0 and depth != 0: break
                    msg = buf[:end + 1]; buf = buf[end + 1:]
                    try:
                        # Détection UpdateState sur bytes bruts — évite decode inutile
                        _now = time.monotonic()
                        _is_update = b'"UpdateState"' in msg[:60]
                        if not _is_update or (_now - self._last_update_log_t) >= 1.0:
                            _decoded = msg.decode(errors="replace")
                            self.signals.log_event.emit(_decoded[:80])
                            if _is_update:
                                self._last_update_log_t = _now
                    except RuntimeError:
                        return
                    try:
                        self._process_event(json.loads(msg))
                    except Exception as e:
                        try: self.signals.log_event.emit(f"ERR parse: {e}")
                        except RuntimeError: return

        except ConnectionRefusedError:
            if not self._running: return
            try: self.signals.status_changed.emit("error", "Connexion refusée — lance RL + SOS plugin")
            except RuntimeError: return
        except socket.timeout:
            if not self._running: return
            try: self.signals.status_changed.emit("error", "Timeout — SOS plugin actif ?")
            except RuntimeError: return
        except Exception as e:
            if not self._running: return
            try: self.signals.status_changed.emit("error", f"Erreur: {str(e)[:50]}")
            except RuntimeError: return
        finally:
            if sock:
                try: sock.close()
                except: pass
            self._tcp_sock = None; self.my_team = None
            try: self.signals.status_changed.emit("error", "Déconnecté")
            except RuntimeError: pass

        if self._running:
            time.sleep(3)
            self.signals.log_event.emit("Reconnexion StatsAPI…")
            self._loop()

    def _process_event(self, outer: dict):
        event = outer.get("Event", "")
        inner = outer.get("Data", {})
        if isinstance(inner, str):
            try: inner = json.loads(inner)
            except: return

        # ── UpdateState ───────────────────────────────────────────────────
        if event == "UpdateState":
            game    = inner.get("Game", {})
            players = inner.get("Players", [])

            new_names = tuple(p.get("Name") for p in players)
            if new_names != self._current_player_names:
                self._current_player_names = new_names
                self.current_players = players
                self.signals.players_updated.emit(players)

            for team in game.get("Teams", []):
                tnum  = team["TeamNum"]
                score = team["Score"]
                prev  = self._last_scores.get(tnum, -1)
                if prev >= 0 and score > prev:
                    self._goal_counts[tnum] = self._goal_counts.get(tnum, 0) + 1
                    if self.my_team is not None:
                        snd = "goal_scored" if tnum == self.my_team else "goal_conceded"
                        self.signals.trigger_sound.emit(snd)
                    if self.config.get("auto_skip_replay"):
                        key   = self.config.get("skip_replay_key", "key:space")
                        delay = float(self.config.get("skip_replay_delay", 0))
                        self.signals.log_event.emit(
                            f"[Auto] But ! Skip dans {delay:.1f}s → {_key_display(key)}")
                        self.signals.press_key_sig.emit(key, delay)
                self._last_scores[tnum] = score
                self.team_scores[tnum]  = score

            # Vraie partie compétitive = des joueurs physiquement présents
            # dans les deux équipes. En freeplay, le jeu envoie quand même
            # Teams[0] et Teams[1] dans les scores (score=0) sans adversaire,
            # ce qui déclencherait un faux résultat. Vérifier la liste
            # Players est plus fiable : en freeplay il n'y a que toi.
            teams_with_players = {p.get("TeamNum") for p in players}
            if 0 in teams_with_players and 1 in teams_with_players:
                if not self._had_opponent:
                    self._had_opponent = True
                    # Première confirmation d'adversaire réel → désactiver la barre streamer.
                    # On le fait ici (et non dans RoundStarted) pour ignorer le freeplay
                    # qui émet aussi RoundStarted sans jamais avoir de TeamNum 1 dans Players.
                    if self._match_started:
                        self.signals.game_phase_changed.emit("ingame")

            if self.my_team is None:
                platform    = self.config.get("platform", "epic").lower()
                _PLAT_PREFIX = {
                    "epic":   "Epic|",
                    "steam":  "Steam|",
                    "ps4":    "PS4|",
                    "xbox":   "XboxOne|",
                    "switch": "Switch|",
                }
                plat_prefix = _PLAT_PREFIX.get(platform, "Epic|")
                known_name  = (self.config.get("username") or
                               self.detected_player_name or "").strip().lower()
                for p in players:
                    matched = False
                    pid = p.get("PrimaryId", "")
                    if pid.startswith(plat_prefix):
                        if known_name:
                            matched = p.get("Name", "").strip().lower() == known_name
                        else:
                            # Compter les joueurs de cette plateforme par équipe.
                            # Fonctionne en 1v1, 2v2 et 3v3 : si tu es le seul
                            # joueur Epic/Steam dans ton équipe, c'est toi.
                            team_plat_counts = {}
                            for x in players:
                                if x.get("PrimaryId", "").startswith(plat_prefix):
                                    t = x.get("TeamNum")
                                    team_plat_counts[t] = team_plat_counts.get(t, 0) + 1
                            p_team = p.get("TeamNum")
                            matched = (pid.startswith(plat_prefix) and
                                       team_plat_counts.get(p_team, 0) == 1)
                    if not matched and known_name:
                        matched = p.get("Name", "").strip().lower() == known_name
                    if matched:
                        self.my_team = p.get("TeamNum")
                        self._last_known_my_team = self.my_team
                        self.detected_player_name = p.get("Name", "")
                        self.detected_player_primary_id = p.get("PrimaryId", "")
                        self.signals.player_detected.emit(self.detected_player_name, self.my_team)
                        break

                # bHasTarget fallback — UNIQUEMENT si la cible a des champs spectateur
                # (Boost, Speed…) dans la liste joueurs, confirmant qu'elle est dans
                # NOTRE équipe (ces champs ne sont visibles que pour sa propre équipe).
                # Sans cette vérification, la transition fin-de-replay peut pointer
                # la caméra sur le buteur adverse → équipe erronée détectée.
                if self.my_team is None and game.get("bHasTarget") and not game.get("bReplay"):
                    tgt      = game.get("Target", {})
                    tgt_name = tgt.get("Name", "")
                    tgt_team = tgt.get("TeamNum")
                    if tgt_name and tgt_team is not None:
                        for p in players:
                            if p.get("Name") == tgt_name and "Boost" in p:
                                self.my_team = tgt_team
                                self._last_known_my_team = tgt_team
                                if not self.detected_player_name:
                                    self.detected_player_name = tgt_name
                                self.signals.player_detected.emit(tgt_name, tgt_team)
                                break

        # ── GoalScored ────────────────────────────────────────────────────
        elif event == "GoalScored":
            pass  # géré via UpdateState (plus fiable)

        elif event == "MatchCreated":
            # Nouvelle partie qui commence. Si l'ancienne partie n'a pas eu de
            # MatchEnded (abandon, crash…), calculer son résultat MAINTENANT,
            # pendant que my_team et team_scores sont encore valides pour elle.
            # On ne peut plus attendre MatchDestroyed car d'ici là l'état aura
            # été écrasé par la nouvelle partie.
            # _had_opponent évite de déduire un résultat depuis le freeplay
            # (qui n'a qu'une seule équipe).
            if not self._match_result_saved and self._match_started and self._had_opponent:
                my = self.my_team or self._last_known_my_team
                if my is not None and self.team_scores:
                    my_score  = self.team_scores.get(my, 0)
                    opp_score = self.team_scores.get(1 - my, 0)
                    if my_score != opp_score:
                        result = "win" if my_score > opp_score else "loss"
                        self.signals.log_event.emit(
                            f"MatchCreated (résultat parti précédente déduit) → {result.upper()}"
                            f" ({my_score}-{opp_score})")
                        self.signals.match_result.emit("__auto__" + result)
            # Réinitialisation complète pour la nouvelle partie
            self._match_result_saved = False
            self._match_started      = False
            self._had_opponent       = False
            self.my_team             = None
            self._last_known_my_team = None
            self.team_scores         = {}
            self._last_scores        = {}
            self._goal_counts        = {0: 0, 1: 0}
            self.current_players         = []
            self._current_player_names   = ()
            # Barre streamer ON dès MatchCreated : cache le popup "Partie trouvée".
            self.signals.game_phase_changed.emit("lobby")

        elif event in ("MatchInitialized",):
            self._match_result_saved = False

        elif event in ("RoundStarted", "CountdownBegin"):
            self._match_result_saved = False
            self._match_started      = True
            # Si les deux équipes étaient déjà visibles avant le countdown → barre OFF.
            # Freeplay : _had_opponent reste False → barre reste ON. ✓
            if self._had_opponent:
                self.signals.game_phase_changed.emit("ingame")

        # ── StatfeedEvent — demos, saves, epic saves ──────────────────────
        elif event == "StatfeedEvent":
            ev_name     = inner.get("EventName", "")
            main_target = inner.get("MainTarget", {})
            sec_target  = inner.get("SecondaryTarget", {})
            my_name     = self.detected_player_name

            if ev_name == "Demolish":
                if sec_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("demo_me")
                elif main_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("demo_opponent")
            elif ev_name in ("Save", "AerialSave", "AerialSaveReward"):
                if main_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("save")
            elif ev_name in ("EpicSave", "EpicAerialSave"):
                if main_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("epic_save")

        # ── CrossbarHit ───────────────────────────────────────────────────
        elif event == "CrossbarHit":
            self.signals.trigger_sound.emit("crossbar")

        # ── MatchEnded ────────────────────────────────────────────────────
        elif event == "MatchEnded":
            winner = inner.get("WinnerTeamNum")
            my     = self.my_team

            # Fallback 1 : équipe mémorisée pendant le match
            if my is None:
                my = self._last_known_my_team

            # Fallback 2 : cherche par pseudo dans la dernière liste connue
            if my is None and self.current_players:
                known = (self.config.get("username") or
                         self.detected_player_name or "").strip().lower()
                if known:
                    for p in self.current_players:
                        if p.get("Name", "").strip().lower() == known:
                            my = p.get("TeamNum"); break
                if my is None:
                    for p in self.current_players:
                        if "Boost" in p and "Speed" in p:
                            my = p.get("TeamNum"); break

            if winner is not None and my is not None:
                my_score  = self.team_scores.get(my, 0)
                opp_score = self.team_scores.get(1 - my, 0)
                if my_score > opp_score:      result = "win"
                elif opp_score > my_score:    result = "loss"
                else: result = "win" if winner == my else "loss"
                self.signals.log_event.emit(
                    f"MatchEnded → {result.upper()} ({my_score}-{opp_score})"
                    f"{' [ff/forfait]' if my_score + opp_score == 0 else ''}")
                self.signals.match_result.emit("__auto__" + result)
                self._match_result_saved = True
            else:
                self.signals.log_event.emit(
                    f"MatchEnded ignoré — my_team={my} winner={winner}")

            self.my_team        = None
            self.team_scores    = {}
            self._last_scores   = {}
            self._goal_counts   = {0: 0, 1: 0}
            self._match_started = False
            self.signals.game_phase_changed.emit("lobby")   # → barre streamer ON

        # ── MatchDestroyed ────────────────────────────────────────────────
        elif event == "MatchDestroyed":
            # Si MatchEnded n'a jamais été reçu (quitte pendant replay/podium),
            # on tente de déduire le résultat depuis les scores connus.
            # GARDE : _match_started doit être True pour qu'on ait vraiment joué
            # un round — évite les faux résultats quand MatchDestroyed d'une
            # ancienne partie arrive après que la nouvelle partie a déjà démarré.
            # _had_opponent évite les faux résultats depuis le freeplay.
            if not self._match_result_saved and self._match_started and self._had_opponent:
                my = self.my_team or self._last_known_my_team
                if my is not None and self.team_scores:
                    my_score  = self.team_scores.get(my, 0)
                    opp_score = self.team_scores.get(1 - my, 0)
                    if my_score != opp_score:
                        result = "win" if my_score > opp_score else "loss"
                        self.signals.log_event.emit(
                            f"MatchDestroyed (sans MatchEnded) → {result.upper()}"
                            f" ({my_score}-{opp_score})")
                        self.signals.match_result.emit("__auto__" + result)
                    else:
                        self.signals.log_event.emit(
                            "MatchDestroyed sans MatchEnded — score nul, résultat ignoré")
                else:
                    self.signals.log_event.emit(
                        "MatchDestroyed sans MatchEnded — équipe inconnue, résultat ignoré")

            self.my_team              = None
            self._last_known_my_team  = None
            self.team_scores          = {}
            self._last_scores         = {}
            self._goal_counts         = {0: 0, 1: 0}
            self._prev_tgt_stats      = {}
            self._match_result_saved  = False
            self._match_started       = False
            self._had_opponent        = False
            self.current_players         = []
            self._current_player_names   = ()
            self.signals.players_updated.emit([])
            self.signals.game_phase_changed.emit("lobby")   # → barre streamer ON

        elif event in ("PodiumStart", "GoalReplayStart"):
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  SERVICE 2 — MMR  (tracker.gg API — HTTP pur, sans Selenium)
# ─────────────────────────────────────────────────────────────────────────────
class MMRService:
    """Récupère le MMR et le rang via l'API tracker.gg.

    Aucune dépendance externe (pas de Selenium, pas de Chrome).
    Communique uniquement via AppSignals — zéro widget PyQt.
    """

    _CACHE_PATH  = os.path.join(BASE_DIR, "mmr_cache.json")
    _MAX_RETRIES = 3
    _RETRY_WAIT  = 4   # secondes entre tentatives (×attempt pour backoff linéaire)

    # Liste ordonnée des rangs — l'index = tier_id (0 = Unranked, 22 = SSL)
    _RANKS = [
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

    # playlistId tracker.gg → clé interne
    _PLAYLIST_IDS = {10: "1v1", 11: "2v2", 13: "3v3"}

    # Slug plateforme pour l'URL tracker.gg
    _PLATFORM_SLUG = {
        "epic":   "epic",
        "steam":  "steam",
        "ps4":    "psn",
        "xbox":   "xbl",
        "switch": "switch",
    }

    def __init__(self, config: "Config", signals: "AppSignals"):
        self.config            = config
        self.signals           = signals
        self.selected_playlist = "3v3"
        self.all_mmr = {
            k: {"mmr": None, "mmr_start": None, "mmr_change": 0,
                "rank": "", "tier_id": 0, "div_id": 0}
            for k in PLAYLIST_NAMES
        }
        self._load_cache()

    # ── Helpers rang ──────────────────────────────────────────────────────
    def _tier_id(self, rank_name: str) -> int:
        try:
            return self._RANKS.index(rank_name)
        except ValueError:
            return 0

    def _div_id(self, div_name: str) -> int:
        return {"Division I": 1, "Division II": 2,
                "Division III": 3, "Division IV": 4}.get(div_name, 0)

    # ── Cache disque ──────────────────────────────────────────────────────
    def _load_cache(self):
        try:
            with open(self._CACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for k in PLAYLIST_NAMES:
                if k in data:
                    cached_mmr = data[k].get("mmr")
                    self.all_mmr[k]["mmr"]       = cached_mmr
                    self.all_mmr[k]["mmr_start"] = cached_mmr   # delta repart de zéro
                    self.all_mmr[k]["rank"]      = data[k].get("rank", "")
                    self.all_mmr[k]["tier_id"]   = data[k].get("tier_id", 0)
                    self.all_mmr[k]["div_id"]    = data[k].get("div_id", 0)
        except Exception:
            pass   # premier lancement ou cache corrompu, pas grave

    def _save_cache(self):
        try:
            data = {
                k: {"mmr": v["mmr"], "rank": v.get("rank", ""),
                    "tier_id": v.get("tier_id", 0), "div_id": v.get("div_id", 0)}
                for k, v in self.all_mmr.items() if v["mmr"] is not None
            }
            with open(self._CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def reset_deltas(self):
        """Repart le delta depuis le MMR actuel (début de session)."""
        for d in self.all_mmr.values():
            d["mmr_start"] = d["mmr"]
            d["mmr_change"] = 0

    # ── Fetch asynchrone ──────────────────────────────────────────────────
    _FETCH_COOLDOWN_S = 300   # 5 minutes entre deux appels automatiques
    _last_fetch_time  = 0.0   # partagé au niveau classe (une seule instance MMRService)

    def fetch_async(self, player_name="", player_primary_id="", force=False):
        """Lance le fetch MMR dans un thread.

        force=True  → bypass le cooldown (bouton ↻ manuel, démarrage).
        force=False → ignoré si la dernière requête date de moins de 5 min.
        """
        now = time.time()
        if not force:
            elapsed = now - MMRService._last_fetch_time
            remaining = self._FETCH_COOLDOWN_S - elapsed
            if remaining > 0:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                self.signals.log_event.emit(
                    f"[MMR] Cooldown actif — prochain fetch dans {mins}m{secs:02d}s")
                return
        MMRService._last_fetch_time = now
        threading.Thread(target=self._fetch, args=(player_name, player_primary_id), daemon=True).start()

    def _fetch(self, player_name="", player_primary_id=""):
        platform = self.config["platform"].lower()
        slug     = self._PLATFORM_SLUG.get(platform, "epic")

        # Steam : utiliser le Steam ID extrait du PrimaryId détecté,
        # sinon fallback sur le champ username (saisi manuellement)
        if slug == "steam":
            if player_primary_id.startswith("Steam|"):
                parts = player_primary_id.split("|")
                username = parts[1] if len(parts) >= 2 else ""
            else:
                username = self.config["username"] or player_name
            encoded = username
        else:
            username = self.config["username"] or player_name
            encoded = urllib.parse.quote(username, safe="")

        if not username:
            return

        url = (f"https://api.tracker.gg/api/v2/rocket-league/standard/profile"
               f"/{slug}/{encoded}")

        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent":      (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"),
                    "Accept":          "application/json, text/plain, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer":         "https://rocketleague.tracker.network/",
                    "Origin":          "https://rocketleague.tracker.network",
                    "Connection":      "keep-alive",
                    "sec-fetch-site":  "same-site",
                    "sec-fetch-mode":  "cors",
                    "sec-fetch-dest":  "empty",
                })
                self.signals.log_event.emit(
                    f"[MMR] Tentative {attempt}/{self._MAX_RETRIES}"
                    f" — {username} ({slug})…")

                # SSL : essaie d'abord avec vérification (certifi si dispo), puis sans
                try:
                    ssl_ctx = _SSL_CTX   # importé depuis overlay_widgets via *
                    with urllib.request.urlopen(req, context=ssl_ctx, timeout=10) as resp:
                        raw = resp.read().decode("utf-8")
                except Exception:
                    with urllib.request.urlopen(req, context=_SSL_CTX_NOVERIFY, timeout=10) as resp:
                        raw = resp.read().decode("utf-8")
                data = json.loads(raw)

                if not isinstance(data.get("data"), dict):
                    raise ValueError("tracker.gg : pas de données de profil")

                updated = False
                for seg in data["data"].get("segments", []):
                    if seg.get("type") != "playlist":
                        continue
                    pid    = seg.get("attributes", {}).get("playlistId")
                    pl_key = self._PLAYLIST_IDS.get(pid)
                    if pl_key is None:
                        continue

                    s          = seg.get("stats", {})
                    tier_name  = s.get("tier",     {}).get("metadata", {}).get("name", "Unranked")
                    div_str    = s.get("division",  {}).get("metadata", {}).get("name", "")
                    mmr_val    = s.get("rating",    {}).get("value", 0)
                    tier_id    = self._tier_id(tier_name)
                    div_id     = self._div_id(div_str)
                    mmr        = int(mmr_val) if mmr_val else 0

                    d = self.all_mmr[pl_key]
                    d["mmr_start"]  = mmr if d["mmr_start"] is None else d["mmr_start"]
                    d["mmr_change"] = mmr - d["mmr_start"]
                    d["mmr"]        = mmr
                    d["rank"]       = tier_name
                    d["tier_id"]    = tier_id
                    d["div_id"]     = div_id

                    div_txt = f" {div_str}" if div_str else ""
                    self.signals.log_event.emit(
                        f"[{pl_key}] {tier_name}{div_txt} — MMR: {mmr}")
                    updated = True

                if not updated:
                    raise ValueError("Aucune playlist ranked trouvée dans le profil")

                self._save_cache()
                self.signals.mmr_updated.emit()
                self.signals.log_event.emit("✓ MMR & Ranks mis à jour (tracker.gg)")
                return   # succès — on sort de la boucle retry

            except Exception as e:
                self.signals.log_event.emit(
                    f"[MMR] Erreur tentative {attempt}: {str(e)[:60]}")
                if attempt < self._MAX_RETRIES:
                    time.sleep(self._RETRY_WAIT * attempt)
                else:
                    self.signals.mmr_error.emit(
                        f"Échec après {self._MAX_RETRIES} tentatives: {str(e)[:55]}")


# ─────────────────────────────────────────────────────────────────────────────
#  APPLICATION PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BakkyTrack")
        self.setFixedWidth(468)
        self.setMinimumHeight(660)

        self.config  = Config()
        self.signals = AppSignals()

        # ── Services (logique métier, sans PyQt UI) ───────────────────────
        self.match = MatchService(self.config, self.signals)
        self.mmr   = MMRService(self.config, self.signals)

        # ── UI ────────────────────────────────────────────────────────────
        self.overlay_win         = OverlayWindow()
        self.players_overlay_win = PlayersOverlayWindow()
        self.result_overlay      = ResultOverlay()
        self.ingame_mmr_overlay  = InGameMMROverlay()
        self.controller_overlay  = ControllerOverlay(
            self.config.get("controller_overlay_mode", "with_bg")
        )
        if self.config.get("controller_overlay_enabled", False):
            self.controller_overlay.show()
        self.streamer_bar        = StreamerModeBar()
        self._saved_system_vol   = None   # volume sauvegardé avant mute streamer
        self._ingame_stats_cache: dict = {}
        self._overlay_hold_active = False

        # ── Fond SVG — widget racine qui contient tout ────────────────────
        bg_theme = self.config.get("main_bg_theme", "dark_minimal")
        self._bg_widget = SvgBackground(bg_theme)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        self.tracker_tab  = TrackerTab(self)
        self.players_tab  = PlayersTab(self)
        self.overlay_tab  = OverlayTab(self)
        self.auto_tab     = AutomationTab(self)
        self.sound_tab    = SoundTab(self)
        self.settings_tab = SettingsTab(self)

        scroll = QScrollArea()
        scroll.setWidget(self.tracker_tab)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;border:none;")

        sound_scroll = QScrollArea()
        sound_scroll.setWidget(self.sound_tab)
        sound_scroll.setWidgetResizable(True)
        sound_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sound_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sound_scroll.setStyleSheet("background:transparent;border:none;")

        settings_scroll = QScrollArea()
        settings_scroll.setWidget(self.settings_tab)
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        settings_scroll.setStyleSheet("background:transparent;border:none;")

        tabs.addTab(scroll,              "📊  Stats")
        tabs.addTab(self.players_tab,    "👥  Match")
        tabs.addTab(self.overlay_tab,    "🖥  Overlay")
        tabs.addTab(self.auto_tab,       "⚡  Auto")
        tabs.addTab(sound_scroll,        "🔊  Sons")
        tabs.addTab(settings_scroll,     "⚙  Options")
        tabs.setTabToolTip(
            0, "Connexion au serveur StatsAPI (même port que dans le plugin en jeu), "
               "MMR tracker.gg, playlists ranked, victoires / défaites et taux de victoire.")
        tabs.setTabToolTip(
            1, "Liste des joueurs du match en cours et ouverture du profil sur "
               "tracker.network.")
        tabs.setTabToolTip(
            2, "Barre d’informations en jeu : apparence, raccourcis clavier / manette, "
               "aperçu et overlay MMR pendant la partie.")
        tabs.setTabToolTip(
            3, "Automatisations : passer les replays, relancer la file, lancer la freeplay "
               "(nécessite pyautogui et des raccourcis configurés).")
        tabs.setTabToolTip(
            4, "Jouer un son sur but, démo, arrêt décisif, etc., selon les événements "
               "reçus de StatsAPI.")
        tabs.setTabToolTip(
            5, "Plateforme Epic / Steam, pseudo tracker.gg, ports, thème d’arrière-plan "
               "et réglages avancés.")
        self._bg_widget.add_widget(tabs)
        self.setCentralWidget(self._bg_widget)

        # ── Connexions de signaux ─────────────────────────────────────────
        self.signals.player_detected.connect(
            lambda name, _: setattr(self.match, "detected_player_name", name))
        self.signals.match_result.connect(self._handle_auto_match)
        self.signals.players_updated.connect(self.players_overlay_win.update_players)
        self.signals.players_updated.connect(self._on_players_for_ingame)
        self.signals.trigger_sound.connect(self._trigger_sound)
        self.signals.press_key_sig.connect(self._handle_press_key)
        self.signals.game_phase_changed.connect(self._on_game_phase_changed)

        self._overlay_timer = QTimer(self)
        self._overlay_timer.timeout.connect(self._push_overlay)
        self._overlay_timer.start(REFRESH_MS)

        # Timer de mise à jour de l'overlay in-game (joueurs du match)
        self._ingame_timer = QTimer(self)
        self._ingame_timer.timeout.connect(self._push_ingame_overlay)
        self._ingame_timer.start(700)

        self._running = True
        self._last_sse_stats: dict = {}   # Cache pour éviter les SSE redondants
        self._start_http_server()
        self.match.start()
        self._start_hotkey_listener()
        self.fetch_mmr_async(force=True)
        # Mode streamer toujours désactivé au démarrage
        self.config["streamer_mode"] = False

    # ── Property shims — rétrocompatibilité avec les onglets UI ──────────
    @property
    def wins(self):               return self.match.wins
    @property
    def losses(self):             return self.match.losses
    @property
    def streak(self):             return self.match.streak
    @property
    def streak_type(self):        return self.match.streak_type
    @property
    def history(self):            return self.match.history
    @property
    def session_start(self):      return self.match.session_start
    @property
    def detected_player_name(self): return self.match.detected_player_name
    @property
    def all_mmr(self):            return self.mmr.all_mmr
    @property
    def selected_playlist(self):  return self.mmr.selected_playlist

    # ── Délégation vers MatchService ──────────────────────────────────────
    def add(self, t, auto=False):
        self.match.add(t, auto)
        QTimer.singleShot(10000, self.fetch_mmr_async)
        if self.config.get("auto_queue"):
            delay_q = int(float(self.config.get("queue_delay", 2.0)) * 1000)
            QTimer.singleShot(delay_q, self._do_queue_action)
        if self.config.get("auto_freeplay"):
            delay_f = int(float(self.config.get("freeplay_delay", 3.0)) * 1000)
            QTimer.singleShot(delay_f, self._do_freeplay_action)

    def remove(self, t):      self.match.remove(t)
    def reset_session(self):  self.match.reset_session(self.mmr)

    def select_playlist(self, key):
        self.mmr.selected_playlist = key
        self.signals.mmr_updated.emit()

    def highlight_playlist_btns(self, btns):
        for k, b in btns.items():
            active = k == self.mmr.selected_playlist
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};"
                f"color:{C_TEXT if active else C_MUTE};border:none;"
                f"border-radius:4px;padding:5px 12px;font-size:9px;font-weight:700;}}"
                + ("" if active else f"QPushButton:hover{{color:{C_TEXT};}}"))

    def fetch_mmr_async(self, force=False):
        self.mmr.fetch_async(
            self.match.detected_player_name,
            self.match.detected_player_primary_id,
            force=force
        )

    def reconnect_statsapi(self):
        port_str = self.tracker_tab.get_port()
        try:   port = int(port_str)
        except ValueError: port = self.config["statsapi_port"]
        self.match.restart(port)

    # ── Handlers de signaux ───────────────────────────────────────────────
    def _handle_auto_match(self, val):
        if val.startswith("__auto__"):
            result = val[8:]
            self.add(result, auto=True)
            if self.config.get("result_overlay_enabled", True):
                theme = self.config.get("result_overlay_theme", "auto")
                self.result_overlay.show_result(result, theme)
            # Push SSE vers OBS overlay
            stats = self._build_stats_dict()
            stats["result"] = result
            self._push_sse("result", stats)

    def _trigger_sound(self, event_key: str):
        """Reçu depuis MatchService via signal — joue le son si activé."""
        if not self.config.get(f"sound_{event_key}", True):
            return
        f = self.config.get(f"snd_file_{event_key}", "")
        if f:
            self._play_sound(f)

    def _handle_press_key(self, key_str: str, delay: float):
        """Reçu depuis MatchService via signal — appuie sur la touche."""
        def _do():
            if delay > 0: time.sleep(delay)
            self._press_key(key_str)
        threading.Thread(target=_do, daemon=True).start()

    def _play_sound(self, file_str):
        if not PYGAME_AVAILABLE or not file_str:
            return
        def _play(f=file_str):
            try:
                path = f if os.path.isabs(f) else os.path.join(BASE_DIR, f)
                if not os.path.exists(path):
                    self.signals.log_event.emit(f"[Son] Fichier introuvable: {f}")
                    return
                # Initialiser le mixer une seule fois — re-init à chaque son
                # provoque un freeze audible et un gel de l'UI.
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

    def _press_key(self, key_str):
        if not key_str:
            return
        try:
            if key_str.startswith("key:"):
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.press(key_str[4:])
            elif key_str.startswith("mouse:"):
                btn_name = key_str[6:]
                if PYAUTOGUI_AVAILABLE:
                    btn_map = {"left": "left", "right": "right",
                               "middle": "middle", "x1": "left", "x2": "right"}
                    pyautogui.click(button=btn_map.get(btn_name, "left"))
                    self.signals.log_event.emit(f"[Auto] Souris {btn_name}")
            else:
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.press(key_str)
        except Exception as e:
            self.signals.log_event.emit(f"[Auto] Erreur touche: {e}")

    def _do_queue_action(self):
        key = self.config.get("queue_key", "key:return")
        self.signals.log_event.emit(f"[Auto] Rejouer → {_key_display(key)}")
        threading.Thread(target=lambda: self._press_key(key), daemon=True).start()

    def _do_freeplay_action(self):
        key = self.config.get("freeplay_key", "key:f")
        self.signals.log_event.emit(f"[Auto] Freeplay → {_key_display(key)}")
        threading.Thread(target=lambda: self._press_key(key), daemon=True).start()

    # ── Mode Streamer ─────────────────────────────────────────────────────
    def _on_game_phase_changed(self, phase: str):
        """Réagit aux transitions de phase de jeu pour le mode streamer auto."""
        if not self.config.get("streamer_mode", False):
            return
        if phase == "lobby":
            # Fin de partie → on est en lobby/queue : activer la barre
            self._apply_streamer_bar(True)
        elif phase == "ingame":
            # Partie commencée → désactiver la barre (on joue)
            self._apply_streamer_bar(False)

    def _apply_streamer_bar(self, show: bool):
        """Affiche/cache la barre + mute/restore le son. Ne touche pas à la config."""
        if show:
            self.streamer_bar.show()
            self._mute_system_audio()
        else:
            self.streamer_bar.hide()
            self._restore_system_audio()

    def _apply_streamer_mode(self, enabled: bool):
        """Active ou désactive le mode streamer (barre noire + mute système)."""
        if enabled:
            self._apply_streamer_bar(True)
            self.signals.log_event.emit("[Streamer] Mode activé — barre noire + mute son")
        else:
            self._apply_streamer_bar(False)
            self.signals.log_event.emit("[Streamer] Mode désactivé — son restauré")

    def _mute_system_audio(self):
        """Mute uniquement la session audio de RocketLeague.exe (WASAPI via pycaw)."""
        if sys.platform != "win32":
            return
        if not self.config.get("streamer_mute_audio", True):
            return

        # ── pycaw : cible la session audio RL spécifiquement ────────────────
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
                    "[Streamer] RL non trouvé dans les sessions audio "
                    "(jeu pas encore lancé ?)")
            return

        except ImportError:
            self.signals.log_event.emit(
                "[Streamer] pycaw absent — installe : pip install pycaw  "
                "(nécessaire pour couper uniquement le son RL)")
        except Exception as e:
            self.signals.log_event.emit(f"[Streamer] Erreur mute session RL : {e}")

    def _restore_system_audio(self):
        """Restaure le son RL après le mode streamer."""
        if sys.platform != "win32" or self._saved_system_vol is None:
            return
        try:
            method = self._saved_system_vol[0]
            if method == "pycaw_session":
                _, sessions = self._saved_system_vol
                for vol in sessions:
                    try:
                        vol.SetMute(0, None)
                    except Exception:
                        pass
            self._saved_system_vol = None
            self.signals.log_event.emit("[Streamer] Son RL restauré")
        except Exception as e:
            self.signals.log_event.emit(f"[Streamer] Impossible de restaurer le son: {e}")

    # ── Overlay stats ─────────────────────────────────────────────────────
    def _build_stats_dict(self):
        total = self.wins + self.losses
        wr    = round(self.wins / total * 100) if total > 0 else 0
        d     = self.mmr.all_mmr.get(self.mmr.selected_playlist, {})
        return {
            "wins":        self.wins,
            "losses":      self.losses,
            "total":       total,
            "winrate":     wr,
            "streak_val":  self.streak,
            "streak_type": self.streak_type or "",
            "mmr":         d.get("mmr"),
            "mmr_change":  d.get("mmr_change", 0),
            "rank":        d.get("rank", ""),
            "tier_id":     d.get("tier_id", 0),
            "div_id":      d.get("div_id", 0),
        }

    def _push_overlay(self):
        stats = self._build_stats_dict()
        self.overlay_win.update_stats(stats)
        self.overlay_tab.refresh_preview(stats)
        # Ne pousser le SSE que si les stats ont changé — évite d'inonder
        # les clients OBS de messages identiques toutes les 2 secondes.
        if stats != self._last_sse_stats:
            self._last_sse_stats = stats
            self._push_sse("stats", stats)

    # ── Players overlay hotkey ────────────────────────────────────────────
    def _start_hotkey_listener(self):
        threading.Thread(target=self._hotkey_loop, daemon=True).start()
        threading.Thread(target=self._overlay_hold_loop, daemon=True).start()

    def _hotkey_loop(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
        except ImportError:
            return
        prev_pressed  = False
        cached_key    = None
        cached_vk     = None
        # Rafraîchissement lent de la config clé (toutes les ~2s) pour éviter
        # un dict lookup + _key_to_vk() toutes les 40ms.
        _cfg_refresh  = 0
        while self.match._running:
            time.sleep(0.04)
            _cfg_refresh += 1
            if _cfg_refresh >= 50:   # ~2 secondes
                _cfg_refresh = 0
                new_key = self.config.get("players_overlay_key", "key:f7")
                if new_key != cached_key:
                    cached_key = new_key
                    cached_vk  = _key_to_vk(new_key)
            if cached_vk is None:
                continue
            state   = ctypes.windll.user32.GetAsyncKeyState(cached_vk)
            pressed = bool(state & 0x8000)
            if pressed and not prev_pressed:
                QTimer.singleShot(0, self._toggle_players_overlay)
            prev_pressed = pressed

    def _toggle_players_overlay(self):
        if self.players_overlay_win.isVisible():
            self.players_overlay_win.hide()
        else:
            self.players_overlay_win.show()

    # ── Joueurs du match → fetch MMR en background ────────────────────────
    def _on_players_for_ingame(self, players: list):
        """Déclenche le fetch tracker.gg pour chaque joueur nouveau du match."""
        now = time.time()
        for p in players:
            pid  = p.get("PrimaryId", "")
            name = p.get("Name", "")
            if not pid:
                continue
            entry = self._ingame_stats_cache.get(pid)
            # Ne re-fetch que si absent, en erreur, ou expiré
            if entry and entry.get("status") == "ok":
                age = now - entry.get("timestamp", 0)
                if age < _INGAME_CACHE_TTL:
                    continue
            # Marque comme "en cours" pour éviter les doubles fetches
            self._ingame_stats_cache[pid] = {
                "status": "loading", "playlists": {}, "timestamp": now}
            threading.Thread(
                target=_fetch_player_for_ingame,
                args=(pid, name, self._ingame_stats_cache),
                daemon=True
            ).start()

    def _push_ingame_overlay(self):
        """Rafraîchit l'overlay in-game avec les données à jour."""
        if not self.ingame_mmr_overlay.isVisible():
            return
        self.ingame_mmr_overlay.set_data(
            self.match.current_players,
            self._ingame_stats_cache,
            self.mmr.selected_playlist,
        )

    # ── Overlay hold-to-show loop ─────────────────────────────────────────
    def _is_overlay_hotkey_pressed(self) -> bool:
        """Retourne True si la touche overlay est actuellement maintenue."""
        if sys.platform != "win32":
            return False
        import ctypes
        htype = self.config.get("overlay_hotkey_type", "key")
        if htype == "controller":
            btn = self.config.get("overlay_hotkey_controller_btn", 0)
            if btn == 0:
                return False
            xi = get_gamepad_state()
            return bool(xi and (xi.Gamepad.wButtons & btn) == btn)
        else:
            key = self.config.get("overlay_hotkey_key", "key:tab")
            if not key:
                return False
            vk = _key_to_vk(key)
            if vk is None:
                return False
            return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)

    def _overlay_hold_loop(self):
        """Thread : affiche overlay_win tant que la touche est maintenue."""
        if sys.platform != "win32":
            return
        was_pressed   = False
        cfg_refresh   = 0
        while self.match._running:
            time.sleep(0.04)

            # Rafraîchissement config lent (~2 s)
            cfg_refresh += 1
            if cfg_refresh >= 50:
                cfg_refresh = 0

            pressed = self._is_overlay_hotkey_pressed()

            if pressed and not was_pressed:
                # Touche vient d'être appuyée → montrer overlay si pas déjà ouvert par le toggle
                QTimer.singleShot(0, self._on_overlay_hold_start)
            elif not pressed and was_pressed:
                # Touche relâchée → cacher overlay (sauf si toggle UI l'a activé)
                QTimer.singleShot(0, self._on_overlay_hold_end)

            was_pressed = pressed

    def _on_overlay_hold_start(self):
        if not self.ingame_mmr_overlay.isVisible():
            self._overlay_hold_active = True
            # Injecter les données immédiatement à l'ouverture
            self.ingame_mmr_overlay.set_data(
                self.match.current_players,
                self._ingame_stats_cache,
                self.mmr.selected_playlist,
            )
            self.ingame_mmr_overlay.show()

    def _on_overlay_hold_end(self):
        if getattr(self, "_overlay_hold_active", False):
            self._overlay_hold_active = False
            self.ingame_mmr_overlay.hide()

    # ── HTTP server ───────────────────────────────────────────────────────
    def closeEvent(self, event):
        """Nettoyage complet avant fermeture."""
        # 1. Sauvegarde automatique de la config
        try:
            self.config.save()
        except Exception:
            pass

        # 2. Arrêt du timer overlay
        try:
            self._overlay_timer.stop()
        except Exception:
            pass

        # 3. Arrêt de la connexion StatsAPI
        self.match.stop()

        # 4. Fermeture propre de toutes les fenêtres overlay
        for w in (self.overlay_win, self.players_overlay_win,
                  self.result_overlay, self.ingame_mmr_overlay,
                  self.controller_overlay, self.streamer_bar):
            try:
                w.close()
            except Exception:
                pass

        # 5. Restauration du volume système si mode streamer actif
        try:
            self._restore_system_audio()
        except Exception:
            pass

        # 6. Arrêt propre de pygame si actif
        if PYGAME_AVAILABLE:
            try:
                import pygame as _pg
                if _pg.mixer.get_init():
                    _pg.mixer.quit()
                _pg.quit()
            except Exception:
                pass

        super().closeEvent(event)

    # ── Répertoire des overlays externes ─────────────────────────────────────
    OVERLAYS_DIR = os.path.join(BASE_DIR, "overlays")

    @staticmethod
    def _load_overlay(name: str) -> bytes:
        """Charge un fichier HTML depuis overlays/<name>.
        Cherche d'abord overlays/<name>, puis overlays/<name>.html.
        Retourne les bytes ou b'' si introuvable."""
        base = MainApp.OVERLAYS_DIR
        for candidate in [os.path.join(base, name),
                          os.path.join(base, name + ".html")]:
            try:
                with open(candidate, "rb") as f:
                    return f.read()
            except FileNotFoundError:
                pass
        return b""

    def _start_http_server(self):
        app = self
        app._sse_clients = []   # liste des wfile en attente d'events SSE

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                # Sert n'importe quel *.html depuis le dossier overlays/
                # Ex: /overlay.html       -> overlays/overlay.html
                #     /my_overlay.html    -> overlays/my_overlay.html
                path = self.path.lstrip("/")
                if path.endswith(".html") and "/" not in path:
                    data = app._load_overlay(path)
                    if data:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers(); self.wfile.write(data)
                    else:
                        msg = f"Overlay '{path}' introuvable dans overlays/".encode()
                        self.send_response(404)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers(); self.wfile.write(msg)

                elif self.path == "/stats":
                    payload = json.dumps(app._build_stats_dict()).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers(); self.wfile.write(payload)

                elif self.path == "/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()
                    # Envoie les stats actuelles immédiatement
                    try:
                        data = json.dumps(app._build_stats_dict())
                        self.wfile.write(f"event: stats\ndata: {data}\n\n".encode())
                        self.wfile.flush()
                    except Exception:
                        return
                    app._sse_clients.append(self.wfile)
                    # Reste en attente jusqu'à déconnexion
                    try:
                        while True:
                            import time; time.sleep(15)
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                    except Exception:
                        pass
                    finally:
                        try: app._sse_clients.remove(self.wfile)
                        except ValueError: pass

                else:
                    self.send_response(404); self.end_headers()

            def log_message(self, *a): pass

        def run():
            try:
                HTTPServer(("0.0.0.0", OVERLAY_PORT), Handler).serve_forever()
            except Exception as e:
                print(f"[HTTP] {e}")
        threading.Thread(target=run, daemon=True).start()

    def _push_sse(self, event_type: str, data: dict):
        """Envoie un event SSE à tous les clients OBS connectés."""
        if not hasattr(self, "_sse_clients"):
            return
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()
        dead = []
        for wfile in list(self._sse_clients):
            try:
                wfile.write(msg); wfile.flush()
            except Exception:
                dead.append(wfile)
        for w in dead:
            try: self._sse_clients.remove(w)
            except ValueError: pass

#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Instance unique — empêche plusieurs lancements simultanés ────────
    if sys.platform == "win32":
        import ctypes as _ctypes
        _mutex = _ctypes.windll.kernel32.CreateMutexW(None, False, "BakkyTrack_SingleInstance")
        if _ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "BakkyTrack est déjà en cours d'exécution.",
                "BakkyTrack",
                0x30  # MB_ICONWARNING
            )
            sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    font = QFont(); font.setFamily("Segoe UI"); font.setPointSize(10)
    app.setFont(font)

    # ── Chargement du logo ───────────────────────────────────────────────
    from PyQt6.QtGui import QPixmap
    icon = None

    for name in ["logo.png", "logo.ico", "logo.jpg", "logo.jpeg", "logo.bmp", "logo.webp"]:
        candidate = os.path.join(BASE_DIR, name)
        if os.path.exists(candidate):
            px = QPixmap(candidate)
            if not px.isNull():
                icon = QIcon(px)
                break

    if icon is None:
        import base64
        px = QPixmap()
        px.loadFromData(base64.b64decode(_DEFAULT_ICON_B64))
        if not px.isNull():
            icon = QIcon(px)

    if icon:
        app.setWindowIcon(icon)

    # ── Splash screen ────────────────────────────────────────────────────
    from PyQt6.QtWidgets import QSplashScreen
    from PyQt6.QtCore import Qt as _Qt
    splash_px = QPixmap(400, 120)
    splash_px.fill(QColor(C_BG))
    splash = QSplashScreen(splash_px, _Qt.WindowType.WindowStaysOnTopHint)
    splash.showMessage(
        "  Chargement de BakkyTrack…",
        _Qt.AlignmentFlag.AlignBottom | _Qt.AlignmentFlag.AlignLeft,
        QColor(C_MUTE)
    )
    splash.show()
    app.processEvents()

    win = MainApp()
    if icon:
        win.setWindowIcon(icon)

    splash.finish(win)   # ferme le splash dès que la fenêtre est prête
    win.show()
    win.raise_()                 # amène au premier plan
    win.activateWindow()         # donne le focus clavier
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
