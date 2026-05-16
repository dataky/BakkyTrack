"""ui/tabs.py — Les 6 onglets : TrackerTab, PlayersTab, OverlayTab, AutomationTab, SoundTab, SettingsTab."""
import time, json, os, sys, urllib.parse
from PyQt6.QtCore    import Qt, QTimer, QSize, QUrl
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QScrollArea, QCheckBox,
    QSlider, QStyle, QSizePolicy, QProgressBar, QDialog, QFileDialog,
    QStackedWidget, QTabWidget,
)
from PyQt6.QtGui import QDesktopServices, QColor, QCursor, QFont, QIcon
from style import (
    C_BG, C_BG2, C_BG3, C_BLUE, C_ORG, C_TEXT, C_MUTE, C_GREEN, C_GOLD,
    card, lbl, btn, hsep,
)
from utils import (
    _key_display, get_rank_pixmap, SvgBackground,
)
from ui.dialogs import (
    KeyCaptureWidget, OverlayBindDialog, _overlay_hotkey_display,
)

_PLAYER_PLATFORM_SLUGS = {
    "steam": "steam", "epic": "epic",
    "ps4": "psn", "xbox": "xbl", "switch": "switch",
}

_SOUND_EVENTS = [
    ("goal_scored",   "🎯  But marqué"),
    ("goal_conceded", "💀  But encaissé"),
    ("crossbar",      "🏐  Poteau / Barre"),
    ("demo_me",       "💥  Démoli (toi)"),
    ("demo_opponent", "🔥  Démolition adverse"),
    ("epic_save",     "🧤  Epic Save"),
    ("save",          "🛡  Save"),
]


