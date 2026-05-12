"""ui/dialogs.py — KeyCaptureDialog, KeyCaptureWidget, OverlayBindDialog, BindWorker."""
from PyQt6.QtCore    import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
)
from PyQt6.QtGui import QCursor
from style import C_BG2, C_BG3, C_BLUE, C_TEXT, C_MUTE, C_ORG, card, btn
from utils import _QT_KEY_MAP, _key_display, _VK_MAP

# ── Import de get_gamepad_state ──────────────────────────────────────────
import sys as _sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in _sys.path:
    _sys.path.insert(0, _ROOT)
from gamepad_state import get_gamepad_state
# ────────────────────────────────────────────────────────────────────────


# ── KeyCaptureDialog ─────────────────────────────────────────────────────
class KeyCaptureDialog(QDialog):
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


# ── KeyCaptureWidget ─────────────────────────────────────────────────────
class KeyCaptureWidget(QWidget):
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


# ── BindWorker ───────────────────────────────────────────────────────────
class BindWorker(QThread):
    finished_bind = pyqtSignal(str, bool, int)

    def run(self):
        import time, sys
        time.sleep(0.4)
        get_gamepad_state()
        while True:
            if sys.platform == "win32":
                import ctypes
                for vk in list(_VK_MAP.values()):
                    if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
                        for name, code in _VK_MAP.items():
                            if code == vk:
                                if name.startswith("mouse:"):
                                    continue
                                self.finished_bind.emit(f"key:{name}", False, 0)
                                return
                        if 0x30 <= vk <= 0x39:
                            self.finished_bind.emit(f"key:{chr(vk)}", False, 0)
                            return
                        if 0x41 <= vk <= 0x5A:
                            self.finished_bind.emit(f"key:{chr(vk).lower()}", False, 0)
                            return
            xi = get_gamepad_state()
            if xi and xi.Gamepad.wButtons != 0:
                btn = xi.Gamepad.wButtons
                while True:
                    xi2 = get_gamepad_state()
                    if not xi2 or xi2.Gamepad.wButtons == 0:
                        break
                    time.sleep(0.05)
                self.finished_bind.emit("", True, btn)
                return
            time.sleep(0.02)


# ── OverlayBindDialog ────────────────────────────────────────────────────
def _overlay_hotkey_display(cfg) -> str:
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


class OverlayBindDialog(QDialog):
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
            "Appuie sur une touche clavier\nou maintiens un bouton manette…")
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
        self._worker = BindWorker()
        self._worker.finished_bind.connect(self._on_bind)
        self._worker.start()

    def _disable(self):
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