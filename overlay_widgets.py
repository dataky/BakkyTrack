"""
overlay_widgets.py — Tous les widgets overlay de RL Tracker.
Importé par rl_tracker.py : from overlay_widgets import *
"""
import os, sys, time
from PyQt6.QtCore    import Qt, QTimer, QRectF, QByteArray, QPointF, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QCheckBox, QStackedWidget
)
from PyQt6.QtGui import (
    QColor, QCursor, QPainter, QBrush, QPen, QLinearGradient, QRadialGradient,
    QFont, QPolygonF
)
from PyQt6.QtSvg import QSvgRenderer

# ── Couleurs (partagées avec rl_tracker.py) ──────────────────────────────────
C_BG    = "#0A0C10"
C_BG2   = "#12151C"
C_BG3   = "#1A1E2A"
C_BLUE  = "#1A8CFF"
C_ORG   = "#FF6B00"
C_TEXT  = "#E8ECF4"
C_MUTE  = "#5A6275"
C_GREEN = "#3AE08A"
C_GOLD  = "#FFD700"

# ── BASE_DIR (résolu au runtime) ──────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Helpers UI ────────────────────────────────────────────────────────────────
def card(parent=None, bg=C_BG2):
    f = QFrame(parent)
    f.setStyleSheet(f"QFrame{{background:{bg};border-radius:6px;}}")
    return f

def lbl(text, color=C_MUTE, size=9, bold=False, parent=None):
    w = QLabel(text, parent)
    weight = "700" if bold else "400"
    w.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{weight};"
                    f"background:transparent;letter-spacing:1px;")
    return w

def btn(text, bg=C_BG3, fg=C_TEXT, size=10, bold=True, parent=None):
    from PyQt6.QtWidgets import QPushButton
    w = QPushButton(text, parent)
    w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    weight = "700" if bold else "400"
    w.setStyleSheet(f"""
        QPushButton{{background:{bg};color:{fg};border:none;border-radius:4px;
                     padding:5px 12px;font-size:{size}px;font-weight:{weight};}}
        QPushButton:hover{{background:{bg}cc;}}
        QPushButton:pressed{{background:{bg}99;}}
    """)
    return w

def hsep(parent=None):
    s = QFrame(parent)
    s.setFrameShape(QFrame.Shape.HLine)
    s.setFixedHeight(1)
    s.setStyleSheet(f"background:{C_BG3};border:none;")
    return s

#  SVG BACKGROUNDS — chargement depuis themes/
# ─────────────────────────────────────────────────────────────────────────────
THEMES_DIR  = os.path.join(BASE_DIR, "themes")
_THEME_NAMES = ["rl_classic", "victory", "defeat", "neon", "dark_minimal"]

def _load_svg(name: str) -> bytes:
    path = os.path.join(THEMES_DIR, f"{name}.svg")
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return b""

SVG_BACKGROUNDS = {n: _load_svg(n) for n in _THEME_NAMES}


class SvgBackground(QWidget):
    """Widget qui dessine un SVG en fond et contient les autres widgets par-dessus.
    C'est lui qui est le central widget — pas QMainWindow directement."""
    def __init__(self, svg_name="dark_minimal", parent=None):
        super().__init__(parent)
        self._renderer = QSvgRenderer()
        self.set_theme(svg_name)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._inner_lay = lay

    def set_theme(self, name: str):
        data = SVG_BACKGROUNDS.get(name, b"")
        if data:
            self._renderer.load(QByteArray(data))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self._renderer.isValid():
            self._renderer.render(p, QRectF(self.rect()))
        else:
            # Fallback fond sombre si SVG absent
            p.fillRect(self.rect(), QColor(10, 12, 18))
        p.end()

    def add_widget(self, w):
        self._inner_lay.addWidget(w)


