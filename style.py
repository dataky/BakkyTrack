"""style.py — Couleurs, feuille de style globale, helpers UI modernes."""
from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from PyQt6.QtGui     import QCursor, QFont, QLinearGradient, QColor

# ── Palette unifiée v2 — plus riche, plus moderne ────────────────────────
C_BG    = "#080A12"
C_BG2   = "#0E111A"
C_BG3   = "#161B28"
C_BLUE  = "#1A8CFF"
C_BLUE2 = "#0055CC"
C_ORG   = "#FF6B00"
C_ORG2  = "#CC5500"
C_TEXT  = "#E8ECF4"
C_MUTE  = "#5A6A82"
C_GREEN = "#3AE08A"
C_GREEN2= "#00B85A"
C_GOLD  = "#FFD700"
C_RED   = "#FF3D57"
C_RED2  = "#CC1F2E"
C_CYAN  = "#00CFFF"
C_PURPLE= "#8A2BE2"
C_PINK  = "#FF69B4"
C_GLASS = "rgba(255,255,255,0.04)"
C_GLASS_HOVER = "rgba(255,255,255,0.08)"

# ── Dégradés pré-construits ──────────────────────────────────────────────
GRADIENT_BLUE  = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1A8CFF,stop:1 #0055CC)"
GRADIENT_ORG   = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF6B00,stop:1 #CC5500)"
GRADIENT_GREEN = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3AE08A,stop:1 #00B85A)"
GRADIENT_RED   = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FF3D57,stop:1 #CC1F2E)"
GRADIENT_GOLD  = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #FFD700,stop:1 #FF8C00)"
GRADIENT_CYAN  = "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00CFFF,stop:1 #0088CC)"
GRADIENT_DARK  = "qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0E111A,stop:1 #080A12)"


APP_STYLE = f"""
QWidget {{ background:transparent; color:{C_TEXT};
           font-family:'Segoe UI','Inter','Rajdhani',system-ui,sans-serif; font-size:13px; }}
QMainWindow {{ background:transparent; }}
QToolTip {{ background:{C_BG3}; color:{C_TEXT}; border:none;
            padding:6px 8px; font-size:11px; border-radius:4px; }}
QTabWidget {{ background:transparent; }}
QTabWidget::pane {{ border:none;
                    background:{C_BG2}; border-radius:0 0 12px 12px; }}
QTabBar::tab {{ background:{C_BG2}; color:{C_MUTE};
                padding:10px 18px; min-height:24px; border:none;
                font-size:10px; font-weight:700; letter-spacing:0.8px;
                text-transform:uppercase;
                border-top-left-radius:8px; border-top-right-radius:8px; margin-right:2px; }}
QTabBar::tab:selected {{ background:{C_BG3}; color:{C_TEXT};
                         border-bottom:2px solid transparent;
                         border-image:linear-gradient(to right, {C_BLUE}, {C_CYAN}) 1;
                         padding-bottom:8px; }}
QTabBar::tab:hover:!selected {{ color:{C_TEXT}; background:{C_GLASS_HOVER}; }}
QLineEdit, QComboBox {{ background:{C_BG3}; color:{C_TEXT};
                        border:1px solid {C_GLASS}; border-radius:6px;
                        padding:7px 12px; font-size:11px; }}
QLineEdit:focus, QComboBox:focus {{ border:1px solid {C_BLUE}; 
                                     background:{C_BG2};
                                     outline:none; }}
QComboBox::drop-down {{ border:none; padding-right:8px; }}
QComboBox QAbstractItemView {{ background:{C_BG3}; color:{C_TEXT};
                               selection-background-color:{C_BLUE}; outline:none;
                               padding:4px; border-radius:6px; }}
QTextEdit {{ background:{C_BG3}; color:{C_MUTE}; border:1px solid {C_GLASS};
             font-family:'Consolas','Courier New',monospace; font-size:9px; border-radius:6px;
             padding:4px; }}
QScrollBar:vertical {{ background:{C_BG2}; width:4px; border:none; }}
QScrollBar::handle:vertical {{ background:{C_GLASS}; border-radius:2px; }}
QScrollBar::handle:vertical:hover {{ background:{C_MUTE}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QCheckBox {{ color:{C_TEXT}; font-size:11px; spacing:10px; }}
QCheckBox::indicator {{ width:18px; height:18px; border-radius:5px;
                        border:1px solid {C_GLASS}; background:{C_BG3}; }}
QCheckBox::indicator:checked {{ background:{GRADIENT_BLUE}; border:1px solid {C_BLUE}; }}
QCheckBox::indicator:hover {{ border:1px solid {C_BLUE}; }}
QScrollArea {{ background:transparent; border:none; }}
QScrollArea > QWidget > QWidget {{ background:transparent; }}
QProgressBar {{ border:none; background:{C_BG3}; border-radius:4px; height:6px; }}
QProgressBar::chunk {{ background:{GRADIENT_BLUE}; border-radius:4px; }}
QSlider::groove:horizontal {{ background:{C_BG3}; border-radius:4px; height:6px; }}
QSlider::sub-page:horizontal {{ background:{GRADIENT_BLUE}; border-radius:4px; height:6px; }}
QSlider::handle:horizontal {{ background:{C_TEXT}; border-radius:7px; width:14px; height:14px; 
                               margin:-4px 0; border:2px solid {C_BG3}; }}
QSlider::handle:horizontal:hover {{ background:{C_BLUE}; }}
QMenu {{ background:{C_BG2}; border:1px solid {C_GLASS}; border-radius:8px; padding:4px; }}
QMenu::item {{ padding:8px 16px; border-radius:4px; font-size:11px; }}
QMenu::item:selected {{ background:{C_GLASS_HOVER}; color:{C_TEXT}; }}
QMenu::separator {{ height:1px; background:{C_GLASS}; margin:4px 8px; }}
"""


