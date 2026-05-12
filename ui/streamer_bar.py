"""ui/streamer_bar.py — StreamerModeBar (barre noire haut d'écran)."""
import sys
from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QApplication


class StreamerModeBar(QWidget):
    BAR_HEIGHT = 80

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint  |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool                 |
            Qt.WindowType.BypassWindowManagerHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.x(), screen.y(), screen.width(), self.BAR_HEIGHT)
        self.setStyleSheet("background:#000000;")
        hint = QLabel("🤫", self)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setGeometry(0, 0, screen.width(), self.BAR_HEIGHT)
        hint.setStyleSheet(
            "color:rgba(255,255,255,0.07);font-size:11px;"
            "font-weight:700;letter-spacing:4px;background:transparent;"
        )
        self.hide()

    def showEvent(self, e):
        super().showEvent(e)
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                HWND_TOPMOST, SWP_NOMOVE_NOSIZE = -1, 0x0003
                ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE_NOSIZE)
                GWL_EXSTYLE = -20
                ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | 0x08000000 | 0x00000020)
            except Exception:
                pass

    def hideEvent(self, e):
        super().hideEvent(e)
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                SW_HIDE = 0
                ctypes.windll.user32.ShowWindow(hwnd, SW_HIDE)
                HWND_NOTOPMOST = -2
                SWP_NOMOVE_NOSIZE = 0x0003
                ctypes.windll.user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE_NOSIZE)
            except Exception:
                pass