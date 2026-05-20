"""ui/tabs.py — 3 onglets modernes : Stats, Overlay & Auto, Paramètres."""
import time, json, os, sys, urllib.parse
from PyQt6.QtCore    import Qt, QTimer, QSize, QUrl, pyqtSignal as _pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QScrollArea, QCheckBox,
    QSlider, QStyle, QSizePolicy, QProgressBar, QDialog, QFileDialog,
    QStackedWidget, QTabWidget,
)
from PyQt6.QtGui import QDesktopServices, QColor, QCursor, QFont, QIcon
from style import (
    C_BG, C_BG2, C_BG3, C_BLUE, C_ORG, C_TEXT, C_MUTE, C_GREEN, C_GOLD, C_RED,
    C_CYAN, C_PURPLE, C_GLASS, C_GLASS_HOVER,
    GRADIENT_BLUE, GRADIENT_ORG, GRADIENT_GREEN, GRADIENT_RED, GRADIENT_GOLD, GRADIENT_CYAN,
    card, lbl, btn, hsep, stat_block, gradient_btn, glass_card,
)
from utils import (
    _key_display, get_rank_pixmap, extract_auth_code,
)
from config import platform_from_id, id_from_primary_id
from ui.dialogs import (
    KeyCaptureWidget, OverlayBindDialog, _overlay_hotkey_display,
)