class ResultOverlay(QWidget):
    """Overlay plein écran animé victoire/défaite."""
    FADE_IN  = 20
    HOLD     = 65
    FADE_OUT = 30
    FRAME_MS = 30

    def __init__(self):
        super().__init__(None,
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint  |
            Qt.WindowType.Tool                 |
            Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._renderer = QSvgRenderer()
        self._alpha = 0.0; self._scale = 0.85
        self._step = 0;    self._result = "win"
        self._phase = "idle"
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.hide()

    def show_result(self, result: str, theme: str = "auto"):
        self._result = result
        svg_key = ("victory" if result == "win" else "defeat") if theme == "auto" else theme
        data = SVG_BACKGROUNDS.get(svg_key, b"")
        if data:
            self._renderer.load(QByteArray(data))
        else:
            self._renderer = QSvgRenderer()   # renderer vide → fallback couleur

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._step = 0; self._alpha = 0.0; self._scale = 0.82; self._phase = "fadein"
        self.show(); self.raise_()
        self._timer.start(self.FRAME_MS)

    def _tick(self):
        self._step += 1
        if self._phase == "fadein":
            t = min(1.0, self._step / self.FADE_IN)
            self._alpha = t; self._scale = 0.82 + 0.18 * t
            if self._step >= self.FADE_IN: self._phase = "hold"; self._step = 0
        elif self._phase == "hold":
            self._alpha = 1.0; self._scale = 1.0
            if self._step >= self.HOLD: self._phase = "fadeout"; self._step = 0
        elif self._phase == "fadeout":
            t = min(1.0, self._step / self.FADE_OUT)
            self._alpha = 1.0 - t
            if self._step >= self.FADE_OUT:
                self._timer.stop(); self._phase = "idle"; self.hide(); return
        self.update()

    def paintEvent(self, event):
        if self._phase == "idle": return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        is_win = self._result == "win"
        color  = QColor("#00e676" if is_win else "#ff3d57")

        # ── Fond : SVG si dispo, sinon dégradé couleur ────────────────────
        p.setOpacity(self._alpha * 0.93)
        if self._renderer.isValid():
            self._renderer.render(p, QRectF(0, 0, w, h))
        else:
            # Fallback : dégradé sombre coloré
            bg_col = QColor("#011a0a" if is_win else "#1a0101")
            p.fillRect(self.rect(), bg_col)
            g = QLinearGradient(w / 2, 0, w / 2, h)
            glow = QColor(color); glow.setAlpha(40)
            g.setColorAt(0.0, QColor(0, 0, 0, 0))
            g.setColorAt(0.5, glow)
            g.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(self.rect(), QBrush(g))
        text   = "VICTOIRE" if is_win else "DÉFAITE"
        p.setOpacity(self._alpha)
        p.save()
        p.translate(w / 2, h / 2); p.scale(self._scale, self._scale); p.translate(-w / 2, -h / 2)
        halo = QColor(color); halo.setAlpha(int(35 * self._alpha))
        p.setBrush(QBrush(halo)); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(w/2 - 260, h/2 - 85, 520, 170))
        f = QFont(); f.setPointSize(72); f.setWeight(QFont.Weight.Black)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 10)
        p.setFont(f)
        p.setPen(QColor(0, 0, 0, int(160 * self._alpha)))
        p.drawText(QRectF(3, h/2 - 55 + 4, w, 110), Qt.AlignmentFlag.AlignHCenter, text)
        txt_col = QColor(color); txt_col.setAlpha(int(255 * self._alpha))
        p.setPen(txt_col)
        p.drawText(QRectF(0, h/2 - 55, w, 110), Qt.AlignmentFlag.AlignHCenter, text)
        f2 = QFont(); f2.setPointSize(14); f2.setWeight(QFont.Weight.Bold)
        f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        p.setFont(f2)
        p.setPen(QColor(255, 255, 255, int(150 * self._alpha)))
        sub = "BIEN JOUÉ !" if is_win else "LA PROCHAINE FOIS"
        p.drawText(QRectF(0, h/2 + 55, w, 40), Qt.AlignmentFlag.AlignHCenter, sub)
        p.restore()
        border = QColor(color); border.setAlpha(int(200 * self._alpha))
        p.setPen(QPen(border, 3)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(0, 0, w, 0); p.drawLine(0, h-1, w, h-1)
        p.end()


# ─────────────────────────────────────────────────────────────────────────────
#  OVERLAY WIDGETS
# ─────────────────────────────────────────────────────────────────────────────
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


class _CompactCard(_GlassCard):
    def __init__(self):
        super().__init__()
        self.setFixedSize(224, 172)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 12)
        lay.setSpacing(6)

        # Ligne MMR avec delta à côté
        mmr_row = QHBoxLayout()
        mmr_lbl_w = QLabel("MMR")
        mmr_lbl_w.setStyleSheet(f"color:{C_MUTE};font-size:9px;letter-spacing:1.2px;background:transparent;")
        self.v_delta = QLabel("")
        self.v_delta.setStyleSheet(f"color:{C_GREEN};font-size:11px;font-weight:700;background:transparent;")
        self.v_mmr = QLabel("--")
        self.v_mmr.setStyleSheet(f"color:{C_GOLD};font-size:18px;font-weight:700;background:transparent;")
        mmr_row.addWidget(mmr_lbl_w); mmr_row.addStretch()
        mmr_row.addWidget(self.v_delta); mmr_row.addSpacing(5)
        mmr_row.addWidget(self.v_mmr)
        lay.addLayout(mmr_row)
        lay.addWidget(hsep())

        def row(lbl_txt, val_color, size=16):
            r = QHBoxLayout()
            l = QLabel(lbl_txt)
            l.setStyleSheet(f"color:{C_MUTE};font-size:9px;letter-spacing:1.2px;background:transparent;")
            v = QLabel("--")
            v.setStyleSheet(f"color:{val_color};font-size:{size}px;font-weight:700;background:transparent;")
            r.addWidget(l); r.addStretch(); r.addWidget(v)
            return r, v

        r2, self.v_stk    = row("STREAK", C_GREEN)
        lay.addLayout(r2);  lay.addWidget(hsep())
        r3, self.v_wins   = row("WINS",   C_BLUE)
        lay.addLayout(r3)
        r4, self.v_losses = row("LOSSES", C_ORG)
        lay.addLayout(r4)

    def update_stats(self, d, mmr_mode="both"):
        mmr = d.get("mmr")
        chg = d.get("mmr_change", 0)
        sv  = d.get("streak_val", 0)
        st  = d.get("streak_type", "")

        if mmr_mode == "delta":
            self.v_mmr.setText("")
            if chg:
                sign = "+" if chg > 0 else ""
                clr  = C_GREEN if chg > 0 else C_ORG
                self.v_delta.setText(f"{sign}{chg}")
                self.v_delta.setStyleSheet(f"color:{clr};font-size:18px;font-weight:700;background:transparent;")
            else:
                self.v_delta.setText("--")
                self.v_delta.setStyleSheet(f"color:{C_MUTE};font-size:18px;font-weight:700;background:transparent;")
        elif mmr_mode == "mmr":
            self.v_mmr.setText(str(mmr) if mmr else "--")
            self.v_delta.setText("")
        else:  # both
            self.v_mmr.setText(str(mmr) if mmr else "--")
            if chg and mmr:
                sign = "+" if chg > 0 else ""
                clr  = C_GREEN if chg > 0 else C_ORG
                self.v_delta.setText(f"{sign}{chg}")
                self.v_delta.setStyleSheet(f"color:{clr};font-size:11px;font-weight:700;background:transparent;")
            else:
                self.v_delta.setText("")

        self.v_wins.setText(str(d.get("wins", 0)))
        self.v_losses.setText(str(d.get("losses", 0)))
        if sv > 0:
            clr = C_GREEN if st == "win" else C_ORG
            self.v_stk.setText(f"{'+'if st=='win'else'-'}{sv}")
            self.v_stk.setStyleSheet(f"color:{clr};font-size:16px;font-weight:700;background:transparent;")
        else:
            self.v_stk.setText("--")
            self.v_stk.setStyleSheet(f"color:{C_GREEN};font-size:16px;font-weight:700;background:transparent;")


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


