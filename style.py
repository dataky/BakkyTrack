"""style.py — Couleurs, feuille de style globale, helpers UI légers."""
from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton
from PyQt6.QtGui     import QCursor

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


def card(parent=None, bg=C_BG2):
    f = QFrame(parent)
    f.setStyleSheet(
        f"QFrame{{background:{bg};border-radius:8px;border:none;}}")
    return f


def lbl(text, color=C_MUTE, size=9, bold=False, parent=None):
    w = QLabel(text, parent)
    weight = "700" if bold else "400"
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