# overlays/prestige.py
"""
Overlay 'prestige'  —  380 × 178 px
═══════════════════════════════════════════════════════════════════
Style : holographique cristallin, multi-couches, animations 60 fps
─────────────────────────────────────────────────────────────────
• Grille hexagonale subtile en arrière-plan
• Particules cyan flottantes avec halos radials
• Bordure prismatique à rotation lente (bleu→cyan→orange→or)
• Arc winrate dégradé avec tip lumineux et pulsation
• Section stats : badge rang, pilules W/L, streak pulsant, MMR doré
• Barre W/L en bas avec reflet et marqueur 50 %
• Reflet glassmorphism en haut
"""

import sys, os, math, random
from PyQt6.QtCore    import Qt, QTimer, QRectF, QPointF
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui     import (
    QPainter, QColor, QBrush, QPen,
    QLinearGradient, QRadialGradient, QConicalGradient,
    QFont, QPolygonF, QPixmap,
)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))

_RANK_FOLDER = os.path.join(BASE_DIR, "all rank")
_rank_cache: dict = {}

def _get_rank_pixmap(tier_id: int, size: int = 28):
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

OVERLAY_NAME = "prestige"
OVERLAY_SIZE = (380, 178)

# ── Palette ──────────────────────────────────────────────────────
C_BG      = "#0A0C10"
C_BG2     = "#12151C"
C_BG3     = "#1A1E2A"
C_BLUE    = "#1A8CFF"
C_ORG     = "#FF6B00"
C_TEXT    = "#E8ECF4"
C_MUTE    = "#5A6275"
C_GREEN   = "#3AE08A"
C_GOLD    = "#FFD700"
NEON_CYAN = "#00cfff"
WIN_GREEN = "#00e676"
LOSS_RED  = "#ff3d57"