# ── TrackerTab ───────────────────────────────────────────────────────────
class TrackerTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()
        self._connect_signals()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        conn = card()
        cl = QVBoxLayout(conn); cl.setContentsMargins(12,10,12,10); cl.setSpacing(6)
        cl.addWidget(lbl("CONNEXION AU JEU", C_MUTE, 8, True))
        cl.addWidget(lbl("Les événements du jeu arrivent ici via StatsAPI.", C_MUTE, 9))
        row_conn = QHBoxLayout()
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{C_MUTE};font-size:14px;background:transparent;")
        self._status_lbl = lbl("Non connecté")
        port_lbl = lbl("Port :")
        self._port_edit = QLineEdit(str(self.app.config["statsapi_port"]))
        self._port_edit.setFixedWidth(60)
        reconn_btn = btn("Reconnecter", bg=C_BG3, size=9)
        reconn_btn.clicked.connect(self.app.reconnect_statsapi)
        row_conn.addWidget(self._dot); row_conn.addSpacing(6)
        row_conn.addWidget(self._status_lbl); row_conn.addStretch()
        row_conn.addWidget(port_lbl); row_conn.addSpacing(4)
        row_conn.addWidget(self._port_edit); row_conn.addSpacing(8)
        row_conn.addWidget(reconn_btn)
        cl.addLayout(row_conn); root.addWidget(conn)

        info = card()
        il = QVBoxLayout(info); il.setContentsMargins(14,12,14,12); il.setSpacing(7)
        row_player = QHBoxLayout()
        row_player.addWidget(lbl("COMPTE DÉTECTÉ (EN JEU)", C_MUTE, 8, True))
        self._player_lbl = lbl("--", C_TEXT, 11, True)
        row_player.addStretch(); row_player.addWidget(self._player_lbl)
        il.addLayout(row_player); il.addWidget(hsep())

        row_mmr = QHBoxLayout()
        row_mmr.addWidget(lbl("MMR"))
        self._mmr_lbl   = lbl("--", C_GOLD, 16, True)
        self._delta_lbl = lbl("",   C_GREEN, 10, True)
        self._rank_lbl  = lbl("",   C_MUTE,   9)
        self._rank_icon_lbl = QLabel()
        self._rank_icon_lbl.setFixedSize(28, 28)
        self._rank_icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rank_icon_lbl.setStyleSheet("background:transparent;")
        ref_btn = QPushButton()
        ref_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ref_btn.setFixedSize(26, 26)
        ref_btn.setIcon(ref_btn.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        ref_btn.setIconSize(QSize(14, 14))
        ref_btn.setStyleSheet(f"""
            QPushButton{{background:{C_BG3};border:none;border-radius:4px;}}
            QPushButton:hover{{background:{C_BG3}cc;}}
            QPushButton:pressed{{background:{C_BG3}99;}}
        """)
        ref_btn.clicked.connect(lambda: self.app.fetch_mmr_async(force=True))
        row_mmr.addStretch()
        row_mmr.addWidget(self._rank_icon_lbl); row_mmr.addSpacing(4)
        row_mmr.addWidget(self._rank_lbl); row_mmr.addWidget(self._mmr_lbl)
        row_mmr.addWidget(self._delta_lbl); row_mmr.addWidget(ref_btn)
        il.addLayout(row_mmr); il.addWidget(hsep())

        row_pl = QHBoxLayout()
        row_pl.addWidget(lbl("PLAYLIST", C_MUTE, 8)); row_pl.addStretch()
        self._pl_btns = {}
        for key in ("1v1", "2v2", "3v3"):
            b = btn(key, bg=C_BG3, fg=C_MUTE, size=9); b.setFixedWidth(50)
            b.clicked.connect(lambda _, k=key: self.app.select_playlist(k))
            row_pl.addWidget(b); self._pl_btns[key] = b
        il.addLayout(row_pl); root.addWidget(info)

        wl = QHBoxLayout(); wl.setSpacing(8)
        for side in ("win", "loss"):
            c_card = card(); c_card.setFixedHeight(124)
            c_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            color  = C_BLUE if side == "win" else C_ORG
            label  = "VICTOIRES" if side == "win" else "DÉFAITES"
            bar    = QFrame(c_card); bar.setFixedHeight(3)
            bar.setStyleSheet(f"background:{color};border:none;")
            cl2 = QVBoxLayout(c_card); cl2.setContentsMargins(0,0,0,8); cl2.setSpacing(2)
            cl2.addWidget(bar)
            cl2.addWidget(lbl(label, color, 9), alignment=Qt.AlignmentFlag.AlignHCenter)
            count_lbl = QLabel("0")
            count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); count_lbl.setFixedHeight(54)
            count_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            count_lbl.setStyleSheet(f"color:{color};font-size:52px;font-weight:700;background:transparent;")
            cl2.addWidget(count_lbl)
            brow = QHBoxLayout(); brow.setSpacing(6); brow.setContentsMargins(10,0,10,0)
            bp = btn("+", bg=C_BG3, size=14); bm = btn("−", bg=C_BG3, size=14)
            bp.clicked.connect(lambda _, s=side: self.app.add(s))
            bm.clicked.connect(lambda _, s=side: self.app.remove(s))
            brow.addWidget(bp); brow.addWidget(bm)
            cl2.addLayout(brow); wl.addWidget(c_card, 1)
            if side == "win":
                self._wins_lbl = count_lbl; wl.addWidget(lbl("VS", C_MUTE, 13))
            else:
                self._losses_lbl = count_lbl
        root.addLayout(wl)

        wr_card = card()
        wr_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        wrc = QVBoxLayout(wr_card); wrc.setContentsMargins(14,8,14,8); wrc.setSpacing(4)
        wr_top = QHBoxLayout()
        wr_top.addWidget(lbl("WIN RATE", C_MUTE, 9))
        self._wr_lbl = lbl("--", C_TEXT, 13, True)
        wr_top.addStretch(); wr_top.addWidget(self._wr_lbl)
        wrc.addLayout(wr_top)
        self._wr_progress = QProgressBar()
        self._wr_progress.setRange(0, 100); self._wr_progress.setValue(0)
        self._wr_progress.setTextVisible(False); self._wr_progress.setFixedHeight(10)
        self._wr_progress.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._wr_progress.setStyleSheet(f"""
            QProgressBar {{ border: none; background: #1A0500; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {C_BLUE}; border-radius: 4px; }}
        """)
        wrc.addWidget(self._wr_progress); root.addWidget(wr_card)

        ms = QHBoxLayout(); ms.setSpacing(6)
        self._total_lbl  = QLabel("0")
        self._streak_lbl = QLabel("--")
        self._clock_lbl  = QLabel("0:00")
        for caption, val_ref in [("TOTAL", self._total_lbl), ("STREAK", self._streak_lbl), ("DURÉE", self._clock_lbl)]:
            c = card(); cl3 = QVBoxLayout(c); cl3.setContentsMargins(8,8,8,8); cl3.setSpacing(2)
            cl3.addWidget(lbl(caption, C_MUTE, 8), alignment=Qt.AlignmentFlag.AlignHCenter)
            val_ref.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_ref.setStyleSheet(f"color:{C_TEXT};font-size:15px;font-weight:700;background:transparent;")
            cl3.addWidget(val_ref); ms.addWidget(c, 1)
        root.addLayout(ms)

        dbg = card()
        dbg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dl = QVBoxLayout(dbg); dl.setContentsMargins(12,8,12,10); dl.setSpacing(6)
        dl.addWidget(lbl("MESSAGES STATSAPI", C_MUTE, 8))
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True); self._log.setFixedHeight(72)
        self._log.setMaximumBlockCount(400)
        self._log.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._log.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._log.setStyleSheet(
            f"QPlainTextEdit{{background:{C_BG3};color:{C_MUTE};border:none;"
            f"font-family:'Consolas','Courier New',monospace;font-size:9px;padding:4px;border-radius:4px;}}")
        dl.addWidget(self._log); root.addWidget(dbg)

        reset_btn = btn("Réinitialiser la session", bg=C_BG, fg=C_MUTE, size=10)
        reset_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        reset_btn.clicked.connect(self.app.reset_session)
        root.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addStretch(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _connect_signals(self):
        s = self.app.signals
        s.status_changed.connect(self._on_status)
        s.player_detected.connect(lambda name, _: self._player_lbl.setText(name))
        s.match_result.connect(self._refresh)
        s.log_event.connect(self._on_log)
        s.mmr_updated.connect(self._on_mmr)
        s.mmr_error.connect(self._on_mmr_error)
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)

    def _on_status(self, state, msg):
        colors = {"connected": C_GREEN, "error": C_ORG}
        c = colors.get(state, C_MUTE)
        self._dot.setStyleSheet(f"color:{c};font-size:14px;background:transparent;")
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color:{c};font-size:9px;background:transparent;letter-spacing:1px;")

    def _refresh(self, _=None):
        a = self.app
        self._wins_lbl.setText(str(a.wins))
        self._losses_lbl.setText(str(a.losses))
        total = a.wins + a.losses
        self._total_lbl.setText(str(total))
        if total == 0:
            self._wr_lbl.setText("--"); self._wr_progress.setValue(0); self._streak_lbl.setText("--")
        else:
            wr = round(a.wins / total * 100)
            self._wr_lbl.setText(f"{wr}%"); self._wr_progress.setValue(wr)
            if a.streak > 1:
                self._streak_lbl.setText(f"{a.streak}{'W' if a.streak_type=='win' else 'L'}")
            else:
                self._streak_lbl.setText("--")

    def _on_mmr(self):
        d   = self.app.all_mmr.get(self.app.selected_playlist, {})
        mmr = d.get("mmr")
        self._mmr_lbl.setText(str(mmr) if mmr else "--")
        rank_name = d.get("rank", ""); self._rank_lbl.setText(rank_name)
        tier_id = d.get("tier_id", 0)
        pm = get_rank_pixmap(tier_id, 26)
        if pm: self._rank_icon_lbl.setPixmap(pm)
        else: self._rank_icon_lbl.clear()
        chg = d.get("mmr_change", 0)
        if chg != 0 and mmr:
            sign = "+" if chg > 0 else ""; clr = C_GREEN if chg > 0 else C_ORG
            self._delta_lbl.setText(f"{sign}{chg}")
            self._delta_lbl.setStyleSheet(f"color:{clr};font-size:9px;font-weight:700;background:transparent;")
        else:
            self._delta_lbl.setText("")
        self.app.highlight_playlist_btns(self._pl_btns)

    def _on_mmr_error(self, msg):
        self._mmr_lbl.setText("ERR")
        self._mmr_lbl.setStyleSheet(f"color:{C_ORG};font-size:16px;font-weight:700;background:transparent;")
        self._delta_lbl.setText(""); self._rank_lbl.setText(msg[:40])
        self._rank_lbl.setStyleSheet(f"color:{C_ORG};font-size:9px;background:transparent;")

    def _on_log(self, msg):
        self._log.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {msg}")
        sb = self._log.verticalScrollBar(); sb.setValue(sb.maximum())

    def _tick_clock(self):
        elapsed = int(time.time() - self.app.session_start)
        m, s = divmod(elapsed, 60); self._clock_lbl.setText(f"{m}:{s:02d}")

    def get_port(self):
        return self._port_edit.text().strip()


