# overlays/aurora.py
# Overlay "aurora" — 500×84 — Rectangle horizontal premium
# Anime : scan line, hex pulsant, barre winrate avec glow

import sys, os, math
from PyQt6.QtCore    import Qt, QTimer, QRectF, QPointF
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui     import (
    QColor, QPainter, QBrush, QPen,
    QLinearGradient, QRadialGradient, QFont, QPolygonF, QPixmap
)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))

_RANK_FOLDER = os.path.join(BASE_DIR, "all rank")
_rank_cache: dict = {}

def _get_rank_pixmap(tier_id: int, size: int = 38):
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

OVERLAY_NAME = "aurora"
OVERLAY_SIZE = (500, 84)

# ── Palette ────────────────────────────────────────────────
C_BG       = "#0A0C10"
C_BG2      = "#12151C"
C_BG3      = "#1A1E2A"
C_BLUE     = "#1A8CFF"
C_ORG      = "#FF6B00"
C_TEXT     = "#E8ECF4"
C_MUTE     = "#5A6275"
C_GREEN    = "#3AE08A"
C_GOLD     = "#FFD700"
NEON_CYAN  = "#00CFFF"
WIN_GREEN  = "#00E676"
LOSS_RED   = "#FF3D57"


def _hex(color: str, alpha: int = 255) -> QColor:
    """Helper : crée un QColor depuis un code hex avec alpha optionnel."""
    c = QColor(color)
    c.setAlpha(alpha)
    return c


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(*OVERLAY_SIZE)

        # Données par défaut
        self._d = {
            "wins": 7, "losses": 3, "total": 10,
            "winrate": 70, "streak_val": 3, "streak_type": "win",
            "mmr": 1024, "mmr_change": 48, "rank": "Diamond II",
        }
        self._mmr_mode   = "both"
        self._winrate    = 0.7

        # Animation state
        self._tick       = 0
        self._scan_y     = -20      # scan line Y
        self._pulse      = 0.0      # 0.0 → 1.0 → 0.0 (streak glow)
        self._pulse_dir  = 1
        self._bar_fill   = 0.0      # croît jusqu'à self._winrate au lancement
        self._launched   = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(28)       # ≈ 36 fps

    # ── Animation tick ──────────────────────────────────────
    def _animate(self):
        self._tick += 1
        W, H = OVERLAY_SIZE

        # Scan line (de haut en bas en boucle)
        self._scan_y = (self._scan_y + 1.2) % (H + 20)

        # Pulse streak
        speed = 0.04 if self._d.get("streak_val", 0) >= 3 else 0.02
        self._pulse += speed * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._pulse_dir = 1

        # Barre winrate — animation d'entrée
        if self._bar_fill < self._winrate:
            self._bar_fill = min(self._bar_fill + 0.008, self._winrate)

        self.update()

    # ── Mise à jour des stats ────────────────────────────────
    def update_stats(self, d: dict, mmr_mode: str = "both"):
        self._d        = d
        self._mmr_mode = mmr_mode
        wins   = d.get("wins", 0)
        losses = d.get("losses", 0)
        total  = wins + losses
        target = (wins / total) if total > 0 else 0.5
        # Re-trigger bar animation si changement
        if abs(target - self._winrate) > 0.001:
            self._bar_fill = max(0.0, self._bar_fill - 0.01)
        self._winrate = target
        self.update()

    # ── paintEvent principal ─────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        W, H = OVERLAY_SIZE
        d = self._d

        # ╔══════════════════════════════════════════════╗
        # ║  1. FOND PRINCIPAL (polygone coins coupés)   ║
        # ╚══════════════════════════════════════════════╝
        CUT = 10
        shape = QPolygonF([
            QPointF(CUT, 0),
            QPointF(W - CUT, 0),
            QPointF(W, CUT),
            QPointF(W, H - CUT),
            QPointF(W - CUT, H),
            QPointF(CUT, H),
            QPointF(0, H - CUT),
            QPointF(0, CUT),
        ])

        bg = QLinearGradient(0, 0, W, H)
        bg.setColorAt(0.00, QColor("#0C0F16"))
        bg.setColorAt(0.45, QColor("#0F1520"))
        bg.setColorAt(1.00, QColor("#0A0C10"))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(shape)

        # ╔══════════════════════════════════════════════╗
        # ║  2. SCAN LINE animée                         ║
        # ╚══════════════════════════════════════════════╝
        sy = self._scan_y
        scan = QLinearGradient(0, sy - 10, 0, sy + 10)
        scan.setColorAt(0.0, _hex(NEON_CYAN, 0))
        scan.setColorAt(0.5, _hex(NEON_CYAN, 22))
        scan.setColorAt(1.0, _hex(NEON_CYAN, 0))
        p.setBrush(QBrush(scan))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(shape)

        # ╔══════════════════════════════════════════════╗
        # ║  3. BORDURE dégradée cyan → orange           ║
        # ╚══════════════════════════════════════════════╝
        bord = QLinearGradient(0, 0, W, 0)
        bord.setColorAt(0.00, _hex(C_BLUE, 0))
        bord.setColorAt(0.10, _hex(C_BLUE))
        bord.setColorAt(0.40, _hex(NEON_CYAN))
        bord.setColorAt(0.65, _hex(C_ORG))
        bord.setColorAt(0.90, _hex(C_ORG))
        bord.setColorAt(1.00, _hex(C_ORG, 0))
        p.setPen(QPen(QBrush(bord), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(shape)

        # Ligne top (plus visible, effet rail)
        rail = QLinearGradient(0, 0, W, 0)
        rail.setColorAt(0.00, _hex(NEON_CYAN, 0))
        rail.setColorAt(0.15, _hex(NEON_CYAN, 200))
        rail.setColorAt(0.55, _hex(C_ORG, 160))
        rail.setColorAt(0.85, _hex(C_ORG, 200))
        rail.setColorAt(1.00, _hex(C_ORG, 0))
        p.setPen(QPen(QBrush(rail), 1.5))
        p.drawLine(CUT, 1, W - CUT, 1)

        # ╔══════════════════════════════════════════════╗
        # ║  SECTION GAUCHE — RANG (x: 0 → 130)         ║
        # ╚══════════════════════════════════════════════╝
        LX = 14      # left margin
        SEC1_W = 116

        # Trait accent vertical gauche
        vline = QLinearGradient(LX, 0, LX, H)
        vline.setColorAt(0.0, _hex(NEON_CYAN, 0))
        vline.setColorAt(0.5, _hex(NEON_CYAN, 200))
        vline.setColorAt(1.0, _hex(NEON_CYAN, 0))
        p.setPen(QPen(QBrush(vline), 2))
        p.drawLine(LX, 8, LX, H - 8)

        # ── Hexagone rang ──────────────────────────────
        HEX_CX = LX + 32
        HEX_CY = H // 2
        HEX_R  = 22
        hex_poly = QPolygonF()
        for i in range(6):
            angle = math.pi / 6 + i * math.pi / 3
            hex_poly.append(QPointF(
                HEX_CX + HEX_R * math.cos(angle),
                HEX_CY + HEX_R * math.sin(angle),
            ))

        # Fond hex
        hex_bg = QRadialGradient(HEX_CX, HEX_CY, HEX_R)
        hex_bg.setColorAt(0.0, QColor("#1C2438"))
        hex_bg.setColorAt(1.0, QColor("#0D1018"))
        p.setBrush(QBrush(hex_bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(hex_poly)

        # Couleur bordure hex selon rang
        rank_str  = d.get("rank", "Unranked")
        hex_col   = self._rank_color(rank_str)

        # Pulsation si streak ≥ 3
        streak_val  = d.get("streak_val", 0)
        streak_type = d.get("streak_type", "")
        if streak_val >= 3:
            sc = WIN_GREEN if streak_type == "win" else LOSS_RED
            alpha_pulse = int(150 + 105 * self._pulse)
            hex_col = _hex(sc, alpha_pulse)

        p.setPen(QPen(hex_col, 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(hex_poly)

        # Halo hex (glow externe)
        if streak_val >= 3:
            sc = WIN_GREEN if streak_type == "win" else LOSS_RED
            glow_a = int(40 * self._pulse)
            glow_r = QRadialGradient(HEX_CX, HEX_CY, HEX_R + 10)
            glow_r.setColorAt(0.6, _hex(sc, glow_a))
            glow_r.setColorAt(1.0, _hex(sc, 0))
            p.setBrush(QBrush(glow_r))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(HEX_CX, HEX_CY), HEX_R + 10, HEX_R + 10)

        # Icône de rang dans l'hexagone (remplace la lettre initiale)
        tier_id   = d.get("tier_id", 0)
        rank_icon = _get_rank_pixmap(tier_id, 38)
        if rank_icon:
            p.drawPixmap(
                int(HEX_CX - rank_icon.width()  / 2),
                int(HEX_CY - rank_icon.height() / 2),
                rank_icon,
            )
        else:
            # Fallback : lettre initiale si PNG absent
            rank_init = rank_str[0].upper() if rank_str else "?"
            p.setPen(QColor(C_TEXT))
            f_init = QFont("Consolas", 14, QFont.Weight.Bold)
            p.setFont(f_init)
            p.drawText(
                QRectF(HEX_CX - HEX_R, HEX_CY - HEX_R, HEX_R * 2, HEX_R * 2),
                Qt.AlignmentFlag.AlignCenter,
                rank_init,
            )

        # Texte rang + "SESSION"
        txt_rx = HEX_CX + HEX_R + 5
        txt_rw = LX + SEC1_W - txt_rx - 2

        p.setPen(QColor(C_TEXT))
        f_rank = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(f_rank)
        p.drawText(
            QRectF(txt_rx, 8, txt_rw, H // 2 - 4),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
            | Qt.TextFlag.TextWordWrap,
            rank_str,
        )

        p.setPen(_hex(C_MUTE, 180))
        f_sess = QFont("Consolas", 7)
        p.setFont(f_sess)
        p.drawText(
            QRectF(txt_rx, H // 2 + 2, txt_rw, H // 2 - 8),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            "SESSION",
        )

        # ── Séparateur 1 ──────────────────────────────
        DIV1 = LX + SEC1_W + 4
        self._draw_divider(p, DIV1, H)

        # ╔══════════════════════════════════════════════╗
        # ║  SECTION CENTRE — W/L + BARRE               ║
        # ╚══════════════════════════════════════════════╝
        CX     = DIV1 + 12
        SEC2_W = 188

        wins   = d.get("wins", 0)
        losses = d.get("losses", 0)
        wr_pct = d.get("winrate", 50)

        # W (grand, vert)
        p.setPen(_hex(WIN_GREEN))
        f_big = QFont("Consolas", 20, QFont.Weight.Bold)
        p.setFont(f_big)
        p.drawText(
            QRectF(CX, 4, 44, H // 2 + 6),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            str(wins),
        )

        # séparateur "/"
        p.setPen(_hex(C_MUTE, 140))
        f_sep = QFont("Consolas", 12)
        p.setFont(f_sep)
        p.drawText(
            QRectF(CX + 42, 4, 16, H // 2 + 6),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter,
            "/",
        )

        # L (grand, rouge)
        p.setPen(_hex(LOSS_RED))
        p.setFont(f_big)
        p.drawText(
            QRectF(CX + 56, 4, 44, H // 2 + 6),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            str(losses),
        )

        # WR % (petit, blanc)
        p.setPen(_hex(C_TEXT, 200))
        f_wr = QFont("Consolas", 8, QFont.Weight.Bold)
        p.setFont(f_wr)
        p.drawText(
            QRectF(CX + 104, 4, 78, H // 2 + 6),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            f"{wr_pct}% WR",
        )

        # ── Barre winrate ──────────────────────────────
        BAR_X = CX
        BAR_Y = H // 2 + 9
        BAR_H = 5
        BAR_W = SEC2_W - 4

        # Track
        p.setBrush(QColor(C_BG3))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(BAR_X, BAR_Y, BAR_W, BAR_H), BAR_H / 2, BAR_H / 2)

        # Fill animé
        fill = BAR_W * self._bar_fill
        if fill > 1:
            bar_gr = QLinearGradient(BAR_X, 0, BAR_X + BAR_W, 0)
            bar_gr.setColorAt(0.0, QColor(WIN_GREEN))
            bar_gr.setColorAt(0.6, QColor(NEON_CYAN))
            bar_gr.setColorAt(1.0, QColor(C_BLUE))
            p.setBrush(QBrush(bar_gr))
            p.drawRoundedRect(QRectF(BAR_X, BAR_Y, fill, BAR_H), BAR_H / 2, BAR_H / 2)

            # Glow tip
            tip_x = BAR_X + fill
            glow_tip = QRadialGradient(tip_x, BAR_Y + BAR_H / 2, BAR_H * 4)
            glow_tip.setColorAt(0.0, _hex(NEON_CYAN, 100))
            glow_tip.setColorAt(1.0, _hex(NEON_CYAN, 0))
            p.setBrush(QBrush(glow_tip))
            p.drawEllipse(
                QPointF(tip_x, BAR_Y + BAR_H / 2),
                BAR_H * 4, BAR_H * 4,
            )

        # Streak indicator sous la barre
        STREAK_Y = BAR_Y + BAR_H + 4
        if streak_val > 0:
            sc      = WIN_GREEN if streak_type == "win" else LOSS_RED
            sl      = "W" if streak_type == "win" else "L"
            s_alpha = int(180 + 75 * self._pulse)
            p.setPen(_hex(sc, s_alpha))
            f_streak = QFont("Consolas", 7, QFont.Weight.Bold)
            p.setFont(f_streak)
            streak_text = f"STREAK  {sl}×{streak_val}"
            p.drawText(
                QRectF(BAR_X, STREAK_Y, BAR_W, 14),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                streak_text,
            )
        else:
            p.setPen(_hex(C_MUTE, 100))
            f_no = QFont("Consolas", 7)
            p.setFont(f_no)
            p.drawText(
                QRectF(BAR_X, STREAK_Y, BAR_W, 14),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                "no streak",
            )

        # ── Séparateur 2 ──────────────────────────────
        DIV2 = CX + SEC2_W + 4
        self._draw_divider(p, DIV2, H)

        # ╔══════════════════════════════════════════════╗
        # ║  SECTION DROITE — MMR                        ║
        # ╚══════════════════════════════════════════════╝
        RX   = DIV2 + 12
        RW   = W - RX - 14

        mmr        = d.get("mmr")
        mmr_change = d.get("mmr_change", 0)
        mode       = self._mmr_mode

        # Halo or MMR
        mmr_glow = QRadialGradient(RX + RW / 2, H / 2, RW * 0.85)
        mmr_glow.setColorAt(0.0, _hex(C_GOLD, 18))
        mmr_glow.setColorAt(1.0, _hex(C_GOLD, 0))
        p.setBrush(QBrush(mmr_glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(RX - 4, 0, RW + 14, H))

        # Label "MMR"
        p.setPen(_hex(C_MUTE, 180))
        f_lbl = QFont("Consolas", 7, QFont.Weight.Bold)
        p.setFont(f_lbl)
        p.drawText(
            QRectF(RX, 8, RW, 14),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "MMR",
        )

        # Valeur MMR principale
        if mode in ("both", "mmr") and mmr is not None:
            p.setPen(QColor(C_GOLD))
            f_mmr = QFont("Consolas", 18, QFont.Weight.Bold)
            p.setFont(f_mmr)
            p.drawText(
                QRectF(RX, 16, RW, 38),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                str(mmr),
            )
        elif mode == "delta":
            dc  = WIN_GREEN if mmr_change >= 0 else LOSS_RED
            dtx = f"+{mmr_change}" if mmr_change >= 0 else str(mmr_change)
            p.setPen(QColor(dc))
            f_d = QFont("Consolas", 18, QFont.Weight.Bold)
            p.setFont(f_d)
            p.drawText(
                QRectF(RX, 16, RW, 38),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                dtx,
            )

        # Delta MMR (sous le MMR, en mode "both")
        if mode == "both":
            dc  = WIN_GREEN if mmr_change >= 0 else LOSS_RED
            dtx = f"+{mmr_change}" if mmr_change >= 0 else str(mmr_change)
            p.setPen(QColor(dc))
            f_d2 = QFont("Consolas", 9, QFont.Weight.Bold)
            p.setFont(f_d2)
            p.drawText(
                QRectF(RX, H - 26, RW, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                dtx,
            )

        # Trait accent vertical droit
        vright = QLinearGradient(W - LX, 0, W - LX, H)
        vright.setColorAt(0.0, _hex(C_ORG, 0))
        vright.setColorAt(0.5, _hex(C_ORG, 200))
        vright.setColorAt(1.0, _hex(C_ORG, 0))
        p.setPen(QPen(QBrush(vright), 2))
        p.drawLine(W - LX, 8, W - LX, H - 8)

        p.end()

    # ── Helpers ─────────────────────────────────────────────
    def _draw_divider(self, p: QPainter, x: int, H: int):
        dg = QLinearGradient(x, 0, x, H)
        dg.setColorAt(0.0, _hex(C_BG3, 0))
        dg.setColorAt(0.5, _hex(C_BG3, 220))
        dg.setColorAt(1.0, _hex(C_BG3, 0))
        p.setPen(QPen(QBrush(dg), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(x, 10, x, H - 10)

    def _rank_color(self, rank: str) -> QColor:
        r = rank.lower()
        if "ssl" in r or "supersonic" in r:
            return QColor("#FF00FF")
        if "grand champ" in r:
            return QColor(NEON_CYAN)
        if "champ" in r:
            return QColor("#8B5CF6")
        if "diamond" in r:
            return QColor(C_BLUE)
        if "platinum" in r:
            return QColor("#00BFFF")
        if "gold" in r:
            return QColor(C_GOLD)
        if "silver" in r:
            return QColor("#C0C0C0")
        if "bronze" in r:
            return QColor("#CD7F32")
        return QColor(C_MUTE)