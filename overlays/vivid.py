"""Auto-généré — overlay plugin pour RL Tracker."""
import sys, os
from PyQt6.QtCore    import Qt, QTimer, QRectF, QByteArray, QPointF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QStackedWidget
from PyQt6.QtGui     import (QColor, QPainter, QBrush, QPen, QLinearGradient,
                              QRadialGradient, QFont, QPolygonF, QCursor, QPixmap)
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

# ── Rank icon — réutilise le helper de overlay_widgets si dispo ───────────────
_RANK_FOLDER = os.path.join(BASE_DIR, "all rank")
_rank_pixmap_cache: dict = {}

def _get_rank_pixmap(tier_id: int, size: int = 24):
    """Charge et met en cache l'icône de rang depuis le dossier 'all rank'."""
    key = (tier_id, size)
    if key in _rank_pixmap_cache:
        return _rank_pixmap_cache[key]
    path = os.path.join(_RANK_FOLDER, f"{tier_id}.png")
    if os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            scaled = pm.scaled(size, size,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
            _rank_pixmap_cache[key] = scaled
            return scaled
    _rank_pixmap_cache[key] = None
    return None

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

class _VividCard(QWidget):
    """Overlay vivid gradient — 400×78, couleurs saturées, moderne, 4 colonnes."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 78)
        self._vals    = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(0)

        # 4 blocs colorés côte à côte
        cols = QHBoxLayout(); cols.setSpacing(2); cols.setContentsMargins(2, 0, 2, 2)

        block_defs = [
            ("mmr",    "MMR",    "#0a1830", "#60d0ff"),
            ("delta",  "DELTA",  "#0a1a10", "#60ffaa"),
            ("wins",   "WINS",   "#101a0a", "#a0ff70"),
            ("losses", "LOSSES", "#1a0a0a", "#ff7090"),
            ("stk",    "STREAK", "#100a1a", "#c080ff"),
        ]

        for key, label, bg_col, val_col in block_defs:
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet(f"background:{bg_col};border-radius:6px;")
            v = QVBoxLayout(w); v.setContentsMargins(6, 5, 6, 5); v.setSpacing(1)

            if key == "mmr":
                # ── Bloc MMR : [icône 34×34] + [valeur MMR] côte à côte ────
                row = QHBoxLayout(); row.setSpacing(5); row.setContentsMargins(0, 0, 0, 0)
                rank_icon = QLabel()
                rank_icon.setFixedSize(34, 34)
                rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
                rank_icon.setStyleSheet("background:transparent;")
                self._vals["rank_icon"] = rank_icon
                row.addWidget(rank_icon)
                val_w = QLabel("--")
                val_w.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                val_w.setStyleSheet(
                    f"color:{val_col};font-size:17px;font-weight:900;background:transparent;")
                row.addWidget(val_w)
                v.addLayout(row)
                lbl_w = QLabel(label)
                lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_w.setStyleSheet(
                    f"color:{val_col}80;font-size:7px;letter-spacing:1.5px;"
                    "font-weight:700;background:transparent;")
                v.addWidget(lbl_w)
            else:
                val_w = QLabel("--")
                val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
                val_w.setStyleSheet(
                    f"color:{val_col};font-size:17px;font-weight:900;background:transparent;")
                lbl_w = QLabel(label)
                lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_w.setStyleSheet(
                    f"color:{val_col}80;font-size:7px;letter-spacing:1.5px;"
                    "font-weight:700;background:transparent;")
                v.addWidget(val_w); v.addWidget(lbl_w)
            self._vals[key] = val_w
            self._vals[f"_{key}_color"] = val_col
            cols.addWidget(w)

        root.addLayout(cols)

        # Titre ultra-fin en haut
        title_row = QHBoxLayout(); title_row.setContentsMargins(6, 0, 6, 2)
        t = QLabel("RL TRACKER  ·  RANKED")
        t.setStyleSheet(
            "color:rgba(255,255,255,0.18);font-size:6px;letter-spacing:2px;"
            "font-weight:600;background:transparent;")
        title_row.addWidget(t); title_row.addStretch()
        wr_lbl = QLabel("WR: --%")
        wr_lbl.setStyleSheet(
            "color:rgba(255,255,255,0.18);font-size:6px;letter-spacing:1px;"
            "font-weight:600;background:transparent;")
        self._vals["wr_lbl"] = wr_lbl
        title_row.addWidget(wr_lbl)
        root.insertLayout(0, title_row)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        # Fond global très sombre
        p.setBrush(QBrush(QColor(6, 8, 14, 200)))
        p.drawRoundedRect(0, 0, w, h, 8, 8)
        p.end()

    def update_stats(self, d, mmr_mode="both"):
        mmr    = d.get("mmr")
        chg    = d.get("mmr_change", 0)
        sv     = d.get("streak_val", 0)
        st     = d.get("streak_type", "")
        wins   = d.get("wins", 0)
        losses = d.get("losses", 0)
        tier   = d.get("tier_id", 0)        # ← tier_id pour l'icône de rang
        total  = wins + losses
        wr = (wins / total * 100) if total > 0 else None
        self._winrate = (wins / total) if total > 0 else 0.5

        # ── Icône de rang ──────────────────────────────────────────────────
        rank_icon_lbl = self._vals.get("rank_icon")
        if rank_icon_lbl is not None:
            pm = _get_rank_pixmap(tier, size=34)
            if pm:
                rank_icon_lbl.setPixmap(pm)
                rank_icon_lbl.setVisible(True)
            else:
                rank_icon_lbl.clear()
                rank_icon_lbl.setVisible(False)

        # ── MMR ────────────────────────────────────────────────────────────
        self._vals["mmr"].setText(str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))

        # ── Delta ──────────────────────────────────────────────────────────
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#60ffaa" if chg > 0 else "#ff7090"
            self._vals["delta"].setText(f"{sign}{chg}")
            self._vals["delta"].setStyleSheet(
                f"color:{clr};font-size:17px;font-weight:900;background:transparent;")
        else:
            self._vals["delta"].setText("--" if mmr_mode != "mmr" else "")

        # ── Wins / Losses ──────────────────────────────────────────────────
        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))

        # ── Streak ────────────────────────────────────────────────────────
        if sv > 0:
            clr = "#a0ff70" if st == "win" else "#ff7090"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(
                f"color:{clr};font-size:17px;font-weight:900;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(
                "color:#c080ff;font-size:17px;font-weight:900;background:transparent;")

        # ── Win rate ──────────────────────────────────────────────────────
        if wr is not None:
            self._vals["wr_lbl"].setText(f"WR: {wr:.0f}%")


OVERLAY_NAME = 'vivid'
OVERLAY_SIZE = (400, 78)
Overlay = _VividCard