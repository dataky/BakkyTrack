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
from PyQt6.QtGui import QPixmap

_RANK_FOLDER = os.path.join(BASE_DIR, "all rank")
_rank_cache: dict = {}

def _get_rank_pixmap(tier_id: int, size: int = 22):
    key = (tier_id, size)
    if key in _rank_cache:
        return _rank_cache[key]
    path = os.path.join(_RANK_FOLDER, f"{tier_id}.png")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            scaled = pm.scaled(size, size,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            _rank_cache[key] = scaled
            return scaled
    _rank_cache[key] = None
    return None

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

class _PillCard(QWidget):
    """Overlay pill ultra-compact : barre horizontale fine 360×36."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(360, 36)
        self._vals = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(0)

        # Icône rang (20px — intégré naturellement au début)
        self._rank_icon = QLabel()
        self._rank_icon.setFixedSize(22, 22)
        self._rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon.setStyleSheet("background:transparent;")
        lay.addWidget(self._rank_icon)

        def dot():
            d = QLabel("·")
            d.setStyleSheet("color:rgba(100,100,120,0.6);font-size:18px;background:transparent;")
            return d

        def seg(key, label, color):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet("background:transparent;")
            h = QHBoxLayout(w)
            h.setContentsMargins(8, 0, 8, 0); h.setSpacing(4)
            lbl_w = QLabel(label)
            lbl_w.setStyleSheet(
                "color:rgba(160,170,190,0.55);font-size:8px;"
                "letter-spacing:1.5px;font-weight:600;background:transparent;")
            val_w = QLabel("--")
            val_w.setStyleSheet(
                f"color:{color};font-size:13px;font-weight:800;background:transparent;")
            h.addWidget(lbl_w); h.addWidget(val_w)
            self._vals[key] = val_w
            return w

        lay.addWidget(dot())
        lay.addWidget(seg("mmr",    "MMR",  "#00cfff"))
        lay.addWidget(dot())
        lay.addWidget(seg("delta",  "±",    "#aaaaaa"))
        lay.addWidget(dot())
        lay.addWidget(seg("wins",   "W",    "#00e676"))
        lay.addWidget(dot())
        lay.addWidget(seg("losses", "L",    "#ff3d57"))
        lay.addWidget(dot())
        lay.addWidget(seg("stk",    "STK",  "#00e676"))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(18, 20, 30, 210)))
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)

        win_w = max(0, min(w, int(w * self._winrate)))
        if win_w > 0:
            g = QLinearGradient(0, 0, win_w, 0)
            g.setColorAt(0.0, QColor("#00e676"))
            g.setColorAt(1.0, QColor("#00b84a"))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(0, h - 3, win_w, 3), 2, 2)
        if win_w < w:
            g2 = QLinearGradient(win_w, 0, w, 0)
            g2.setColorAt(0.0, QColor("#cc1f2e"))
            g2.setColorAt(1.0, QColor("#ff3d57"))
            p.setBrush(QBrush(g2))
            p.drawRoundedRect(QRectF(win_w, h - 3, w - win_w, 3), 2, 2)

        pen = QPen(QColor(60, 70, 100, 120))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), h // 2, h // 2)
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

        pm = _get_rank_pixmap(d.get("tier_id", 0), 22)
        if pm:
            self._rank_icon.setPixmap(pm)
        else:
            self._rank_icon.clear()

        self._vals["mmr"].setText(str(mmr) if mmr and mmr_mode != "delta" else "")
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#00e676" if chg > 0 else "#ff3d57"
            self._vals["delta"].setText(f"{sign}{chg}")
            self._vals["delta"].setStyleSheet(
                f"color:{clr};font-size:13px;font-weight:800;background:transparent;")
        else:
            self._vals["delta"].setText("")

        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))
        if sv > 0:
            clr = "#00e676" if st == "win" else "#ff3d57"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(
                f"color:{clr};font-size:13px;font-weight:800;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(
                "color:#00e676;font-size:13px;font-weight:800;background:transparent;")


OVERLAY_NAME = 'pill'
OVERLAY_SIZE = (360, 36)
Overlay = _PillCard
