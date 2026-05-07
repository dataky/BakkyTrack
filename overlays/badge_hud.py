"""Overlay plugin pour RL Tracker — Badge HUD."""
import sys, os
from PyQt6.QtCore    import Qt, QRectF, QPointF
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui     import (QColor, QPainter, QBrush, QPen,
                              QFont, QLinearGradient, QPixmap)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))

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


C_TEXT  = "#E8ECF4"
C_GREEN = "#2DBD6E"
C_RED   = "#CC2233"
C_ORG   = "#CC5500"
C_BLUE  = "#1A6FCC"

ROW_H = 34
ROW_W = 200
PAD_X = 10
GAP   = 5

BADGES = {
    "streak": (C_ORG,   "#FFFFFF", "🔥", "STRK"),
    "wins":   (C_GREEN, "#FFFFFF", "🏆", "WINS"),
    "losses": (C_RED,   "#FFFFFF", "⊗",  "LOSS"),
    "mmr":    (C_BLUE,  "#FFFFFF", "★",  "MMR"),
}


def _darker(hex_color: str, factor: float = 0.55) -> QColor:
    c = QColor(hex_color)
    return QColor(int(c.red() * factor), int(c.green() * factor), int(c.blue() * factor))





class _BadgeRow(QWidget):
    """Une ligne : [valeur]   [ICÔNE  LABEL]"""

    def __init__(self, badge_key: str, parent=None):
        super().__init__(parent)
        bg, fg, icon, label = BADGES[badge_key]
        self._bg    = bg
        self._fg    = fg
        self._icon  = icon
        self._label = label
        self._value = "—"
        self._rank_tier_id = None  # Pour afficher l'icône rang
        self.setFixedSize(ROW_W, ROW_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_value(self, v: str):
        self._value = v
        self.update()
    
    def set_rank_tier(self, tier_id: int):
        """Définir le tier du rang à afficher à côté de la valeur."""
        self._rank_tier_id = tier_id
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fond de la ligne
        p.setBrush(QBrush(QColor(18, 21, 28, 180)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 6, 6)

        # Icône rang (si défini) + valeur à gauche
        left_offset = PAD_X
        if self._rank_tier_id is not None:
            rank_icon_size = 32
            pm = _get_rank_pixmap(self._rank_tier_id, rank_icon_size)
            if pm:
                icon_y = (ROW_H - pm.height()) // 2
                p.drawPixmap(left_offset, icon_y, pm)
                left_offset += rank_icon_size + 8
        
        # Valeur à gauche
        p.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        p.setPen(QColor(C_TEXT))
        p.drawText(QRectF(left_offset, 0, 60, ROW_H),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._value)

        # Badge à droite
        badge_w = 90
        badge_h = ROW_H - 8
        badge_x = ROW_W - badge_w - PAD_X
        badge_y = (ROW_H - badge_h) / 2
        badge_rect = QRectF(badge_x, badge_y, badge_w, badge_h)

        grad = QLinearGradient(QPointF(badge_x, badge_y),
                               QPointF(badge_x, badge_y + badge_h))
        grad.setColorAt(0.0, QColor(self._bg))
        grad.setColorAt(1.0, _darker(self._bg))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(self._bg).lighter(150), 1))
        p.drawRoundedRect(badge_rect, 5, 5)

        # Icône
        p.setFont(QFont("Segoe UI Emoji", 11))
        p.setPen(QColor(self._fg))
        p.drawText(QRectF(badge_x + 6, badge_y, 22, badge_h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._icon)

        # Texte du badge
        p.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        p.drawText(QRectF(badge_x + 28, badge_y, badge_w - 32, badge_h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   self._label)


class BadgeHudCard(QWidget):
    def __init__(self):
        super().__init__()
        # Pas de window flags ici — le widget est embarqué dans la fenêtre principale
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(ROW_W, ROW_H * 4 + GAP * 3 + 8)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(GAP)

        self._streak = _BadgeRow("streak")
        self._wins   = _BadgeRow("wins")
        self._losses = _BadgeRow("losses")
        self._mmr    = _BadgeRow("mmr")

        for row in (self._streak, self._wins, self._losses, self._mmr):
            lay.addWidget(row)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(10, 12, 16, 200)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(self.rect(), 8, 8)

    def update_stats(self, d: dict, mmr_mode: str = "both"):
        # Rang (à côté du MMR)
        self._mmr.set_rank_tier(d.get("tier_id", 0))
        # Streak
        sv = d.get("streak_val", 0)
        st = d.get("streak_type", "win")
        if sv:
            self._streak.set_value(f"+{sv}W" if st == "win" else f"-{sv}L")
        else:
            self._streak.set_value("—")

        # Wins / Losses
        self._wins.set_value(str(d.get("wins", 0)))
        self._losses.set_value(str(d.get("losses", 0)))

        # MMR
        mmr   = d.get("mmr")
        delta = d.get("mmr_change", 0) or 0
        if mmr_mode == "delta":
            self._mmr.set_value(f"{'+' if delta > 0 else ''}{delta}" if delta else "—")
        elif mmr_mode == "mmr":
            self._mmr.set_value(str(mmr) if mmr is not None else "—")
        else:  # both
            base = str(mmr) if mmr is not None else "—"
            self._mmr.set_value(f"{base} ({'+' if delta > 0 else ''}{delta})" if delta else base)


OVERLAY_NAME = "badge_hud"
OVERLAY_SIZE = (200, 191)
Overlay = BadgeHudCard