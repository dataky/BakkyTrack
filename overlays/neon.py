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

def _get_rank_pixmap(tier_id: int, size: int = 36):
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

class _NeonCard(QWidget):
    """Overlay neon cyberpunk : 260×140, halo coloré, bordures lumineuses."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(260, 140)
        self._vals  = {}
        self._is_win_streak = True
        self._winrate = 0.5
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(6)

        # ── Titre ──────────────────────────────────────────────────────────
        title = QLabel("ROCKET LEAGUE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:rgba(0,207,255,0.45);font-size:7px;letter-spacing:4px;"
            "font-weight:700;background:transparent;")
        root.addWidget(title)

        # ── MMR grande valeur ───────────────────────────────────────────────
        mmr_row = QHBoxLayout()
        mmr_row.setSpacing(6)
        
        # Icône de rang
        self._rank_icon = QLabel()
        self._rank_icon.setFixedSize(36, 36)
        self._rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon.setStyleSheet("background:transparent;")
        
        v_mmr = QLabel("--")
        v_mmr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v_mmr.setStyleSheet(
            "color:#00cfff;font-size:36px;font-weight:900;"
            "letter-spacing:-1px;background:transparent;")
        v_delta = QLabel("")
        v_delta.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        v_delta.setStyleSheet(
            "color:#888;font-size:14px;font-weight:700;background:transparent;")
        mmr_row.addStretch()
        mmr_row.addWidget(self._rank_icon)
        mmr_row.addWidget(v_mmr)
        mmr_row.addWidget(v_delta)
        mmr_row.addStretch()
        root.addLayout(mmr_row)
        self._vals["mmr"]   = v_mmr
        self._vals["delta"] = v_delta

        # ── Séparateur ligne lumineuse ──────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(0,207,255,0.25);border:none;")
        root.addWidget(sep)

        # ── 3 colonnes W / L / STK ─────────────────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(0)

        def col(key, label, color):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 4, 0, 0)
            v.setSpacing(1)
            val_w = QLabel("--")
            val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_w.setStyleSheet(
                f"color:{color};font-size:18px;font-weight:800;background:transparent;")
            lbl_w = QLabel(label)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_w.setStyleSheet(
                "color:rgba(150,160,180,0.5);font-size:7px;letter-spacing:2px;"
                "font-weight:600;background:transparent;")
            v.addWidget(val_w)
            v.addWidget(lbl_w)
            self._vals[key] = val_w
            return w

        def vsep_neon():
            s = QFrame()
            s.setFrameShape(QFrame.Shape.VLine)
            s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(0,207,255,0.18);border:none;")
            return s

        cols.addWidget(col("wins",   "VICTOIRES", "#00e676"))
        cols.addWidget(vsep_neon())
        cols.addWidget(col("losses", "DÉFAITES",  "#ff3d57"))
        cols.addWidget(vsep_neon())
        cols.addWidget(col("stk",    "STREAK",    "#00e676"))
        root.addLayout(cols)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fond sombre quasi-opaque
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(8, 10, 18, 230)))
        p.drawRoundedRect(0, 0, w, h, 8, 8)

        # Halo cyan centré
        halo = QRadialGradient(w / 2, h * 0.35, w * 0.55)
        halo.setColorAt(0.0, QColor(0, 207, 255, 22))
        halo.setColorAt(1.0, QColor(0, 207, 255, 0))
        p.setBrush(QBrush(halo))
        p.drawRect(0, 0, w, h)

        # Bordure neon cyan
        pen = QPen(QColor(0, 207, 255, 80))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8, 8)

        # Accent de winrate en haut (liseré 3px)
        win_w = max(0, min(w, int(w * self._winrate)))
        p.setPen(Qt.PenStyle.NoPen)
        if win_w > 0:
            g = QLinearGradient(0, 0, win_w, 0)
            g.setColorAt(0.0, QColor("#00e676"))
            g.setColorAt(1.0, QColor("#00b84a"))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(8, 0, win_w - 8, 3), 2, 2)
        if win_w < w:
            g2 = QLinearGradient(win_w, 0, w, 0)
            g2.setColorAt(0.0, QColor("#cc1f2e"))
            g2.setColorAt(1.0, QColor("#ff3d57"))
            p.setBrush(QBrush(g2))
            p.drawRoundedRect(QRectF(win_w, 0, w - win_w - 8, 3), 2, 2)

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
        pm = _get_rank_pixmap(d.get("tier_id", 0), 36)
        if pm:
            self._rank_icon.setPixmap(pm)
        else:
            self._rank_icon.clear()

        self._vals["mmr"].setText(str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#00e676" if chg > 0 else "#ff3d57"
            self._vals["delta"].setText(f"{sign}{chg}")
            self._vals["delta"].setStyleSheet(
                f"color:{clr};font-size:14px;font-weight:700;background:transparent;")
        else:
            self._vals["delta"].setText("")

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




OVERLAY_NAME = 'neon'
OVERLAY_SIZE = (260, 140)
Overlay = _NeonCard