# ── PlayersTab ───────────────────────────────────────────────────────────
class PlayersTab(QWidget):
    _PLAYLIST_KEY_TO_ID = {"1v1": 10, "2v2": 11, "3v3": 13}

    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._players = []
        self._build()
        app_ref.signals.players_updated.connect(self._on_players)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_mmr_labels)
        self._refresh_timer.start(1000)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14); root.setSpacing(10)
        header = QHBoxLayout()
        header.addWidget(lbl("JOUEURS EN MATCH", C_MUTE, 9)); header.addStretch()
        open_all_btn = btn("Ouvrir tous →", bg=C_BG3, size=9)
        open_all_btn.clicked.connect(self._open_all)
        header.addWidget(open_all_btn); root.addLayout(header)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0,0,0,0); self._list_layout.setSpacing(4)
        scroll = QScrollArea(); scroll.setWidget(self._list_widget)
        scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;border:none;")
        root.addWidget(scroll, 1)
        hint = lbl("Clic sur → pour ouvrir le profil sur tracker.network", C_MUTE, 9)
        hint.setWordWrap(True); root.addWidget(hint)
        self._show_empty()

    _TRACKER_COOLDOWN_S = 3
    _tracker_last_open: dict = {}
    _URL_SLUG = {"epic": "epic", "steam": "steam", "ps4": "psn", "xbox": "xbl", "switch": "switch"}

    def _show_empty(self):
        self._clear_list()
        empty = lbl("Aucun match en cours", C_MUTE, 10)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addWidget(empty); self._list_layout.addStretch()

    def _refresh_mmr_labels(self):
        if not self._players: return
        cache = getattr(self.app, "_ingame_stats_cache", {})
        has_pending = any(
            cache.get(p.get("PrimaryId", ""), {}).get("status") in ("loading", None, "")
            for p in self._players if p.get("PrimaryId"))
        if has_pending: self._on_players(self._players)

    def _clear_list(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _on_players(self, players):
        self._players = players
        if not players: self._show_empty(); return
        self._clear_list()
        blues   = [p for p in players if p.get("TeamNum") == 0]
        oranges = [p for p in players if p.get("TeamNum") == 1]
        for team_name, team_color, team_players in [("🔵  BLUE", C_BLUE, blues), ("🟠  ORANGE", C_ORG, oranges)]:
            if team_players:
                self._list_layout.addWidget(lbl(team_name, team_color, 9, True))
                for p in team_players:
                    self._list_layout.addWidget(self._make_row(p, team_color))
        self._list_layout.addStretch()

    def _platform_from_id(self, primary_id):
        if primary_id.startswith("Steam|"): return "steam"
        if primary_id.startswith("Epic|"): return "epic"
        if primary_id.startswith("PS4|"): return "ps4"
        if primary_id.startswith("XboxOne|"): return "xbox"
        if primary_id.startswith("Switch|"): return "switch"
        return "epic"

    def _id_from_primary_id(self, primary_id):
        parts = primary_id.split("|")
        return parts[1] if len(parts) >= 2 else primary_id

    def _make_row(self, player, color):
        row = card(bg=C_BG2); row.setFixedHeight(58)
        rl = QHBoxLayout(row); rl.setContentsMargins(12,6,12,6)
        primary_id = player.get("PrimaryId", "")
        platform   = self._platform_from_id(primary_id)
        raw_id     = self._id_from_primary_id(primary_id) or player.get("Name", "")
        user_id    = raw_id if platform == "steam" else player.get("Name", raw_id)
        plat_lbl = QLabel(platform.upper())
        plat_lbl.setStyleSheet(f"color:{C_MUTE};background:transparent;border-radius:3px;padding:2px 5px;font-size:7px;font-weight:700;border:none;")
        name_lbl = lbl(player.get("Name", "?"), color, 12, True)
        cache   = getattr(self.app, "_ingame_stats_cache", {})
        entry   = cache.get(primary_id, {})
        status  = entry.get("status", "")
        pl_key  = getattr(self.app, "selected_playlist", "3v3")
        pid_int = self._PLAYLIST_KEY_TO_ID.get(pl_key, 13)
        pl_data = entry.get("playlists", {}).get(pid_int, {})
        if status == "loading": mmr_text, mmr_color, mmr_bold = "⏳ …", C_MUTE, False
        elif status == "ok" and pl_data:
            tier_name = pl_data.get("tier_name", "Unranked"); mmr_val = pl_data.get("mmr", 0)
            mmr_text, mmr_color, mmr_bold = f"{tier_name}  {mmr_val}", C_GOLD, True
        elif status == "error": mmr_text, mmr_color, mmr_bold = "—", C_MUTE, False
        else: mmr_text, mmr_color, mmr_bold = "", C_MUTE, False
        mmr_lbl   = lbl(mmr_text, mmr_color, 9, bold=mmr_bold)
        stats_lbl = lbl(f"⚽ {player.get('Goals',0)}   🅰 {player.get('Assists',0)}   🛡 {player.get('Saves',0)}", C_MUTE, 9)
        open_btn = btn("→", bg=C_BG3, size=11); open_btn.setFixedSize(30, 30)
        open_btn.clicked.connect(lambda _, uid=user_id, pl=platform: self._open_profile(uid, pl))
        rl.addWidget(plat_lbl); rl.addSpacing(8)
        vl = QVBoxLayout(); vl.setSpacing(1); vl.setContentsMargins(0,0,0,0)
        vl.addWidget(name_lbl)
        br = QHBoxLayout(); br.setSpacing(8); br.setContentsMargins(0,0,0,0)
        br.addWidget(stats_lbl); br.addStretch(); br.addWidget(mmr_lbl)
        vl.addLayout(br); rl.addLayout(vl); rl.addStretch(); rl.addWidget(open_btn)
        return row

    def _open_profile(self, user_id, platform):
        now = time.time(); last = self._tracker_last_open.get(user_id, 0)
        if now - last < self._TRACKER_COOLDOWN_S: return
        self._tracker_last_open[user_id] = now
        slug = self._URL_SLUG.get(platform, platform)
        url = (f"https://rocketleague.tracker.network/rocket-league/profile/{slug}/{urllib.parse.quote(user_id)}/overview")
        QDesktopServices.openUrl(QUrl(url))

    def _open_all(self):
        for p in self._players:
            primary_id = p.get("PrimaryId", "")
            pl = self._platform_from_id(primary_id)
            raw_id = self._id_from_primary_id(primary_id) or p.get("Name", "")
            user_id = raw_id if pl == "steam" else p.get("Name", raw_id)
            self._open_profile(user_id, pl)


# ── OverlayTab ───────────────────────────────────────────────────────────
class OverlayTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._active = False
        self._ctrl_active = False
        self._build()

    def _build(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;border:none;")
        inner_w = QWidget(); inner_w.setStyleSheet("background:transparent;")
        root = QVBoxLayout(inner_w)
        root.setContentsMargins(16,20,16,16); root.setSpacing(12)
        scroll.setWidget(inner_w); outer.addWidget(scroll)

        # Touche hold-to-show
        hk_card = card()
        hkl = QVBoxLayout(hk_card); hkl.setContentsMargins(16,14,16,16); hkl.setSpacing(10)
        hkl.addWidget(lbl("TOUCHE D'OVERLAY  (maintenir = afficher)", C_MUTE, 9))
        hkl.addWidget(lbl("Maintiens cette touche en jeu pour afficher l'overlay.", C_TEXT, 9))
        hk_row = QHBoxLayout()
        self._hk_display = QLabel(_overlay_hotkey_display(self.app.config))
        self._hk_display.setFixedWidth(170)
        self._hk_display.setStyleSheet(f"background:{C_BG3};color:{C_TEXT};border-radius:4px;padding:5px 9px;font-size:11px;border:none;")
        hk_bind_btn = QPushButton("🎯  Configurer")
        hk_bind_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        hk_bind_btn.setStyleSheet(f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:5px 10px;font-size:9px;font-weight:700;}}QPushButton:hover{{background:{C_BLUE};color:{C_TEXT};}}")
        hk_bind_btn.clicked.connect(self._reconfigure_hotkey)
        hk_row.addWidget(self._hk_display); hk_row.addWidget(hk_bind_btn); hk_row.addStretch()
        hkl.addLayout(hk_row); root.addWidget(hk_card)

        # Rang affiché
        rm_card = card()
        rml = QVBoxLayout(rm_card); rml.setContentsMargins(16,14,16,16); rml.setSpacing(10)
        rml.addWidget(lbl("RANG AFFICHÉ DANS L'OVERLAY TAB", C_MUTE, 9))
        rml.addWidget(lbl("Choisit quel rang / MMR est affiché pour chaque joueur.", C_TEXT, 9))
        rm_btn_row = QHBoxLayout(); rm_btn_row.setSpacing(6)
        _RM_OPTS = [("1V1", "1v1"), ("2V2", "2v2"), ("3V3", "3v3"), ("BEST", "best")]
        self._rm_btns = {}
        def _make_rm_btn(label, key):
            b = QPushButton(label); b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            b.setCheckable(True); b.setFixedHeight(30)
            def _style(active):
                bg = C_BLUE if active else C_BG3
                b.setStyleSheet(f"QPushButton{{background:{bg};color:{C_TEXT};border:none;border-radius:4px;font-size:10px;font-weight:700;padding:0 12px;}}QPushButton:hover{{background:{C_BLUE if not active else C_BLUE}cc;}}")
            b.setChecked(self.app.config.get("tab_rank_mode", "2v2") == key)
            _style(b.isChecked())
            def _on_click(checked, k=key, btn_ref=b, style_fn=_style):
                self.app.config["tab_rank_mode"] = k
                for other_key, other_btn in self._rm_btns.items():
                    is_active = other_key == k
                    other_btn.setChecked(is_active)
                    other_btn._style_fn(is_active)
            b._style_fn = _style; b.clicked.connect(_on_click); return b
        for lbl_txt, key in _RM_OPTS:
            b = _make_rm_btn(lbl_txt, key); self._rm_btns[key] = b; rm_btn_row.addWidget(b)
        rm_btn_row.addStretch(); rml.addLayout(rm_btn_row)
        rml.addWidget(hsep())
        self._peak_chk = QCheckBox("Afficher le peak MMR  (ex : peak[1950])")
        self._peak_chk.setChecked(self.app.config.get("tab_show_peak", True))
        self._peak_chk.setStyleSheet(f"color:{C_TEXT};font-size:11px;spacing:8px;background:transparent;")
        self._peak_chk.stateChanged.connect(self._on_peak_toggle)
        rml.addWidget(self._peak_chk); root.addWidget(rm_card)

        # Toggle overlay principal
        tog_card = card()
        tl = QVBoxLayout(tog_card); tl.setContentsMargins(16,16,16,16); tl.setSpacing(8)
        tl.addWidget(lbl("OVERLAY", C_MUTE, 9))
        self._toggle_btn = btn("▶  ACTIVER L'OVERLAY", bg=C_BG3, fg=C_TEXT, size=12)
        self._toggle_btn.setFixedHeight(44); self._toggle_btn.clicked.connect(self._toggle)
        tl.addWidget(self._toggle_btn)
        tl.addWidget(lbl("Double-clic sur l'overlay pour changer de mode", C_MUTE, 9))
        root.addWidget(tog_card)

        # Format
        from overlay_widgets import _load_overlay_plugins
        mode_card = card()
        ml = QVBoxLayout(mode_card); ml.setContentsMargins(16,14,16,16); ml.setSpacing(10)
        ml.addWidget(lbl("FORMAT", C_MUTE, 9))
        r_mode = QHBoxLayout(); r_mode.addWidget(lbl("Type d'overlay", C_TEXT, 11))
        self._mode_combo = QComboBox()
        self._available_modes = _load_overlay_plugins()
        self._MODE_MAP = {}; self._MODE_REVERSE = {}
        for idx, (mode_name, mode_info) in enumerate(sorted(self._available_modes.items())):
            size = mode_info.get("size", (0,0))
            self._mode_combo.addItem(f"{mode_name}  ({size[0]}×{size[1]})")
            self._MODE_MAP[idx] = mode_name; self._MODE_REVERSE[mode_name] = idx
        self._mode_combo.setFixedWidth(200)
        self._mode_combo.currentIndexChanged.connect(lambda i: self._set_mode(self._MODE_MAP.get(i, "compact")))
        r_mode.addStretch(); r_mode.addWidget(self._mode_combo); ml.addLayout(r_mode)
        root.addWidget(mode_card)

        # MMR display
        mmr_card = card()
        mml = QVBoxLayout(mmr_card); mml.setContentsMargins(16,14,16,16); mml.setSpacing(8)
        mml.addWidget(lbl("AFFICHAGE MMR", C_MUTE, 9))
        self._mmr_btns = {}
        for mode, label in [("both", "MMR + Delta"), ("mmr", "MMR uniquement"), ("delta", "Delta uniquement")]:
            b = btn(label, bg=C_BG3, fg=C_MUTE, size=10); b.setFixedHeight(34)
            b.clicked.connect(lambda _, m=mode: self._set_mmr_mode(m))
            mml.addWidget(b); self._mmr_btns[mode] = b
        root.addWidget(mmr_card)

        # Preview
        from overlay_widgets import _CompactCard
        prev_card = card()
        pl = QVBoxLayout(prev_card); pl.setContentsMargins(16,14,16,16); pl.setSpacing(8)
        pl.addWidget(lbl("APERÇU COMPACT", C_MUTE, 9))
        prev_inner = QHBoxLayout()
        self._preview = _CompactCard(); self._preview.setEnabled(False)
        prev_inner.addStretch(); prev_inner.addWidget(self._preview); prev_inner.addStretch()
        pl.addLayout(prev_inner); root.addWidget(prev_card)

        # Overlay manette
        ctrl_card = card()
        ctl = QVBoxLayout(ctrl_card); ctl.setContentsMargins(16,14,16,16); ctl.setSpacing(10)
        ctl.addWidget(lbl("OVERLAY MANETTE", C_MUTE, 9))
        self._ctrl_toggle_btn = btn("🎮  ACTIVER L'OVERLAY MANETTE", bg=C_BG3, fg=C_TEXT, size=11)
        self._ctrl_toggle_btn.setFixedHeight(40); self._ctrl_toggle_btn.clicked.connect(self._toggle_controller)
        ctl.addWidget(self._ctrl_toggle_btn)
        style_row = QHBoxLayout(); style_row.addWidget(lbl("Style :", C_TEXT, 11)); style_row.addStretch()
        self._ctrl_style_btns = {}
        for mode_key, mode_label in [("with_bg", "Avec fond"), ("transparent", "Transparent")]:
            b = btn(mode_label, bg=C_BG3, fg=C_MUTE, size=10); b.setFixedHeight(30)
            b.clicked.connect(lambda _, m=mode_key: self._set_ctrl_mode(m))
            style_row.addWidget(b); self._ctrl_style_btns[mode_key] = b
        ctl.addLayout(style_row); ctl.addWidget(lbl("Déplaçable en jeu.", C_MUTE, 8))
        root.addWidget(ctrl_card)

        # Vitesse balle en temps réel
        ball_card = card()
        bll = QVBoxLayout(ball_card); bll.setContentsMargins(16, 12, 16, 14); bll.setSpacing(6)
        bll.addWidget(lbl("VITESSE DE LA BALLE (EN JEU)", C_MUTE, 9))
        ball_inner = QHBoxLayout(); ball_inner.setSpacing(10)
        self._ball_speed_val = QLabel("—")
        self._ball_speed_val.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        self._ball_speed_val.setStyleSheet(
            "color:#4FC3F7;font-size:28px;font-weight:700;background:transparent;"
        )
        self._ball_speed_unit = lbl("km/h", "#4FC3F7", 12)
        self._ball_speed_unit.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        ball_inner.addStretch()
        ball_inner.addWidget(self._ball_speed_val)
        ball_inner.addWidget(self._ball_speed_unit)
        ball_inner.addStretch()
        bll.addLayout(ball_inner)
        self._ball_speed_bar = QProgressBar()
        self._ball_speed_bar.setRange(0, 216); self._ball_speed_bar.setValue(0)
        self._ball_speed_bar.setTextVisible(False); self._ball_speed_bar.setFixedHeight(6)
        self._ball_speed_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._ball_speed_bar.setStyleSheet("""
            QProgressBar { border: none; background: #1A2A35; border-radius: 3px; }
            QProgressBar::chunk { background: #4FC3F7; border-radius: 3px; }
        """)
        bll.addWidget(self._ball_speed_bar)
        bll.addWidget(lbl("Max absolu : 216 km/h  ·  Supersonique voiture : 79 km/h  ·  Boost max voiture : 83 km/h", C_MUTE, 8))
        bll.addWidget(hsep())

        # Toggle overlay flottant
        self._ball_overlay_active = False
        self._ball_overlay_win    = None
        self._ball_ovl_btn = btn("⚽  ACTIVER L'OVERLAY VITESSE BALLE", bg=C_BG3, fg=C_TEXT, size=11)
        self._ball_ovl_btn.setFixedHeight(40)
        self._ball_ovl_btn.clicked.connect(self._toggle_ball_overlay)
        bll.addWidget(self._ball_ovl_btn)

        # Slider taille
        size_row = QHBoxLayout(); size_row.setSpacing(8)
        size_row.addWidget(lbl("Taille :", C_TEXT, 10))
        self._ball_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._ball_size_slider.setRange(14, 72)
        self._ball_size_slider.setValue(self.app.config.get("ball_overlay_font_size", 28))
        self._ball_size_slider.setFixedHeight(20)
        self._ball_size_slider.valueChanged.connect(self._on_ball_overlay_size)
        size_row.addWidget(self._ball_size_slider, 1)
        self._ball_size_lbl = lbl(f"{self.app.config.get('ball_overlay_font_size', 28)}pt", C_MUTE, 9)
        size_row.addWidget(self._ball_size_lbl)
        bll.addLayout(size_row)
        bll.addWidget(lbl("Déplaçable en jeu.", C_MUTE, 8))

        root.addWidget(ball_card)
        self.app.signals.ball_speed_updated.connect(self._on_ball_speed)

        root.addStretch()

        saved_mode = self.app.config.get("overlay_mode", "compact")
        if saved_mode not in self._available_modes:
            saved_mode = next(iter(self._available_modes), "compact")
        self._mode_combo.setCurrentIndex(self._MODE_REVERSE.get(saved_mode, 0))
        self._set_mode(saved_mode)
        self._set_mmr_mode(self.app.config.get("mmr_display_mode", "both"))
        self._ctrl_active = self.app.config.get("controller_overlay_enabled", False)
        self._update_ctrl_btn_style()
        self._set_ctrl_mode(self.app.config.get("controller_overlay_mode", "with_bg"), save=False)

    def _toggle_controller(self):
        from ui.controller_overlay import ControllerOverlay
        self._ctrl_active = not self._ctrl_active
        self.app.config["controller_overlay_enabled"] = self._ctrl_active; self.app.config.save()
        if self._ctrl_active: self.app.controller_overlay.show()
        else: self.app.controller_overlay.hide()
        self._update_ctrl_btn_style()

    def _update_ctrl_btn_style(self):
        if self._ctrl_active:
            self._ctrl_toggle_btn.setText("🎮  DÉSACTIVER L'OVERLAY MANETTE")
            self._ctrl_toggle_btn.setStyleSheet(f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;padding:5px 12px;font-size:11px;font-weight:700;}}QPushButton:hover{{background:#e06000;}}")
        else:
            self._ctrl_toggle_btn.setText("🎮  ACTIVER L'OVERLAY MANETTE")
            self._ctrl_toggle_btn.setStyleSheet(f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:5px 12px;font-size:11px;font-weight:700;}}QPushButton:hover{{background:{C_BG3}cc;}}")

    def _set_ctrl_mode(self, mode, save=True):
        self.app.controller_overlay.set_mode(mode)
        if save: self.app.config["controller_overlay_mode"] = mode; self.app.config.save()
        for m, b in self._ctrl_style_btns.items():
            active = m == mode
            b.setStyleSheet(f"QPushButton{{background:{C_BLUE if active else C_BG3};color:{C_TEXT if active else C_MUTE};border:none;border-radius:4px;padding:5px 12px;font-size:10px;font-weight:700;}}{'' if active else 'QPushButton:hover{color:' + C_TEXT + ';}'}")

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

    def _toggle(self):
        self._active = not self._active
        if self._active:
            self.app.overlay_win.show()
            self._toggle_btn.setText("■  DÉSACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;padding:5px 12px;font-size:12px;font-weight:700;}}QPushButton:hover{{background:#e06000;}}")
        else:
            self.app.overlay_win.hide()
            self._toggle_btn.setText("▶  ACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:5px 12px;font-size:12px;font-weight:700;}}QPushButton:hover{{background:{C_BG3}cc;}}")

    def _set_mode(self, mode):
        self.app.overlay_win.set_mode(mode); self.app.config["overlay_mode"] = mode
        idx = self._MODE_REVERSE.get(mode, 0)
        if self._mode_combo.currentIndex() != idx: self._mode_combo.setCurrentIndex(idx)

    def _set_mmr_mode(self, mode):
        self.app.overlay_win.set_mmr_mode(mode); self.app.config["mmr_display_mode"] = mode
        for m, b in self._mmr_btns.items():
            active = m == mode
            b.setStyleSheet(f"QPushButton{{background:{C_BLUE if active else C_BG3};color:{C_TEXT if active else C_MUTE};border:none;border-radius:4px;padding:5px 12px;font-size:10px;font-weight:700;}}{'' if active else 'QPushButton:hover{color:' + C_TEXT + ';}'}")

    def _toggle_ball_overlay(self):
        from ui.ball_speed_overlay import BallSpeedOverlay
        self._ball_overlay_active = not self._ball_overlay_active
        if self._ball_overlay_active:
            if self._ball_overlay_win is None:
                self._ball_overlay_win = BallSpeedOverlay(self.app.signals, self.app.config)
            self._ball_overlay_win.show()
            self._ball_ovl_btn.setText("⚽  DÉSACTIVER L'OVERLAY VITESSE BALLE")
            self._ball_ovl_btn.setStyleSheet(
                f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;"
                f"padding:5px 12px;font-size:11px;font-weight:700;}}QPushButton:hover{{background:#e06000;}}"
            )
        else:
            if self._ball_overlay_win:
                self._ball_overlay_win.hide()
            self._ball_ovl_btn.setText("⚽  ACTIVER L'OVERLAY VITESSE BALLE")
            self._ball_ovl_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;"
                f"padding:5px 12px;font-size:11px;font-weight:700;}}QPushButton:hover{{background:{C_BG3}cc;}}"
            )

    def _on_ball_overlay_size(self, value: int):
        self._ball_size_lbl.setText(f"{value}pt")
        self.app.config["ball_overlay_font_size"] = value
        if self._ball_overlay_win:
            self._ball_overlay_win.set_font_size(value)

    def _on_ball_speed(self, kmh: float):
        self._ball_speed_val.setText(f"{kmh:.0f}")
        # Barre : 100 km/h = pleine barre (vitesse max balle ~95 km/h)
        self._ball_speed_bar.setValue(min(216, int(kmh)))

    def _on_peak_toggle(self, state):
        show = bool(state); self.app.config["tab_show_peak"] = show
        self.app.ingame_mmr_overlay.set_show_peak(show)

    def refresh_preview(self, stats):
        if hasattr(self._preview, "update_stats"):
            self._preview.update_stats(stats, self.app.config.get("mmr_display_mode", "both"))