class _BannerClassicCard(_GlassCard):
    """Ancienne bannière horizontale simple (380×62) — 5 blocs égaux."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(380, 62)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 8)
        lay.setSpacing(0)
        self._vals = {}

        def block(key, lbl_txt, color):
            w = QWidget(); w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(1)
            l = QLabel(lbl_txt); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet(f"color:{C_MUTE};font-size:8px;letter-spacing:1px;background:transparent;")
            val = QLabel("--"); val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(f"color:{color};font-size:15px;font-weight:700;background:transparent;")
            v.addWidget(l); v.addWidget(val)
            self._vals[key] = val
            return w

        def vsep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine); s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(255,255,255,0.12);border:none;")
            return s

        lay.addWidget(block("mmr",    "MMR",    C_GOLD))
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


class _PillCard(QWidget):
    """Overlay pill ultra-compact : barre horizontale fine 340×36.
    Idéal pour un stream épuré — quasi invisible, toujours lisible."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(340, 36)
        self._vals = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(0)

        def seg(key, label, color, stretch=1):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet("background:transparent;")
            h = QHBoxLayout(w)
            h.setContentsMargins(8, 0, 8, 0)
            h.setSpacing(4)
            lbl_w = QLabel(label)
            lbl_w.setStyleSheet(
                "color:rgba(160,170,190,0.55);font-size:8px;"
                "letter-spacing:1.5px;font-weight:600;background:transparent;")
            val_w = QLabel("--")
            val_w.setStyleSheet(
                f"color:{color};font-size:13px;font-weight:800;background:transparent;")
            h.addWidget(lbl_w)
            h.addWidget(val_w)
            self._vals[key] = val_w
            return w

        def dot():
            d = QLabel("·")
            d.setStyleSheet("color:rgba(100,100,120,0.6);font-size:18px;background:transparent;")
            return d

        lay.addWidget(seg("mmr",    "MMR",    "#00cfff"))
        lay.addWidget(dot())
        lay.addWidget(seg("delta",  "±",      "#aaaaaa"))
        lay.addWidget(dot())
        lay.addWidget(seg("wins",   "W",      "#00e676"))
        lay.addWidget(dot())
        lay.addWidget(seg("losses", "L",      "#ff3d57"))
        lay.addWidget(dot())
        lay.addWidget(seg("stk",    "STK",    "#00e676"))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fond en capsule semi-transparente
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(18, 20, 30, 210)))
        p.drawRoundedRect(0, 0, w, h, h // 2, h // 2)

        # Liseré winrate en bas (4px)
        win_w = max(0, min(w, int(w * self._winrate)))
        r = h // 2
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

        # Contour subtil
        pen = QPen(QColor(60, 70, 100, 120))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)
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


