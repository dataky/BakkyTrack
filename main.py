#!/usr/bin/env python3
"""main.py — Entry point de BakkyTrack."""
import sys
import os

# ── Garantit que la racine du projet est dans sys.path ──────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt as _Qt
from config import BASE_DIR, DEFAULT_ICON_B64
from style import APP_STYLE, C_BG, C_MUTE
from utils import _github_auto_update
from ui.main_window import MainApp


def main():
    if sys.platform == "win32":
        import ctypes as _ctypes
        _mutex = _ctypes.windll.kernel32.CreateMutexW(None, False, "BakkyTrack_SingleInstance")
        if _ctypes.windll.kernel32.GetLastError() == 183:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "BakkyTrack est déjà en cours d'exécution.", "BakkyTrack", 0x30)
            sys.exit(0)

    # Auto-update en arrière-plan (non bloquant)
    _github_auto_update(blocking=False)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    font = app.font(); font.setFamily("Segoe UI"); font.setPointSize(10)
    app.setFont(font)

    import base64
    icon = None
    for name in ["logo.png", "logo.ico", "logo.jpg", "logo.jpeg", "logo.bmp", "logo.webp"]:
        candidate = os.path.join(BASE_DIR, name)
        if os.path.exists(candidate):
            px = QPixmap(candidate)
            if not px.isNull(): icon = QIcon(px); break
    if icon is None:
        px = QPixmap(); px.loadFromData(base64.b64decode(DEFAULT_ICON_B64))
        if not px.isNull(): icon = QIcon(px)
    if icon: app.setWindowIcon(icon)

    from PyQt6.QtGui import QColor as _QColor
    splash_px = QPixmap(400, 120); splash_px.fill(_QColor(C_BG))
    splash = QSplashScreen(splash_px, _Qt.WindowType.WindowStaysOnTopHint)
    splash.showMessage("  Chargement de BakkyTrack…",
                       _Qt.AlignmentFlag.AlignBottom | _Qt.AlignmentFlag.AlignLeft,
                       _QColor(C_MUTE))
    splash.show(); app.processEvents()

    win = MainApp()
    if icon: win.setWindowIcon(icon)
    splash.finish(win); win.show(); win.raise_(); win.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()