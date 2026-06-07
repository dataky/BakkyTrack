"""ui/ball_speed_overlay.py — Overlay vitesse balle always-on-top, style screenshot.

Rendu 100 % via QPainter : on ne dépend plus de QLabel ni de
QGraphicsDropShadowEffect. C'est ce dernier qui empêchait setFont()
d'avoir un effet visuel (pixmap en cache non invalidé → texte figé à
la taille initiale, seule la fenêtre se redimensionnait).
"""
import time
from PyQt6.QtCore    import Qt
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui     import QFont, QFontMetrics, QColor, QPainter, QPixmap

# ── Constantes visuelles ─────────────────────────────────────────────────
_COL_MAIN   = QColor(255, 255, 255)      # blanc pur
_COL_SHADOW = QColor(0, 0, 0, 200)       # ombre noire semi-opaque
_SHADOW_OFF = 2                          # décalage de l'ombre en px
_PAD_H      = 10                         # marge horizontale
_PAD_V      = 4                          # marge verticale
_GAP        = 8                          # espace entre vitesse et unité
_REF_TEXT   = "000.000"                  # texte de référence pour la largeur (supporte jusqu'à 3 décimales)

# Throttle : pas plus de ~15 mises à jour/s pour éviter le lag
_UPDATE_INTERVAL = 0.065


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
        self._speed_text  = "-"
        self._decimals    = int(config.get("ball_speed_decimals", 2))
        self._last_update_time = 0.0
        self._cached_pixmap = None

        self._cache_fonts()   # ← construit le cache QFont/QFontMetrics une seule fois
        self._refresh_size()

        signals.ball_speed_updated.connect(self._on_speed)
        pos = config.get("pos_ball_overlay")
        if pos and len(pos) == 2:
            screen = QApplication.primaryScreen().geometry()
            sw, sh = screen.width(), screen.height()
            x = int(pos[0]) if pos[0] > 1.0 else int(pos[0] * sw)
            y = int(pos[1]) if pos[1] > 1.0 else int(pos[1] * sh)
            self.move(int(x), int(y))
        else:
            self.move(80, 80)

    # ── Polices ──────────────────────────────────────────────────────────
    def _cache_fonts(self):
        """Construit et met en cache les polices + métriques. Appelé à la construction et sur changement de taille."""
        fs = self._font_size
        fu = max(8, fs * 80 // 100)

        self._f_speed = QFont("Consolas", fs)
        self._f_speed.setStyleHint(QFont.StyleHint.Monospace)
        self._f_speed.setStyleStrategy(QFont.StyleStrategy.NoAntialias)

        self._f_unit = QFont("Consolas", fu)
        self._f_unit.setStyleHint(QFont.StyleHint.Monospace)
        self._f_unit.setStyleStrategy(QFont.StyleStrategy.NoAntialias)

        self._fm_s = QFontMetrics(self._f_speed)
        self._fm_u = QFontMetrics(self._f_unit)

    def _make_fonts(self):
        """Compatibilité avec _refresh_size — retourne les polices depuis le cache."""
        return self._f_speed, self._f_unit

    # ── Taille de la fenêtre ──────────────────────────────────────────────
    def _refresh_size(self):
        """Calcule et applique la taille de la fenêtre d'après la police courante."""
        f_speed, f_unit = self._make_fonts()
        fm_s = QFontMetrics(f_speed)
        fm_u = QFontMetrics(f_unit)

        w = (_PAD_H
             + fm_s.horizontalAdvance(_REF_TEXT)
             + _GAP
             + fm_u.horizontalAdvance("km/h")
             + _PAD_H)
        h = fm_s.height() + _PAD_V * 2

        self.setFixedSize(w, h)
        self._cached_pixmap = None

    # ── API publique ──────────────────────────────────────────────────────
    def set_font_size(self, size: int):
        """Appelé par le slider dans OverlayTab → change immédiatement la taille du texte."""
        self._font_size = size
        self.config["ball_overlay_font_size"] = size
        self._cache_fonts()   # ← recrée le cache avant _refresh_size
        self._refresh_size()
        self.update()

    def set_decimals(self, decimals: int):
        """Change le nombre de décimales (appelé depuis l'onglet)."""
        self._decimals = decimals

    # ── Rendu ─────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        if self._cached_pixmap is None:
            self._update_pixmap_cache()
            
        p = QPainter(self)
        if self._cached_pixmap is not None:
            p.drawPixmap(0, 0, self._cached_pixmap)
        p.end()

    def _update_pixmap_cache(self):
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        # Utilise les polices + métriques mises en cache (pas de réallocation)
        fm_s = self._fm_s
        fm_u = self._fm_u

        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)

        # Positions
        baseline_speed = _PAD_V + fm_s.ascent()
        h_total        = self.height()
        baseline_unit  = h_total - _PAD_V - fm_u.descent()
        x_speed = _PAD_H
        x_unit  = _PAD_H + fm_s.horizontalAdvance(_REF_TEXT) + _GAP

        # Vitesse (ombre + texte)
        p.setFont(self._f_speed)
        p.setPen(_COL_SHADOW)
        p.drawText(x_speed + _SHADOW_OFF, baseline_speed + _SHADOW_OFF, self._speed_text)
        p.setPen(_COL_MAIN)
        p.drawText(x_speed, baseline_speed, self._speed_text)

        # Unité (ombre + texte)
        p.setFont(self._f_unit)
        p.setPen(_COL_SHADOW)
        p.drawText(x_unit + _SHADOW_OFF, baseline_unit + _SHADOW_OFF, "km/h")
        p.setPen(_COL_MAIN)
        p.drawText(x_unit, baseline_unit, "km/h")

        p.end()
        self._cached_pixmap = pixmap

    # ── Signal vitesse (throttlé ~15 fps max pour éviter le lag) ──────────
    def _on_speed(self, kmh: float):
        # Pas de travail Qt si l'overlay est caché
        if not self.isVisible():
            return
        now = time.time()
        if now - self._last_update_time < _UPDATE_INTERVAL:
            return
        self._last_update_time = now
        new_text = f"{kmh:.{self._decimals}f}"
        if new_text == self._speed_text:
            return  # valeur inchangée — pas de repaint inutile
        self._speed_text = new_text
        self._cached_pixmap = None
        self.update()

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
            p = self.pos()
            screen = QApplication.primaryScreen().geometry()
            sw, sh = screen.width(), screen.height()
            self.config["pos_ball_overlay"] = (p.x() / sw, p.y() / sh)
            self.config.save()
            self._drag_pos = None
        e.accept()