class _TickerCard(QWidget):
    """Overlay ticker TV — bande défilante 640×26, style chaîne sportive."""

    SPEED_PX = 1   # pixels par frame

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(640, 26)
        self._text   = "MMR: --   |   0W  0L   |   STREAK: --   |   WIN RATE: --%"
        self._offset = 0
        self._fm_w   = 0   # largeur du texte mesuré
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self):
        self._offset -= self.SPEED_PX
        if self._fm_w > 0 and self._offset < -self._fm_w - 60:
            self._offset = self.width()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fond dark avec bordure accent
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(8, 10, 18, 235)))
        p.drawRoundedRect(0, 0, w, h, 3, 3)

        # Accent bleu à gauche (badge "LIVE")
        g = QLinearGradient(0, 0, 56, 0)
        g.setColorAt(0.0, QColor("#1A8CFF"))
        g.setColorAt(1.0, QColor("#0a3a6e"))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(0, 0, 56, h, 3, 3)

        # Texte "RL" dans le badge
        p.setPen(QColor(255, 255, 255, 230))
        f_badge = QFont(); f_badge.setPointSize(8); f_badge.setWeight(QFont.Weight.Black)
        f_badge.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        p.setFont(f_badge)
        p.drawText(QRectF(0, 0, 56, h), Qt.AlignmentFlag.AlignCenter, "RL")

        # Séparateur vertical
        p.setPen(QPen(QColor(40, 80, 160, 140), 1))
        p.drawLine(56, 0, 56, h)

        # Zone de scroll — clipping à partir de x=64
        p.setClipRect(QRectF(64, 0, w - 64, h))
        f_text = QFont(); f_text.setPointSize(9); f_text.setWeight(QFont.Weight.Bold)
        f_text.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        p.setFont(f_text)

        fm = p.fontMetrics()
        self._fm_w = fm.horizontalAdvance(self._text)
        if self._offset == 0:
            self._offset = w  # démarre hors écran

        # Colorer segments du texte (vert pour wins, rouge pour losses)
        x = self._offset + 64
        parts = self._text.split("   |   ")
        colors = ["#00cfff", "#00e676", "#ff3d57" if parts[1].split("W")[0].strip() == "0" else "#00e676", "#aaaaaa", "#FFD700"]
        col_cycle = ["#00cfff", "#e8ecf4", "#e8ecf4", "#aaaaaa"]
        for i, part in enumerate(parts):
            clr = col_cycle[i % len(col_cycle)]
            p.setPen(QColor(clr))
            p.drawText(QPointF(x, h - 7), part)
            x += fm.horizontalAdvance(part)
            if i < len(parts) - 1:
                p.setPen(QColor(60, 80, 120, 180))
                p.drawText(QPointF(x, h - 7), "   |   ")
                x += fm.horizontalAdvance("   |   ")

        p.setClipping(False)

        # Dégradé de fondu sur les bords droite et gauche
        fade_l = QLinearGradient(64, 0, 96, 0)
        fade_l.setColorAt(0.0, QColor(8, 10, 18, 235))
        fade_l.setColorAt(1.0, QColor(8, 10, 18, 0))
        p.setBrush(QBrush(fade_l))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(64, 0, 32, h))

        fade_r = QLinearGradient(w - 32, 0, w, 0)
        fade_r.setColorAt(0.0, QColor(8, 10, 18, 0))
        fade_r.setColorAt(1.0, QColor(8, 10, 18, 235))
        p.setBrush(QBrush(fade_r))
        p.drawRect(QRectF(w - 32, 0, 32, h))

        # Liseré bleu en bas
        p.setBrush(QBrush(QColor("#1A8CFF")))
        p.drawRect(QRectF(0, h - 2, w, 2))

        p.end()

    def update_stats(self, d, mmr_mode="both"):
        mmr  = d.get("mmr")
        chg  = d.get("mmr_change", 0)
        sv   = d.get("streak_val", 0)
        st   = d.get("streak_type", "")
        wins = d.get("wins", 0)
        losses = d.get("losses", 0)
        total  = wins + losses
        wr   = f"{wins / total * 100:.0f}%" if total > 0 else "--%"

        mmr_str = str(mmr) if mmr else "--"
        delta_str = ""
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            delta_str = f" ({sign}{chg})"

        stk_str = f"{'+'if st=='win'else'-'}{sv}" if sv > 0 else "--"
        self._text = (
            f"MMR: {mmr_str}{delta_str}"
            f"   |   {wins}W  {losses}L"
            f"   |   STREAK: {stk_str}"
            f"   |   WIN RATE: {wr}"
            f"   |   "
        )


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

        # 4 colonnes
        cols = QHBoxLayout(); cols.setSpacing(0)

        def col(key, label, color):
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)
            val_w = QLabel("--")
            val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_w.setStyleSheet(
                f"color:{color};font-size:20px;font-weight:800;background:transparent;")
            lbl_w = QLabel(label)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_w.setStyleSheet(
                "color:rgba(255,255,255,0.4);font-size:7px;letter-spacing:1.5px;"
                "font-weight:600;background:transparent;")
            v.addWidget(val_w); v.addWidget(lbl_w)
            self._vals[key] = val_w
            return w

        def vsep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine); s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(255,255,255,0.12);border:none;")
            return s

        cols.addWidget(col("mmr",    "MMR",    "rgba(255,255,255,0.95)"))
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

        # Fond verre dépoli semi-transparent
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 255, 255, 22)))
        p.drawRoundedRect(0, 0, w, h, 16, 16)

        # Reflet haut (brillance)
        shine = QLinearGradient(0, 0, 0, h * 0.5)
        shine.setColorAt(0.0, QColor(255, 255, 255, 45))
        shine.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(shine))
        p.drawRoundedRect(0, 0, w, h // 2, 16, 16)

        # Bordure lumineuse
        pen = QPen(QColor(255, 255, 255, 60))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 16, 16)

        # Barre winrate en bas
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

        self._vals["mmr"].setText(str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))
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


