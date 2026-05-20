"""utils.py — Icônes, SVG, overlays globaux, auto-updater, VK keys, helpers partagés."""
import os, sys, time, urllib.parse, urllib.request, urllib.error, json, hashlib, threading
import re, webbrowser, ctypes
from typing import Optional
from config import BASE_DIR, SSL_CTX, SSL_CTX_NOVERIFY

# ── VK key map ──────────────────────────────────────────────────────────
_VK_MAP = {
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "space": 0x20, "return": 0x0D, "escape": 0x1B,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "insert": 0x2D, "delete": 0x2E, "tab": 0x09,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "backspace": 0x08,
    "num_div": 0x6F, "num_mul": 0x6A,
    "num_minus": 0x6D, "num_plus": 0x6B, "num_dec": 0x6E,
    "numlock": 0x90,
    "printscreen": 0x2C, "scrolllock": 0x91, "pause": 0x13,
    "capslock": 0x14,
    "mouse:left": 0x01, "mouse:right": 0x02,
    "mouse:middle": 0x04, "mouse:x1": 0x05, "mouse:x2": 0x06,
}


def _key_to_vk(key_str):
    if not key_str:
        return None
    if key_str.startswith("mouse:"):
        return _VK_MAP.get(key_str)
    if key_str.startswith("key:"):
        k = key_str[4:].lower()
        if k in _VK_MAP:
            return _VK_MAP[k]
        if len(k) == 1 and k.isalpha():
            return ord(k.upper())
        if len(k) == 1 and k.isdigit():
            return ord(k)
    return None


def _key_display(key_str):
    if not key_str:
        return "—"
    if key_str.startswith("key:"):
        return f"⌨  {key_str[4:].upper()}"
    if key_str.startswith("mouse:"):
        labels = {"left": "Clic gauche", "right": "Clic droit",
                  "middle": "Clic milieu", "x1": "Btn retour", "x2": "Btn avant"}
        return f"🖱  {labels.get(key_str[6:], key_str[6:].upper())}"
    return f"⌨  {key_str.upper()}"


# ── Qt key codes → pyautogui ────────────────────────────────────────────
from PyQt6.QtCore import Qt
_QT_KEY_MAP = {
    Qt.Key.Key_Space: "space", Qt.Key.Key_Return: "return",
    Qt.Key.Key_Enter: "return", Qt.Key.Key_Escape: "escape",
    Qt.Key.Key_Tab: "tab", Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Delete: "delete", Qt.Key.Key_Up: "up",
    Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right",
    Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3",
    Qt.Key.Key_F4: "f4", Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6",
    Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8", Qt.Key.Key_F9: "f9",
    Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
    Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end",
    Qt.Key.Key_PageUp: "pageup", Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Insert: "insert",
    Qt.Key.Key_0: "0", Qt.Key.Key_1: "1", Qt.Key.Key_2: "2",
    Qt.Key.Key_3: "3", Qt.Key.Key_4: "4", Qt.Key.Key_5: "5",
    Qt.Key.Key_6: "6", Qt.Key.Key_7: "7", Qt.Key.Key_8: "8",
    Qt.Key.Key_9: "9",
    Qt.Key.Key_division: "num_div", Qt.Key.Key_multiply: "num_mul",
    Qt.Key.Key_Minus: "num_minus", Qt.Key.Key_Plus: "num_plus",
    Qt.Key.Key_Period: "num_dec",
    Qt.Key.Key_Print: "printscreen", Qt.Key.Key_ScrollLock: "scrolllock",
    Qt.Key.Key_Pause: "pause", Qt.Key.Key_NumLock: "numlock",
    Qt.Key.Key_CapsLock: "capslock",
}


# ── Icônes de rang (cache LRU — max 64 entrées) ─────────────────────────
from functools import lru_cache

_RANK_FOLDER = os.path.join(BASE_DIR, "all rank")


def get_rank_pixmap(tier_id: int, size: int = 40):
    from PyQt6.QtGui import QPixmap
    key = (tier_id, size)
    # Cache LRU intégré via lru_cache sur une fonction interne
    return _get_rank_pixmap_impl(key)


@lru_cache(maxsize=64)
def _get_rank_pixmap_impl(key):
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt as _Qt
    tier_id, size = key
    path = os.path.join(_RANK_FOLDER, f"{tier_id}.png")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            scaled = pm.scaled(size, size,
                               _Qt.AspectRatioMode.KeepAspectRatio,
                               _Qt.TransformationMode.SmoothTransformation)
            return scaled
    return None


# ── Icônes de playlist (cache LRU — max 32 entrées) ─────────────────────
_PLAYLIST_FOLDER = os.path.join(BASE_DIR, "Playlist")

