#!/usr/bin/env python3
"""main.py — Entry point de BakkyTrack."""
import sys
import os
import asyncio

if sys.platform == 'win32':
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# ── Garantit que la racine du projet est dans sys.path ──────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# ────────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt as _Qt
from config import BASE_DIR, DEFAULT_ICON_B64
from style import APP_STYLE, C_BG, C_MUTE
from ui.main_window import MainApp


def _create_splash():
    """Crée un splash screen moderne avec dégradé."""
    from PyQt6.QtCore import Qt as _QtCore
    from PyQt6.QtGui import QPainter, QLinearGradient, QColor, QFont as _QFont, QPen
    
    size = (480, 160)
    splash_px = QPixmap(*size)
    splash_px.fill(_QtCore.GlobalColor.transparent)
    
    p = QPainter(splash_px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Fond dégradé
    g = QLinearGradient(0, 0, size[0], size[1])
    g.setColorAt(0.0, QColor("#0E111A"))
    g.setColorAt(0.5, QColor("#080A12"))
    g.setColorAt(1.0, QColor("#0E111A"))
    p.setBrush(g)
    p.setPen(_QtCore.PenStyle.NoPen)
    p.drawRoundedRect(0, 0, size[0], size[1], 12, 12)
    
    # Bordure subtile
    pen = QPen(QColor(26, 140, 255, 60))
    pen.setWidth(1)
    p.setPen(pen)
    p.setBrush(_QtCore.BrushStyle.NoBrush)
    p.drawRoundedRect(1, 1, size[0]-2, size[1]-2, 12, 12)
    
    # Texte
    font_big = _QFont("Segoe UI", 18, _QFont.Weight.Black)
    p.setFont(font_big)
    p.setPen(QColor("#E8ECF4"))
    p.drawText(24, 40, 300, 50, _QtCore.AlignmentFlag.AlignLeft | _QtCore.AlignmentFlag.AlignVCenter, "BakkyTrack")
    
    font_sub = _QFont("Segoe UI", 9, _QFont.Weight.Medium)
    p.setFont(font_sub)
    p.setPen(QColor("#5A6A82"))
    p.drawText(24, 80, 300, 30, _QtCore.AlignmentFlag.AlignLeft | _QtCore.AlignmentFlag.AlignVCenter, "Rocket League Stats Tracker")
    
    # Indicateur de chargement
    font_small = _QFont("Segoe UI", 9, _QFont.Weight.Medium)
    p.setFont(font_small)
    p.setPen(QColor("#3AE08A"))
    p.drawText(24, 130, 300, 20, _QtCore.AlignmentFlag.AlignLeft | _QtCore.AlignmentFlag.AlignVCenter, "● Chargement…")
    
    # Ligne bleue en bas
    g2 = QLinearGradient(0, 0, size[0], 0)
    g2.setColorAt(0.0, QColor("#1A8CFF"))
    g2.setColorAt(0.5, QColor("#00CFFF"))
    g2.setColorAt(1.0, QColor("#1A8CFF"))
    p.setBrush(g2)
    p.setPen(_QtCore.PenStyle.NoPen)
    p.drawRoundedRect(24, size[1]-12, size[0]-48, 3, 2, 2)
    
    p.end()
    return QSplashScreen(splash_px, _Qt.WindowType.WindowStaysOnTopHint)


def main():
    if sys.platform == "win32":
        import ctypes as _ctypes
        _mutex = _ctypes.windll.kernel32.CreateMutexW(None, False, "BakkyTrack_SingleInstance")
        if _ctypes.windll.kernel32.GetLastError() == 183:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "BakkyTrack est déjà en cours d'exécution.", "BakkyTrack", 0x30)
            sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    font = app.font(); font.setFamily("Segoe UI"); font.setPointSize(10)
    app.setFont(font)

    icon = None
    for name in ["logo.png", "logo.ico", "logo.jpg", "logo.jpeg", "logo.bmp", "logo.webp"]:
        candidate = os.path.join(BASE_DIR, name)
        if os.path.exists(candidate):
            px = QPixmap(candidate)
            if not px.isNull(): icon = QIcon(px); break
    if icon is None:
        import base64
        px = QPixmap(); px.loadFromData(base64.b64decode(DEFAULT_ICON_B64))
        if not px.isNull(): icon = QIcon(px)
    if icon: app.setWindowIcon(icon)

    splash = _create_splash()
    splash.show()
    app.processEvents()

    win = MainApp()
    if icon: win.setWindowIcon(icon)
    
    # Animation de fondu
    win.setWindowOpacity(0.0)
    splash.finish(win)
    win.show()
    win.raise_()
    win.activateWindow()
    
    from PyQt6.QtCore import QPropertyAnimation
    anim = QPropertyAnimation(win, b"windowOpacity")
    anim.setDuration(300)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.start()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()