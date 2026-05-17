"""ui/ball_speed_overlay.py — Overlay vitesse balle always-on-top, style screenshot.

Rendu 100 % via QPainter : on ne dépend plus de QLabel ni de
QGraphicsDropShadowEffect. C'est ce dernier qui empêchait setFont()
d'avoir un effet visuel (pixmap en cache non invalidé → texte figé à
la taille initiale, seule la fenêtre se redimensionnait).
"""
from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui     import QFont, QFontMetrics, QColor, QPainter

# ── Constantes visuelles ─────────────────────────────────────────────────
_COL_MAIN   = QColor(255, 255, 255)      # blanc pur
_COL_SHADOW = QColor(0, 0, 0, 200)       # ombre noire semi-opaque
_SHADOW_OFF = 2                          # décalage de l'ombre en px
_PAD_H      = 10                         # marge horizontale
_PAD_V      = 4                          # marge verticale
_GAP        = 8                          # espace entre vitesse et unité
_REF_TEXT   = "000.00"                   # texte de référence pour la largeur


class BallSpeedOverlay(QWidget):
    def __init__(self, signals, config):
        super().__init__(
            None,
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint  |
            Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.signals      = signals
        self.config       = config
        self._drag_pos    = None
        self._font_size   = int(config.get("ball_overlay_font_size", 28))
        self._speed_text  = "-"           # texte affiché (mis à jour par le signal)

        self._refresh_size()

        signals.ball_speed_updated.connect(self._on_speed)
        self.move(
            int(config.get("ball_overlay_x", 80)),
            int(config.get("ball_overlay_y", 80)),
        )

    # ── Polices ──────────────────────────────────────────────────────────
    def _make_fonts(self):
        """Crée les deux polices (vitesse + unité) depuis _font_size."""
        fs = self._font_size
        fu = max(8, fs * 80 // 100)

        f_speed = QFont("Consolas", fs)
        f_speed.setStyleHint(QFont.StyleHint.Monospace)
        f_speed.setStyleStrategy(QFont.StyleStrategy.NoAntialias)

        f_unit = QFont("Consolas", fu)
        f_unit.setStyleHint(QFont.StyleHint.Monospace)
        f_unit.setStyleStrategy(QFont.StyleStrategy.NoAntialias)

        return f_speed, f_unit

    # ── Taille de la fenêtre ──────────────────────────────────────────────
    def _refresh_size(self):
        """Calcule et applique la taille de la fenêtre d'après la police courante."""
        f_speed, f_unit = self._make_fonts()
        fm_s = QFontMetrics(f_speed)
        fm_u = QFontMetrics(f_unit)

        # Largeur basée sur _REF_TEXT pour que la fenêtre ne saute pas à
        # chaque changement de valeur (ex. "9.00" vs "216.00").
        w = (_PAD_H
             + fm_s.horizontalAdvance(_REF_TEXT)
             + _GAP
             + fm_u.horizontalAdvance("km/h")
             + _PAD_H)
        h = fm_s.height() + _PAD_V * 2

        self.setFixedSize(w, h)

    # ── API publique ──────────────────────────────────────────────────────
    def set_font_size(self, size: int):
        """Appelé par le slider dans OverlayTab → change immédiatement la taille du texte."""
        self._font_size = size
        self.config["ball_overlay_font_size"] = size
        self._refresh_size()   # redimensionne la fenêtre
        self.update()          # force le repaint avec la nouvelle police

    # ── Rendu ─────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        f_speed, f_unit = self._make_fonts()
        fm_s = QFontMetrics(f_speed)
        fm_u = QFontMetrics(f_unit)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)

        # ── Positions ────────────────────────────────────────────────────
        # Baseline commune (vitesse) : _PAD_V + ascent
        baseline_speed = _PAD_V + fm_s.ascent()

        # "km/h" aligné en bas (descente alignée avec celle de la vitesse)
        h_total        = self.height()
        baseline_unit  = h_total - _PAD_V - fm_u.descent()

        x_speed = _PAD_H
        x_unit  = _PAD_H + fm_s.horizontalAdvance(_REF_TEXT) + _GAP

        # ── Vitesse (ombre + texte) ───────────────────────────────────────
        p.setFont(f_speed)

        p.setPen(_COL_SHADOW)
        p.drawText(x_speed + _SHADOW_OFF, baseline_speed + _SHADOW_OFF, self._speed_text)

        p.setPen(_COL_MAIN)
        p.drawText(x_speed, baseline_speed, self._speed_text)

        # ── Unité (ombre + texte) ─────────────────────────────────────────
        p.setFont(f_unit)

        p.setPen(_COL_SHADOW)
        p.drawText(x_unit + _SHADOW_OFF, baseline_unit + _SHADOW_OFF, "km/h")

        p.setPen(_COL_MAIN)
        p.drawText(x_unit, baseline_unit, "km/h")

        p.end()

    # ── Signal vitesse ────────────────────────────────────────────────────
    def _on_speed(self, kmh: float):
        self._speed_text = f"{kmh:.2f}"
        self.update()   # pas de resize : on utilise _REF_TEXT comme référence fixe

    # ── Drag ──────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        if self._drag_pos:
            pos = self.pos()
            self.config["ball_overlay_x"] = pos.x()
            self.config["ball_overlay_y"] = pos.y()
            self.config.save()
            self._drag_pos = None
        e.accept()