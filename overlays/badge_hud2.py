"""
badge_hud.py — Overlay "Badges colorés" (200×152)
Plugin overlay pour BakkyTrack / rl_tracker.py

Placer ce fichier dans :  <dossier_du_tracker>/overlays/badge_hud.py

Chaque stat dans un badge arrondi avec sa propre couleur d'accent.
Layout :
  ┌─────────────────────────────┐
  │ • RL TRACKER                │  ← header discret
  │    1234   +12               │  ← MMR + delta
  ├─────────┬────────┬──────────┤
  │   14 W  │  8 L  │  +3 STK  │  ← badges colorés
  ├─────────────────────────────┤
  │ WR ████████░░░░░░  63 %     │  ← barre winrate
  └─────────────────────────────┘
"""

from PyQt6.QtCore    import Qt, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui     import (
    QPainter, QColor, QBrush, QPen,
    QLinearGradient, QRadialGradient, QFont, QPixmap
)
import sys, os

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))

_RANK_FOLDER = os.path.join(BASE_DIR, "all rank")
_rank_cache: dict = {}

def _get_rank_pixmap(tier_id: int, size: int = 45):
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

OVERLAY_NAME = "badge_hud2"
OVERLAY_SIZE = (200, 152)


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(*OVERLAY_SIZE)
        self._vals    = {}
        self._winrate = 0.5
        self._build()

    # ── Construction UI ───────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 14)
        root.setSpacing(5)

        # ── Header ────────────────────────────────────────────────────────
        hdr = QLabel("RL TRACKER")
        hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setStyleSheet(
            "color:rgba(26,140,255,0.45);font-size:7px;letter-spacing:3px;"
            "font-weight:700;background:transparent;")
        root.addWidget(hdr)

        # ── MMR + delta ───────────────────────────────────────────────────
        mmr_row = QHBoxLayout()
        mmr_row.setSpacing(6)
        mmr_row.setContentsMargins(0, 0, 0, 0)

        # Icône de rang (45×45)
        self._rank_icon = QLabel()
        self._rank_icon.setFixedSize(45, 45)
        self._rank_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon.setStyleSheet("background:transparent;")

        self._mmr_lbl = QLabel("--")
        self._mmr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mmr_lbl.setStyleSheet(
            "color:#ffd700;font-size:30px;font-weight:900;"
            "letter-spacing:-1px;background:transparent;")

        self._delta_lbl = QLabel("")
        self._delta_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._delta_lbl.setStyleSheet(
            "color:#888;font-size:13px;font-weight:700;background:transparent;")

        mmr_row.addStretch()
        mmr_row.addWidget(self._rank_icon)
        mmr_row.addWidget(self._mmr_lbl)
        mmr_row.addWidget(self._delta_lbl)
        mmr_row.addStretch()
        root.addLayout(mmr_row)

        # ── Badges W / L / STK ────────────────────────────────────────────
        badges_row = QHBoxLayout()
        badges_row.setSpacing(5)
        badges_row.setContentsMargins(0, 0, 0, 0)

        for key, label, color in [
            ("wins",   "W",   "#00e676"),
            ("losses", "L",   "#ff3d57"),
            ("stk",    "STK", "#00cfff"),
        ]:
            badge = QWidget()
            badge.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            badge.setStyleSheet("background:transparent;")
            badge.setFixedHeight(44)
            bl = QVBoxLayout(badge)
            bl.setContentsMargins(0, 4, 0, 4)
            bl.setSpacing(1)

            val_w = QLabel("0")
            val_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_w.setStyleSheet(
                f"color:{color};font-size:17px;font-weight:800;"
                "background:transparent;")

            lbl_w = QLabel(label)
            lbl_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_w.setStyleSheet(
                f"color:{color}80;font-size:7px;letter-spacing:2px;"
                "font-weight:700;background:transparent;")

            bl.addWidget(val_w)
            bl.addWidget(lbl_w)
            self._vals[key] = val_w
            badges_row.addWidget(badge)

        root.addLayout(badges_row)

        # ── Winrate label ─────────────────────────────────────────────────
        wr_row = QHBoxLayout()
        wr_row.setContentsMargins(0, 2, 0, 0)
        wr_label = QLabel("WIN RATE")
        wr_label.setStyleSheet(
            "color:rgba(160,170,190,0.45);font-size:7px;letter-spacing:1.5px;"
            "font-weight:600;background:transparent;")
        self._wr_lbl = QLabel("--%")
        self._wr_lbl.setStyleSheet(
            "color:rgba(255,255,255,0.65);font-size:10px;"
            "font-weight:700;background:transparent;")
        wr_row.addWidget(wr_label)
        wr_row.addStretch()
        wr_row.addWidget(self._wr_lbl)
        root.addLayout(wr_row)

    # ── Dessin de fond ────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Corps principal semi-opaque
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(10, 12, 20, 218)))
        p.drawRoundedRect(0, 0, w, h, 10, 10)

        # Halo radial subtil (MMR area)
        halo = QRadialGradient(w / 2, 42, 60)
        halo.setColorAt(0.0, QColor(255, 215, 0, 18))
        halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(halo))
        p.drawRoundedRect(0, 0, w, h, 10, 10)

        # ── Badges arrière-plan colorés (zone W/L/STK) ────────────────────
        badge_y   = 74
        badge_h   = 44
        inner_w   = w - 24           # 12px marge de chaque côté
        gap       = 5
        badge_w   = (inner_w - 2 * gap) // 3
        bg_colors = [
            QColor(0,  100,  50, 52),
            QColor(100,  20, 30, 52),
            QColor(0,   80, 120, 52),
        ]
        for i, c in enumerate(bg_colors):
            x = 12 + i * (badge_w + gap)
            p.setBrush(QBrush(c))
            p.drawRoundedRect(QRectF(x, badge_y, badge_w, badge_h), 7, 7)

            # Micro-ligne de couleur en haut du badge
            accent_colors = ["#00e676", "#ff3d57", "#00cfff"]
            gc = QLinearGradient(x, badge_y, x + badge_w, badge_y)
            gc.setColorAt(0.0, QColor(accent_colors[i]))
            gc.setColorAt(1.0, QColor(accent_colors[i] + "44"))
            p.setBrush(QBrush(gc))
            p.drawRoundedRect(QRectF(x, badge_y, badge_w, 2), 1, 1)

        # ── Barre winrate (4 px) en bas ────────────────────────────────────
        bar_x = 12
        bar_w = w - 24
        bar_y = h - 10
        win_w = max(0, min(bar_w, int(bar_w * self._winrate)))

        if win_w > 0:
            g = QLinearGradient(bar_x, 0, bar_x + win_w, 0)
            g.setColorAt(0.0, QColor("#00e676"))
            g.setColorAt(1.0, QColor("#00b84a"))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(bar_x, bar_y, win_w, 4), 2, 2)

        if win_w < bar_w:
            g2 = QLinearGradient(bar_x + win_w, 0, bar_x + bar_w, 0)
            g2.setColorAt(0.0, QColor("#cc1f2e"))
            g2.setColorAt(1.0, QColor("#ff3d57"))
            p.setBrush(QBrush(g2))
            p.drawRoundedRect(QRectF(bar_x + win_w, bar_y, bar_w - win_w, 4), 2, 2)

        # ── Accent dégradé bleu→orange en haut ────────────────────────────
        g3 = QLinearGradient(0, 0, w, 0)
        g3.setColorAt(0.0, QColor("#1A8CFF"))
        g3.setColorAt(1.0, QColor("#FF6B00"))
        p.setBrush(QBrush(g3))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, 3), 2, 2)

        # ── Bordure externe ────────────────────────────────────────────────
        pen = QPen(QColor(50, 65, 100, 130))
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 10, 10)

        p.end()

    # ── Mise à jour des stats ──────────────────────────────────────────────
    def update_stats(self, d, mmr_mode="both"):
        mmr    = d.get("mmr")
        chg    = d.get("mmr_change", 0)
        sv     = d.get("streak_val", 0)
        st     = d.get("streak_type", "")
        wins   = d.get("wins", 0)
        losses = d.get("losses", 0)
        total  = wins + losses

        self._winrate = (wins / total) if total > 0 else 0.5
        self.update()   # force repaint

        # ── Icône de rang ──────────────────────────────────────────────────
        pm = _get_rank_pixmap(d.get("tier_id", 0), 45)
        if pm:
            self._rank_icon.setPixmap(pm)
            self._rank_icon.setVisible(True)
        else:
            self._rank_icon.clear()
            self._rank_icon.setVisible(False)

        # ── MMR ──────────────────────────────────────────────────────────
        if mmr_mode == "delta":
            self._mmr_lbl.setText("")
        else:
            self._mmr_lbl.setText(str(mmr) if mmr else "--")

        # ── Delta ─────────────────────────────────────────────────────────
        if chg and mmr_mode != "mmr":
            sign = "+" if chg > 0 else ""
            clr  = "#00e676" if chg > 0 else "#ff3d57"
            self._delta_lbl.setText(f"{sign}{chg}")
            self._delta_lbl.setStyleSheet(
                f"color:{clr};font-size:13px;font-weight:700;background:transparent;")
        elif mmr_mode == "delta" and chg:
            sign = "+" if chg > 0 else ""
            clr  = "#00e676" if chg > 0 else "#ff3d57"
            # Affiche le delta en grand si mode delta
            self._mmr_lbl.setStyleSheet(
                f"color:{clr};font-size:30px;font-weight:900;"
                "letter-spacing:-1px;background:transparent;")
            self._mmr_lbl.setText(f"{sign}{chg}")
            self._delta_lbl.setText("")
        else:
            self._delta_lbl.setText("")

        # ── W / L ─────────────────────────────────────────────────────────
        self._vals["wins"].setText(str(wins))
        self._vals["losses"].setText(str(losses))

        # ── Streak ────────────────────────────────────────────────────────
        if sv > 0:
            clr = "#00cfff" if st == "win" else "#ff7070"
            self._vals["stk"].setText(f"{'+'if st=='win'else'-'}{sv}")
            self._vals["stk"].setStyleSheet(
                f"color:{clr};font-size:17px;font-weight:800;background:transparent;")
        else:
            self._vals["stk"].setText("--")
            self._vals["stk"].setStyleSheet(
                "color:#00cfff;font-size:17px;font-weight:800;background:transparent;")

        # ── Win rate label ─────────────────────────────────────────────────
        if total > 0:
            wr = round(wins / total * 100)
            self._wr_lbl.setText(f"{wr}%")
        else:
            self._wr_lbl.setText("--%")