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

class _GlassmorphCard(QWidget):
    """Overlay glassmorphism — 300×110, verre dépoli avec reflet et bordure lumineuse."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(300, 110)
        self._vals    = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 14)
        root.setSpacing(8)

        # Titre
        title = QLabel("ROCKET LEAGUE STATS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:rgba(255,255,255,0.35);font-size:7px;letter-spacing:3px;"
            "font-weight:700;background:transparent;")
        root.addWidget(title)

        # 4 colonnes (pas de colonne rang séparée)
        cols = QHBoxLayout(); cols.setSpacing(0)

        def col(key, label, color, with_rank=False):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)

            # Valeur (avec icône rang optionnel en ligne)
            val_cont = QWidget()
            val_cont.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            val_cont.setStyleSheet("background:transparent;")
            val_h = QHBoxLayout(val_cont)
            val_h.setContentsMargins(0, 0, 0, 0); val_h.setSpacing(5)
            val_h.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if with_rank:
                self._rank_icon = QLabel()
                self._rank_icon.setFixedSize(32, 32)
                self._rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._rank_icon.setStyleSheet("background:transparent;")
                val_h.addWidget(self._rank_icon)

            val_w = QLabel("--")
            val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_w.setStyleSheet(
                f"color:{color};font-size:20px;font-weight:800;background:transparent;")
            val_h.addWidget(val_w)

            lbl_w = QLabel(label)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_w.setStyleSheet(
                "color:rgba(255,255,255,0.4);font-size:7px;letter-spacing:1.5px;"
                "font-weight:600;background:transparent;")
            v.addWidget(val_cont); v.addWidget(lbl_w)
            self._vals[key] = val_w
            return w

        def vsep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine); s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(255,255,255,0.12);border:none;")
            return s

        cols.addWidget(col("mmr",    "MMR",    "rgba(255,255,255,0.95)", with_rank=True))
        cols.addWidget(vsep())
        cols.addWidget(col("wins",   "W",      "#7dffb3"))
        cols.addWidget(vsep())
        cols.addWidget(col("losses", "L",      "#ff8fa3"))
        cols.addWidget(vsep())
        cols.addWidget(col("stk",    "STREAK", "rgba(255,255,255,0.85)"))
        root.addLayout(cols)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 22)))
        p.drawRoundedRect(0, 0, w, h, 16, 16)

        shine = QLinearGradient(0, 0, 0, h * 0.5)
        shine.setColorAt(0.0, QColor(255, 255, 255, 45))
        shine.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shine))
        p.drawRoundedRect(0, 0, w, h // 2, 16, 16)

        pen = QPen(QColor(255, 255, 255, 60))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 16, 16)

        bh = 3
        win_w = max(0, min(w, int(w * self._winrate)))
        p.setPen(Qt.PenStyle.NoPen)
        if win_w > 0:
            gw = QLinearGradient(0, 0, win_w, 0)
            gw.setColorAt(0.0, QColor(125, 255, 179, 180))
            gw.setColorAt(1.0, QColor(0, 230, 118, 180))
            p.setBrush(QBrush(gw))
            p.drawRoundedRect(QRectF(0, h - bh, win_w, bh), 2, 2)
        if win_w < w:
            gl = QLinearGradient(win_w, 0, w, 0)
            gl.setColorAt(0.0, QColor(255, 61, 87, 120))
            gl.setColorAt(1.0, QColor(200, 30, 50, 120))
            p.setBrush(QBrush(gl))
            p.drawRoundedRect(QRectF(win_w, h - bh, w - win_w, bh), 2, 2)

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

        pm = _get_rank_pixmap(d.get("tier_id", 0), 32)
        if pm:
            self._rank_icon.setPixmap(pm)
        else:
            self._rank_icon.clear()

        self._vals["mmr"].setText(
            str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))
        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))
        if sv > 0:
            clr = "#7dffb3" if st == "win" else "#ff8fa3"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(
                f"color:{clr};font-size:20px;font-weight:800;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(
                "color:rgba(255,255,255,0.85);font-size:20px;font-weight:800;background:transparent;")


OVERLAY_NAME = 'glassmorph'
OVERLAY_SIZE = (300, 110)
Overlay = _GlassmorphCard
