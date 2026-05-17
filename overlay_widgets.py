"""
overlay_widgets.py — Widgets overlay BakkyTrack.
Importé par rl_tracker.py : from overlay_widgets import *
"""
import os, sys, time, urllib.parse
from PyQt6.QtCore    import Qt, QTimer, QRectF, QByteArray, QPointF, pyqtSignal, QUrl
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QCheckBox, QStackedWidget
)
from PyQt6.QtGui import (
    QColor, QCursor, QPainter, QBrush, QPen, QLinearGradient, QRadialGradient,
    QFont, QPolygonF, QDesktopServices
)
from PyQt6.QtSvg import QSvgRenderer

# ── Imports centralisés (plus de duplication) ────────────────────────────────
from style  import C_BG, C_BG2, C_BG3, C_BLUE, C_ORG, C_TEXT, C_MUTE, C_GREEN, C_GOLD
from style  import card, lbl, btn, hsep
from config import BASE_DIR
from utils  import (
    get_rank_pixmap, get_playlist_pixmap, _PLAYLIST_ID_TO_KEY,
    SvgBackground, ResultOverlay, SVG_BACKGROUNDS, enforce_topmost, OverlayStats,
)

# ── (supprimé — code désormais importé depuis style.py, config.py, utils.py) ──


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
        self.setFixedSize(224, 210)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 12)
        lay.setSpacing(6)

        # ── Ligne rang : icône + texte ────────────────────────────────────
        rank_row = QHBoxLayout()
        rank_lbl_w = QLabel("RANG")
        rank_lbl_w.setStyleSheet(
            f"color:{C_MUTE};font-size:9px;letter-spacing:1.2px;background:transparent;")
        self.v_rank_icon = QLabel()
        self.v_rank_icon.setFixedSize(32, 32)
        self.v_rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v_rank_icon.setStyleSheet("background:transparent;")
        self.v_rank_name = QLabel("--")
        self.v_rank_name.setStyleSheet(
            f"color:{C_TEXT};font-size:11px;font-weight:700;background:transparent;")
        rank_row.addWidget(rank_lbl_w)
        rank_row.addStretch()
        rank_row.addWidget(self.v_rank_icon)
        rank_row.addSpacing(4)
        rank_row.addWidget(self.v_rank_name)
        lay.addLayout(rank_row)
        lay.addWidget(hsep())

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

        # ── Rang ──────────────────────────────────────────────────────────
        tier_id   = d.get("tier_id", 0)
        rank_name = d.get("rank", "")
        pm = get_rank_pixmap(tier_id, 30)
        if pm:
            self.v_rank_icon.setPixmap(pm)
        else:
            self.v_rank_icon.setText("?")
            self.v_rank_icon.setStyleSheet(
                f"color:{C_MUTE};font-size:9px;background:transparent;")
        self.v_rank_name.setText(rank_name if rank_name else "Unranked")

        # ── MMR + delta ───────────────────────────────────────────────────
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

        def rank_block():
            w = QWidget()
            w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(2)
            lbl_w = QLabel("RANG")
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_w.setStyleSheet(
                "color:rgba(180,180,180,0.55);font-size:8px;"
                "letter-spacing:2.5px;font-weight:600;background:transparent;")
            icon = QLabel()
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setStyleSheet("background:transparent;")
            v.addWidget(lbl_w); v.addWidget(icon)
            self._vals["rank_icon"] = icon
            return w

        lay.addWidget(rank_block())
        lay.addWidget(vsep())
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

        # Icône de rang
        tier_id = d.get("tier_id", 0)
        if "rank_icon" in self._vals:
            pm = get_rank_pixmap(tier_id, 28)
            if pm:
                self._vals["rank_icon"].setPixmap(pm)
                self._vals["rank_icon"].setText("")
            else:
                self._vals["rank_icon"].setPixmap(
                    __import__("PyQt6.QtGui", fromlist=["QPixmap"]).QPixmap())
                self._vals["rank_icon"].setText("?")

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
    """Ancienne bannière horizontale simple (440×62) — 6 blocs égaux."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(440, 62)
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

        # Bloc rang : icône PNG au-dessus du label
        def rank_block():
            w = QWidget(); w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w); v.setContentsMargins(0,0,0,0); v.setSpacing(1)
            l = QLabel("RANG"); l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.setStyleSheet(f"color:{C_MUTE};font-size:8px;letter-spacing:1px;background:transparent;")
            icon = QLabel(); icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedHeight(26)
            icon.setStyleSheet("background:transparent;")
            v.addWidget(l); v.addWidget(icon)
            self._vals["rank_icon"] = icon
            return w

        def vsep():
            s = QFrame(); s.setFrameShape(QFrame.Shape.VLine); s.setFixedWidth(1)
            s.setStyleSheet("background:rgba(255,255,255,0.12);border:none;")
            return s

        lay.addWidget(rank_block())
        lay.addWidget(vsep())
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

        # Icône de rang
        tier_id = d.get("tier_id", 0)
        pm = get_rank_pixmap(tier_id, 26)
        if "rank_icon" in self._vals:
            if pm:
                self._vals["rank_icon"].setPixmap(pm)
                self._vals["rank_icon"].setText("")
            else:
                self._vals["rank_icon"].setPixmap(
                    __import__("PyQt6.QtGui", fromlist=["QPixmap"]).QPixmap())
                self._vals["rank_icon"].setText("?")

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
        title = QLabel("BakkyTrack")
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
        self._text      = "MMR: --   |   0W  0L   |   STREAK: --   |   WIN RATE: --%"
        self._text_prev = ""
        self._offset    = 0
        self._fm_w      = 0
        self._timer     = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

        # ── Objets de paint mis en cache — évite les re-créations à 30fps ──
        self._brush_bg   = QBrush(QColor(8, 10, 18, 235))
        self._font_badge = QFont()
        self._font_badge.setPointSize(8)
        self._font_badge.setWeight(QFont.Weight.Black)
        self._font_badge.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        self._font_text  = QFont()
        self._font_text.setPointSize(9)
        self._font_text.setWeight(QFont.Weight.Bold)
        self._font_text.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        self._pen_white  = QColor(255, 255, 255, 230)
        self._pen_sep    = QPen(QColor(40, 80, 160, 140), 1)
        self._col_cycle  = [
            QColor("#00cfff"), QColor("#e8ecf4"),
            QColor("#e8ecf4"), QColor("#aaaaaa"),
        ]
        self._col_sep_txt = QColor(60, 80, 120, 180)
        self._col_bg_fade = QColor(8, 10, 18, 235)
        self._col_bg_zero = QColor(8, 10, 18, 0)
        self._col_blue    = QColor("#1A8CFF")
        self._col_blue_dk = QColor("#0a3a6e")
        self._col_rl_bar  = QColor("#1A8CFF")

    def _tick(self):
        self._offset -= self.SPEED_PX
        if self._fm_w > 0 and self._offset < -self._fm_w - 60:
            self._offset = self.width()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Fond dark (objet en cache)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._brush_bg)
        p.drawRoundedRect(0, 0, w, h, 3, 3)

        # Accent bleu badge "RL" (gradient recréé seulement si taille change)
        g = QLinearGradient(0, 0, 56, 0)
        g.setColorAt(0.0, self._col_blue)
        g.setColorAt(1.0, self._col_blue_dk)
        p.setBrush(QBrush(g))
        p.drawRoundedRect(0, 0, 56, h, 3, 3)

        # Texte "RL" (font en cache)
        p.setPen(self._pen_white)
        p.setFont(self._font_badge)
        p.drawText(QRectF(0, 0, 56, h), Qt.AlignmentFlag.AlignCenter, "RL")

        # Séparateur vertical (pen en cache)
        p.setPen(self._pen_sep)
        p.drawLine(56, 0, 56, h)

        # Zone de scroll
        p.setClipRect(QRectF(64, 0, w - 64, h))
        p.setFont(self._font_text)

        fm = p.fontMetrics()
        if self._text != self._text_prev:
            self._fm_w      = fm.horizontalAdvance(self._text)
            self._text_prev = self._text
        if self._offset == 0:
            self._offset = w

        x = self._offset + 64
        parts = self._text.split("   |   ")
        sep_w = fm.horizontalAdvance("   |   ")
        for i, part in enumerate(parts):
            p.setPen(self._col_cycle[i % len(self._col_cycle)])
            p.drawText(QPointF(x, h - 7), part)
            x += fm.horizontalAdvance(part)
            if i < len(parts) - 1:
                p.setPen(self._col_sep_txt)
                p.drawText(QPointF(x, h - 7), "   |   ")
                x += sep_w

        p.setClipping(False)

        # Dégradés de fondu gauche/droite (objets en cache pour les couleurs)
        p.setPen(Qt.PenStyle.NoPen)
        fade_l = QLinearGradient(64, 0, 96, 0)
        fade_l.setColorAt(0.0, self._col_bg_fade)
        fade_l.setColorAt(1.0, self._col_bg_zero)
        p.setBrush(QBrush(fade_l))
        p.drawRect(QRectF(64, 0, 32, h))

        fade_r = QLinearGradient(w - 32, 0, w, 0)
        fade_r.setColorAt(0.0, self._col_bg_zero)
        fade_r.setColorAt(1.0, self._col_bg_fade)
        p.setBrush(QBrush(fade_r))
        p.drawRect(QRectF(w - 32, 0, 32, h))

        # Liseré bleu en bas
        p.setBrush(QBrush(self._col_rl_bar))
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
        t = QLabel("BakkyTrack  ·  RANKED")
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
        enforce_topmost(self, clickthrough=True)

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

# PlayersOverlayWindow  → ui/players_overlay.py
# InGameMMROverlay      → ui/ingame_overlay.py
# _CtrlCanvas           → ui/controller_overlay.py
# StreamerModeBar       → ui/streamer_bar.py
# ControllerOverlay     → ui/controller_overlay.py