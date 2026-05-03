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

class _ScoreboardCard(QWidget):
    """Overlay scoreboard style Rocket League — 380×88, Blue vs Orange."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 88)
        self._vals    = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Barre top : Wins vs Losses ──────────────────────────────────────
        top = QWidget()
        top.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        top.setFixedHeight(32)
        top.setStyleSheet("background:transparent;")
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(0)

        # Bloc BLUE (wins)
        blue_w = QWidget()
        blue_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        bl = QHBoxLayout(blue_w); bl.setContentsMargins(14, 4, 8, 4)
        lbl_b = QLabel("BLUE")
        lbl_b.setStyleSheet("color:#7ac4ff;font-size:8px;font-weight:700;letter-spacing:2px;background:transparent;")
        val_b = QLabel("0")
        val_b.setStyleSheet("color:#ffffff;font-size:16px;font-weight:900;background:transparent;")
        bl.addWidget(lbl_b); bl.addStretch(); bl.addWidget(val_b)
        self._vals["wins"] = val_b

        # VS
        vs = QLabel("VS")
        vs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vs.setFixedWidth(36)
        vs.setStyleSheet("color:rgba(200,210,230,0.4);font-size:9px;font-weight:700;letter-spacing:2px;background:transparent;")

        # Bloc ORANGE (losses)
        org_w = QWidget()
        org_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ol = QHBoxLayout(org_w); ol.setContentsMargins(8, 4, 14, 4)
        val_o = QLabel("0")
        val_o.setStyleSheet("color:#ffffff;font-size:16px;font-weight:900;background:transparent;")
        lbl_o = QLabel("ORG")
        lbl_o.setStyleSheet("color:#ffb347;font-size:8px;font-weight:700;letter-spacing:2px;background:transparent;")
        ol.addWidget(val_o); ol.addStretch(); ol.addWidget(lbl_o)
        self._vals["losses"] = val_o

        top_lay.addWidget(blue_w, 1)
        top_lay.addWidget(vs)
        top_lay.addWidget(org_w, 1)
        root.addWidget(top)

        # ── Séparateur ──────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:rgba(255,255,255,0.08);border:none;")
        root.addWidget(sep)

        # ── Bas : MMR, DELTA, STREAK ─────────────────────────────────────
        bot = QWidget()
        bot.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        bot_lay = QHBoxLayout(bot); bot_lay.setContentsMargins(14, 4, 14, 4)
        bot_lay.setSpacing(0)

        def mini_block(key, label, color):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
            val_w = QLabel("--")
            val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_w.setStyleSheet(f"color:{color};font-size:15px;font-weight:800;background:transparent;")
            lbl_w = QLabel(label)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_w.setStyleSheet("color:rgba(160,170,190,0.45);font-size:7px;letter-spacing:1.5px;font-weight:600;background:transparent;")
            v.addWidget(val_w); v.addWidget(lbl_w)
            self._vals[key] = val_w
            return w

        def vsep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine); s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(255,255,255,0.08);border:none;")
            return s

        bot_lay.addWidget(mini_block("mmr",   "MMR",    "#00cfff"))
        bot_lay.addWidget(vsep())
        bot_lay.addWidget(mini_block("delta",  "DELTA",  "#aaaaaa"))
        bot_lay.addWidget(vsep())
        bot_lay.addWidget(mini_block("stk",   "STREAK", "#00e676"))
        root.addWidget(bot)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        wr = self._winrate

        # Fond split Blue | Orange
        half = int(w * wr)
        p.setPen(Qt.PenStyle.NoPen)
        # Côté bleu (wins)
        gb = QLinearGradient(0, 0, half, 0)
        gb.setColorAt(0.0, QColor(10, 40, 80, 210))
        gb.setColorAt(1.0, QColor(15, 30, 60, 180))
        p.setBrush(QBrush(gb))
        p.drawRoundedRect(QRectF(0, 0, half + 8, h), 8, 8)

        # Côté orange (losses)
        go = QLinearGradient(half, 0, w, 0)
        go.setColorAt(0.0, QColor(80, 35, 10, 180))
        go.setColorAt(1.0, QColor(100, 45, 10, 210))
        p.setBrush(QBrush(go))
        p.drawRoundedRect(QRectF(half - 8, 0, w - half + 8, h), 8, 8)

        # Zone centrale neutre (bas MMR/delta/stk) — overlay
        p.setBrush(QBrush(QColor(10, 12, 20, 60)))
        p.drawRoundedRect(QRectF(0, 33, w, h - 33), 0, 0)

        # Bordure
        pen = QPen(QColor(60, 70, 100, 120))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 8, 8)

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

        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))
        self._vals["mmr"].setText(str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))

        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#00e676" if chg > 0 else "#ff3d57"
            self._vals["delta"].setText(f"{sign}{chg}")
            self._vals["delta"].setStyleSheet(f"color:{clr};font-size:15px;font-weight:800;background:transparent;")
        else:
            self._vals["delta"].setText("--" if mmr_mode != "mmr" else "")
            self._vals["delta"].setStyleSheet("color:#555;font-size:15px;font-weight:800;background:transparent;")

        if sv > 0:
            clr = "#00e676" if st == "win" else "#ff3d57"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(f"color:{clr};font-size:15px;font-weight:800;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet("color:#00e676;font-size:15px;font-weight:800;background:transparent;")




OVERLAY_NAME = 'scoreboard'
OVERLAY_SIZE = (380, 88)
Overlay = _ScoreboardCard
