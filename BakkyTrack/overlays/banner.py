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

class _BannerCard(QWidget):
    """Overlay bannière redesigné :
    - barre de winrate verte/rouge en haut (dynamique)
    - 4 colonnes : MMR, WIN, LOSS, STREAK
    - coin bas-droit coupé style RL
    """
    CORNER = 22   # taille de la découpe d'angle
    BAR_H  = 6    # hauteur de la barre winrate

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(440, 68)
        self._winrate = 0.5   # 0.0 → 1.0, mis à jour via update_stats
        self._vals    = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, self.BAR_H + 2, 0, 0)
        root.setSpacing(0)

        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        content.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(content)
        lay.setContentsMargins(24, 6, 24 + self.CORNER, 6)
        lay.setSpacing(0)

        def block(key, label_txt, color_val, color_delta=None):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(1)

            lbl = QLabel(label_txt)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "color:rgba(180,180,180,0.55);font-size:8px;"
                "letter-spacing:2.5px;font-weight:600;background:transparent;")

            val = QLabel("--")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(
                f"color:{color_val};font-size:16px;font-weight:800;"
                "background:transparent;")

            v.addWidget(lbl)
            v.addWidget(val)
            self._vals[key] = val

            if color_delta is not None:
                delta = QLabel("")
                delta.setAlignment(Qt.AlignmentFlag.AlignCenter)
                delta.setStyleSheet(
                    f"color:{color_delta};font-size:10px;font-weight:700;"
                    "background:transparent;")
                v.addWidget(delta)
                self._vals[key + "_delta"] = delta

            return w

        def vsep():
            s = QFrame()
            s.setFrameShape(QFrame.Shape.VLine)
            s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(160,30,30,0.7);border:none;")
            return s

        lay.addWidget(block("mmr",    "MMR",    "#00cfff", "#888888"))
        lay.addWidget(vsep())
        lay.addWidget(block("wins",   "WIN",    "#00e676"))
        lay.addWidget(vsep())
        lay.addWidget(block("losses", "LOSS",   "#ff3d57"))
        lay.addWidget(vsep())
        lay.addWidget(block("stk",    "STREAK", "#00e676"))

        root.addWidget(content)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        c = self.CORNER

        # ── Corps principal (fond sombre avec coin coupé) ─────────────────
        body = QPolygonF([
            QPointF(0,     self.BAR_H),
            QPointF(w,     self.BAR_H),
            QPointF(w,     h - c),
            QPointF(w - c, h),
            QPointF(0,     h),
        ])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#252525")))
        p.drawPolygon(body)

        # ── Bordure subtile ───────────────────────────────────────────────
        pen = QPen(QColor("#383838"))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(body)

        # ── Barre winrate (verte → rouge selon ratio) ─────────────────────
        p.setPen(Qt.PenStyle.NoPen)
        win_w = max(0, min(w, int(w * self._winrate)))

        if win_w > 0:
            g = QLinearGradient(0, 0, win_w, 0)
            g.setColorAt(0.0, QColor("#00e676"))
            g.setColorAt(1.0, QColor("#00b84a"))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(0, 0, win_w, self.BAR_H), 2, 2)

        if win_w < w:
            g2 = QLinearGradient(win_w, 0, w, 0)
            g2.setColorAt(0.0, QColor("#cc1f2e"))
            g2.setColorAt(1.0, QColor("#ff3d57"))
            p.setBrush(QBrush(g2))
            p.drawRoundedRect(QRectF(win_w, 0, w - win_w, self.BAR_H), 2, 2)

        # ── Reflet léger en haut du corps ─────────────────────────────────
        shine = QLinearGradient(0, self.BAR_H, 0, self.BAR_H + 18)
        shine.setColorAt(0.0, QColor(255, 255, 255, 14))
        shine.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shine))
        p.drawPolygon(body)

        p.end()

    def update_stats(self, d, mmr_mode="both"):
        mmr = d.get("mmr")
        chg = d.get("mmr_change", 0)
        sv  = d.get("streak_val", 0)
        st  = d.get("streak_type", "")
        wins   = d.get("wins", 0)
        losses = d.get("losses", 0)
        total  = wins + losses

        # Winrate pour la barre
        self._winrate = (wins / total) if total > 0 else 0.5
        self.update()   # repaint

        # MMR
        mmr_txt = str(mmr) if mmr and mmr_mode != "delta" else ("--" if mmr_mode != "delta" else "")
        self._vals["mmr"].setText(mmr_txt)

        # Delta sous MMR
        if "mmr_delta" in self._vals:
            if chg and mmr:
                sign = "+" if chg > 0 else ""
                clr  = "#00e676" if chg > 0 else "#ff3d57"
                self._vals["mmr_delta"].setText(f"{sign}{chg}")
                self._vals["mmr_delta"].setStyleSheet(
                    f"color:{clr};font-size:9px;font-weight:700;background:transparent;")
            else:
                self._vals["mmr_delta"].setText("")

        # WIN / LOSS
        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))

        # STREAK
        if sv > 0:
            clr = "#00e676" if st == "win" else "#ff3d57"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(
                f"color:{clr};font-size:16px;font-weight:800;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(
                "color:#00e676;font-size:16px;font-weight:800;background:transparent;")




OVERLAY_NAME = 'banner'
OVERLAY_SIZE = (440, 68)
Overlay = _BannerCard
