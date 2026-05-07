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

def _get_rank_pixmap(tier_id: int, size: int = 40):
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

class _GaugeCard(QWidget):
    """Overlay arc de cercle — winrate en gauge, MMR au centre. 200×200."""

    ARC_WIDTH = 14
    ARC_R     = 72    # rayon de l'arc

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(200, 200)
        self._winrate = 0.5
        self._vals    = {}
        self._build()

    def _build(self):
        # Labels superposés au centre via layout absolu
        self._lbl_mmr   = QLabel("--",  self)
        self._lbl_delta = QLabel("",    self)
        self._lbl_ws    = QLabel("0W 0L", self)
        self._lbl_stk   = QLabel("",    self)
        
        # Icône de rang en bas
        self._rank_icon = QLabel("", self)
        self._rank_icon.setFixedSize(40, 40)
        self._rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon.setStyleSheet("background:transparent;")
        self._rank_icon.setGeometry(80, 155, 40, 40)

        self._lbl_mmr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_delta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_ws.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_stk.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl_mmr.setStyleSheet(
            "color:#00cfff;font-size:26px;font-weight:900;background:transparent;")
        self._lbl_delta.setStyleSheet(
            "color:#aaaaaa;font-size:13px;font-weight:700;background:transparent;")
        self._lbl_ws.setStyleSheet(
            "color:rgba(200,210,230,0.55);font-size:10px;font-weight:600;"
            "letter-spacing:1px;background:transparent;")
        self._lbl_stk.setStyleSheet(
            "color:#00e676;font-size:12px;font-weight:700;background:transparent;")

        cx, cy = 100, 96
        self._lbl_mmr.setGeometry(cx - 55, cy - 20, 110, 36)
        self._lbl_delta.setGeometry(cx - 55, cy + 14, 110, 20)
        self._lbl_ws.setGeometry(cx - 55, cy + 34, 110, 18)
        self._lbl_stk.setGeometry(cx - 55, cy - 42, 110, 20)

        self._lbl_title = QLabel("MMR", self)
        self._lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_title.setStyleSheet(
            "color:rgba(0,207,255,0.4);font-size:7px;letter-spacing:3px;"
            "font-weight:700;background:transparent;")
        self._lbl_title.setGeometry(cx - 55, cy - 58, 110, 16)

    def paintEvent(self, event):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 - 4

        # Fond circulaire
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(12, 14, 22, 220)))
        p.drawEllipse(QRectF(cx - 96, cy - 96, 192, 192))

        r = self.ARC_R
        lw = self.ARC_WIDTH
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)

        # Arc de fond (gris)
        pen_bg = QPen(QColor(40, 45, 60))
        pen_bg.setWidth(lw)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_bg)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Arc de 225° à -45° (bas gauche → bas droite, sens anti-horaire)
        p.drawArc(rect, 225 * 16, -270 * 16)

        # Arc winrate vert
        win_span = int(270 * self._winrate)
        if win_span > 0:
            pen_win = QPen()
            pen_win.setWidth(lw)
            pen_win.setCapStyle(Qt.PenCapStyle.RoundCap)
            g = QLinearGradient(cx - r, cy, cx + r, cy)
            g.setColorAt(0.0, QColor("#00e676"))
            g.setColorAt(1.0, QColor("#00cfaa"))
            pen_win.setBrush(QBrush(g))
            p.setPen(pen_win)
            p.drawArc(rect, 225 * 16, -win_span * 16)

        # Arc défaite rouge
        loss_span = 270 - win_span
        if loss_span > 0:
            pen_loss = QPen()
            pen_loss.setWidth(lw)
            pen_loss.setCapStyle(Qt.PenCapStyle.RoundCap)
            g2 = QLinearGradient(cx, cy - r, cx, cy + r)
            g2.setColorAt(0.0, QColor("#ff3d57"))
            g2.setColorAt(1.0, QColor("#cc1f2e"))
            pen_loss.setBrush(QBrush(g2))
            p.setPen(pen_loss)
            start_angle = (225 - win_span) * 16
            p.drawArc(rect, start_angle, -loss_span * 16)

        # Bordure externe douce
        pen_border = QPen(QColor(40, 50, 80, 100))
        pen_border.setWidth(1)
        p.setPen(pen_border)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - 96, cy - 96, 192, 192))

        # Halo intérieur
        halo = QRadialGradient(cx, cy, 58)
        halo.setColorAt(0.0, QColor(0, 207, 255, 18))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(halo))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - 58, cy - 58, 116, 116))

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
        
        # Icône de rang
        pm = _get_rank_pixmap(d.get("tier_id", 0), 40)
        if pm:
            self._rank_icon.setPixmap(pm)
        else:
            self._rank_icon.clear()

        self._lbl_mmr.setText(str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#00e676" if chg > 0 else "#ff3d57"
            self._lbl_delta.setText(f"{sign}{chg}")
            self._lbl_delta.setStyleSheet(
                f"color:{clr};font-size:13px;font-weight:700;background:transparent;")
        else:
            self._lbl_delta.setText("")
        self._lbl_ws.setText(f"{wins}W  {losses}L")
        if sv > 0:
            clr = "#00e676" if st == "win" else "#ff3d57"
            self._lbl_stk.setText(f"{'+'if st=='win'else'-'}{sv} STK")
            self._lbl_stk.setStyleSheet(
                f"color:{clr};font-size:12px;font-weight:700;background:transparent;")
        else:
            self._lbl_stk.setText("")




OVERLAY_NAME = 'gauge'
OVERLAY_SIZE = (200, 200)
Overlay = _GaugeCard
