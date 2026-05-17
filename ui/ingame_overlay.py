"""ui/ingame_overlay.py — InGameMMROverlay (affichage MMR sur le Tab scoreboard RL)."""
import math
from PyQt6.QtCore    import Qt, QPointF, QRectF, QTimer
from PyQt6.QtWidgets import QMainWindow, QWidget, QLabel, QApplication
from PyQt6.QtGui     import QPainter, QColor, QFont, QPixmap
from utils import get_rank_pixmap, get_playlist_pixmap, _PLAYLIST_ID_TO_KEY, enforce_topmost


class InGameMMROverlay(QMainWindow):
    _PLAYLIST_IDS  = {"1v1": 10, "2v2": 11, "3v3": 13}
    _RANKED_PL_IDS = [10, 11, 13]
    _Y_ORG0            = 0.590
    _ROW_H             = 0.055
    _ORANGE_HEADER_GAP = 0.133
    _X_TEXT            = 0.443
    _X_RANK_ICON       = 0.188
    _X_PLAYLIST_ICON   = 0.160

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint  |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool                 |
            Qt.WindowType.BypassWindowManagerHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._players      = []
        self._stats        = {}
        self._playlist_key = "2v2"
        self._rank_mode    = "2v2"
        self._show_peak    = True
        self._game_state   = {}
        self._container = QWidget(self)
        self._container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._container.setStyleSheet("background:transparent;")
        self.setCentralWidget(self._container)
        self._labels: list = []
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._rebuild)
        self._top_timer = QTimer(self)
        self._top_timer.timeout.connect(self._enforce_topmost)
        self._top_timer.start(2000)

    def showEvent(self, e):
        super().showEvent(e)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._container.setGeometry(0, 0, screen.width(), screen.height())
        self._refresh_timer.start(2000)
        self._rebuild()
        self._enforce_topmost()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._refresh_timer.stop()

    def _enforce_topmost(self):
        enforce_topmost(self)

    def set_data(self, players: list, stats: dict, playlist_key: str,
                 rank_mode: str = "", game_state: dict = None):
        self._players      = players or []
        self._stats        = stats or {}
        self._playlist_key = playlist_key
        if rank_mode: self._rank_mode = rank_mode
        if game_state is not None: self._game_state = game_state

    def set_show_peak(self, show: bool):
        self._show_peak = show
        if self.isVisible(): self._rebuild()

    def _best_playlist_stats(self, playlists: dict):
        best_id = None; best_stats = None; best_tier = -1; best_mmr = -1
        for pid in self._RANKED_PL_IDS:
            s = playlists.get(pid)
            if not s: continue
            t = s.get("tier_id", 0); m = s.get("mmr", 0)
            if t > best_tier or (t == best_tier and m > best_mmr):
                best_tier = t; best_mmr = m; best_id = pid; best_stats = s
        return best_id, best_stats

    def _player_rank_tier(self, p: dict):
        pid   = p.get("PrimaryId", "")
        entry = self._stats.get(pid) if pid else None
        if not entry or entry.get("status") != "ok":
            return 0, None
        all_pls = entry.get("playlists", {})
        mode    = self._rank_mode
        if mode == "best":
            pl_id, pl_stats = self._best_playlist_stats(all_pls)
            pl_key = _PLAYLIST_ID_TO_KEY.get(pl_id, "2v2") if pl_id else None
        else:
            pl_key  = mode
            pl_stats = all_pls.get(self._PLAYLIST_IDS.get(mode, 11))
        if not pl_stats: return 0, pl_key
        return pl_stats.get("tier_id", 0), pl_key

    def _player_html(self, p: dict, mmr_px: int, peak_px: int) -> str:
        pid   = p.get("PrimaryId", "")
        entry = self._stats.get(pid) if pid else None
        status = entry.get("status", "loading") if entry else ("bot" if not pid else "loading")
        _font = "'Rajdhani','Segoe UI Semibold','Arial Narrow',Arial,sans-serif"
        mmr_style  = (f"font-size:{mmr_px}px;font-weight:800;letter-spacing:0.5px;color:white;font-family:{_font};text-shadow:0 1px 4px rgba(0,0,0,0.9);")
        peak_style = (f"font-size:{peak_px}px;font-weight:600;letter-spacing:0.3px;color:#FFD700;font-family:{_font};text-shadow:0 1px 3px rgba(0,0,0,0.8);")
        mute_style = (f"font-size:{mmr_px}px;font-weight:700;letter-spacing:0.5px;color:rgba(200,200,200,0.6);font-family:{_font};text-shadow:0 1px 3px rgba(0,0,0,0.7);")
        if status == "ok":
            all_pls = entry.get("playlists", {})
            mode    = self._rank_mode
            if mode == "best": _, pl_stats = self._best_playlist_stats(all_pls)
            else: pl_stats = all_pls.get(self._PLAYLIST_IDS.get(mode, 11))
            if pl_stats:
                mmr  = pl_stats.get("mmr", 0); peak = pl_stats.get("peak_mmr")
                if mmr:
                    html = f'<span style="{mmr_style}">[{mmr}]</span>'
                    if peak and self._show_peak:
                        html += f'&nbsp;<span style="{peak_style}">peak[{peak}]</span>'
                    return html
            return f'<span style="{mute_style}">[--]</span>'
        if status == "loading": return f'<span style="{mute_style}">[…]</span>'
        if status == "error":
            http = entry.get("http_code", 0) if entry else 0
            sym  = "🔒" if http == 403 else "?"
            return f'<span style="{mute_style}">[{sym}]</span>'
        return ""

    def _rebuild(self):
        for lbl_w in self._labels: lbl_w.deleteLater()
        self._labels.clear()
        if not self._players: return
        screen = QApplication.primaryScreen().geometry()
        sw, sh = screen.width(), screen.height()
        sort_key = lambda p: (-p.get("Score", 0), p.get("PrimaryId", ""))
        blues   = sorted([p for p in self._players if p.get("TeamNum") == 0], key=sort_key)
        oranges = sorted([p for p in self._players if p.get("TeamNum") == 1], key=sort_key)
        row_h    = int(sh * self._ROW_H)
        x_text   = int(sw * self._X_TEXT)
        mmr_px   = max(16, int(sh * 0.020))
        peak_px  = max(11, int(sh * 0.013))
        icon_sz  = max(26, int(sh * 0.070))
        pl_sz    = max(16, int(sh * 0.040))
        n_blues  = max(len(blues), 1)
        y_blue0  = int(sh * (self._Y_ORG0 - (n_blues - 1) * self._ROW_H - self._ORANGE_HEADER_GAP))
        y_org0   = int(sh * self._Y_ORG0)
        x_rank     = int(sw * self._X_RANK_ICON)
        x_playlist = int(sw * self._X_PLAYLIST_ICON)
        for team_players, y0 in [(blues, y_blue0), (oranges, y_org0)]:
            for j, player in enumerate(team_players):
                html = self._player_html(player, mmr_px, peak_px)
                y    = y0 + j * row_h
                if html:
                    lbl_w = QLabel(self._container)
                    lbl_w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                    lbl_w.setTextFormat(Qt.TextFormat.RichText)
                    lbl_w.setText(html)
                    lbl_w.setStyleSheet("background:transparent;")
                    lbl_w.adjustSize()
                    lbl_w.move(x_text - lbl_w.width(), y - lbl_w.height() // 2)
                    lbl_w.show(); self._labels.append(lbl_w)
                tier_id, pl_key = self._player_rank_tier(player)
                if tier_id:
                    rank_pm = get_rank_pixmap(tier_id, icon_sz)
                    if rank_pm:
                        rank_lbl = QLabel(self._container)
                        rank_lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                        rank_lbl.setStyleSheet("background:transparent;")
                        rank_lbl.setPixmap(rank_pm); rank_lbl.adjustSize()
                        rank_lbl.move(x_rank - rank_lbl.width() // 2, y - rank_lbl.height() // 2)
                        rank_lbl.show(); self._labels.append(rank_lbl)
                if pl_key:
                    pl_pm = get_playlist_pixmap(pl_key, pl_sz)
                    if pl_pm:
                        pl_lbl = QLabel(self._container)
                        pl_lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                        pl_lbl.setStyleSheet("background:transparent;")
                        pl_lbl.setPixmap(pl_pm); pl_lbl.adjustSize()
                        pl_lbl.move(x_playlist - pl_lbl.width() // 2, y - pl_lbl.height() // 2)
                        pl_lbl.show(); self._labels.append(pl_lbl)