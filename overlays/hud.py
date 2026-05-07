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

class _HUDCard(QWidget):
    """Overlay HUD FPS militaire — 320×130, coins découpés, lignes de scan, style ARMA/DayZ."""

    CORNER = 18

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(330, 130)
        self._vals    = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 18)
        root.setSpacing(4)

        # Header simplifié (sans icône rang)
        hdr = QHBoxLayout()
        title = QLabel("TACTICAL STATS")
        title.setStyleSheet(
            "color:rgba(0,230,80,0.6);font-size:7px;letter-spacing:4px;"
            "font-weight:700;background:transparent;")
        status = QLabel("● ONLINE")
        status.setStyleSheet(
            "color:rgba(0,230,80,0.7);font-size:7px;letter-spacing:1px;"
            "font-weight:700;background:transparent;")
        hdr.addWidget(title); hdr.addStretch(); hdr.addWidget(status)
        root.addLayout(hdr)

        # Ligne scan
        scan = QFrame(); scan.setFixedHeight(1)
        scan.setStyleSheet("background:rgba(0,230,80,0.3);border:none;")
        root.addWidget(scan)
        root.addSpacing(4)

        # Ligne MMR avec icône rang inline
        mmr_row = QHBoxLayout(); mmr_row.setSpacing(6)
        mmr_lbl = QLabel("▸  RATING")
        mmr_lbl.setStyleSheet(
            "color:rgba(0,200,60,0.5);font-size:8px;letter-spacing:1.5px;"
            "font-weight:600;background:transparent;")

        self._rank_icon = QLabel()
        self._rank_icon.setFixedSize(32, 32)
        self._rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon.setStyleSheet("background:transparent;")

        mmr_val = QLabel("--")
        mmr_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        mmr_val.setStyleSheet("color:#00e650;font-size:18px;font-weight:800;background:transparent;")

        mmr_row.addWidget(mmr_lbl)
        mmr_row.addStretch()
        mmr_row.addWidget(self._rank_icon)
        mmr_row.addSpacing(4)
        mmr_row.addWidget(mmr_val)
        self._vals["mmr_line"] = mmr_val
        root.addLayout(mmr_row)

        # Lignes W/L et STREAK
        def row_stat(key, label, color, size=13):
            r = QHBoxLayout(); r.setSpacing(6)
            lbl_w = QLabel(f"▸  {label}")
            lbl_w.setStyleSheet(
                "color:rgba(0,200,60,0.5);font-size:8px;letter-spacing:1.5px;"
                "font-weight:600;background:transparent;")
            val_w = QLabel("--")
            val_w.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_w.setStyleSheet(
                f"color:{color};font-size:{size}px;font-weight:800;background:transparent;")
            r.addWidget(lbl_w); r.addStretch(); r.addWidget(val_w)
            self._vals[key] = val_w
            return r

        root.addLayout(row_stat("wl_line",  "W/L",    "#b0ffb0", 13))
        root.addLayout(row_stat("stk_line", "STREAK", "#00e650", 13))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        c = self.CORNER

        body = QPolygonF([
            QPointF(c, 0),
            QPointF(w, 0),
            QPointF(w, h - c),
            QPointF(w - c, h),
            QPointF(0, h),
            QPointF(0, c),
        ])

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(4, 16, 8, 220)))
        p.drawPolygon(body)

        p.setOpacity(0.04)
        p.setBrush(QBrush(QColor("#00e650")))
        for y in range(0, h, 4):
            p.drawRect(QRectF(0, y, w, 1))
        p.setOpacity(1.0)

        pen = QPen(QColor(0, 200, 60, 160))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(body)

        accent = QPen(QColor(0, 230, 80, 220))
        accent.setWidth(2)
        p.setPen(accent)
        size_l = 14
        p.drawLine(c, 0, c + size_l, 0); p.drawLine(c, 0, c, size_l)
        p.drawLine(w - size_l, 0, w, 0); p.drawLine(w, 0, w, size_l)
        p.drawLine(0, h - size_l, 0, h); p.drawLine(0, h, size_l, h)
        p.drawLine(w - c, h, w - c - size_l + c, h); p.drawLine(w - c, h, w, h - c)

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

        pm = _get_rank_pixmap(d.get("tier_id", 0), 32)
        if pm:
            self._rank_icon.setPixmap(pm)
        else:
            self._rank_icon.clear()

        mmr_str = str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--")
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            mmr_str += f"  {sign}{chg}"
        self._vals["mmr_line"].setText(mmr_str)

        self._vals["wl_line"].setText(f"{wins}W  /  {losses}L")

        if sv > 0:
            clr = "#00e650" if st == "win" else "#ff5060"
            self._vals["stk_line"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk_line"].setStyleSheet(
                f"color:{clr};font-size:13px;font-weight:800;background:transparent;")
        else:
            self._vals["stk_line"].setText("--")
            self._vals["stk_line"].setStyleSheet(
                "color:#00e650;font-size:13px;font-weight:800;background:transparent;")


OVERLAY_NAME = 'hud'
OVERLAY_SIZE = (330, 130)
Overlay = _HUDCard
