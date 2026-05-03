"""Auto-généré — overlay plugin pour RL Tracker."""
import sys, os
from PyQt6.QtCore    import Qt, QTimer, QRectF, QByteArray, QPointF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QStackedWidget
from PyQt6.QtGui     import (QColor, QPainter, QBrush, QPen, QLinearGradient,
                              QRadialGradient, QFont, QPolygonF, QCursor)
from PyQt6.QtSvg     import QSvgRenderer

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))

C_BG   = "#0A0C10"; C_BG2  = "#12151C"; C_BG3  = "#1A1E2A"
C_BLUE = "#1A8CFF"; C_ORG  = "#FF6B00"; C_TEXT = "#E8ECF4"
C_MUTE = "#5A6275"; C_GREEN= "#3AE08A"; C_GOLD = "#FFD700"

THEMES_DIR = os.path.join(BASE_DIR, "themes")
def _load_svg(name):
    try:
        with open(os.path.join(THEMES_DIR, f"{name}.svg"), "rb") as f: return f.read()
    except FileNotFoundError: return b""
SVG_BACKGROUNDS = {n: _load_svg(n) for n in ["rl_classic","victory","defeat","neon","dark_minimal"]}

def lbl(text, color=C_MUTE, size=9, bold=False, parent=None):
    from PyQt6.QtWidgets import QLabel
    w = QLabel(text, parent)
    w.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{'700' if bold else '400'};"
                    "background:transparent;letter-spacing:1px;")
    return w

def hsep(parent=None):
    s = QFrame(parent); s.setFrameShape(QFrame.Shape.HLine)
    s.setFixedHeight(1); s.setStyleSheet(f"background:{C_BG3};border:none;")
    return s

class _GlassCard(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(10, 12, 16, 220)))
        p.setPen(QPen(QColor(255, 255, 255, 25), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 2, 0, 0), 8, 8)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0.0, QColor("#1A8CFF"))
        g.setColorAt(1.0, QColor("#FF6B00"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRoundedRect(0, 0, self.width(), 2, 1, 1)


class _GlassCard(QWidget):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(10, 12, 16, 220)))
        p.setPen(QPen(QColor(255, 255, 255, 25), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 2, 0, 0), 8, 8)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0.0, QColor("#1A8CFF"))
        g.setColorAt(1.0, QColor("#FF6B00"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(g))
        p.drawRoundedRect(0, 0, self.width(), 2, 1, 1)


class _CompactCard(_GlassCard):
    def __init__(self):
        super().__init__()
        self.setFixedSize(224, 172)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 12)
        lay.setSpacing(6)

        # Ligne MMR avec delta à côté
        mmr_row = QHBoxLayout()
        mmr_lbl_w = QLabel("MMR")
        mmr_lbl_w.setStyleSheet(f"color:{C_MUTE};font-size:9px;letter-spacing:1.2px;background:transparent;")
        self.v_delta = QLabel("")
        self.v_delta.setStyleSheet(f"color:{C_GREEN};font-size:11px;font-weight:700;background:transparent;")
        self.v_mmr = QLabel("--")
        self.v_mmr.setStyleSheet(f"color:{C_GOLD};font-size:18px;font-weight:700;background:transparent;")
        mmr_row.addWidget(mmr_lbl_w); mmr_row.addStretch()
        mmr_row.addWidget(self.v_delta); mmr_row.addSpacing(5)
        mmr_row.addWidget(self.v_mmr)
        lay.addLayout(mmr_row)
        lay.addWidget(hsep())

        def row(lbl_txt, val_color, size=16):
            r = QHBoxLayout()
            l = QLabel(lbl_txt)
            l.setStyleSheet(f"color:{C_MUTE};font-size:9px;letter-spacing:1.2px;background:transparent;")
            v = QLabel("--")
            v.setStyleSheet(f"color:{val_color};font-size:{size}px;font-weight:700;background:transparent;")
            r.addWidget(l); r.addStretch(); r.addWidget(v)
            return r, v

        r2, self.v_stk    = row("STREAK", C_GREEN)
        lay.addLayout(r2);  lay.addWidget(hsep())
        r3, self.v_wins   = row("WINS",   C_BLUE)
        lay.addLayout(r3)
        r4, self.v_losses = row("LOSSES", C_ORG)
        lay.addLayout(r4)

    def update_stats(self, d, mmr_mode="both"):
        mmr = d.get("mmr")
        chg = d.get("mmr_change", 0)
        sv  = d.get("streak_val", 0)
        st  = d.get("streak_type", "")

        if mmr_mode == "delta":
            self.v_mmr.setText("")
            if chg:
                sign = "+" if chg > 0 else ""
                clr  = C_GREEN if chg > 0 else C_ORG
                self.v_delta.setText(f"{sign}{chg}")
                self.v_delta.setStyleSheet(f"color:{clr};font-size:18px;font-weight:700;background:transparent;")
            else:
                self.v_delta.setText("--")
                self.v_delta.setStyleSheet(f"color:{C_MUTE};font-size:18px;font-weight:700;background:transparent;")
        elif mmr_mode == "mmr":
            self.v_mmr.setText(str(mmr) if mmr else "--")
            self.v_delta.setText("")
        else:  # both
            self.v_mmr.setText(str(mmr) if mmr else "--")
            if chg and mmr:
                sign = "+" if chg > 0 else ""
                clr  = C_GREEN if chg > 0 else C_ORG
                self.v_delta.setText(f"{sign}{chg}")
                self.v_delta.setStyleSheet(f"color:{clr};font-size:11px;font-weight:700;background:transparent;")
            else:
                self.v_delta.setText("")

        self.v_wins.setText(str(d.get("wins", 0)))
        self.v_losses.setText(str(d.get("losses", 0)))
        if sv > 0:
            clr = C_GREEN if st == "win" else C_ORG
            self.v_stk.setText(f"{'+'if st=='win'else'-'}{sv}")
            self.v_stk.setStyleSheet(f"color:{clr};font-size:16px;font-weight:700;background:transparent;")
        else:
            self.v_stk.setText("--")
            self.v_stk.setStyleSheet(f"color:{C_GREEN};font-size:16px;font-weight:700;background:transparent;")




OVERLAY_NAME = 'compact'
OVERLAY_SIZE = (224, 172)
Overlay = _CompactCard