_PLAYLIST_FILE_INDEX = {
    "1v1": 0, "2v2": 1, "3v3": 2,
    "hoops": 3, "rumble": 4, "dropshot": 5, "snowday": 6, "tournament": 7,
}
_PLAYLIST_ID_TO_KEY = {10: "1v1", 11: "2v2", 13: "3v3"}


@lru_cache(maxsize=32)
def _get_playlist_pixmap_impl(key):
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt as _Qt
    file_idx, size = key
    path = os.path.join(_PLAYLIST_FOLDER, f"{file_idx}.png")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            scaled = pm.scaled(size, size,
                               _Qt.AspectRatioMode.KeepAspectRatio,
                               _Qt.TransformationMode.SmoothTransformation)
            return scaled
    return None


def get_playlist_pixmap(playlist_key, size: int = 28):
    file_idx = _PLAYLIST_FILE_INDEX.get(playlist_key, 2)
    return _get_playlist_pixmap_impl((file_idx, size))


# ── SVG Backgrounds ──────────────────────────────────────────────────────
from PyQt6.QtCore import QRectF, QByteArray
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui import QPainter
from PyQt6.QtSvg import QSvgRenderer  # noqa: F401 — requis explicitement pour PyInstaller

THEMES_DIR = os.path.join(BASE_DIR, "themes")
_THEME_NAMES = ["rl_classic", "victory", "defeat", "neon", "dark_minimal"]


def _load_svg(name: str) -> bytes:
    path = os.path.join(THEMES_DIR, f"{name}.svg")
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return b""


SVG_BACKGROUNDS = {n: _load_svg(n) for n in _THEME_NAMES}


class SvgBackground(QWidget):
    def __init__(self, svg_name="dark_minimal", parent=None):
        super().__init__(parent)
        self._renderer  = QSvgRenderer()
        self._bg_pixmap = None
        self.set_theme(svg_name)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._inner_lay = lay

    def set_theme(self, name: str):
        data = SVG_BACKGROUNDS.get(name, b"")
        if data:
            self._renderer.load(QByteArray(data))
        self._bg_pixmap = None
        self.update()

    def _rebuild_pixmap(self):
        from PyQt6.QtGui import QPixmap
        px = QPixmap(self.size())
        px.fill(QColor(10, 12, 18))
        if self._renderer.isValid():
            painter = QPainter(px)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self._renderer.render(painter, QRectF(px.rect()))
            painter.end()
        self._bg_pixmap = px

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._bg_pixmap = None

    def paintEvent(self, event):
        if self._bg_pixmap is None or self._bg_pixmap.size() != self.size():
            self._rebuild_pixmap()
        p = QPainter(self)
        p.drawPixmap(0, 0, self._bg_pixmap)
        p.end()

    def add_widget(self, w):
        self._inner_lay.addWidget(w)


# ── enforce_topmost (utilitaire partagé par les overlays) ────────────────
def enforce_topmost(widget, clickthrough=False):
    """Force une fenêtre Qt au-dessus de tout (y compris les jeux plein écran).
    Si clickthrough=True, ajoute aussi le flag WS_EX_TRANSPARENT.
    """
    if sys.platform != "win32" or not widget.isVisible():
        return
    try:
        import ctypes
        hwnd = int(widget.winId())
        ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0003)
        GWL_EXSTYLE = -20
        ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        flags = ex | 0x00080000 | 0x08000000  # WS_EX_LAYERED | WS_EX_NOACTIVATE
        if clickthrough:
            flags |= 0x00000008  # WS_EX_TOPMOST passthrough
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, flags)
    except Exception:
        pass


# ── OverlayStats (helper pour les widgets overlay) ────────────────────
class OverlayStats:
    """Parse un dict de stats brutes en attributs typés.
    Évite la duplication du même parsing dans 12+ widgets overlay."""
    __slots__ = ('mmr', 'chg', 'sv', 'st', 'wins', 'losses', 'total', 'winrate', 'wr_pct')

    def __init__(self, d: dict):
        self.mmr    = d.get("mmr")
        self.chg    = d.get("mmr_change", 0)
        self.sv     = d.get("streak_val", 0)
        self.st     = d.get("streak_type", "")
        self.wins   = d.get("wins", 0)
        self.losses = d.get("losses", 0)
        self.total  = self.wins + self.losses
        self.winrate = (self.wins / self.total) if self.total > 0 else 0.5
        self.wr_pct  = f"{self.wins / self.total * 100:.0f}%" if self.total > 0 else "--%"

    def mmr_text(self, mmr_mode: str) -> str:
        if mmr_mode == "delta":
            return ""
        return str(self.mmr) if self.mmr else "--"

    def delta_text(self, mmr_mode: str) -> tuple:
        """Retourne (text, color) pour le delta MMR."""
        if self.chg and mmr_mode != "mmr":
            sign = "+" if self.chg > 0 else ""
            clr  = "#00e676" if self.chg > 0 else "#ff3d57"
            return f"{sign}{self.chg}", clr
        return "", None

    def streak_text(self) -> tuple:
        """Retourne (text, color) pour le streak."""
        if self.sv > 0:
            clr = "#00e676" if self.st == "win" else "#ff3d57"
            return f"{'+'if self.st=='win'else'-'}{self.sv}", clr
        return "--", None