# ── AutomationTab ────────────────────────────────────────────────────────
class AutomationTab(QWidget):
    def __init__(self, app_ref):
        super().__init__(); self.app = app_ref; self._build()

    def _build(self):
        try: import pyautogui; PYAUTOGUI_AVAILABLE = True
        except ImportError: PYAUTOGUI_AVAILABLE = False
        root = QVBoxLayout(self); root.setContentsMargins(16,20,16,16); root.setSpacing(12)
        if not PYAUTOGUI_AVAILABLE:
            warn = card(bg="#2A0E00")
            wl = QVBoxLayout(warn); wl.setContentsMargins(16,14,16,14)
            wl.addWidget(lbl("⚠  pyautogui non installé", C_ORG, 11, True))
            wl.addWidget(lbl("pip install pyautogui", C_TEXT, 10)); root.addWidget(warn)

        def _parse_delay(v, default):
            try: return float(v.replace(",", "."))
            except: return default

        def _delay_row(label, cfg_key, default):
            row = QHBoxLayout(); row.addWidget(lbl(label, C_TEXT, 10)); row.addStretch()
            field = QLineEdit(str(self.app.config.get(cfg_key, default)))
            field.setFixedWidth(70); field.setAlignment(Qt.AlignmentFlag.AlignCenter)
            field.textChanged.connect(lambda v, k=cfg_key, d=default: self.app.config.__setitem__(k, _parse_delay(v, d)))
            sec_lbl = lbl("sec", C_MUTE, 9); row.addWidget(field); row.addWidget(sec_lbl); return row

        def _key_row(label, cfg_key, default):
            row = QHBoxLayout(); row.addWidget(lbl(label, C_TEXT, 10)); row.addStretch()
            w = KeyCaptureWidget(self.app.config.get(cfg_key, default))
            w.key_changed.connect(lambda v, k=cfg_key: self.app.config.__setitem__(k, v))
            row.addWidget(w); return row

        sr_card = card()
        sl = QVBoxLayout(sr_card); sl.setContentsMargins(16,14,16,16); sl.setSpacing(10)
        sl.addWidget(lbl("SKIP REPLAY AUTO", C_MUTE, 9))
        self._skip_cb = QCheckBox("Activer le skip replay automatique")
        self._skip_cb.setChecked(bool(self.app.config.get("auto_skip_replay", False)))
        self._skip_cb.toggled.connect(lambda v: self.app.config.__setitem__("auto_skip_replay", v))
        sl.addWidget(self._skip_cb)
        sl.addLayout(_key_row("Touche de skip :", "skip_replay_key", "key:space"))
        sl.addLayout(_delay_row("Délai avant skip :", "skip_replay_delay", 0))
        sl.addWidget(lbl("Ajuste le délai si le skip est trop tôt ou trop tard.", C_MUTE, 8))
        root.addWidget(sr_card)

        q_card = card()
        ql = QVBoxLayout(q_card); ql.setContentsMargins(16,14,16,16); ql.setSpacing(10)
        ql.addWidget(lbl("AUTO REJOUER", C_MUTE, 9))
        self._queue_cb = QCheckBox("Lancer une nouvelle partie automatiquement")
        self._queue_cb.setChecked(bool(self.app.config.get("auto_queue", False)))
        self._queue_cb.toggled.connect(lambda v: self.app.config.__setitem__("auto_queue", v))
        ql.addWidget(self._queue_cb)
        ql.addLayout(_key_row("Touche rejouer :", "queue_key", "key:return"))
        ql.addLayout(_delay_row("Délai après fin de match :", "queue_delay", 5))
        root.addWidget(q_card)

        fp_card = card()
        fpl = QVBoxLayout(fp_card); fpl.setContentsMargins(16,14,16,16); fpl.setSpacing(10)
        fpl.addWidget(lbl("AUTO FREEPLAY", C_MUTE, 9))
        self._freeplay_cb = QCheckBox("Lancer le freeplay automatiquement")
        self._freeplay_cb.setChecked(bool(self.app.config.get("auto_freeplay", False)))
        self._freeplay_cb.toggled.connect(lambda v: self.app.config.__setitem__("auto_freeplay", v))
        fpl.addWidget(self._freeplay_cb)
        fpl.addLayout(_key_row("Touche freeplay :", "freeplay_key", "key:f"))
        fpl.addLayout(_delay_row("Délai après fin de match :", "freeplay_delay", 55))
        root.addWidget(fp_card)

        po_card = card()
        pol = QVBoxLayout(po_card); pol.setContentsMargins(16,14,16,16); pol.setSpacing(10)
        pol.addWidget(lbl("OVERLAY JOUEURS  (hotkey)", C_MUTE, 9))
        pol.addWidget(lbl("Appuie sur cette touche en jeu pour afficher / masquer le mini-overlay.", C_TEXT, 9))
        pol.addLayout(_key_row("Touche overlay joueurs :", "players_overlay_key", "key:f7"))
        root.addWidget(po_card)

        save_btn = btn("💾  Sauvegarder", bg=C_BLUE, fg=C_TEXT, size=10)
        save_btn.clicked.connect(self.app.config.save); root.addWidget(save_btn); root.addStretch()