class _HUDCard(QWidget):
    """Overlay HUD FPS militaire — 320×130, coins découpés, lignes de scan, style ARMA/DayZ."""

    CORNER = 18

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 130)
        self._vals    = {}
        self._winrate = 0.5
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 18)
        root.setSpacing(4)

        # Header
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

        # 2 lignes de stats
        def row_stat(key, label, color, size=18):
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

        root.addLayout(row_stat("mmr_line", "RATING", "#00e650", 18))
        root.addLayout(row_stat("wl_line",  "W/L",    "#b0ffb0", 13))
        root.addLayout(row_stat("stk_line", "STREAK", "#00e650", 13))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        c = self.CORNER

        # Forme hexagonale tronquée (coins coupés en haut-gauche et bas-droite)
        body = QPolygonF([
            QPointF(c, 0),
            QPointF(w, 0),
            QPointF(w, h - c),
            QPointF(w - c, h),
            QPointF(0, h),
            QPointF(0, c),
        ])

        # Fond vert sombre militaire
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(4, 16, 8, 220)))
        p.drawPolygon(body)

        # Lignes de scan horizontales (effet CRT)
        p.setOpacity(0.04)
        p.setBrush(QBrush(QColor("#00e650")))
        for y in range(0, h, 4):
            p.drawRect(QRectF(0, y, w, 1))
        p.setOpacity(1.0)

        # Bordure verte militaire
        pen = QPen(QColor(0, 200, 60, 160))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(body)

        # Coins d'accent (petits L dans les angles)
        accent = QPen(QColor(0, 230, 80, 220))
        accent.setWidth(2)
        p.setPen(accent)
        size_l = 14
        # Haut-gauche
        p.drawLine(c, 0, c + size_l, 0)
        p.drawLine(c, 0, c, size_l)
        # Haut-droite
        p.drawLine(w - size_l, 0, w, 0)
        p.drawLine(w, 0, w, size_l)
        # Bas-gauche
        p.drawLine(0, h - size_l, 0, h)
        p.drawLine(0, h, size_l, h)
        # Bas-droite
        p.drawLine(w - c, h, w - c - size_l + c, h)
        p.drawLine(w - c, h, w, h - c)

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
            v = QVBoxLayout(w); v.setContentsMargins(8, 8, 8, 6); v.setSpacing(2)
            val_w = QLabel("--")
            val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_w.setStyleSheet(
                f"color:{val_col};font-size:17px;font-weight:900;"
                "background:transparent;")
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
        mmr  = d.get("mmr")
        chg  = d.get("mmr_change", 0)
        sv   = d.get("streak_val", 0)
        st   = d.get("streak_type", "")
        wins = d.get("wins", 0)
        losses = d.get("losses", 0)
        total  = wins + losses
        wr = (wins / total * 100) if total > 0 else None
        self._winrate = (wins / total) if total > 0 else 0.5

        self._vals["mmr"].setText(str(mmr) if mmr and mmr_mode != "delta" else ("" if mmr_mode == "delta" else "--"))

        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#60ffaa" if chg > 0 else "#ff7090"
            self._vals["delta"].setText(f"{sign}{chg}")
            self._vals["delta"].setStyleSheet(
                f"color:{clr};font-size:17px;font-weight:900;background:transparent;")
        else:
            self._vals["delta"].setText("--" if mmr_mode != "mmr" else "")

        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))

        if sv > 0:
            clr = "#a0ff70" if st == "win" else "#ff7090"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(
                f"color:{clr};font-size:17px;font-weight:900;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(
                "color:#c080ff;font-size:17px;font-weight:900;background:transparent;")

        if wr is not None:
            self._vals["wr_lbl"].setText(f"WR: {wr:.0f}%")


