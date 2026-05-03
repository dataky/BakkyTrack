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

class _SidebarCard(QWidget):
    """Overlay sidebar vertical : 108×260, 5 blocs empilés avec barre de winrate."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(108, 260)
        self._vals    = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(1)

        def block(key, label, val_color, bg_color):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet(f"background:rgba(0,0,0,0);")
            w.setFixedHeight(46)
            v = QVBoxLayout(w)
            v.setContentsMargins(12, 6, 12, 6)
            v.setSpacing(1)
            val_w = QLabel("--")
            val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_w.setStyleSheet(
                f"color:{val_color};font-size:18px;font-weight:800;background:transparent;")
            lbl_w = QLabel(label)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_w.setStyleSheet(
                "color:rgba(160,170,190,0.5);font-size:7px;letter-spacing:2px;"
                "font-weight:600;background:transparent;")
            v.addWidget(val_w)
            v.addWidget(lbl_w)
            self._vals[key] = val_w
            self._vals[f"_{key}_bg"] = bg_color
            return w

        # ── Header ──────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        hdr.setFixedHeight(26)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 6, 12, 0)
        title = QLabel("RL TRACKER")
        title.setStyleSheet(
            "color:rgba(26,140,255,0.6);font-size:7px;font-weight:700;"
            "letter-spacing:2px;background:transparent;")
        hdr_lay.addWidget(title)
        root.addWidget(hdr)

        # ── Barre winrate ─────────────────────────────────────────────────
        self._wr_bar = QWidget()
        self._wr_bar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._wr_bar.setFixedHeight(4)
        root.addWidget(self._wr_bar)

        # ── Blocs stats ───────────────────────────────────────────────────
        root.addWidget(block("mmr",    "MMR",      "#00cfff", "#0a1520"))
        root.addWidget(block("delta",  "DELTA",    "#aaaaaa", "#0e0e18"))
        root.addWidget(block("wins",   "WINS",     "#00e676", "#071510"))
        root.addWidget(block("losses", "LOSSES",   "#ff3d57", "#150708"))
        root.addWidget(block("stk",    "STREAK",   "#00e676", "#071510"))
        root.addStretch()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fond de base
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(12, 14, 22, 225)))
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        # Couleur par bloc (alternance)
        colors = [
            QColor(0, 40, 60, 50),   # mmr – cyan teinté
            QColor(20, 20, 35, 40),  # delta – neutre
            QColor(0, 60, 30, 50),   # wins – vert teinté
            QColor(60, 10, 15, 50),  # losses – rouge teinté
            QColor(0, 60, 30, 40),   # stk – vert teinté
        ]
        block_h = 46
        y_start = 30  # header 26 + winrate bar 4
        for i, c in enumerate(colors):
            p.setBrush(QBrush(c))
            p.drawRect(QRectF(0, y_start + i * (block_h + 1), w, block_h))

        # Barre winrate (4px sous le header)
        bar_y = 26
        win_w = max(0, min(w, int(w * self._winrate)))
        if win_w > 0:
            g = QLinearGradient(0, 0, win_w, 0)
            g.setColorAt(0.0, QColor("#00e676"))
            g.setColorAt(1.0, QColor("#00b84a"))
            p.setBrush(QBrush(g))
            p.drawRect(QRectF(0, bar_y, win_w, 4))
        if win_w < w:
            g2 = QLinearGradient(win_w, 0, w, 0)
            g2.setColorAt(0.0, QColor("#cc1f2e"))
            g2.setColorAt(1.0, QColor("#ff3d57"))
            p.setBrush(QBrush(g2))
            p.drawRect(QRectF(win_w, bar_y, w - win_w, 4))

        # Bordure extérieure
        pen = QPen(QColor(40, 50, 80, 140))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8, 8)

        # Accent bleu à gauche (4px)
        p.setPen(Qt.PenStyle.NoPen)
        g3 = QLinearGradient(0, 0, 0, h)
        g3.setColorAt(0.0, QColor("#1A8CFF"))
        g3.setColorAt(1.0, QColor("#FF6B00"))
        p.setBrush(QBrush(g3))
        p.drawRoundedRect(QRectF(0, 0, 3, h), 2, 2)

        p.end()

    def update_stats(self, d, mmr_mode="both"):
        mmr  = d.get("mmr")
        chg  = d.get("mmr_change", 0)
        sv   = d.get("streak_val", 0)
        st   = d.get("streak_type", "")
        wins = d.get("wins", 0)
        losses = d.get("losses", 0)
        total  = wins + losses
        self._winrate = (wins / total) if total > 0 else 0.5
        self.update()

        self._vals["mmr"].setText(str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#00e676" if chg > 0 else "#ff3d57"
            self._vals["delta"].setText(f"{sign}{chg}")
            self._vals["delta"].setStyleSheet(
                f"color:{clr};font-size:18px;font-weight:800;background:transparent;")
        else:
            self._vals["delta"].setText("--" if mmr_mode != "mmr" else "")
            self._vals["delta"].setStyleSheet(
                "color:#555;font-size:18px;font-weight:800;background:transparent;")

        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))
        if sv > 0:
            clr = "#00e676" if st == "win" else "#ff3d57"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(
                f"color:{clr};font-size:18px;font-weight:800;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(
                "color:#00e676;font-size:18px;font-weight:800;background:transparent;")




OVERLAY_NAME = 'sidebar'
OVERLAY_SIZE = (108, 260)
Overlay = _SidebarCard