# ═══════════════════════════════════════════════════════════════════════════
#  ONGLET 1 : STATS (TrakerTab + PlayersTab fusionnés)
# ═══════════════════════════════════════════════════════════════════════════
class StatsTab(QWidget):
    """Tableau de bord : connexion, stats session, MMR, joueurs en match."""

    _PLAYLIST_KEY_TO_ID = {"1v1": 10, "2v2": 11, "3v3": 13}
    _TRACKER_COOLDOWN_S = 3
    _tracker_last_open: dict = {}
    _URL_SLUG = {"epic": "epic", "steam": "steam", "ps4": "psn", "xbox": "xbl", "switch": "switch"}

    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._players = []
        self._build()
        self._connect_signals()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        # ── Barre de connexion ────────────────────────────────────────────
        conn = card()
        cl = QHBoxLayout(conn)
        cl.setContentsMargins(14, 10, 14, 10)
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{C_MUTE};font-size:14px;background:transparent;")
        self._status_lbl = lbl("Déconnecté", C_MUTE, 9)
        port_lbl = lbl("Port :", C_MUTE, 9)
        self._port_edit = QLineEdit(str(self.app.config["statsapi_port"]))
        self._port_edit.setFixedWidth(55)
        reconn_btn = btn("↻", bg=C_BG3, size=9)
        reconn_btn.setFixedSize(28, 28)
        reconn_btn.clicked.connect(self.app.reconnect_statsapi)
        self._player_lbl = lbl("—", C_TEXT, 10, bold=True)
        cl.addWidget(self._dot); cl.addSpacing(6)
        cl.addWidget(self._status_lbl); cl.addSpacing(8)
        cl.addWidget(self._player_lbl, 1)
        cl.addWidget(port_lbl); cl.addWidget(self._port_edit)
        cl.addSpacing(4); cl.addWidget(reconn_btn)
        root.addWidget(conn)

        # ── Carte MMR / Rang ──────────────────────────────────────────────
        mmr_card = card()
        ml = QHBoxLayout(mmr_card)
        ml.setContentsMargins(16, 12, 16, 12)
        ml.setSpacing(12)

        # Bloc icône + rang
        rank_v = QVBoxLayout()
        rank_v.setSpacing(2)
        rank_v.addWidget(lbl("RANG", C_MUTE, 8), alignment=Qt.AlignmentFlag.AlignCenter)
        self._rank_icon_lbl = QLabel()
        self._rank_icon_lbl.setFixedSize(36, 36)
        self._rank_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon_lbl.setStyleSheet("background:transparent;")
        rank_v.addWidget(self._rank_icon_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        self._rank_lbl = lbl("—", C_MUTE, 9)
        rank_v.addWidget(self._rank_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        ml.addLayout(rank_v)

        # Bloc MMR
        mmr_v = QVBoxLayout()
        mmr_v.setSpacing(0)
        mmr_v.addWidget(lbl("MMR", C_MUTE, 8), alignment=Qt.AlignmentFlag.AlignCenter)
        self._mmr_lbl = QLabel("—")
        self._mmr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mmr_lbl.setStyleSheet(f"color:{C_GOLD};font-size:28px;font-weight:900;background:transparent;")
        mmr_v.addWidget(self._mmr_lbl)
        self._delta_lbl = lbl("", C_GREEN, 11)
        mmr_v.addWidget(self._delta_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        ml.addLayout(mmr_v)

        # Bloc playlist
        pl_v = QVBoxLayout()
        pl_v.setSpacing(4)
        pl_v.addWidget(lbl("PLAYLIST", C_MUTE, 8), alignment=Qt.AlignmentFlag.AlignCenter)
        self._pl_btns = {}
        pl_row = QHBoxLayout()
        pl_row.setSpacing(4)
        for key in ("1v1", "2v2", "3v3"):
            b = btn(key, bg=C_BG3, fg=C_MUTE, size=9)
            b.setFixedSize(44, 28)
            b.clicked.connect(lambda _, k=key: self.app.select_playlist(k))
            pl_row.addWidget(b); self._pl_btns[key] = b
        pl_v.addLayout(pl_row)
        ref_btn = QPushButton()
        ref_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ref_btn.setFixedSize(26, 26)
        ref_btn.setIcon(ref_btn.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        ref_btn.setIconSize(QSize(14, 14))
        ref_btn.setStyleSheet(f"QPushButton{{background:{C_BG3};border:none;border-radius:4px;}}QPushButton:hover{{background:{C_BG3}cc;}}")
        ref_btn.clicked.connect(lambda: self.app.fetch_mmr_async(force=True))
        pl_v.addWidget(ref_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        ml.addLayout(pl_v)
        root.addWidget(mmr_card)

        # ── Bloc Victoires / Ratio / Défaites ─────────────────────────────
        wl = QHBoxLayout()
        wl.setSpacing(8)
        # Victoires
        w_card = card()
        w_card.setStyleSheet(f"QFrame{{background:rgba(0,230,118,0.04);border:1px solid rgba(0,230,118,0.12);border-radius:10px;}}")
        wc = QVBoxLayout(w_card)
        wc.setContentsMargins(0, 8, 0, 8)
        wc.setSpacing(2)
        wc.addWidget(lbl("VICTOIRES", C_GREEN, 7), alignment=Qt.AlignmentFlag.AlignCenter)
        self._wins_lbl = QLabel("0")
        self._wins_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wins_lbl.setStyleSheet(f"color:{C_GREEN};font-size:36px;font-weight:800;background:transparent;")
        wc.addWidget(self._wins_lbl)
        wl.addWidget(w_card, 1)
        # Winrate
        wr_card = card()
        wr_card.setStyleSheet(f"QFrame{{background:rgba(26,140,255,0.04);border:1px solid rgba(26,140,255,0.12);border-radius:10px;}}")
        wrc = QVBoxLayout(wr_card)
        wrc.setContentsMargins(0, 8, 0, 8)
        wrc.setSpacing(2)
        wrc.addWidget(lbl("WIN RATE", C_BLUE, 7), alignment=Qt.AlignmentFlag.AlignCenter)
        self._wr_lbl = QLabel("—")
        self._wr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wr_lbl.setStyleSheet(f"color:{C_BLUE};font-size:36px;font-weight:800;background:transparent;")
        wrc.addWidget(self._wr_lbl)
        wl.addWidget(wr_card, 1)
        # Défaites
        l_card = card()
        l_card.setStyleSheet(f"QFrame{{background:rgba(255,61,87,0.04);border:1px solid rgba(255,61,87,0.12);border-radius:10px;}}")
        lc = QVBoxLayout(l_card)
        lc.setContentsMargins(0, 8, 0, 8)
        lc.setSpacing(2)
        lc.addWidget(lbl("DÉFAITES", C_RED, 7), alignment=Qt.AlignmentFlag.AlignCenter)
        self._losses_lbl = QLabel("0")
        self._losses_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._losses_lbl.setStyleSheet(f"color:{C_RED};font-size:36px;font-weight:800;background:transparent;")
        lc.addWidget(self._losses_lbl)
        wl.addWidget(l_card, 1)
        root.addLayout(wl)

        # ── Mini infos session ────────────────────────────────────────────
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        for caption, attr in [("TOTAL", "total"), ("SÉRIE", "streak"), ("DURÉE", "clock")]:
            c = card()
            c.setStyleSheet(f"QFrame{{background:{C_BG3};border:1px solid {C_GLASS};border-radius:8px;}}")
            cl3 = QVBoxLayout(c)
            cl3.setContentsMargins(8, 6, 8, 8)
            cl3.setSpacing(2)
            cl3.addWidget(lbl(caption, C_MUTE, 7), alignment=Qt.AlignmentFlag.AlignCenter)
            val = QLabel("—")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setStyleSheet(f"color:{C_TEXT};font-size:16px;font-weight:700;background:transparent;")
            cl3.addWidget(val)
            info_row.addWidget(c, 1)
            setattr(self, f"_{attr}_lbl", val)
        root.addLayout(info_row)

        # ── Barre winrate (progression) ───────────────────────────────────
        self._wr_progress = QProgressBar()
        self._wr_progress.setRange(0, 100)
        self._wr_progress.setValue(0)
        self._wr_progress.setTextVisible(False)
        self._wr_progress.setFixedHeight(6)
        self._wr_progress.setStyleSheet(
            f"QProgressBar{{border:none;background:{C_BG3};border-radius:3px;}}"
            f"QProgressBar::chunk{{background:{GRADIENT_BLUE};border-radius:3px;}}"
        )
        root.addWidget(self._wr_progress)

        # ── Boutons +/− pour ajustement manuel ────────────────────────────
        adj_row = QHBoxLayout()
        adj_row.setSpacing(4)
        adj_row.addStretch()
        bp = btn("+ Victoire", bg="rgba(0,230,118,0.15)", fg=C_GREEN, size=9)
        bp.clicked.connect(lambda: self.app.add("win"))
        bm = btn("− Défaite", bg="rgba(255,61,87,0.15)", fg=C_RED, size=9)
        bm.clicked.connect(lambda: self.app.add("loss"))
        adj_row.addWidget(bp)
        adj_row.addSpacing(4)
        adj_row.addWidget(bm)
        adj_row.addStretch()
        root.addLayout(adj_row)

        # ── Messages StatsAPI ─────────────────────────────────────────────
        dbg = card()
        dl = QVBoxLayout(dbg)
        dl.setContentsMargins(12, 8, 12, 8)
        dl.addWidget(lbl("MESSAGES STATSAPI", C_MUTE, 8))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(60)
        self._log.setMaximumBlockCount(200)
        self._log.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._log.setStyleSheet(
            f"QPlainTextEdit{{background:{C_BG3};color:{C_MUTE};border:none;"
            f"font-family:'Consolas','Courier New',monospace;font-size:8px;padding:4px;border-radius:4px;}}")
        dl.addWidget(self._log)
        root.addWidget(dbg)

        # ── Joueurs en match ──────────────────────────────────────────────
        players_header = QHBoxLayout()
        players_header.addWidget(lbl("JOUEURS EN MATCH", C_MUTE, 9))
        players_header.addStretch()
        open_all_btn = btn("Tout ouvrir →", bg=C_BG3, size=8)
        open_all_btn.clicked.connect(self._open_all)
        players_header.addWidget(open_all_btn)
        root.addLayout(players_header)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        scroll = QScrollArea()
        scroll.setWidget(self._list_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;border:none;")
        scroll.setFixedHeight(140)
        root.addWidget(scroll)
        self._show_empty_players()

        reset_btn = btn("Réinitialiser la session", bg=C_BG, fg=C_MUTE, size=9)
        reset_btn.clicked.connect(self.app.reset_session)
        root.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _show_empty_players(self):
        self._clear_players()
        empty = lbl("Aucun match en cours", C_MUTE, 10)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addWidget(empty)
        self._list_layout.addStretch()

    def _clear_players(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _connect_signals(self):
        s = self.app.signals
        s.status_changed.connect(self._on_status)
        s.player_detected.connect(lambda name, _: self._player_lbl.setText(name if name else "—"))
        s.match_result.connect(self._refresh)
        s.log_event.connect(self._on_log)
        s.mmr_updated.connect(self._on_mmr)
        s.mmr_error.connect(self._on_mmr_error)
        s.players_updated.connect(self._on_players)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)

    def _on_status(self, state, msg):
        colors = {"connected": C_GREEN, "error": C_ORG}
        c = colors.get(state, C_MUTE)
        self._dot.setStyleSheet(f"color:{c};font-size:14px;background:transparent;")
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color:{c};font-size:9px;background:transparent;")

    def _refresh(self, _=None):
        a = self.app
        self._wins_lbl.setText(str(a.wins))
        self._losses_lbl.setText(str(a.losses))
        total = a.wins + a.losses
        self._total_lbl.setText(str(total))
        if total == 0:
            self._wr_lbl.setText("—")
            self._wr_progress.setValue(0)
            self._streak_lbl.setText("—")
        else:
            wr = round(a.wins / total * 100)
            self._wr_lbl.setText(f"{wr}%")
            self._wr_progress.setValue(wr)
            if a.streak > 1:
                icon = "🔥" if a.streak_type == "win" else "💀"
                self._streak_lbl.setText(f"{icon} {a.streak}")
            else:
                self._streak_lbl.setText("—")

    def _on_mmr(self):
        d = self.app.all_mmr.get(self.app.selected_playlist, {})
        mmr = d.get("mmr")
        self._mmr_lbl.setText(str(mmr) if mmr else "—")
        rank_name = d.get("rank", "")
        self._rank_lbl.setText(rank_name if rank_name else "Unranked")
        tier_id = d.get("tier_id", 0)
        pm = get_rank_pixmap(tier_id, 34)
        if pm:
            self._rank_icon_lbl.setPixmap(pm)
        else:
            self._rank_icon_lbl.clear()
        chg = d.get("mmr_change", 0)
        if chg != 0 and mmr:
            sign = "+" if chg > 0 else ""
            clr = C_GREEN if chg > 0 else C_RED
            icon = "▲" if chg > 0 else "▼"
            self._delta_lbl.setText(f"{icon} {sign}{chg}")
            self._delta_lbl.setStyleSheet(f"color:{clr};font-size:11px;font-weight:700;background:transparent;")
        else:
            self._delta_lbl.setText("")
        self.app.highlight_playlist_btns(self._pl_btns)

    def _on_mmr_error(self, msg):
        self._mmr_lbl.setText("⚠")
        self._mmr_lbl.setStyleSheet(f"color:{C_ORG};font-size:28px;font-weight:700;background:transparent;")
        self._delta_lbl.setText("")
        self._rank_lbl.setText(msg[:40])
        self._rank_lbl.setStyleSheet(f"color:{C_ORG};font-size:9px;background:transparent;")

    def _on_log(self, msg):
        self._log.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {msg}")
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _tick_clock(self):
        elapsed = int(time.time() - self.app.session_start)
        m, s = divmod(elapsed, 60)
        h, m = divmod(m, 60)
        if h > 0:
            self._clock_lbl.setText(f"{h}h{m:02d}")
        else:
            self._clock_lbl.setText(f"{m}:{s:02d}")

    def get_port(self):
        return self._port_edit.text().strip()

    # ── Joueurs en match ─────────────────────────────────────────────────
    def _on_players(self, players):
        self._players = players
        if not players:
            self._show_empty_players()
            return
        self._clear_players()
        blues = [p for p in players if p.get("TeamNum") == 0]
        oranges = [p for p in players if p.get("TeamNum") == 1]
        for team_name, team_color, team_players in [("🔵  BLEU", C_BLUE, blues), ("🟠  ORANGE", C_ORG, oranges)]:
            if team_players:
                self._list_layout.addWidget(lbl(team_name, team_color, 8, True))
                for p in team_players:
                    self._list_layout.addWidget(self._make_player_row(p, team_color))
        self._list_layout.addStretch()

    def _make_player_row(self, player, color):
        row = card(bg=C_BG2)
        row.setFixedHeight(48)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 4, 10, 4)
        primary_id = player.get("PrimaryId", "")
        platform = platform_from_id(primary_id)
        raw_id = id_from_primary_id(primary_id) or player.get("Name", "")
        user_id = raw_id if platform == "steam" else player.get("Name", raw_id)

        plat_lbl = QLabel(platform.upper())
        plat_lbl.setStyleSheet(f"color:{C_MUTE};background:{C_BG3};border-radius:3px;padding:1px 4px;font-size:7px;font-weight:700;border:none;")
        name_lbl = lbl(player.get("Name", "?"), color, 11, True)

        cache = getattr(self.app, "_ingame_stats_cache", {})
        entry = cache.get(primary_id, {})
        status = entry.get("status", "")
        pl_key = getattr(self.app, "selected_playlist", "3v3")
        pid_int = self._PLAYLIST_KEY_TO_ID.get(pl_key, 13)
        pl_data = entry.get("playlists", {}).get(pid_int, {})

        if status == "ok" and pl_data:
            mmr_text = f"{pl_data.get('tier_name', 'Unranked')}  {pl_data.get('mmr', 0)}"
            mmr_color = C_GOLD
        elif status == "loading":
            mmr_text = "⏳"
            mmr_color = C_MUTE
        elif status == "error":
            mmr_text = "—"
            mmr_color = C_MUTE
        else:
            mmr_text = ""
            mmr_color = C_MUTE
        mmr_lbl = lbl(mmr_text, mmr_color, 8, bold=(status == "ok"))
        stats_lbl = lbl(f"⚽{player.get('Goals',0)} 🅰{player.get('Assists',0)} 🛡{player.get('Saves',0)}", C_MUTE, 8)

        open_btn = btn("→", bg=C_BG3, size=8)
        open_btn.setFixedSize(24, 24)
        open_btn.clicked.connect(lambda _, uid=user_id, pl=platform: self._open_profile(uid, pl))

        rl.addWidget(plat_lbl)
        rl.addSpacing(6)
        rl.addWidget(name_lbl, 1)
        rl.addWidget(stats_lbl)
        rl.addSpacing(6)
        rl.addWidget(mmr_lbl)
        rl.addSpacing(4)
        rl.addWidget(open_btn)
        return row

    def _open_profile(self, user_id, platform):
        now = time.time()
        last = self._tracker_last_open.get(user_id, 0)
        if now - last < self._TRACKER_COOLDOWN_S:
            return
        self._tracker_last_open[user_id] = now
        slug = self._URL_SLUG.get(platform, platform)
        url = f"https://rocketleague.tracker.network/rocket-league/profile/{slug}/{urllib.parse.quote(user_id)}/overview"
        QDesktopServices.openUrl(QUrl(url))

    def _open_all(self):
        for p in self._players:
            primary_id = p.get("PrimaryId", "")
            pl = platform_from_id(primary_id)
            raw_id = id_from_primary_id(primary_id) or p.get("Name", "")
            user_id = raw_id if pl == "steam" else p.get("Name", raw_id)
            self._open_profile(user_id, pl)


# ═══════════════════════════════════════════════════════════════════════════
#  ONGLET 2 : OVERLAY & AUTO (OverlayTab + AutomationTab fusionnés)
# ═══════════════════════════════════════════════════════════════════════════
class OverlayAutoTab(QWidget):
    """Overlay en jeu + automatisations (skip, queue, freeplay, GG, overlay joueurs)."""

    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._active = False
        self._ctrl_active = False
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Section : OVERLAY PRINCIPAL ───────────────────────────────────
        root.addWidget(lbl("OVERLAY", C_BLUE, 9, True))
        ov_card = card()
        ovl = QVBoxLayout(ov_card)
        ovl.setContentsMargins(14, 12, 14, 12)
        ovl.setSpacing(8)

        # Toggle
        self._toggle_btn = btn("▶  ACTIVER L'OVERLAY", bg=C_BG3, fg=C_TEXT, size=11)
        self._toggle_btn.setFixedHeight(38)
        self._toggle_btn.clicked.connect(self._toggle)
        ovl.addWidget(self._toggle_btn)

        # Mode
        from overlay_widgets import _load_overlay_plugins
        mode_row = QHBoxLayout()
        mode_row.addWidget(lbl("Format :", C_TEXT, 10))
        self._mode_combo = QComboBox()
        self._available_modes = _load_overlay_plugins()
        self._MODE_MAP = {}
        self._MODE_REVERSE = {}
        for idx, (mode_name, mode_info) in enumerate(sorted(self._available_modes.items())):
            size = mode_info.get("size", (0, 0))
            self._mode_combo.addItem(f"{mode_name}  ({size[0]}×{size[1]})")
            self._MODE_MAP[idx] = mode_name
            self._MODE_REVERSE[mode_name] = idx
        self._mode_combo.setFixedWidth(200)
        self._mode_combo.currentIndexChanged.connect(
            lambda i: self._set_mode(self._MODE_MAP.get(i, "compact")))
        mode_row.addStretch()
        mode_row.addWidget(self._mode_combo)
        ovl.addLayout(mode_row)

        # Affichage MMR
        mmr_row = QHBoxLayout()
        mmr_row.addWidget(lbl("Affichage MMR :", C_TEXT, 10))
        self._mmr_btns = {}
        for mode, label in [("both", "MMR+Delta"), ("mmr", "MMR"), ("delta", "Delta")]:
            b = btn(label, bg=C_BG3, fg=C_MUTE, size=9)
            b.setFixedHeight(28)
            b.clicked.connect(lambda _, m=mode: self._set_mmr_mode(m))
            mmr_row.addWidget(b)
            self._mmr_btns[mode] = b
        mmr_row.addStretch()
        ovl.addLayout(mmr_row)

        # Affichage du rang des joueurs (ingame overlay)
        rank_mode_row = QHBoxLayout()
        rank_mode_row.addWidget(lbl("Rang joueurs :", C_TEXT, 10))
        self._rank_mode_btns = {}
        saved_rank_mode = self.app.config.get("tab_rank_mode", "2v2")
        for mode_key, mode_label in [("1v1", "1v1"), ("2v2", "2v2"), ("3v3", "3v3"), ("best", "Meilleur")]:
            b = btn(mode_label, bg=C_BG3, fg=C_MUTE, size=9)
            b.setFixedHeight(28)
            b.clicked.connect(lambda _, m=mode_key: self._set_rank_mode(m))
            rank_mode_row.addWidget(b)
            self._rank_mode_btns[mode_key] = b
        rank_mode_row.addStretch()
        ovl.addLayout(rank_mode_row)
        self._highlight_rank_mode(saved_rank_mode)
        root.addWidget(ov_card)

        # ── Section : OVERLAY MANETTE ──────────────────────────────────────
        ctrl_card = card()
        ctl = QVBoxLayout(ctrl_card)
        ctl.setContentsMargins(14, 10, 14, 10)
        ctl.setSpacing(6)
        ctl.addWidget(lbl("OVERLAY MANETTE", C_MUTE, 9))
        self._ctrl_toggle_btn = btn("🎮  ACTIVER L'OVERLAY MANETTE", bg=C_BG3, fg=C_TEXT, size=10)
        self._ctrl_toggle_btn.setFixedHeight(34)
        self._ctrl_toggle_btn.clicked.connect(self._toggle_controller)
        ctl.addWidget(self._ctrl_toggle_btn)
        style_row = QHBoxLayout()
        style_row.addWidget(lbl("Style :", C_TEXT, 10))
        self._ctrl_style_btns = {}
        for mode_key, mode_label in [("with_bg", "Avec fond"), ("transparent", "Transparent")]:
            b = btn(mode_label, bg=C_BG3, fg=C_MUTE, size=9)
            b.setFixedHeight(28)
            b.clicked.connect(lambda _, m=mode_key: self._set_ctrl_mode(m))
            style_row.addWidget(b)
            self._ctrl_style_btns[mode_key] = b
        style_row.addStretch()
        ctl.addLayout(style_row)
        ctl.addWidget(lbl("Déplaçable en jeu.", C_MUTE, 8))
        root.addWidget(ctrl_card)

        # ── Section : OVERLAY VITESSE BALLE ────────────────────────────────
        root.addWidget(lbl("OVERLAY VITESSE BALLE", C_BLUE, 9, True))

        ball_card = card()
        ball = QVBoxLayout(ball_card)
        ball.setContentsMargins(16, 14, 16, 14)
        ball.setSpacing(10)

        # ── En-tête : description + indicateur live ──────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        desc_col = QVBoxLayout()
        desc_col.setSpacing(2)
        desc_col.addWidget(lbl("Affiche la vitesse de la balle", C_TEXT, 10))
        desc_col.addWidget(lbl("en km/h sur votre écran en jeu.", C_MUTE, 9))
        header_row.addLayout(desc_col, 1)

        # Pastille vitesse live
        live_box = QFrame()
        live_box.setStyleSheet(f"background:{C_BG3};border-radius:8px;border:none;")
        live_box.setFixedSize(80, 44)
        live_v = QVBoxLayout(live_box)
        live_v.setContentsMargins(6, 4, 6, 4)
        live_v.setSpacing(0)
        live_v.addWidget(lbl("LIVE", C_MUTE, 7, bold=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self._ball_speed_val = QLabel("—")
        self._ball_speed_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ball_speed_val.setStyleSheet(f"color:{C_GOLD};font-size:18px;font-weight:900;background:transparent;")
        live_v.addWidget(self._ball_speed_val)
        live_v.addWidget(lbl("km/h", C_MUTE, 7), alignment=Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(live_box)
        ball.addLayout(header_row)

        # ── Barre de vitesse ─────────────────────────────────────────────
        self._ball_speed_bar = QProgressBar()
        self._ball_speed_bar.setRange(0, 216)
        self._ball_speed_bar.setValue(0)
        self._ball_speed_bar.setTextVisible(False)
        self._ball_speed_bar.setFixedHeight(5)
        self._ball_speed_bar.setStyleSheet(
            f"QProgressBar{{background:{C_BG3};border-radius:3px;border:none;}}"
            f"QProgressBar::chunk{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {C_GREEN},stop:0.6 {C_GOLD},stop:1 {C_ORG});border-radius:3px;}}")
        ball.addWidget(self._ball_speed_bar)

        ball.addWidget(hsep())

        # ── Bouton ON/OFF ─────────────────────────────────────────────────
        # Variable d'état
        self._ball_overlay_active = bool(self.app.config.get("ball_overlay_active", False))
        self._ball_overlay_win = None

        self._ball_ovl_btn = btn(
            "⚽  DÉSACTIVER L'OVERLAY VITESSE" if self._ball_overlay_active
            else "⚽  ACTIVER L'OVERLAY VITESSE",
            bg=C_ORG if self._ball_overlay_active else C_BG3,
            fg=C_TEXT, size=10)
        self._ball_ovl_btn.setFixedHeight(36)
        self._ball_ovl_btn.clicked.connect(self._toggle_ball_overlay)
        ball.addWidget(self._ball_ovl_btn)

        # ── Taille du texte ───────────────────────────────────────────────
        font_size = int(self.app.config.get("ball_overlay_font_size", 28))

        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_icon = lbl("Aa", C_MUTE, 9)
        font_icon.setFixedWidth(20)
        font_row.addWidget(font_icon)

        self._ball_font_slider = QSlider(Qt.Orientation.Horizontal)
        self._ball_font_slider.setRange(14, 64)
        self._ball_font_slider.setValue(font_size)
        self._ball_font_slider.setFixedHeight(20)
        font_row.addWidget(self._ball_font_slider, 1)

        self._ball_font_val = QLabel(f"{font_size}px")
        self._ball_font_val.setFixedWidth(36)
        self._ball_font_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._ball_font_val.setStyleSheet(f"color:{C_TEXT};font-size:10px;font-weight:700;background:transparent;")
        font_row.addWidget(self._ball_font_val)
        ball.addLayout(font_row)

        font_hint = lbl("Taille du texte affiché sur l'overlay", C_MUTE, 8)
        ball.addWidget(font_hint)

        def _on_font_size(v):
            self._ball_font_val.setText(f"{v}px")
            self.app.config["ball_overlay_font_size"] = v
            if self._ball_overlay_win is not None:
                self._ball_overlay_win.set_font_size(v)
        self._ball_font_slider.valueChanged.connect(_on_font_size)

        # ── Conseil ───────────────────────────────────────────────────────
        tip_row = QHBoxLayout()
        tip_row.setSpacing(6)
        tip_row.addWidget(lbl("💡", C_GOLD, 10))
        tip_row.addWidget(lbl("Glisse l'overlay directement sur ton écran pour le repositionner.", C_MUTE, 8))
        tip_row.addStretch()
        ball.addLayout(tip_row)

        root.addWidget(ball_card)

        # Réactiver l'overlay si actif dans la config
        if self._ball_overlay_active:
            QTimer.singleShot(200, lambda: self._toggle_ball_overlay(save=False))

        # Connecter le signal de vitesse balle pour l'affichage dans l'onglet
        self.app.signals.ball_speed_updated.connect(self._on_ball_speed)

        # ── Section : AUTOMATISATIONS ─────────────────────────────────────
        root.addWidget(hsep())
        root.addWidget(lbl("AUTOMATISATIONS", C_BLUE, 9, True))

        auto_card = card()
        autol = QVBoxLayout(auto_card)
        autol.setContentsMargins(14, 12, 14, 12)
        autol.setSpacing(8)

        def _parse_delay(v, default):
            try:
                return float(v.replace(",", "."))
            except:
                return default

        def _delay_row(label, cfg_key, default):
            row = QHBoxLayout()
            row.addWidget(lbl(label, C_TEXT, 10))
            field = QLineEdit(str(self.app.config.get(cfg_key, default)))
            field.setFixedWidth(60)
            field.setAlignment(Qt.AlignmentFlag.AlignCenter)
            field.textChanged.connect(lambda v, k=cfg_key, d=default: self.app.config.__setitem__(k, _parse_delay(v, d)))
            row.addStretch()
            row.addWidget(field)
            row.addWidget(lbl("sec", C_MUTE, 9))
            return row

        def _key_row(label, cfg_key, default):
            row = QHBoxLayout()
            row.addWidget(lbl(label, C_TEXT, 10))
            row.addStretch()
            w = KeyCaptureWidget(self.app.config.get(cfg_key, default))
            w.key_changed.connect(lambda v, k=cfg_key: self.app.config.__setitem__(k, v))
            row.addWidget(w)
            return row

        cfg = self.app.config

        # Skip replay
        self._skip_cb = QCheckBox("Skip replay automatique")
        self._skip_cb.setChecked(bool(cfg.get("auto_skip_replay", False)))
        self._skip_cb.toggled.connect(lambda v: cfg.__setitem__("auto_skip_replay", v))
        autol.addWidget(self._skip_cb)
        autol.addLayout(_key_row("Touche skip :", "skip_replay_key", "key:space"))
        autol.addLayout(_delay_row("Délai skip :", "skip_replay_delay", 0))

        # Auto rejouer
        self._queue_cb = QCheckBox("Rejouer automatiquement")
        self._queue_cb.setChecked(bool(cfg.get("auto_queue", False)))
        self._queue_cb.toggled.connect(lambda v: cfg.__setitem__("auto_queue", v))
        autol.addWidget(self._queue_cb)
        autol.addLayout(_key_row("Touche rejouer :", "queue_key", "key:return"))
        autol.addLayout(_delay_row("Délai rejouer :", "queue_delay", 5))

        # Auto freeplay
        self._freeplay_cb = QCheckBox("Freeplay automatique")
        self._freeplay_cb.setChecked(bool(cfg.get("auto_freeplay", False)))
        self._freeplay_cb.toggled.connect(lambda v: cfg.__setitem__("auto_freeplay", v))
        autol.addWidget(self._freeplay_cb)
        autol.addLayout(_key_row("Touche freeplay :", "freeplay_key", "key:f"))
        autol.addLayout(_delay_row("Délai freeplay :", "freeplay_delay", 55))

        # Auto GG
        self._agg_cb = QCheckBox("GG automatique")
        self._agg_cb.setChecked(bool(cfg.get("auto_gg", False)))
        self._agg_cb.toggled.connect(lambda v: cfg.__setitem__("auto_gg", v))
        autol.addWidget(self._agg_cb)
        autol.addLayout(_key_row("Touche chat :", "auto_gg_key", "key:t"))
        autol.addLayout(_delay_row("Délai GG :", "auto_gg_delay", 4))
        gg_row = QHBoxLayout()
        gg_row.addWidget(lbl("Texte :", C_TEXT, 10))
        gg_row.addStretch()
        gg_field = QLineEdit(str(cfg.get("auto_gg_text", "gg")))
        gg_field.setFixedWidth(60)
        gg_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gg_field.textChanged.connect(lambda v: cfg.__setitem__("auto_gg_text", v))
        gg_row.addWidget(gg_field)
        autol.addLayout(gg_row)

        # Overlay joueurs hotkey
        autol.addWidget(hsep())
        po_label = lbl("OVERLAY JOUEURS (hotkey)", C_MUTE, 9)
        autol.addWidget(po_label)
        autol.addLayout(_key_row("Touche :", "players_overlay_key", "key:f7"))

        # Touche hold-to-show
        autol.addWidget(hsep())
        autol.addWidget(lbl("TOUCHE OVERLAY (maintenir)", C_MUTE, 9))
        hk_row = QHBoxLayout()
        self._hk_display = QLabel(_overlay_hotkey_display(self.app.config))
        self._hk_display.setFixedWidth(160)
        self._hk_display.setStyleSheet(f"background:{C_BG3};color:{C_TEXT};border-radius:4px;padding:4px 8px;font-size:10px;border:none;")
        hk_bind_btn = QPushButton("Configurer")
        hk_bind_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        hk_bind_btn.setStyleSheet(
            f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:4px 8px;font-size:9px;font-weight:700;}}"
            f"QPushButton:hover{{background:{C_BLUE};color:{C_TEXT};}}")
        hk_bind_btn.clicked.connect(self._reconfigure_hotkey)
        hk_row.addWidget(self._hk_display)
        hk_row.addWidget(hk_bind_btn)
        hk_row.addStretch()
        autol.addLayout(hk_row)

        root.addWidget(auto_card)

        # Restaurer l'état sauvegardé
        self._ctrl_active = cfg.get("controller_overlay_enabled", False)
        self._update_ctrl_btn_style()
        saved_mode = cfg.get("overlay_mode", "compact")
        if saved_mode not in self._available_modes:
            saved_mode = next(iter(self._available_modes), "compact")
        self._mode_combo.setCurrentIndex(self._MODE_REVERSE.get(saved_mode, 0))
        self._set_mode(saved_mode)
        self._set_mmr_mode(cfg.get("mmr_display_mode", "both"))
        if cfg.get("overlay_active", False):
            self._toggle(save=False)

    def _toggle(self, *args, save=True):
        self._active = not self._active
        if save:
            self.app.config["overlay_active"] = self._active
            self.app.config.save()
        if self._active:
            self.app.overlay_win.show()
            self._toggle_btn.setText("■  DÉSACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(
                f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:6px;padding:5px 12px;font-size:11px;font-weight:700;}}"
                f"QPushButton:hover{{background:#e06000;}}")
        else:
            self.app.overlay_win.hide()
            self._toggle_btn.setText("▶  ACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:6px;padding:5px 12px;font-size:11px;font-weight:700;}}"
                f"QPushButton:hover{{background:{C_BG3}cc;}}")

    def _set_mode(self, mode):
        self.app.overlay_win.set_mode(mode)
        self.app.config["overlay_mode"] = mode
        idx = self._MODE_REVERSE.get(mode, 0)
        if self._mode_combo.currentIndex() != idx:
            self._mode_combo.setCurrentIndex(idx)

    def _set_mmr_mode(self, mode):
        self.app.overlay_win.set_mmr_mode(mode)
        self.app.config["mmr_display_mode"] = mode
        for m, b in self._mmr_btns.items():
            active = m == mode
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};color:{C_TEXT if active else C_MUTE};"
                f"border:none;border-radius:6px;padding:4px 10px;font-size:9px;font-weight:700;}}"
                f"{'' if active else 'QPushButton:hover{color:' + C_TEXT + ';}'}")

    def _set_rank_mode(self, mode):
        """Change le mode de sélection du rang pour l'overlay ingame (1v1, 2v2, 3v3, best)."""
        self.app.config["tab_rank_mode"] = mode
        self.app.config.save()
        self.app.ingame_mmr_overlay._rank_mode = mode
        self._highlight_rank_mode(mode)

    def _highlight_rank_mode(self, mode):
        """Met à jour le style des boutons de sélection du rang joueur."""
        for m, b in self._rank_mode_btns.items():
            active = m == mode
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};color:{C_TEXT if active else C_MUTE};"
                f"border:none;border-radius:6px;padding:4px 10px;font-size:9px;font-weight:700;}}"
                f"{'' if active else 'QPushButton:hover{color:' + C_TEXT + ';}'}")

    def _toggle_controller(self):
        self._ctrl_active = not self._ctrl_active
        self.app.config["controller_overlay_enabled"] = self._ctrl_active
        self.app.config.save()
        if self._ctrl_active:
            self.app.controller_overlay.show()
        else:
            self.app.controller_overlay.hide()
        self._update_ctrl_btn_style()

    def _update_ctrl_btn_style(self):
        if self._ctrl_active:
            self._ctrl_toggle_btn.setText("🎮  DÉSACTIVER L'OVERLAY MANETTE")
            self._ctrl_toggle_btn.setStyleSheet(
                f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:6px;padding:4px 10px;font-size:10px;font-weight:700;}}"
                f"QPushButton:hover{{background:#e06000;}}")
        else:
            self._ctrl_toggle_btn.setText("🎮  ACTIVER L'OVERLAY MANETTE")
            self._ctrl_toggle_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:6px;padding:4px 10px;font-size:10px;font-weight:700;}}"
                f"QPushButton:hover{{background:{C_BG3}cc;}}")

    def _set_ctrl_mode(self, mode, save=True):
        self.app.controller_overlay.set_mode(mode)
        if save:
            self.app.config["controller_overlay_mode"] = mode
            self.app.config.save()
        for m, b in self._ctrl_style_btns.items():
            active = m == mode
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};color:{C_TEXT if active else C_MUTE};"
                f"border:none;border-radius:6px;padding:4px 10px;font-size:9px;font-weight:700;}}"
                f"{'' if active else 'QPushButton:hover{color:' + C_TEXT + ';}'}")

    def _toggle_ball_overlay(self, *args, save=True):
        self._ball_overlay_active = not self._ball_overlay_active
        if save:
            self.app.config["ball_overlay_active"] = self._ball_overlay_active
            self.app.config.save()
        if self._ball_overlay_active:
            if self._ball_overlay_win is None:
                from ui.ball_speed_overlay import BallSpeedOverlay
                self._ball_overlay_win = BallSpeedOverlay(self.app.signals, self.app.config)
                pos = self.app.config.get("pos_ball_overlay")
                if pos:
                    self._ball_overlay_win.move(*pos)
            self._ball_overlay_win.show()
            self._ball_ovl_btn.setText("⚽  DÉSACTIVER OVERLAY VITESSE")
            self._ball_ovl_btn.setStyleSheet(
                f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:6px;padding:4px 10px;font-size:10px;font-weight:700;}}"
                f"QPushButton:hover{{background:#e06000;}}")
        else:
            if self._ball_overlay_win:
                self._ball_overlay_win.hide()
            self._ball_ovl_btn.setText("⚽  ACTIVER L'OVERLAY VITESSE")
            self._ball_ovl_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:6px;padding:4px 10px;font-size:10px;font-weight:700;}}"
                f"QPushButton:hover{{background:{C_BG3}cc;}}")

    def _on_ball_speed(self, kmh: float):
        self._ball_speed_val.setText(f"{kmh:.0f}")
        self._ball_speed_bar.setValue(min(216, int(kmh)))

    def _reconfigure_hotkey(self):
        dlg = OverlayBindDialog(self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.is_controller:
                self.app.config["overlay_hotkey_type"] = "controller"
                self.app.config["overlay_hotkey_controller_btn"] = dlg.controller_btn
                self.app.config["overlay_hotkey_key"] = ""
            else:
                self.app.config["overlay_hotkey_type"] = "key"
                self.app.config["overlay_hotkey_key"] = dlg.captured_key or ""
                self.app.config["overlay_hotkey_controller_btn"] = 0
            self.app.config.save()
            self._hk_display.setText(_overlay_hotkey_display(self.app.config))

    def refresh_preview(self, stats):
        if hasattr(self, "_preview") and hasattr(self._preview, "update_stats"):
            self._preview.update_stats(stats, self.app.config.get("mmr_display_mode", "both"))


# ═══════════════════════════════════════════════════════════════════════════
#  ONGLET 3 : PARAMÈTRES (SoundTab + SettingsTab fusionnés)
# ═══════════════════════════════════════════════════════════════════════════
_SOUND_EVENTS = [
    ("goal_scored",   "🎯  But marqué"),
    ("goal_conceded", "💀  But encaissé"),
    ("crossbar",      "🏐  Poteau / Barre"),
    ("demo_me",       "💥  Démoli (toi)"),
    ("demo_opponent", "🔥  Démolition adverse"),
    ("epic_save",     "🧤  Epic Save"),
    ("save",          "🛡  Save"),
]


class SettingsTab(QWidget):
    """Paramètres : joueur, mode streamer, anti-smurf, overlay résultat, OBS, webhook, sons, statsAPI, compte bot."""

    _bot_auth_done = _pyqtSignal(object)
    _bot_url_ready = _pyqtSignal(str)

    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._bot_auth_done.connect(self._on_auth_finished)
        self._bot_url_ready.connect(self._show_auth_url)
        self._streamer_active = self.app.config.get("streamer_mode", False)
        self._build()
        self._load_bot_account_on_startup()
        self._update_streamer_btn()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ── JOUEUR ────────────────────────────────────────────────────────
        root.addWidget(lbl("JOUEUR", C_BLUE, 9, True))
        player_card = card()
        pl = QVBoxLayout(player_card)
        pl.setContentsMargins(14, 10, 14, 10)
        pl.setSpacing(8)

        row_plat = QHBoxLayout()
        row_plat.addWidget(lbl("Plateforme :", C_TEXT, 10))
        self._platform = QComboBox()
        self._platform.addItems(["epic", "steam", "ps4", "xbox", "switch"])
        self._platform.setCurrentText(self.app.config["platform"])
        self._platform.setFixedWidth(110)
        row_plat.addStretch()
        row_plat.addWidget(self._platform)
        pl.addLayout(row_plat)
        self._platform.currentTextChanged.connect(self._on_platform_changed)

        row_user = QHBoxLayout()
        self._username_lbl = lbl("Pseudo :", C_TEXT, 10)
        row_user.addWidget(self._username_lbl)
        self._username = QLineEdit(self.app.config["username"])
        self._username.setFixedWidth(200)
        row_user.addStretch()
        row_user.addWidget(self._username)
        pl.addLayout(row_user)
        self._on_platform_changed(self._platform.currentText())
        root.addWidget(player_card)

        # ── MODE STREAMER ─────────────────────────────────────────────────
        streamer_card = card()
        stl = QVBoxLayout(streamer_card)
        stl.setContentsMargins(14, 10, 14, 10)
        stl.setSpacing(6)
        stl.addWidget(lbl("MODE STREAMER", C_MUTE, 9))
        self._streamer_btn = btn("🎥  ACTIVER LE MODE STREAMER", bg=C_BG3, fg=C_TEXT, size=10)
        self._streamer_btn.setFixedHeight(34)
        self._streamer_btn.clicked.connect(self._toggle_streamer)
        stl.addWidget(self._streamer_btn)
        mute_row = QHBoxLayout()
        mute_row.addWidget(lbl("Couper le son hors partie", C_TEXT, 10))
        self._streamer_mute_chk = QCheckBox()
        self._streamer_mute_chk.setChecked(self.app.config.get("streamer_mute_audio", True))
        self._streamer_mute_chk.stateChanged.connect(self._on_streamer_mute_changed)
        mute_row.addStretch()
        mute_row.addWidget(self._streamer_mute_chk)
        stl.addLayout(mute_row)
        self._streamer_hint = lbl("", C_GREEN, 9)
        stl.addWidget(self._streamer_hint)
        root.addWidget(streamer_card)

        # ── ANTI-SMURF ────────────────────────────────────────────────────
        smurf_card = card()
        sml = QVBoxLayout(smurf_card)
        sml.setContentsMargins(14, 10, 14, 10)
        sml.setSpacing(6)
        sml.addWidget(lbl("ANTI-SMURF", C_MUTE, 9))
        smurf_row = QHBoxLayout()
        smurf_row.addWidget(lbl("Détection des smurfs", C_TEXT, 10))
        self._smurf_cb = QCheckBox()
        self._smurf_cb.setChecked(bool(self.app.config.get("smurf_detection_enabled", True)))
        self._smurf_cb.toggled.connect(lambda v: self.app.config.__setitem__("smurf_detection_enabled", v))
        smurf_row.addStretch()
        smurf_row.addWidget(self._smurf_cb)
        sml.addLayout(smurf_row)
        root.addWidget(smurf_card)

        # ── OVERLAY RÉSULTAT ──────────────────────────────────────────────
        result_card = card()
        rl = QVBoxLayout(result_card)
        rl.setContentsMargins(14, 10, 14, 10)
        rl.setSpacing(6)
        rl.addWidget(lbl("OVERLAY VICTOIRE / DÉFAITE", C_MUTE, 9))
        r_on = QHBoxLayout()
        r_on.addWidget(lbl("Activer", C_TEXT, 10))
        self._result_overlay_enabled = QCheckBox()
        self._result_overlay_enabled.setChecked(self.app.config.get("result_overlay_enabled", True))
        r_on.addStretch()
        r_on.addWidget(self._result_overlay_enabled)
        rl.addLayout(r_on)
        r_th = QHBoxLayout()
        r_th.addWidget(lbl("Thème :", C_TEXT, 10))
        self._result_theme = QComboBox()
        self._result_theme.addItems(["auto", "rl_classic", "victory", "defeat", "neon", "dark_minimal"])
        self._result_theme.setCurrentText(self.app.config.get("result_overlay_theme", "auto"))
        self._result_theme.setFixedWidth(130)
        r_th.addStretch()
        r_th.addWidget(self._result_theme)
        rl.addLayout(r_th)
        root.addWidget(result_card)

        # ── INTÉGRATIONS ──────────────────────────────────────────────────
        root.addWidget(lbl("INTÉGRATIONS", C_BLUE, 9, True))

        # Webhook Discord
        wh_card = card()
        whl = QVBoxLayout(wh_card)
        whl.setContentsMargins(14, 10, 14, 10)
        whl.setSpacing(6)
        whl.addWidget(lbl("WEBHOOK DISCORD", C_MUTE, 9))
        self._wh_cb = QCheckBox("Envoyer le résultat sur Discord")
        self._wh_cb.setChecked(bool(self.app.config.get("webhook_enabled", False)))
        self._wh_cb.toggled.connect(lambda v: self.app.config.__setitem__("webhook_enabled", v))
        whl.addWidget(self._wh_cb)
        wh_edit = QLineEdit(str(self.app.config.get("webhook_url", "")))
        wh_edit.textChanged.connect(lambda v: self.app.config.__setitem__("webhook_url", v))
        whl.addLayout(self._labeled_row("URL :", wh_edit))
        root.addWidget(wh_card)

        # OBS
        obs_card = card()
        obsl = QVBoxLayout(obs_card)
        obsl.setContentsMargins(14, 10, 14, 10)
        obsl.setSpacing(6)
        obsl.addWidget(lbl("OBS WEBSOCKET", C_MUTE, 9))
        self._obs_cb = QCheckBox("Changer de scène OBS automatiquement")
        self._obs_cb.setChecked(bool(self.app.config.get("obs_ws_enabled", False)))
        self._obs_cb.toggled.connect(lambda v: self.app.config.__setitem__("obs_ws_enabled", v))
        obsl.addWidget(self._obs_cb)
        for label, key in [
            ("Host :", "obs_ws_host"), ("Port :", "obs_ws_port"),
            ("Password :", "obs_ws_password"),
            ("Scène en-jeu :", "obs_scene_ingame"),
            ("Scène lobby :", "obs_scene_outgame"),
        ]:
            edit = QLineEdit(str(self.app.config.get(key, "")))
            edit.setStyleSheet(f"background:{C_BG3};color:{C_TEXT};border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:4px 8px;font-size:10px;")
            edit.textChanged.connect(lambda v, k=key: self.app.config.__setitem__(k, v))
            obsl.addLayout(self._labeled_row(label, edit))
        root.addWidget(obs_card)

        # ── STATSAPI ──────────────────────────────────────────────────────
        api_card = card(bg="#091409")
        al = QVBoxLayout(api_card)
        al.setContentsMargins(14, 10, 14, 10)
        al.setSpacing(6)
        al.addWidget(lbl("STATSAPI", C_GREEN, 9, True))
        al.addWidget(lbl("Configure le fichier avant de lancer RL :", C_TEXT, 9))
        al.addWidget(lbl("TAGame\\Config\\DefaultStatsAPI.ini", C_GOLD, 9, True))
        ini_preview = QTextEdit()
        ini_preview.setReadOnly(True)
        ini_preview.setFixedHeight(50)
        ini_preview.setText("[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123")
        al.addWidget(ini_preview)
        open_btn = btn("📂 Ouvrir dossier Config RL", bg=C_BG3, size=9)
        open_btn.clicked.connect(self._open_rl_config)
        auto_btn = btn("⚡ Configurer auto", bg=C_GREEN, fg="#000000", size=9)
        auto_btn.clicked.connect(self._auto_configure_ini)
        btn_row = QHBoxLayout()
        btn_row.addWidget(open_btn)
        btn_row.addWidget(auto_btn)
        al.addLayout(btn_row)
        self._ini_status = lbl("", C_GREEN, 9)
        self._ini_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(self._ini_status)
        root.addWidget(api_card)

        # ── COMPTE BOT ────────────────────────────────────────────────────
        bot_card = card()
        bot_layout = QVBoxLayout(bot_card)
        bot_layout.setContentsMargins(14, 10, 14, 10)
        bot_layout.setSpacing(8)
        bot_layout.addWidget(lbl("COMPTE BOT API ROCKET LEAGUE", C_MUTE, 9))
        self.bot_status = lbl("Non configuré", C_ORG, 9)
        bot_layout.addWidget(self.bot_status)
        self.bot_login_btn = btn("🔑  Connecter un compte secondaire", bg=C_BLUE, fg=C_TEXT, size=10)
        self.bot_login_btn.clicked.connect(self._start_bot_auth)
        bot_layout.addWidget(self.bot_login_btn)

        self.bot_instructions = lbl(
            "1. Connecte-toi sur la page Epic qui vient de s'ouvrir.\n"
            "2. Clique sur « Ouvrir la page du code ».\n"
            "3. Copie le code ci-dessous et clique Valider.", C_MUTE, 9)
        self.bot_instructions.setWordWrap(True)
        self.bot_instructions.hide()
        bot_layout.addWidget(self.bot_instructions)

        self.bot_open_code_btn = btn("🌐  Ouvrir la page du code", bg=C_BG3, fg=C_TEXT, size=9)
        self.bot_open_code_btn.clicked.connect(self._open_auth_code_page)
        self.bot_open_code_btn.hide()
        bot_layout.addWidget(self.bot_open_code_btn)
        self._bot_auth_url = ""

        bot_code_row = QHBoxLayout()
        self.bot_code_edit = QLineEdit()
        self.bot_code_edit.setPlaceholderText("Colle le code Epic ici...")
        self.bot_code_edit.setStyleSheet(
            f"background:{C_BG3};color:{C_TEXT};border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:4px 8px;font-size:10px;")
        self.bot_code_edit.hide()
        self.bot_validate_btn = btn("✔  Valider", bg=C_GREEN, fg="#000000", size=9)
        self.bot_validate_btn.clicked.connect(self._submit_bot_code)
        self.bot_validate_btn.hide()
        bot_code_row.addWidget(self.bot_code_edit, 1)
        bot_code_row.addWidget(self.bot_validate_btn)
        bot_layout.addLayout(bot_code_row)

        self.bot_logout_btn = btn("❌  Supprimer le compte", bg=C_BG3, fg=C_MUTE, size=9)
        self.bot_logout_btn.clicked.connect(self._clear_bot_token)
        bot_layout.addWidget(self.bot_logout_btn)
        root.addWidget(bot_card)

        # ── SONS ──────────────────────────────────────────────────────────
        root.addWidget(lbl("SONS", C_BLUE, 9, True))

        vol_card = card()
        vl = QVBoxLayout(vol_card)
        vl.setContentsMargins(14, 10, 14, 10)
        vl.setSpacing(6)
        vl.addWidget(lbl("Volume global", C_MUTE, 9))
        vol_row = QHBoxLayout()
        vol_icon = lbl("🔈", C_TEXT, 12)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(int(self.app.config.get("sound_volume", 100)))
        self._vol_slider.setFixedHeight(20)
        self._vol_pct = lbl(f"{self._vol_slider.value()}%", C_TEXT, 10, bold=True)
        self._vol_pct.setFixedWidth(36)

        def _on_vol(v):
            self._vol_pct.setText(f"{v}%")
            self.app.config["sound_volume"] = v
        self._vol_slider.valueChanged.connect(_on_vol)
        vol_row.addWidget(vol_icon)
        vol_row.addWidget(self._vol_slider, 1)
        vol_row.addWidget(lbl("🔊", C_TEXT, 12))
        vol_row.addWidget(self._vol_pct)
        vl.addLayout(vol_row)
        root.addWidget(vol_card)

        for key, label in _SOUND_EVENTS:
            cfg_en = f"sound_{key}"
            cfg_file = f"snd_file_{key}"
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(14, 8, 14, 8)
            cl.setSpacing(4)
            cb = QCheckBox(label)
            cb.setChecked(bool(self.app.config.get(cfg_en, True)))
            cb.toggled.connect(lambda v, k=cfg_en: self.app.config.__setitem__(k, v))
            cl.addWidget(cb)
            file_row = QHBoxLayout()
            field = QLineEdit(self.app.config.get(cfg_file, ""))
            field.setPlaceholderText("son.wav")
            field.setStyleSheet(f"background:{C_BG3};color:{C_TEXT};border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:3px 8px;font-size:9px;")
            field.textChanged.connect(lambda v, k=cfg_file: self.app.config.__setitem__(k, v.strip()))
            browse_btn = QPushButton("📂")
            browse_btn.setFixedWidth(30)
            browse_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:3px;font-size:10px;}}"
                f"QPushButton:hover{{background:{C_BLUE};}}")
            browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            browse_btn.clicked.connect(lambda _, f=field, k=cfg_file: self._browse(f, k))
            test_btn = QPushButton("▶")
            test_btn.setFixedWidth(30)
            test_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_GREEN};border:none;border-radius:4px;padding:3px;font-size:10px;}}"
                f"QPushButton:hover{{background:{C_BG3};color:white;}}")
            test_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            test_btn.clicked.connect(lambda _, f=field: self.app._play_sound(f.text().strip()))
            file_row.addWidget(field, 1)
            file_row.addWidget(browse_btn)
            file_row.addWidget(test_btn)
            cl.addLayout(file_row)
            root.addWidget(c)

        # ── Bouton de sauvegarde ──────────────────────────────────────────
        save_btn = btn("💾  Sauvegarder les paramètres", bg=C_BLUE, fg=C_TEXT, size=11)
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save_all)
        root.addWidget(save_btn)
        self._save_lbl = lbl("", C_GREEN, 10)
        self._save_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._save_lbl)
        root.addStretch()

    def _labeled_row(self, label_text, widget):
        row = QHBoxLayout()
        row.addWidget(lbl(label_text, C_TEXT, 10))
        row.addStretch()
        row.addWidget(widget)
        return row

    # ── BOT AUTH ──────────────────────────────────────────────────────────
    def _start_bot_auth(self):
        import threading, webbrowser
        self.bot_login_btn.setEnabled(False)
        self.bot_status.setText("En attente du code Epic...")
        self.bot_status.setStyleSheet(f"color:{C_MUTE};")

        def _open():
            try:
                from rlapi.egs import EGS
                egs = EGS()
                auth_url = egs.get_auth_url()
                egs.close()
                _open_guest_browser("https://www.epicgames.com/id/login")
                self._bot_url_ready.emit(auth_url)
            except Exception as e:
                self.app.signals.log_event.emit(f"[Bot] Impossible d'ouvrir l'URL Epic : {e}")
        threading.Thread(target=_open, daemon=True).start()
        self.bot_instructions.show()
        self.bot_code_edit.show()
        self.bot_code_edit.clear()
        self.bot_code_edit.setFocus()
        self.bot_validate_btn.show()

    def _show_auth_url(self, auth_url: str):
        self._bot_auth_url = auth_url
        self.bot_open_code_btn.show()
        self.bot_code_edit.show()
        self.bot_code_edit.clear()
        self.bot_validate_btn.show()

    def _open_auth_code_page(self):
        if self._bot_auth_url:
            _open_guest_browser(self._bot_auth_url)

    def _submit_bot_code(self):
        import threading, re
        raw = self.bot_code_edit.text().strip()
        if not raw:
            self.bot_status.setText("⚠  Champ vide")
            self.bot_status.setStyleSheet(f"color:{C_ORG};")
            return
        code = extract_auth_code(raw)
        if not code:
            self.bot_status.setText("⚠  Code non reconnu")
            self.bot_status.setStyleSheet(f"color:{C_ORG};")
            return
        self.bot_validate_btn.setEnabled(False)
        self.bot_status.setText("Authentification...")
        self.bot_status.setStyleSheet(f"color:{C_MUTE};")
        threading.Thread(target=self._do_bot_auth, args=(code,), daemon=True).start()

    def _do_bot_auth(self, code: str):
        from rlapi.egs import EGS
        result = None
        try:
            egs = EGS()
            launcher_token = egs.authenticate_with_code(code)
            exchange_code = egs.get_exchange_code(launcher_token.access_token)
            eos_token = egs.exchange_eos_token(exchange_code)
            result = {
                "refresh_token": eos_token.refresh_token,
                "account_id": eos_token.account_id,
                "account_name": launcher_token.display_name,
            }
            egs.close()
        except Exception as e:
            self.app.signals.log_event.emit(f"[Bot] Erreur : {e}")
        self._bot_auth_done.emit(result)

    def _on_auth_finished(self, result):
        self.bot_instructions.hide()
        self.bot_open_code_btn.hide()
        self.bot_code_edit.hide()
        self.bot_validate_btn.hide()
        self.bot_validate_btn.setEnabled(True)
        self.bot_login_btn.setEnabled(True)
        if result:
            self.app.config["bot_refresh_token"] = result["refresh_token"]
            self.app.config["bot_account_id"] = result["account_id"]
            self.app.config["bot_account_name"] = result["account_name"]
            self.app.config.save()
            self.bot_status.setText(f"✓  Connecté : {result['account_name']}")
            self.bot_status.setStyleSheet(f"color:{C_GREEN};")
            self.app.signals.log_event.emit("[Bot] Compte bot configuré.")
            self.app.fetch_mmr_async(force=True)
        else:
            self.bot_status.setText("Échec — code invalide ou expiré.")
            self.bot_status.setStyleSheet(f"color:{C_ORG};")
            self.app.signals.log_event.emit("[Bot] Échec authentification.")

    def _clear_bot_token(self):
        self.app.config["bot_refresh_token"] = ""
        self.app.config["bot_account_id"] = ""
        self.app.config["bot_account_name"] = ""
        self.app.config.save()
        self.bot_status.setText("Non configuré")
        self.bot_status.setStyleSheet(f"color:{C_ORG};")
        self.app.signals.log_event.emit("[Bot] Compte bot supprimé.")

    def _load_bot_account_on_startup(self):
        try:
            QTimer.singleShot(100, self._update_bot_status_display)
        except Exception as e:
            print(f"[Bot] Erreur au chargement : {e}")

    def _update_bot_status_display(self):
        bot_name = self.app.config.get("bot_account_name", "")
        if bot_name:
            self.bot_status.setText(f"✓  Connecté : {bot_name}")
            self.bot_status.setStyleSheet(f"color:{C_GREEN};")
        else:
            self.bot_status.setText("Non configuré")
            self.bot_status.setStyleSheet(f"color:{C_ORG};")

    # ── STREAMER ──────────────────────────────────────────────────────────
    def _on_streamer_mute_changed(self, state):
        self.app.config["streamer_mute_audio"] = bool(state)
        self.app.config.save()
        self._update_streamer_btn()

    def _toggle_streamer(self):
        self._streamer_active = not self._streamer_active
        self.app.config["streamer_mode"] = self._streamer_active
        self.app.config.save()
        self.app._apply_streamer_mode(self._streamer_active)
        self._update_streamer_btn()

    def _update_streamer_btn(self):
        if self._streamer_active:
            self._streamer_btn.setText("🎥  DÉSACTIVER LE MODE STREAMER")
            self._streamer_btn.setStyleSheet(
                f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:6px;padding:5px 10px;font-size:10px;font-weight:700;}}"
                f"QPushButton:hover{{background:#e06000;}}")
            self._streamer_hint.setText("✓  Barre noire active + son coupé")
        else:
            self._streamer_btn.setText("🎥  ACTIVER LE MODE STREAMER")
            self._streamer_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:6px;padding:5px 10px;font-size:10px;font-weight:700;}}"
                f"QPushButton:hover{{background:{C_BG3}cc;}}")
            self._streamer_hint.setText("")

    # ── PLATFORM ─────────────────────────────────────────────────────────
    def _on_platform_changed(self, platform):
        if platform == "steam":
            self._username_lbl.setText("Steam ID (64-bit) :")
            self._username.setPlaceholderText("76561198012345678")
        else:
            self._username_lbl.setText("Pseudo :")
            self._username.setPlaceholderText("MonPseudo#1234")

    # ── RL CONFIG ─────────────────────────────────────────────────────────
    def _find_rl_config_dirs(self):
        rl_variants = ["rocketleague", "Rocket League", "RocketLeague"]
        base_paths = [
            r"C:\Program Files\Epic Games", r"C:\Program Files (x86)\Epic Games",
            r"C:\Program Files (x86)\Steam\steamapps\common", r"C:\Program Files\Steam\steamapps\common",
        ]
        found = []
        for base in base_paths:
            if not os.path.exists(base):
                continue
            for variant in rl_variants:
                cfg_dir = os.path.join(base, variant, "TAGame", "Config")
                if os.path.exists(cfg_dir):
                    found.append(cfg_dir)
        return found

    def _open_rl_config(self):
        dirs = self._find_rl_config_dirs()
        QDesktopServices.openUrl(QUrl.fromLocalFile(dirs[0] if dirs else os.path.expanduser("~")))

    def _auto_configure_ini(self):
        dirs = self._find_rl_config_dirs()
        found = []
        ini_content = "[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123\n"
        for cfg_dir in dirs:
            ini_path = os.path.join(cfg_dir, "DefaultStatsAPI.ini")
            try:
                with open(ini_path, "w", encoding="utf-8") as f:
                    f.write(ini_content)
                found.append(ini_path)
            except Exception as e:
                self._ini_status.setText(f"Erreur: {e}")
                return
        if found:
            self._ini_status.setStyleSheet(f"color:{C_GREEN};font-size:9px;")
            self._ini_status.setText(f"✓  Configuré dans {len(found)} dossier(s)")
        else:
            self._ini_status.setStyleSheet(f"color:{C_ORG};font-size:9px;")
            self._ini_status.setText("⚠  Dossier RL introuvable")
        QTimer.singleShot(5000, lambda: self._ini_status.setText(""))

    # ── SOUND ─────────────────────────────────────────────────────────────
    def _browse(self, field, cfg_key):
        import os as _os
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un son", "", "Audio (*.wav *.mp3 *.ogg *.flac);;Tous (*)")
        if path:
            rel = _os.path.relpath(path, _get_app_dir())
            if not rel.startswith(".."):
                path = rel
            field.setText(path)
            self.app.config[cfg_key] = path
            self.app.config.save()

    # ── SAVE ──────────────────────────────────────────────────────────────
    def _save_all(self):
        self.app.config["platform"] = self._platform.currentText()
        self.app.config["username"] = self._username.text().strip()
        self.app.config["result_overlay_enabled"] = self._result_overlay_enabled.isChecked()
        self.app.config["result_overlay_theme"] = self._result_theme.currentText()
        self.app.config.save()
        self._save_lbl.setText("✓  Sauvegardé !")
        QTimer.singleShot(2500, lambda: self._save_lbl.setText(""))
        self.app.fetch_mmr_async(force=True)


def _get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _open_guest_browser(url: str):
    import subprocess, webbrowser
    browsers = [
        (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "--guest"),
        (r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "--guest"),
        (r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "--guest"),
        (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "--guest"),
        (r"C:\Program Files\Mozilla Firefox\firefox.exe", "--private-window"),
        (r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe", "--private-window"),
    ]
    for exe, flag in browsers:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, flag, url])
                return
            except Exception:
                continue
    webbrowser.open(url)