class _DragLayer(QWidget):
    dbl_clicked = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self.raise_()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        self.dbl_clicked.emit()


def _load_overlay_plugins() -> dict:
    """Charge dynamiquement tous les plugins depuis le dossier overlays/.
    Retourne {name: {"widget": QWidget, "size": (w, h)}}
    """
    import importlib.util, glob
    plugins = {}
    folder = os.path.join(BASE_DIR, "overlays")
    for path in sorted(glob.glob(os.path.join(folder, "*.py"))):
        try:
            spec = importlib.util.spec_from_file_location(
                os.path.splitext(os.path.basename(path))[0], path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            name   = getattr(mod, "OVERLAY_NAME", None)
            size   = getattr(mod, "OVERLAY_SIZE", (224, 172))
            cls    = getattr(mod, "Overlay", None)
            if name and cls:
                plugins[name] = {"widget": cls(), "size": size}
        except Exception as e:
            print(f"[Overlay] Erreur chargement {path}: {e}")
    return plugins


class OverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("background:transparent;")

        cont = QWidget()
        cont.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(cont)

        self._stack   = QStackedWidget(cont)
        # ── Chargement dynamique des plugins ──────────────────────────────
        self._plugins = _load_overlay_plugins()   # {name: {widget, size}}
        for p in self._plugins.values():
            self._stack.addWidget(p["widget"])

        outer = QVBoxLayout(cont)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._stack)

        self._drag = _DragLayer(cont)
        self._drag.dbl_clicked.connect(self.toggle_mode)

        self._svg_renderer = QSvgRenderer()
        self._bg_theme = "dark_minimal"

        self.mode     = next(iter(self._plugins), "compact")
        self.mmr_mode = "both"
        self._stats   = {}
        self._apply_mode()

        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._enforce_topmost)
        self._topmost_timer.start(2000)

    def showEvent(self, e):
        super().showEvent(e)
        self._enforce_topmost()

    def _enforce_topmost(self):
        """Force la fenêtre au-dessus des jeux plein écran via l'API Windows."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0003)
            GWL_EXSTYLE = -20
            ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                ex | 0x00080000 | 0x08000000 | 0x00000008)
        except Exception:
            pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_drag"):
            self._drag.setGeometry(self.centralWidget().rect())

    def available_modes(self) -> list:
        return list(self._plugins.keys())

    def set_mode(self, m):
        self.mode = m; self._apply_mode()

    def set_mmr_mode(self, m):
        self.mmr_mode = m

    def set_bg_theme(self, theme: str):
        self._bg_theme = theme
        data = SVG_BACKGROUNDS.get(theme, b"")
        if data:
            self._svg_renderer.load(QByteArray(data))
        else:
            self._svg_renderer = QSvgRenderer()
        self.update(); self.update_stats(self._stats)

    def toggle_mode(self):
        modes = self.available_modes()
        idx   = modes.index(self.mode) if self.mode in modes else 0
        self.set_mode(modes[(idx + 1) % len(modes)])

    def _apply_mode(self):
        p = self._plugins.get(self.mode) or next(iter(self._plugins.values()), None)
        if p:
            self._stack.setCurrentWidget(p["widget"])
            self.setFixedSize(*p["size"])

    def update_stats(self, stats: dict):
        self._stats = stats
        p = self._plugins.get(self.mode)
        if p and hasattr(p["widget"], "update_stats"):
            p["widget"].update_stats(stats, self.mmr_mode)



# ─────────────────────────────────────────────────────────────────────────────
#  PLAYERS OVERLAY WINDOW  (hotkey F7 par défaut)
# ─────────────────────────────────────────────────────────────────────────────
class PlayersOverlayWindow(QMainWindow):
    """Petit overlay affichant les pseudos des joueurs en match, cliquables."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(210)

        self._players  = []
        self._drag_pos = None

        cont = QWidget()
        cont.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(cont)

        outer = QVBoxLayout(cont)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = _GlassCard()
        self._card_lay = QVBoxLayout(self._card)
        self._card_lay.setContentsMargins(10, 10, 10, 10)
        self._card_lay.setSpacing(4)

        # ── Header ──────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("JOUEURS")
        title.setStyleSheet(
            f"color:{C_MUTE};font-size:8px;font-weight:700;"
            f"letter-spacing:1.5px;background:transparent;")
        hint_lbl = QLabel("clic = tracker")
        hint_lbl.setStyleSheet(
            f"color:{C_BG3};font-size:7px;background:transparent;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{C_MUTE};border:none;font-size:9px;}}"
            f"QPushButton:hover{{color:{C_TEXT};}}")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(title)
        hdr.addSpacing(6)
        hdr.addWidget(hint_lbl)
        hdr.addStretch()
        hdr.addWidget(close_btn)
        self._card_lay.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C_BG3};border:none;")
        self._card_lay.addWidget(sep)

        # ── Liste joueurs ────────────────────────────────────────────────
        self._players_widget = QWidget()
        self._players_widget.setStyleSheet("background:transparent;")
        self._plist = QVBoxLayout(self._players_widget)
        self._plist.setSpacing(1)
        self._plist.setContentsMargins(0, 4, 0, 4)
        self._card_lay.addWidget(self._players_widget)

        outer.addWidget(self._card)

        # Drag sur la carte
        self._card.mousePressEvent  = self._mouse_press
        self._card.mouseMoveEvent   = self._mouse_move
        self._card.mouseReleaseEvent = lambda e: None

        # Topmost timer
        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._enforce_topmost)
        self._topmost_timer.start(2000)

        self._refresh_empty()

    # ── Drag ──────────────────────────────────────────────────────────────
    def _mouse_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _mouse_move(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    # ── Topmost ───────────────────────────────────────────────────────────
    def showEvent(self, e):
        super().showEvent(e)
        self._enforce_topmost()

    def _enforce_topmost(self):
        if sys.platform != "win32" or not self.isVisible():
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0003)
            GWL_EXSTYLE      = -20
            WS_EX_LAYERED    = 0x00080000
            WS_EX_NOACTIVATE = 0x08000000
            ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED | WS_EX_NOACTIVATE)
        except Exception:
            pass

    # ── Données ───────────────────────────────────────────────────────────
    def _clear_plist(self):
        while self._plist.count():
            item = self._plist.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _refresh_empty(self):
        self._clear_plist()
        e = QLabel("Aucun match en cours")
        e.setStyleSheet(f"color:{C_MUTE};font-size:9px;background:transparent;")
        e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._plist.addWidget(e)
        self.adjustSize()

    def update_players(self, players):
        self._players = players
        self._clear_plist()
        if not players:
            e = QLabel("Aucun match en cours")
            e.setStyleSheet(f"color:{C_MUTE};font-size:9px;background:transparent;")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._plist.addWidget(e)
            self.adjustSize()
            return

        blues   = [p for p in players if p.get("TeamNum") == 0]
        oranges = [p for p in players if p.get("TeamNum") == 1]

        for team_name, team_color, team_players in [
            ("🔵  BLUE", C_BLUE, blues),
            ("🟠  ORANGE", C_ORG, oranges),
        ]:
            if not team_players:
                continue
            tl = QLabel(team_name)
            tl.setStyleSheet(
                f"color:{team_color};font-size:8px;font-weight:700;"
                f"letter-spacing:1px;background:transparent;")
            self._plist.addWidget(tl)
            for p in team_players:
                name     = p.get("Name", "?")
                platform = self._platform_from_id(p.get("PrimaryId", ""))
                pb = QPushButton(name)
                pb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                pb.setStyleSheet(f"""
                    QPushButton{{background:transparent;color:{team_color};border:none;
                                 text-align:left;font-size:12px;font-weight:700;
                                 padding:2px 6px;letter-spacing:0.3px;}}
                    QPushButton:hover{{color:{C_TEXT};background:{C_BG3};
                                       border-radius:3px;}}
                """)
                pb.clicked.connect(
                    lambda _, n=name, pl=platform: self._open_profile(n, pl))
                self._plist.addWidget(pb)

        self.adjustSize()

    def _platform_from_id(self, primary_id):
        if primary_id.startswith("Steam|"):   return "steam"
        if primary_id.startswith("Epic|"):    return "epic"
        if primary_id.startswith("PS4|"):     return "ps4"
        if primary_id.startswith("XboxOne|"): return "xbox"
        if primary_id.startswith("Switch|"):  return "switch"
        return "epic"

    def _open_profile(self, name, platform):
        url = (f"https://rocketleague.tracker.network/rocket-league/profile"
               f"/{platform}/{urllib.parse.quote(name)}/overview")
        QDesktopServices.openUrl(QUrl(url))


# ── VK key map pour le hotkey listener ──────────────────────────────────────
_VK_MAP = {
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "space": 0x20, "return": 0x0D, "escape": 0x1B,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "insert": 0x2D, "delete": 0x2E, "tab": 0x09,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "backspace": 0x08,
}

def _key_to_vk(key_str):
    """Convertit une key string (ex: 'key:f7') en VK code Windows."""
    if not key_str:
        return None
    if key_str.startswith("key:"):
        k = key_str[4:].lower()
        if k in _VK_MAP:
            return _VK_MAP[k]
        if len(k) == 1 and k.isalpha():
            return ord(k.upper())
        if len(k) == 1 and k.isdigit():
            return ord(k)
    return None



# ── Re-export _CompactCard pour OverlayTab (preview) ─────────────────────────
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "compact", os.path.join(BASE_DIR, "overlays", "compact.py"))
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _CompactCard = _mod.Overlay
except Exception as _e:
    print(f"[overlay_widgets] Impossible de charger compact.py : {_e}")
    _CompactCard = QWidget  # fallback silencieux