# ── ResultOverlay ────────────────────────────────────────────────────────
from PyQt6.QtGui import QColor, QBrush, QPen, QLinearGradient, QFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QPointF


class ResultOverlay(QWidget):
    FADE_IN  = 20
    HOLD     = 65
    FADE_OUT = 30
    FRAME_MS = 30

    def __init__(self):
        super().__init__(None,
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint  |
            Qt.WindowType.Tool                 |
            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._renderer = QSvgRenderer()
        self._alpha = 0.0; self._scale = 0.85
        self._step = 0;    self._result = "win"
        self._phase = "idle"
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def show_result(self, result: str, theme: str = "auto"):
        self._result = result
        svg_key = ("victory" if result == "win" else "defeat") if theme == "auto" else theme
        data = SVG_BACKGROUNDS.get(svg_key, b"")
        if data:
            self._renderer.load(QByteArray(data))
        else:
            self._renderer = QSvgRenderer()
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._step = 0; self._alpha = 0.0; self._scale = 0.82; self._phase = "fadein"
        self.show(); self.raise_()
        self._timer.start(self.FRAME_MS)

    def _tick(self):
        self._step += 1
        if self._phase == "fadein":
            t = min(1.0, self._step / self.FADE_IN)
            self._alpha = t; self._scale = 0.82 + 0.18 * t
            if self._step >= self.FADE_IN: self._phase = "hold"; self._step = 0
        elif self._phase == "hold":
            self._alpha = 1.0; self._scale = 1.0
            if self._step >= self.HOLD: self._phase = "fadeout"; self._step = 0
        elif self._phase == "fadeout":
            t = min(1.0, self._step / self.FADE_OUT)
            self._alpha = 1.0 - t
            if self._step >= self.FADE_OUT:
                self._timer.stop(); self._phase = "idle"; self.hide(); return
        self.update()

    def paintEvent(self, event):
        if self._phase == "idle": return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        is_win = self._result == "win"
        color  = QColor("#00e676" if is_win else "#ff3d57")
        p.setOpacity(self._alpha * 0.93)
        if self._renderer.isValid():
            self._renderer.render(p, QRectF(0, 0, w, h))
        else:
            bg_col = QColor("#011a0a" if is_win else "#1a0101")
            p.fillRect(self.rect(), bg_col)
            g = QLinearGradient(w / 2, 0, w / 2, h)
            glow = QColor(color); glow.setAlpha(40)
            g.setColorAt(0.0, QColor(0, 0, 0, 0))
            g.setColorAt(0.5, glow)
            g.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), QBrush(g))
        text = "VICTOIRE" if is_win else "DÉFAITE"
        p.setOpacity(self._alpha)
        p.save()
        p.translate(w / 2, h / 2); p.scale(self._scale, self._scale); p.translate(-w / 2, -h / 2)
        halo = QColor(color); halo.setAlpha(int(35 * self._alpha))
        p.setBrush(QBrush(halo)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(w/2 - 260, h/2 - 85, 520, 170))
        f = QFont(); f.setPointSize(72); f.setWeight(QFont.Weight.Black)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 10)
        p.setFont(f)
        p.setPen(QColor(0, 0, 0, int(160 * self._alpha)))
        p.drawText(QRectF(3, h/2 - 55 + 4, w, 110), Qt.AlignmentFlag.AlignHCenter, text)
        txt_col = QColor(color); txt_col.setAlpha(int(255 * self._alpha))
        p.setPen(txt_col)
        p.drawText(QRectF(0, h/2 - 55, w, 110), Qt.AlignmentFlag.AlignHCenter, text)
        f2 = QFont(); f2.setPointSize(14); f2.setWeight(QFont.Weight.Bold)
        f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        p.setFont(f2)
        p.setPen(QColor(255, 255, 255, int(150 * self._alpha)))
        sub = "BIEN JOUÉ !" if is_win else "LA PROCHAINE FOIS"
        p.drawText(QRectF(0, h/2 + 55, w, 40), Qt.AlignmentFlag.AlignHCenter, sub)
        p.restore()
        border = QColor(color); border.setAlpha(int(200 * self._alpha))
        p.setPen(QPen(border, 3)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(0, 0, w, 0); p.drawLine(0, h-1, w, h-1)
        p.end()


# ── Auto-updater GitHub — SUPPRIMÉ (inutile avec installeur) ─────────────


# ── Estimation progression division ─────────────────────────────────────
def estimate_division_progress(tier_id: int, div_id: int, mmr: int) -> dict:
    MMR_TIERS = {
        0: 0, 1: 180, 2: 240, 3: 300,
        4: 360, 5: 420, 6: 480,
        7: 540, 8: 600, 9: 660,
        10: 720, 11: 780, 12: 840,
        13: 900, 14: 980, 15: 1060,
        16: 1140, 17: 1260, 18: 1380,
        19: 1500, 20: 1620, 21: 1740,
        22: 1860
    }
    if tier_id <= 0 or tier_id >= 22 or not mmr:
        return {"pct": 0, "next_mmr": 0, "prev_mmr": 0, "to_up": 0, "to_down": 0}
    base_mmr = MMR_TIERS.get(tier_id, 900)
    next_base = MMR_TIERS.get(tier_id + 1, base_mmr + 80)
    tier_size = next_base - base_mmr
    div_size = tier_size / 4
    div_idx = max(0, min(3, div_id - 1))
    div_min = base_mmr + (div_idx * div_size)
    div_max = div_min + div_size
    curr_mmr = max(div_min, min(div_max, mmr))
    pct = int(((curr_mmr - div_min) / div_size) * 100) if div_size > 0 else 0
    to_up = int(div_max - mmr)
    to_down = int(mmr - div_min)
    return {
        "pct": pct,
        "next_mmr": int(div_max),
        "prev_mmr": int(div_min),
        "to_up": max(1, to_up),
        "to_down": max(1, to_down)
    }


# ── Authentification compte bot (ajouté) ────────────────────────────────
# Note PyInstaller : ajouter 'rlapi' et 'rlapi.egs' dans hiddenimports du .spec

def extract_auth_code(text: str) -> str:
    """Extrait un code d'autorisation Epic (32 hex) depuis un texte ou URL."""
    if not text:
        return ""
    match = re.search(r'(?:code=|"authorizationCode"\s*:\s*")([0-9a-fA-F]{32})', text, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    match = re.search(r'\b([0-9a-fA-F]{32})\b', text)
    if match:
        return match.group(1).lower()
    return ""

def open_browser_and_wait_for_code(timeout=120) -> Optional[str]:
    """
    Ouvre le navigateur sur la page d'authentification Epic,
    attend que l'utilisateur se connecte et tente de capturer le code d'autorisation
    depuis le presse‑papier ou l'URL.
    Retourne le code (str) ou None.
    """
    from rlapi.egs import EGS
    egs = EGS()
    auth_url = egs.get_auth_url()
    egs.close()
    webbrowser.open(auth_url)

    time.sleep(2)
    start_time = time.time()
    clipboard_content = ""
    last_clipboard = ""
    while time.time() - start_time < timeout:
        try:
            if ctypes.windll.user32.OpenClipboard(None):
                h_data = ctypes.windll.user32.GetClipboardData(13)  # CF_UNICODETEXT
                if h_data:
                    ptr = ctypes.windll.kernel32.GlobalLock(h_data)
                    if ptr:
                        clipboard_content = ctypes.wstring_at(ptr)
                        ctypes.windll.kernel32.GlobalUnlock(h_data)
                ctypes.windll.user32.CloseClipboard()
        except Exception:
            pass
        if clipboard_content and clipboard_content != last_clipboard:
            code = extract_auth_code(clipboard_content)
            if code:
                return code
            last_clipboard = clipboard_content
        time.sleep(1)
    return None

def authenticate_bot_account(signals=None) -> Optional[dict]:
    """
    Lance le flow d'authentification complet pour un compte bot Epic.
    Retourne un dict contenant refresh_token, account_id, account_name.
    En cas d'échec, retourne None.
    """
    from rlapi.egs import EGS
    # Étape 1 : obtenir le code d'autorisation
    code = open_browser_and_wait_for_code()
    if not code:
        if signals:
            signals.log_event.emit("[Auth Bot] Échec : pas de code reçu.")
        return None

    egs = EGS()
    try:
        # Étape 2 : échanger le code contre un token launcher
        launcher_token = egs.authenticate_with_code(code)
        # Étape 3 : obtenir exchange code
        exchange_code = egs.get_exchange_code(launcher_token.access_token)
        # Étape 4 : obtenir token EOS final
        eos_token = egs.exchange_eos_token(exchange_code)

        result = {
            "refresh_token": eos_token.refresh_token,
            "account_id": eos_token.account_id,
            "account_name": launcher_token.display_name,
        }
        if signals:
            signals.log_event.emit(f"[Auth Bot] Connecté en tant que {launcher_token.display_name}")
        return result
    except Exception as e:
        if signals:
            signals.log_event.emit(f"[Auth Bot] Erreur : {e}")
        return None
    finally:
        egs.close()