# ─────────────────────────────────────────────────────────────────
class Overlay(QWidget):

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(*OVERLAY_SIZE)

        # ── Données ──
        self._wins        = 0
        self._losses      = 0
        self._winrate     = 0.5
        self._streak_val  = 0
        self._streak_type = ""
        self._mmr         = None
        self._mmr_change  = 0
        self._rank        = "Unranked"
        self._tier_id     = 0
        self._mmr_mode    = "both"

        # ── État d'animation ──
        self._tick    = 0
        self._pulse   = 0.0
        self._pulse_dir = 1
        self._particles = self._init_particles()

        # ── Timer 60 fps ──
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

    # ──────────────────────────────────────────────────────────────
    #  Particules
    # ──────────────────────────────────────────────────────────────
    def _init_particles(self):
        W, H = OVERLAY_SIZE
        parts = []
        for _ in range(20):
            parts.append({
                'x':     random.uniform(0, W),
                'y':     random.uniform(0, H),
                'vx':    random.uniform(-0.25, 0.25),
                'vy':    random.uniform(-0.45, -0.08),
                'size':  random.uniform(1.0, 2.4),
                'alpha': random.uniform(0.2, 0.85),
                'life':  random.uniform(0.0, 1.0),
            })
        return parts

    def _animate(self):
        W, H = OVERLAY_SIZE
        self._tick += 1

        # Pulsation sinusoïdale douce
        self._pulse += 0.022 * self._pulse_dir
        if   self._pulse >= 1.0: self._pulse_dir = -1
        elif self._pulse <= 0.0: self._pulse_dir =  1

        # Mise à jour particules
        for p in self._particles:
            p['x']    += p['vx']
            p['y']    += p['vy']
            p['life'] += 0.004
            if p['life'] >= 1.0 or p['y'] < -6:
                p['x']    = random.uniform(0, W)
                p['y']    = H + 4
                p['vx']   = random.uniform(-0.25, 0.25)
                p['vy']   = random.uniform(-0.45, -0.08)
                p['life'] = 0.0
                p['alpha']= random.uniform(0.2, 0.85)
                p['size'] = random.uniform(1.0, 2.4)

        self.update()

    # ──────────────────────────────────────────────────────────────
    #  paintEvent principal
    # ──────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        W, H = OVERLAY_SIZE

        self._draw_background(p, W, H)
        self._draw_hex_grid(p, W, H)
        self._draw_particles(p)
        self._draw_border(p, W, H)
        self._draw_winrate_arc(p)
        self._draw_stats(p, W, H)
        self._draw_bottom_bar(p, W, H)
        self._draw_glass_sheen(p, W, H)
        p.end()

    # ──────────────────────────────────────────────────────────────
    #  Couche 1 — Fond
    # ──────────────────────────────────────────────────────────────
    def _draw_background(self, p, W, H):
        r = 14
        rect = QRectF(0, 0, W, H)

        # Ombres portées empilées
        for i in range(7, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, 18)))
            p.drawRoundedRect(QRectF(i * .5, i * .5, W, H), r, r)

        # Fond dégradé radial principal
        grad = QRadialGradient(W * .35, H * .28, W * .82)
        grad.setColorAt(0.0, QColor("#1C2030"))
        grad.setColorAt(0.55, QColor("#12151C"))
        grad.setColorAt(1.0, QColor("#0A0C10"))
        p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, r, r)

        # Halo bleu haut-gauche
        g1 = QRadialGradient(55, 30, 110)
        g1.setColorAt(0.0, QColor(26, 140, 255, 28))
        g1.setColorAt(1.0, QColor(26, 140, 255, 0))
        p.setBrush(QBrush(g1))
        p.drawRoundedRect(rect, r, r)

        # Halo orange bas-droite
        g2 = QRadialGradient(W - 45, H - 22, 130)
        g2.setColorAt(0.0, QColor(255, 107, 0, 22))
        g2.setColorAt(1.0, QColor(255, 107, 0, 0))
        p.setBrush(QBrush(g2))
        p.drawRoundedRect(rect, r, r)

    # ──────────────────────────────────────────────────────────────
    #  Couche 2 — Grille hexagonale
    # ──────────────────────────────────────────────────────────────
    def _draw_hex_grid(self, p, W, H):
        p.save()
        pen = QPen(QColor(255, 255, 255, 6), 0.6)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)

        size = 18
        dx = size * 1.732
        dy = size * 1.5

        for row in range(-1, int(H / dy) + 2):
            for col in range(-1, int(W / dx) + 2):
                cx = col * dx + (dx / 2 if row % 2 else 0)
                cy = row * dy
                pts = [
                    QPointF(cx + size * math.cos(math.radians(60 * i - 30)),
                            cy + size * math.sin(math.radians(60 * i - 30)))
                    for i in range(6)
                ]
                p.drawPolygon(QPolygonF(pts))
        p.restore()

    # ──────────────────────────────────────────────────────────────
    #  Couche 3 — Particules flottantes
    # ──────────────────────────────────────────────────────────────
    def _draw_particles(self, p):
        p.save()
        for pt in self._particles:
            a = int(pt['alpha'] * 190 * max(0.0, 1.0 - pt['life']))
            if a <= 0:
                continue
            c = QColor(0, 207, 255, a)
            s = pt['size']
            x, y = pt['x'], pt['y']

            # Point central
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(c))
            p.drawEllipse(QRectF(x - s / 2, y - s / 2, s, s))

            # Halo radial autour
            g = QRadialGradient(x, y, s * 3.5)
            g.setColorAt(0.0, QColor(0, 207, 255, a // 4))
            g.setColorAt(1.0, QColor(0, 207, 255, 0))
            p.setBrush(QBrush(g))
            p.drawEllipse(QRectF(x - s * 3.5, y - s * 3.5, s * 7, s * 7))
        p.restore()

    # ──────────────────────────────────────────────────────────────
    #  Couche 4 — Bordure prismatique
    # ──────────────────────────────────────────────────────────────
    def _draw_border(self, p, W, H):
        p.save()
        angle = (self._tick * 1.4) % 360

        grad = QConicalGradient(W / 2, H / 2, angle)
        grad.setColorAt(0.00, QColor(26, 140, 255, 210))
        grad.setColorAt(0.22, QColor(0, 207, 255, 170))
        grad.setColorAt(0.50, QColor(255, 107, 0, 210))
        grad.setColorAt(0.75, QColor(255, 215, 0, 170))
        grad.setColorAt(1.00, QColor(26, 140, 255, 210))

        r = 14
        # Ligne extérieure prismatique
        p.setPen(QPen(QBrush(grad), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.8, 0.8, W - 1.6, H - 1.6), r, r)

        # Ligne intérieure très subtile (verre)
        p.setPen(QPen(QColor(255, 255, 255, 14), 1.0))
        p.drawRoundedRect(QRectF(2.0, 2.0, W - 4.0, H - 4.0), r - 1, r - 1)
        p.restore()

    # ──────────────────────────────────────────────────────────────
    #  Couche 5 — Arc winrate (côté gauche)
    # ──────────────────────────────────────────────────────────────
    def _draw_winrate_arc(self, p):
        p.save()
        cx, cy   = 94, 89
        R_out    = 60
        R_in     = 46
        R_mid    = (R_out + R_in) / 2
        stroke_w = R_out - R_in - 2

        # ── Fond disque ──
        p.setPen(Qt.PenStyle.NoPen)
        bg = QRadialGradient(cx, cy, R_out)
        bg.setColorAt(0.0, QColor("#1C2030"))
        bg.setColorAt(1.0, QColor("#0E1018"))
        p.setBrush(QBrush(bg))
        p.drawEllipse(QRectF(cx - R_out, cy - R_out, R_out * 2, R_out * 2))

        # ── Halo radial pulsant ──
        pa = int(25 + 28 * self._pulse)
        glow = QRadialGradient(cx, cy, R_out + 10)
        glow.setColorAt(0.65, QColor(0, 207, 255, 0))
        glow.setColorAt(0.88, QColor(0, 207, 255, pa))
        glow.setColorAt(1.0,  QColor(0, 207, 255, 0))
        p.setBrush(QBrush(glow))
        p.drawEllipse(QRectF(cx - R_out - 12, cy - R_out - 12,
                             (R_out + 12) * 2, (R_out + 12) * 2))

        # ── Rect pour drawArc (centré sur R_mid) ──
        half = R_mid
        arc_rect = QRectF(cx - half, cy - half, half * 2, half * 2)

        # Track (fond de l'arc)
        pen_track = QPen(QColor(20, 24, 36), stroke_w)
        pen_track.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen_track)
        p.setBrush(Qt.BrushStyle.NoBrush)
        ARC_START = 225   # degrés
        ARC_SPAN  = 270
        p.drawArc(arc_rect, ARC_START * 16, -ARC_SPAN * 16)

        # ── Arc rempli par segments (dégradé simulé) ──
        win_span = ARC_SPAN * self._winrate
        if win_span > 0:
            if self._winrate >= 0.60:
                c1, c2 = QColor(WIN_GREEN), QColor(NEON_CYAN)
            elif self._winrate >= 0.50:
                c1, c2 = QColor(C_BLUE), QColor(NEON_CYAN)
            else:
                c1, c2 = QColor(LOSS_RED), QColor(C_ORG)

            SEGS = 40
            seg  = win_span / SEGS
            for i in range(SEGS):
                t   = i / SEGS
                r_v = int(c1.red()   + t * (c2.red()   - c1.red()))
                g_v = int(c1.green() + t * (c2.green() - c1.green()))
                b_v = int(c1.blue()  + t * (c2.blue()  - c1.blue()))
                pen_seg = QPen(QColor(r_v, g_v, b_v), stroke_w)
                pen_seg.setCapStyle(Qt.PenCapStyle.FlatCap)
                p.setPen(pen_seg)
                p.drawArc(arc_rect,
                          int((ARC_START - i * seg) * 16),
                          int((-seg - 0.5) * 16))

            # Tip lumineux à l'extrémité
            tip_rad = math.radians(ARC_START - win_span)
            tip_x   = cx + R_mid * math.cos(tip_rad)
            tip_y   = cy - R_mid * math.sin(tip_rad)

            tip_g = QRadialGradient(tip_x, tip_y, 11)
            tip_g.setColorAt(0.0, QColor(255, 255, 255, 230))
            tip_g.setColorAt(0.3, c2)
            tip_g.setColorAt(1.0, QColor(c2.red(), c2.green(), c2.blue(), 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(tip_g))
            p.drawEllipse(QRectF(tip_x - 11, tip_y - 11, 22, 22))

        # ── Centre sombre ──
        p.setPen(Qt.PenStyle.NoPen)
        center_g = QRadialGradient(cx, cy, R_in - 1)
        center_g.setColorAt(0.0, QColor(16, 18, 26, 200))
        center_g.setColorAt(1.0, QColor(10, 12, 16, 255))
        p.setBrush(QBrush(center_g))
        p.drawEllipse(QRectF(cx - R_in + 2, cy - R_in + 2,
                             (R_in - 2) * 2, (R_in - 2) * 2))

        # ── Texte winrate ──
        wr_pct = int(self._winrate * 100)
        font_big = QFont("Consolas", 17, QFont.Weight.Bold)
        p.setFont(font_big)
        p.setPen(QPen(QColor(C_TEXT)))
        p.drawText(QRectF(cx - 34, cy - 17, 68, 26),
                   Qt.AlignmentFlag.AlignCenter, f"{wr_pct}%")

        font_sm = QFont("Consolas", 6, QFont.Weight.Normal)
        p.setFont(font_sm)
        p.setPen(QPen(QColor(C_MUTE)))
        p.drawText(QRectF(cx - 28, cy + 10, 56, 14),
                   Qt.AlignmentFlag.AlignCenter, "WIN RATE")

        # Etiquettes W / L aux extrémités
        font_ends = QFont("Consolas", 7, QFont.Weight.Bold)
        p.setFont(font_ends)
        p.setPen(QPen(QColor(LOSS_RED)))
        p.drawText(QRectF(cx - R_out - 4, cy + int(R_out * .50), 20, 14),
                   Qt.AlignmentFlag.AlignCenter, "L")
        p.setPen(QPen(QColor(WIN_GREEN)))
        p.drawText(QRectF(cx + R_out - 16, cy + int(R_out * .50), 20, 14),
                   Qt.AlignmentFlag.AlignCenter, "W")

        p.restore()

    # ──────────────────────────────────────────────────────────────
    #  Couche 6 — Section stats droite
    # ──────────────────────────────────────────────────────────────
    def _draw_stats(self, p, W, H):
        p.save()
        x0 = 178

        # Séparateur vertical dégradé
        sep = QLinearGradient(x0 - 1, 14, x0 - 1, H - 22)
        sep.setColorAt(0.0, QColor(26, 140, 255, 0))
        sep.setColorAt(0.3, QColor(26, 140, 255, 120))
        sep.setColorAt(0.7, QColor(0, 207, 255, 100))
        sep.setColorAt(1.0, QColor(26, 140, 255, 0))
        p.setPen(QPen(QBrush(sep), 1.0))
        p.drawLine(QPointF(x0 - 1, 14), QPointF(x0 - 1, H - 22))

        # ── Badge rang ──
        BADGE_X = x0 + 7
        BADGE_Y = 14
        BADGE_H = 40          # un peu plus haut pour accueillir 2 lignes
        BADGE_W = W - x0 - 18
        br = QRectF(BADGE_X, BADGE_Y, BADGE_W, BADGE_H)
        rg = QLinearGradient(br.left(), 0, br.right(), 0)
        rg.setColorAt(0.0, QColor(26, 140, 255, 55))
        rg.setColorAt(1.0, QColor(0, 207, 255, 18))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rg))
        p.drawRoundedRect(br, 6, 6)
        # Accent gauche
        p.setBrush(QBrush(QColor(C_BLUE)))
        p.drawRoundedRect(QRectF(BADGE_X, BADGE_Y, 3, BADGE_H), 1.5, 1.5)

        # ── Icône rang (28×28, centrée verticalement dans le badge) ──
        ICON_SIZE = 28
        rank_icon = _get_rank_pixmap(self._tier_id, ICON_SIZE)
        icon_x = BADGE_X + 8
        icon_y = BADGE_Y + (BADGE_H - ICON_SIZE) // 2
        if rank_icon:
            p.drawPixmap(icon_x, icon_y, rank_icon)
            text_x = icon_x + ICON_SIZE + 5
        else:
            text_x = BADGE_X + 16

        # ── Texte rang — word wrap sur 2 lignes si nécessaire ──
        font_rank = QFont("Consolas", 10, QFont.Weight.Bold)
        p.setFont(font_rank)
        p.setPen(QPen(QColor(C_TEXT)))
        p.drawText(
            QRectF(text_x, BADGE_Y + 2, W - text_x - 12, BADGE_H - 4),
            Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
            self._rank,
        )

        # ── Pilules W / L ──
        self._draw_stat_pill(p, x0 + 8, 58, "W", str(self._wins),  QColor(WIN_GREEN))
        self._draw_stat_pill(p, x0 + 100, 58, "L", str(self._losses), QColor(LOSS_RED))

        # ── Streak ──
        if self._streak_val > 0 and self._streak_type:
            self._draw_streak(p, x0 + 8, 96, W)

        # ── MMR ──
        self._draw_mmr_section(p, x0 + 8, 126, W)

        p.restore()

    # ──────────────────────────────────────────────────────────────
    #  Pilule W / L
    # ──────────────────────────────────────────────────────────────
    def _draw_stat_pill(self, p, x, y, label, value, color):
        w_p, h_p = 84, 34
        r, g, b = color.red(), color.green(), color.blue()

        pill_g = QLinearGradient(x, y, x, y + h_p)
        pill_g.setColorAt(0.0, QColor(r, g, b, 32))
        pill_g.setColorAt(1.0, QColor(r, g, b, 10))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(pill_g))
        p.drawRoundedRect(QRectF(x, y, w_p, h_p), 8, 8)

        p.setPen(QPen(QColor(r, g, b, 80), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x + .5, y + .5, w_p - 1, h_p - 1), 8, 8)

        font_lbl = QFont("Consolas", 7, QFont.Weight.Bold)
        p.setFont(font_lbl); p.setPen(QPen(color))
        p.drawText(QRectF(x + 6, y + 2, 20, 14),
                   Qt.AlignmentFlag.AlignCenter, label)

        font_val = QFont("Consolas", 14, QFont.Weight.Bold)
        p.setFont(font_val); p.setPen(QPen(QColor(C_TEXT)))
        p.drawText(QRectF(x + 6, y + 10, w_p - 12, 22),
                   Qt.AlignmentFlag.AlignCenter, value)

    # ──────────────────────────────────────────────────────────────
    #  Streak pulsant
    # ──────────────────────────────────────────────────────────────
    def _draw_streak(self, p, x, y, W):
        is_win   = self._streak_type == "win"
        sc       = QColor(WIN_GREEN) if is_win else QColor(LOSS_RED)
        icon     = "W" if is_win else "L"
        label    = f"{icon}  {self._streak_val} {'WIN' if is_win else 'LOSS'} STREAK"
        sw       = W - x - 18
        sr       = QRectF(x, y, sw, 26)

        pa = int(38 + 32 * self._pulse)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(sc.red(), sc.green(), sc.blue(), pa)))
        p.drawRoundedRect(sr, 6, 6)

        ba = int(110 + 90 * self._pulse)
        p.setPen(QPen(QColor(sc.red(), sc.green(), sc.blue(), ba), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x + .5, y + .5, sw - 1, 25), 6, 6)

        font_s = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(font_s); p.setPen(QPen(sc))
        p.drawText(sr, Qt.AlignmentFlag.AlignCenter, label)

    # ──────────────────────────────────────────────────────────────
    #  Section MMR / delta
    # ──────────────────────────────────────────────────────────────
    def _draw_mmr_section(self, p, x, y, W):
        mw = W - x - 18
        mr = QRectF(x, y, mw, 42)

        mg = QLinearGradient(x, y, x + mw, y)
        mg.setColorAt(0.0, QColor(255, 215, 0, 22))
        mg.setColorAt(1.0, QColor(255, 215, 0, 5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(mg))
        p.drawRoundedRect(mr, 7, 7)

        # Accent doré gauche
        p.setBrush(QBrush(QColor(C_GOLD)))
        p.drawRoundedRect(QRectF(x, y, 3, 42), 1.5, 1.5)

        # Label "MMR"
        font_lbl = QFont("Consolas", 7)
        p.setFont(font_lbl); p.setPen(QPen(QColor(C_MUTE)))
        p.drawText(QRectF(x + 10, y + 2, 40, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "MMR")

        mmr_str = str(self._mmr) if self._mmr is not None else "---"

        if self._mmr_mode in ("both", "mmr"):
            font_mmr = QFont("Consolas", 16, QFont.Weight.Bold)
            p.setFont(font_mmr); p.setPen(QPen(QColor(C_GOLD)))
            p.drawText(QRectF(x + 10, y + 12, mw - 20, 24),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       mmr_str)

        if self._mmr_mode in ("both", "delta") and self._mmr_change != 0:
            sign  = "+" if self._mmr_change > 0 else ""
            ds    = f"{sign}{self._mmr_change}"
            dc    = QColor(WIN_GREEN) if self._mmr_change > 0 else QColor(LOSS_RED)

            if self._mmr_mode == "both":
                font_d = QFont("Consolas", 9, QFont.Weight.Bold)
                p.setFont(font_d); p.setPen(QPen(dc))
                p.drawText(QRectF(x + 96, y + 20, 60, 20),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           ds)
            else:
                font_d = QFont("Consolas", 16, QFont.Weight.Bold)
                p.setFont(font_d); p.setPen(QPen(dc))
                p.drawText(QRectF(x + 10, y + 12, mw - 20, 24),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           ds)

    # ──────────────────────────────────────────────────────────────
    #  Couche 7 — Barre W/L bas de page
    # ──────────────────────────────────────────────────────────────
    def _draw_bottom_bar(self, p, W, H):
        p.save()
        bh = 5
        by = H - 16
        bx = 14
        bw = W - 28
        r  = 2.5

        # Fond
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#1A1E2A")))
        p.drawRoundedRect(QRectF(bx, by, bw, bh), r, r)

        if self._winrate > 0:
            fw = bw * self._winrate
            win_g = QLinearGradient(bx, 0, bx + fw, 0)
            win_g.setColorAt(0.0, QColor(WIN_GREEN))
            win_g.setColorAt(1.0, QColor(NEON_CYAN))
            p.setBrush(QBrush(win_g))
            p.drawRoundedRect(QRectF(bx, by, fw, bh), r, r)

            # Reflet haut
            shine = QLinearGradient(0, by, 0, by + bh)
            shine.setColorAt(0.0, QColor(255, 255, 255, 65))
            shine.setColorAt(0.6, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(shine))
            p.drawRoundedRect(QRectF(bx, by, fw, bh / 2), r, r)

        # Marqueur 50 %
        mx = bx + bw * 0.5
        p.setPen(QPen(QColor(255, 255, 255, 55), 1))
        p.drawLine(QPointF(mx, by - 2), QPointF(mx, by + bh + 2))

        # Labels
        font_b = QFont("Consolas", 6)
        p.setFont(font_b); p.setPen(QPen(QColor(C_MUTE)))
        p.drawText(QRectF(bx, by + bh + 1, bw, 10),
                   Qt.AlignmentFlag.AlignLeft,  f"{self._wins}W")
        p.drawText(QRectF(bx, by + bh + 1, bw - 2, 10),
                   Qt.AlignmentFlag.AlignRight, f"{self._losses}L")
        p.restore()

    # ──────────────────────────────────────────────────────────────
    #  Couche 8 — Reflet glassmorphism haut
    # ──────────────────────────────────────────────────────────────
    def _draw_glass_sheen(self, p, W, H):
        p.save()
        r  = 14
        sh = QLinearGradient(0, 0, 0, H * 0.44)
        sh.setColorAt(0.0, QColor(255, 255, 255, 20))
        sh.setColorAt(0.5, QColor(255, 255, 255, 5))
        sh.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(sh))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H * 0.44), r - 1, r - 1)
        p.restore()

    # ──────────────────────────────────────────────────────────────
    #  Interface publique
    # ──────────────────────────────────────────────────────────────
    def update_stats(self, d: dict, mmr_mode: str = "both"):
        self._wins        = d.get("wins",        0)
        self._losses      = d.get("losses",      0)
        self._streak_val  = d.get("streak_val",  0)
        self._streak_type = d.get("streak_type", "")
        self._mmr         = d.get("mmr",         None)
        self._mmr_change  = d.get("mmr_change",  0)
        self._rank        = d.get("rank",        "Unranked")
        self._tier_id     = d.get("tier_id",     0)
        self._mmr_mode    = mmr_mode

        total = self._wins + self._losses
        self._winrate = (self._wins / total) if total > 0 else 0.5
        self.update()