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

def _get_rank_pixmap(tier_id: int, size: int = 32):
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


class _BannerClassicCard(_GlassCard):
    """Bannière horizontale classic (420×62) — 5 blocs : MMR (+rank) + DELTA + WINS + LOSSES + STREAK."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(420, 62)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 8)
        lay.setSpacing(0)
        self._vals = {}

        def block(key, lbl_txt, color, with_rank=False):
            w = QWidget(); w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(1)

            l = QLabel(lbl_txt); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet(f"color:{C_MUTE};font-size:8px;letter-spacing:1px;background:transparent;")

            # Conteneur valeur avec icône rang optionnel
            val_cont = QWidget(); val_cont.setStyleSheet("background:transparent;")
            val_h = QHBoxLayout(val_cont)
            val_h.setContentsMargins(0, 0, 0, 0); val_h.setSpacing(5)
            val_h.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if with_rank:
                self._rank_icon = QLabel()
                self._rank_icon.setFixedSize(32, 32)
                self._rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._rank_icon.setStyleSheet("background:transparent;")
                val_h.addWidget(self._rank_icon)

            val = QLabel("--"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(f"color:{color};font-size:15px;font-weight:700;background:transparent;")
            val_h.addWidget(val)

            v.addWidget(l); v.addWidget(val_cont)
            self._vals[key] = val
            return w

        def vsep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine); s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(255,255,255,0.12);border:none;")
            return s

        lay.addWidget(block("mmr",    "MMR",    C_GOLD,  with_rank=True))
        lay.addWidget(vsep())
        lay.addWidget(block("delta",  "DELTA",  C_GREEN))
        lay.addWidget(vsep())
        lay.addWidget(block("wins",   "WINS",   C_BLUE))
        lay.addWidget(vsep())
        lay.addWidget(block("losses", "LOSSES", C_ORG))
        lay.addWidget(vsep())
        lay.addWidget(block("stk",    "STREAK", C_GREEN))

    def update_stats(self, d, mmr_mode="both"):
        mmr = d.get("mmr")
        chg = d.get("mmr_change", 0)
        sv  = d.get("streak_val", 0)
        st  = d.get("streak_type", "")

        pm = _get_rank_pixmap(d.get("tier_id", 0), 32)
        if pm:
            self._rank_icon.setPixmap(pm)
        else:
            self._rank_icon.clear()

        self._vals["mmr"].setText("" if mmr_mode == "delta" else (str(mmr) if mmr else "--"))

        if mmr_mode == "mmr":
            self._vals["delta"].setText("")
        elif chg and mmr:
            sign = "+" if chg > 0 else ""
            clr  = C_GREEN if chg > 0 else C_ORG
            self._vals["delta"].setText(f"{sign}{chg}")
            self._vals["delta"].setStyleSheet(f"color:{clr};font-size:15px;font-weight:700;background:transparent;")
        else:
            self._vals["delta"].setText("--")
            self._vals["delta"].setStyleSheet(f"color:{C_MUTE};font-size:15px;font-weight:700;background:transparent;")

        self._vals["wins"].setText(str(d.get("wins", 0)))
        self._vals["losses"].setText(str(d.get("losses", 0)))
        if sv > 0:
            clr = C_GREEN if st == "win" else C_ORG
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(f"color:{clr};font-size:15px;font-weight:700;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(f"color:{C_GREEN};font-size:15px;font-weight:700;background:transparent;")


OVERLAY_NAME = 'banner_classic'
OVERLAY_SIZE = (420, 62)
Overlay = _BannerClassicCard