def card(parent=None, bg=C_BG2, border=False, glow=False):
    """Carte moderne avec option de bordure ou glow."""
    f = QFrame(parent)
    extras = ""
    if border:
        extras += f";border:1px solid {C_GLASS_HOVER}"
    if glow:
        extras += f";border:1px solid rgba(26,140,255,0.2)"
    f.setStyleSheet(
        f"background:{bg}; border:none; border-radius:10px;{extras}"
    )
    return f


def lbl(text, color=C_MUTE, size=9, bold=False, parent=None):
    """Label moderne avec meilleur rendu typographique."""
    w = QLabel(text, parent)
    weight = "700" if bold else "500"
    w.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{weight};"
                    f"background:transparent;")
    return w


def btn(text, bg=C_BG3, fg=C_TEXT, size=10, bold=True, parent=None):
    """Bouton moderne avec hover lumineux."""
    w = QPushButton(text, parent)
    w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    weight = "700" if bold else "500"
    w.setStyleSheet(f"""
        QPushButton{{background:{bg};color:{fg};border:none;border-radius:6px;
                     padding:7px 16px;font-size:{size}px;font-weight:{weight};}}
        QPushButton:hover{{background:{bg}dd;
                          border:1px solid rgba(255,255,255,0.06);
                          margin:-1px;}}
        QPushButton:pressed{{background:{bg}99;}}
    """)
    return w


def hsep(parent=None, color=None):
    """Séparateur horizontal subtil avec option de dégradé."""
    s = QFrame(parent)
    s.setFrameShape(QFrame.Shape.HLine)
    s.setFixedHeight(1)
    if color:
        s.setStyleSheet(f"background:{color};border:none;")
    else:
        s.setStyleSheet(f"background:{C_GLASS};border:none;")
    return s


def stat_block(label, value, color=C_TEXT, size_label=8, size_value=24):
    """Bloc statistique : label + grande valeur, centré."""
    w = QFrame()
    w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    w.setStyleSheet("background:transparent;")
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(1)
    l = QLabel(label.upper())
    l.setAlignment(Qt.AlignmentFlag.AlignCenter)
    l.setStyleSheet(f"color:{C_MUTE};font-size:{size_label}px;font-weight:600;"
                    f"letter-spacing:2px;background:transparent;")
    val = QLabel(str(value))
    val.setAlignment(Qt.AlignmentFlag.AlignCenter)
    val.setStyleSheet(f"color:{color};font-size:{size_value}px;font-weight:800;"
                      f"background:transparent;")
    v.addWidget(l)
    v.addWidget(val)
    return w


def gradient_btn(text, gradient="blue", size=10, parent=None):
    """Bouton avec fond dégradé."""
    grad_map = {
        "blue": GRADIENT_BLUE,
        "orange": GRADIENT_ORG,
        "green": GRADIENT_GREEN,
        "red": GRADIENT_RED,
        "gold": GRADIENT_GOLD,
        "cyan": GRADIENT_CYAN,
        "dark": GRADIENT_DARK,
    }
    bg = grad_map.get(gradient, GRADIENT_BLUE)
    return btn(text, bg=bg, fg=C_TEXT, size=size, parent=parent)


def glass_card(parent=None):
    """Carte effet verre dépoli."""
    f = QFrame(parent)
    f.setStyleSheet(f"""
        QFrame{{background:{C_GLASS};
                border:1px solid {C_GLASS_HOVER};
                border-radius:12px;}}
    """)
    return f