# ── SoundTab ─────────────────────────────────────────────────────────────
class SoundTab(QWidget):
    def __init__(self, app_ref):
        super().__init__(); self.app = app_ref; self._build()

    def _build(self):
        try: import pygame; PYGAME_AVAILABLE = True
        except ImportError: PYGAME_AVAILABLE = False
        root = QVBoxLayout(self); root.setContentsMargins(16,20,16,16); root.setSpacing(10)
        if not PYGAME_AVAILABLE:
            warn = card(bg="#2A0E00")
            wl = QVBoxLayout(warn); wl.setContentsMargins(16,12,16,12)
            wl.addWidget(lbl("⚠  pygame non installé", C_ORG, 11, True))
            wl.addWidget(lbl("pip install pygame", C_TEXT, 10)); root.addWidget(warn)
        header = card(bg=C_BG2)
        hl = QVBoxLayout(header); hl.setContentsMargins(14,10,14,10)
        hl.addWidget(lbl("Place tes fichiers .mp3 / .wav dans le meme dossier que l exe.", C_MUTE, 8))
        root.addWidget(header)

        vol_card = card()
        vl = QVBoxLayout(vol_card); vl.setContentsMargins(14,10,14,12); vl.setSpacing(6)
        vl.addWidget(lbl("VOLUME GLOBAL", C_MUTE, 9))
        vol_row = QHBoxLayout(); vol_row.setSpacing(10)
        vol_icon = lbl("🔈", C_TEXT, 12)
        self._vol_slider = QSlider(Qt.Orientation.Horizontal)
        self._vol_slider.setRange(0, 100)
        self._vol_slider.setValue(int(self.app.config.get("sound_volume", 100)))
        self._vol_slider.setFixedHeight(22)
        self._vol_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: #1A1E2A; border-radius: 4px; height: 6px; }
            QSlider::sub-page:horizontal { background: #1A8CFF; border-radius: 4px; height: 6px; }
            QSlider::handle:horizontal { background: #E8ECF4; border-radius: 7px; width: 14px; height: 14px; margin: -4px 0; }
            QSlider::handle:horizontal:hover { background: #1A8CFF; }
        """)
        self._vol_pct = lbl(f"{self._vol_slider.value()}%", C_TEXT, 10, bold=True)
        self._vol_pct.setFixedWidth(36)
        def _on_vol(v): self._vol_pct.setText(f"{v}%"); self.app.config["sound_volume"] = v
        self._vol_slider.valueChanged.connect(_on_vol)
        vol_row.addWidget(vol_icon); vol_row.addWidget(self._vol_slider, 1)
        vol_row.addWidget(lbl("🔊", C_TEXT, 12)); vol_row.addWidget(self._vol_pct)
        vl.addLayout(vol_row); root.addWidget(vol_card)

        for key, label in _SOUND_EVENTS:
            cfg_en = f"sound_{key}"; cfg_file = f"snd_file_{key}"
            c = card()
            cl = QVBoxLayout(c); cl.setContentsMargins(14,12,14,12); cl.setSpacing(8)
            cb = QCheckBox(label)
            cb.setChecked(bool(self.app.config.get(cfg_en, True)))
            cb.toggled.connect(lambda v, k=cfg_en: self.app.config.__setitem__(k, v))
            cl.addWidget(cb)
            file_row = QHBoxLayout(); file_row.setSpacing(6)
            field = QLineEdit(self.app.config.get(cfg_file, ""))
            field.setPlaceholderText("son.wav  ou  chemin complet")
            field.setStyleSheet(f"background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:4px 8px;font-size:10px;")
            field.textChanged.connect(lambda v, k=cfg_file: self.app.config.__setitem__(k, v.strip()))
            browse_btn = QPushButton("📂"); browse_btn.setFixedWidth(34)
            browse_btn.setStyleSheet(f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:4px;font-size:11px;}}QPushButton:hover{{background:{C_BLUE};}}")
            browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            browse_btn.clicked.connect(lambda _, f=field, k=cfg_file: self._browse(f, k))
            test_btn = QPushButton("▶"); test_btn.setFixedWidth(34)
            test_btn.setStyleSheet(f"QPushButton{{background:{C_BG3};color:{C_GREEN};border:none;border-radius:4px;padding:4px;font-size:11px;}}QPushButton:hover{{background:{C_BG3};color:white;}}")
            test_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            test_btn.clicked.connect(lambda _, f=field: self.app._play_sound(f.text().strip()))
            file_row.addWidget(field); file_row.addWidget(browse_btn); file_row.addWidget(test_btn)
            cl.addLayout(file_row); root.addWidget(c)

        save_btn = btn("💾  Sauvegarder", bg=C_BLUE, fg=C_TEXT, size=10)
        save_btn.clicked.connect(self.app.config.save); root.addWidget(save_btn); root.addStretch(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _browse(self, field, cfg_key):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier son", os.path.dirname(os.path.abspath(__file__)), "Fichiers audio (*.wav *.mp3 *.ogg *.flac);;Tous (*)")
        if path:
            rel = os.path.relpath(path, os.path.dirname(os.path.abspath(__file__)))
            if not rel.startswith(".."): path = rel
            field.setText(path); self.app.config[cfg_key] = path; self.app.config.save()


# ── SettingsTab ──────────────────────────────────────────────────────────
class SettingsTab(QWidget):
    def __init__(self, app_ref):
        super().__init__(); self.app = app_ref; self._build()

    def _build(self):
        root = QVBoxLayout(self); root.setContentsMargins(16,20,16,16); root.setSpacing(12)

        sm_card = card()
        sml = QVBoxLayout(sm_card); sml.setContentsMargins(16,14,16,16); sml.setSpacing(10)
        sml.addWidget(lbl("MODE STREAMER", C_MUTE, 9))
        sml.addWidget(lbl("Active une barre noire en haut de l'écran pour cacher le popup \"Partie Trouvée\".", C_TEXT, 9))
        self._streamer_btn = btn("🎥  ACTIVER LE MODE STREAMER", bg=C_BG3, fg=C_TEXT, size=11)
        self._streamer_btn.setFixedHeight(42); self._streamer_btn.clicked.connect(self._toggle_streamer)
        sml.addWidget(self._streamer_btn)
        mute_row = QHBoxLayout(); mute_row.addWidget(lbl("Couper le son hors partie", C_TEXT, 11))
        self._streamer_mute_chk = QCheckBox()
        self._streamer_mute_chk.setChecked(self.app.config.get("streamer_mute_audio", True))
        self._streamer_mute_chk.stateChanged.connect(self._on_streamer_mute_changed)
        mute_row.addStretch(); mute_row.addWidget(self._streamer_mute_chk); sml.addLayout(mute_row)
        self._streamer_hint = lbl("", C_MUTE, 9); sml.addWidget(self._streamer_hint)
        root.addWidget(sm_card)
        self._streamer_active = self.app.config.get("streamer_mode", False)
        self._update_streamer_btn()

        jcard = card()
        jl = QVBoxLayout(jcard); jl.setContentsMargins(16,14,16,16); jl.setSpacing(8)
        jl.addWidget(lbl("JOUEUR", C_MUTE, 9))
        r1 = QHBoxLayout(); r1.addWidget(lbl("Plateforme", C_TEXT, 11))
        self._platform = QComboBox(); self._platform.addItems(["epic", "steam", "ps4", "xbox", "switch"])
        self._platform.setCurrentText(self.app.config["platform"]); self._platform.setFixedWidth(110)
        r1.addStretch(); r1.addWidget(self._platform); jl.addLayout(r1)
        r2 = QHBoxLayout()
        self._username_lbl = lbl("Pseudo (exact)", C_TEXT, 11); r2.addWidget(self._username_lbl)
        self._username = QLineEdit(self.app.config["username"]); self._username.setFixedWidth(180)
        r2.addStretch(); r2.addWidget(self._username); jl.addLayout(r2); root.addWidget(jcard)
        self._platform.currentTextChanged.connect(self._on_platform_changed)
        self._on_platform_changed(self._platform.currentText())

        ocard = card()
        ol = QVBoxLayout(ocard); ol.setContentsMargins(16,14,16,16); ol.setSpacing(8)
        ol.addWidget(lbl("OVERLAY VICTOIRE / DÉFAITE", C_MUTE, 9))
        r_on = QHBoxLayout(); r_on.addWidget(lbl("Activer l'overlay résultat", C_TEXT, 11))
        self._result_overlay_enabled = QCheckBox()
        self._result_overlay_enabled.setChecked(self.app.config.get("result_overlay_enabled", True))
        r_on.addStretch(); r_on.addWidget(self._result_overlay_enabled); ol.addLayout(r_on)
        r_th = QHBoxLayout(); r_th.addWidget(lbl("Thème", C_TEXT, 11))
        self._result_theme = QComboBox()
        self._result_theme.addItems(["auto", "rl_classic", "victory", "defeat", "neon", "dark_minimal"])
        self._result_theme.setCurrentText(self.app.config.get("result_overlay_theme", "auto"))
        self._result_theme.setFixedWidth(130)
        r_th.addStretch(); r_th.addWidget(self._result_theme); ol.addLayout(r_th)
        root.addWidget(ocard)

        api_card = card(bg="#091409")
        al = QVBoxLayout(api_card); al.setContentsMargins(16,14,16,16); al.setSpacing(8)
        al.addWidget(lbl("⚙  STATSAPI — CONFIGURATION OBLIGATOIRE", C_GREEN, 9, True))
        al.addWidget(lbl("Édite ce fichier AVANT de lancer Rocket League :", C_TEXT, 10))
        al.addWidget(lbl("TAGame\\Config\\DefaultStatsAPI.ini", C_GOLD, 10, True))
        ini_preview = QTextEdit(); ini_preview.setReadOnly(True); ini_preview.setFixedHeight(62)
        ini_preview.setText("[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123")
        al.addWidget(ini_preview)
        open_btn = btn("📂  Ouvrir le dossier Config de RL", bg=C_BG3, size=10)
        open_btn.clicked.connect(self._open_rl_config); al.addWidget(open_btn)
        auto_btn = btn("⚡  Configurer automatiquement le .ini", bg=C_GREEN, fg="#000000", size=10)
        auto_btn.clicked.connect(self._auto_configure_ini); al.addWidget(auto_btn)
        self._ini_status = lbl("", C_GREEN, 9); self._ini_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(self._ini_status); root.addWidget(api_card)

        tcard = card()
        tl = QVBoxLayout(tcard); tl.setContentsMargins(16,14,16,14); tl.setSpacing(6)
        tl.addWidget(lbl("SOURCE DES DONNÉES MMR & RANG", C_MUTE, 9))
        tl.addWidget(lbl("✓ API tracker.gg — aucune dépendance externe requise", C_GREEN, 9))
        tl.addWidget(lbl("⚠  Le pseudo doit correspondre exactement au profil tracker.gg", C_ORG, 9))
        root.addWidget(tcard)

        save_btn = btn("💾  Sauvegarder les paramètres", bg=C_BLUE, fg=C_TEXT, size=12)
        save_btn.setFixedHeight(42); save_btn.clicked.connect(self._save); root.addWidget(save_btn)
        self._save_lbl = lbl("", C_GREEN, 10); self._save_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._save_lbl); root.addStretch()

    def _on_streamer_mute_changed(self, state):
        self.app.config["streamer_mute_audio"] = bool(state); self.app.config.save(); self._update_streamer_btn()

    def _toggle_streamer(self):
        self._streamer_active = not self._streamer_active
        self.app.config["streamer_mode"] = self._streamer_active
        self.app.config.save(); self.app._apply_streamer_mode(self._streamer_active); self._update_streamer_btn()

    def _update_streamer_btn(self):
        if self._streamer_active:
            self._streamer_btn.setText("🎥  DÉSACTIVER LE MODE STREAMER")
            self._streamer_btn.setStyleSheet(f"QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;padding:5px 12px;font-size:11px;font-weight:700;}}QPushButton:hover{{background:#e06000;}}")
            self._streamer_hint.setText("✓  Barre noire active")
            self._streamer_hint.setStyleSheet(f"color:{C_GREEN};font-size:9px;background:transparent;")
        else:
            self._streamer_btn.setText("🎥  ACTIVER LE MODE STREAMER")
            self._streamer_btn.setStyleSheet(f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;padding:5px 12px;font-size:11px;font-weight:700;}}QPushButton:hover{{background:{C_BG3}cc;}}")
            self._streamer_hint.setText("")

    def _on_platform_changed(self, platform):
        if platform == "steam":
            self._username_lbl.setText("Steam ID (64-bit)"); self._username.setPlaceholderText("ex: 76561198012345678")
        else:
            self._username_lbl.setText("Pseudo (exact)"); self._username.setPlaceholderText("ex: MonPseudo#1234")

    def _find_rl_config_dirs(self):
        rl_variants = ["rocketleague", "Rocket League", "RocketLeague"]
        base_paths = [
            r"C:\Program Files\Epic Games", r"C:\Program Files (x86)\Epic Games",
            r"C:\Program Files (x86)\Steam\steamapps\common", r"C:\Program Files\Steam\steamapps\common",
        ]
        found = []
        for base in base_paths:
            if not os.path.exists(base): continue
            for variant in rl_variants:
                cfg_dir = os.path.join(base, variant, "TAGame", "Config")
                if os.path.exists(cfg_dir): found.append(cfg_dir)
        return found

    def _open_rl_config(self):
        dirs = self._find_rl_config_dirs()
        QDesktopServices.openUrl(QUrl.fromLocalFile(dirs[0] if dirs else os.path.expanduser("~")))

    def _auto_configure_ini(self):
        ini_content = "[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123\n"
        dirs = self._find_rl_config_dirs(); found = []
        for cfg_dir in dirs:
            ini_path = os.path.join(cfg_dir, "DefaultStatsAPI.ini")
            try:
                with open(ini_path, "w", encoding="utf-8") as f: f.write(ini_content)
                found.append(ini_path)
            except Exception as e: self._ini_status.setText(f"Erreur: {e}"); return
        if found:
            self._ini_status.setStyleSheet(f"color:{C_GREEN};font-size:9px;")
            self._ini_status.setText(f"✓  Configuré dans {len(found)} dossier(s) RL")
        else:
            self._ini_status.setStyleSheet(f"color:{C_ORG};font-size:9px;")
            self._ini_status.setText("⚠  Dossier Rocket League introuvable")
        QTimer.singleShot(5000, lambda: self._ini_status.setText(""))

    def _save(self):
        self.app.config["platform"] = self._platform.currentText()
        self.app.config["username"] = self._username.text().strip()
        self.app.config["result_overlay_enabled"] = self._result_overlay_enabled.isChecked()
        self.app.config["result_overlay_theme"] = self._result_theme.currentText()
        self.app.config.save(); self._save_lbl.setText("✓  Sauvegardé !")
        QTimer.singleShot(2500, lambda: self._save_lbl.setText(""))
        self.app.fetch_mmr_async(force=True)
