"""utils.py — Icônes, SVG, overlays globaux, auto-updater, VK keys."""
import os, sys, time, math, urllib.parse, urllib.request, urllib.error, json, hashlib, threading
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


# ── Icônes de rang ───────────────────────────────────────────────────────
_RANK_FOLDER = os.path.join(BASE_DIR, "all rank")
_rank_pixmap_cache: dict = {}


def get_rank_pixmap(tier_id: int, size: int = 40):
    from PyQt6.QtGui import QPixmap
    key = (tier_id, size)
    if key in _rank_pixmap_cache:
        return _rank_pixmap_cache[key]
    path = os.path.join(_RANK_FOLDER, f"{tier_id}.png")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            scaled = pm.scaled(size, size,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            _rank_pixmap_cache[key] = scaled
            return scaled
    _rank_pixmap_cache[key] = None
    return None


# ── Icônes de playlist ───────────────────────────────────────────────────
_PLAYLIST_FOLDER = os.path.join(BASE_DIR, "Playlist")
_playlist_pixmap_cache: dict = {}

_PLAYLIST_FILE_INDEX = {
    "1v1": 0, "2v2": 1, "3v3": 2,
    "hoops": 3, "rumble": 4, "dropshot": 5, "snowday": 6, "tournament": 7,
}
_PLAYLIST_ID_TO_KEY = {10: "1v1", 11: "2v2", 13: "3v3"}


def get_playlist_pixmap(playlist_key, size: int = 28):
    from PyQt6.QtGui import QPixmap
    file_idx = _PLAYLIST_FILE_INDEX.get(playlist_key, 2)
    key = (file_idx, size)
    if key in _playlist_pixmap_cache:
        return _playlist_pixmap_cache[key]
    path = os.path.join(_PLAYLIST_FOLDER, f"{file_idx}.png")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            scaled = pm.scaled(size, size,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            _playlist_pixmap_cache[key] = scaled
            return scaled
    _playlist_pixmap_cache[key] = None
    return None


# ── SVG Backgrounds ──────────────────────────────────────────────────────
from PyQt6.QtCore import QRectF, QByteArray
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui import QPainter
from PyQt6.QtSvg import QSvgRenderer

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


# ── Auto-updater GitHub ──────────────────────────────────────────────────
_GITHUB_API  = "https://api.github.com/repos/dataky/BakkyTrack/contents/"
_GITHUB_RAW  = "https://raw.githubusercontent.com/dataky/BakkyTrack/main/"
_UPDATE_DIRS = {
    "overlays":  os.path.join(BASE_DIR, "overlays"),
    "all rank":  os.path.join(BASE_DIR, "all rank"),
    "themes":    os.path.join(BASE_DIR, "themes"),
    "Playlist":    os.path.join(BASE_DIR, "Playlist"),
}


def _github_auto_update(blocking=False, progress_cb=None):
    # Utilise os.environ pour garantir l'unicité même si utils.py
    # est importé plusieurs fois sous des noms de modules différents
    if os.environ.get("_BAKKYTRACK_UPDATE_DONE"):
        return
    os.environ["_BAKKYTRACK_UPDATE_DONE"] = "1"

    def _log(msg):
        print(msg)
        if progress_cb:
            try: progress_cb(msg)
            except Exception: pass

    def _urlopen(req, timeout=10):
        ctx = SSL_CTX if SSL_CTX is not None else SSL_CTX_NOVERIFY
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        except Exception as e:
            if "SSL" in str(e) or "certificate" in str(e).lower():
                _log(f"[Updater] SSL fallback pour {req.full_url[:60]}")
                return urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX_NOVERIFY)
            raise

    def _git_sha1(data: bytes) -> str:
        header = f"blob {len(data)}\0".encode()
        return hashlib.sha1(header + data).hexdigest()

    def _update_dir(remote_path: str, local_dir: str):
        os.makedirs(local_dir, exist_ok=True)
        if os.path.isdir(local_dir) and any(os.path.isfile(os.path.join(local_dir, f)) for f in os.listdir(local_dir)):
            _log(f"[Updater] {remote_path} — déjà présent localement, skip")
            return
        url = _GITHUB_API + urllib.parse.quote(remote_path)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BakkyTrack"})
            with _urlopen(req, timeout=8) as r:
                entries = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 403:
                _log(f"[Updater] Limite GitHub pour {remote_path}.")
            else:
                _log(f"[Updater] Impossible de lister {remote_path} : {e}")
            return
        except Exception as e:
            _log(f"[Updater] Impossible de lister {remote_path} : {e}")
            return
        time.sleep(0.5)
        downloaded = 0
        for entry in entries:
            if entry.get("type") != "file":
                continue
            name       = entry["name"]
            remote_sha = entry["sha"]
            raw_url    = _GITHUB_RAW + urllib.parse.quote(f"{remote_path}/{name}")
            local_path = os.path.join(local_dir, name)
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f:
                        if _git_sha1(f.read()) == remote_sha:
                            continue
                except Exception:
                    pass
            try:
                time.sleep(0.3)
                req = urllib.request.Request(raw_url, headers={"User-Agent": "BakkyTrack"})
                with _urlopen(req, timeout=10) as r:
                    data = r.read()
                with open(local_path, "wb") as f:
                    f.write(data)
                downloaded += 1
                _log(f"[Updater] ✓ {remote_path}/{name}")
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    _log(f"[Updater] ✗ {remote_path}/{name} : Limite GitHub")
                else:
                    _log(f"[Updater] ✗ {remote_path}/{name} : {e}")
            except Exception as e:
                _log(f"[Updater] ✗ {remote_path}/{name} : {e}")
        if downloaded == 0:
            _log(f"[Updater] {remote_path} — déjà à jour")

    def _run():
        _log("[Updater] Vérification des mises à jour GitHub…")
        for remote_path, local_dir in _UPDATE_DIRS.items():
            _update_dir(remote_path, local_dir)
        _logo_local = os.path.join(BASE_DIR, "logo.ico")
        if os.path.exists(_logo_local):
            _log("[Updater] logo.ico — déjà présent, skip")
            return
        _logo_url = _GITHUB_RAW + "BakkyTrack/logo.ico"
        try:
            time.sleep(0.5)
            req = urllib.request.Request(_logo_url, headers={"User-Agent": "BakkyTrack"})
            with _urlopen(req, timeout=8) as r:
                data = r.read()
            with open(_logo_local, "wb") as f:
                f.write(data)
            _log("[Updater] ✓ logo.ico")
        except urllib.error.HTTPError as e:
            if e.code == 403:
                _log(f"[Updater] ✗ logo.ico : Limite GitHub")
            else:
                _log(f"[Updater] ✗ logo.ico : {e}")
        except Exception as e:
            _log(f"[Updater] ✗ logo.ico : {e}")
        _log("[Updater] ✓ Terminé")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    if blocking:
        t.join(timeout=30)
