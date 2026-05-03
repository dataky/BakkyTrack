#!/usr/bin/env python3
"""
BakkesMod v2 — Compatible StatsAPI
  Onglet 1 : Tracker   (W/L, MMR, streak)
  Onglet 2 : Joueurs   (liste match en cours, clic → tracker.network)
  Onglet 3 : Overlay   (activation, compact/bannière, mode MMR)
  Onglet 4 : Auto      (skip replay, auto-queue, freeplay)
  Onglet 5 : Paramètres
"""

import sys, json, time, threading, os, socket, urllib.parse, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import websocket          # pip install websocket-client
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service as ChromeService
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except Exception:
        WEBDRIVER_MANAGER_AVAILABLE = False
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except ImportError:
    VGAMEPAD_AVAILABLE = False

from PyQt6.QtCore    import Qt, QTimer, pyqtSignal, QObject, QUrl, QPointF, QRectF, QByteArray
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QTabWidget, QLineEdit, QComboBox,
    QTextEdit, QStackedWidget, QScrollArea, QCheckBox, QDialog
)
from PyQt6.QtGui import (
    QColor, QCursor, QPainter, QBrush, QPen, QLinearGradient, QRadialGradient, QFont,
    QDesktopServices, QIcon, QPolygonF
)
from PyQt6.QtSvg import QSvgRenderer

# ─────────────────────────────────────────────────────────────────────────────
#  CHEMINS & CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_DEFAULT_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAB4ElEQVR4nO2bXVLDMAyEVYZzwDXhBHBNuEh5asd47FiKtdIm8ffYyY92tbYzaSyyuDa3yJu9fdzvmuN+v29hdUFvpBU8AmmI+4W9RPfwNsPtYmjhNV5GTF8kWnjNrBEvMydni/eoYbd7XuJ/vsbHvH+Oj9mbhFfrCQxdb/Goy2qEaQh4i/fqfom1RrUBrJ1vYalVZQBCvKb7M2hrnloF0Fjjv4ehAUeKfo2m9k0DUOLR8S8ZaegakN15z/hvaaGeAyJoGoDsPmLt19DTtBJQ/5DdfSQtbXQJiFj7S+gMiOafAWeO/4NaI1UCouMvEmQAS/dbUCUgg6cBZ3r0HVFqNb8Ss6KNf9YT4mGGACohhzEABdQAr9kfOT/QJwA9OcIMYF77S6gTELE0wpbBUfGjhEQ9F6QkgGl4PA2I/CxlBLr7pVbqOSACOgNO/0Zoa/ynvw9gmgdQ1BpphkBG90VIDMgSL9IwADkMstf/lrb0BGR2X6RjQNRkGCm+pyksAdnx79E1AJ0Chu6LDBKAMoFFvIhiCBz54UhTe/g/Q9mzfo3KgCOmQFuzOgEeJkR131KraQjMmMAoXiTgc/nH+I98y2Nh9yRouSGreJG1ZWZtmlrb5jwvVnPJjZNbMG6dXVydP/yruvfRgdsmAAAAAElFTkSuQmCC"


CONFIG_PATH  = os.path.join(BASE_DIR, "config.json")
OVERLAY_PORT = 49124
REFRESH_MS   = 2000

PLAYLIST_NAMES = {
    "1v1": "Ranked Duel 1v1",
    "2v2": "Ranked Doubles 2v2",
    "3v3": "Ranked Standard 3v3",
}

DEFAULT_CONFIG = {
    "platform":           "epic",
    "username":           "",
    "statsapi_port":      49123,
    "overlay_mode":       "compact",
    "mmr_display_mode":   "both",
    "auto_skip_replay":   False,
    "auto_queue":         False,
    "auto_freeplay":      False,
    "skip_replay_key":    "key:k",
    "skip_replay_delay":  4.0,
    "queue_key":          "key:m",
    "queue_delay":        2.0,
    "freeplay_key":       "key:l",
    "freeplay_delay":     3.0,
    "players_overlay_key": "key:f7",
    "sound_goal_scored":   False,
    "sound_goal_conceded": False,
    "sound_crossbar":      False,
    "sound_demo_me":       False,
    "sound_demo_opponent": False,
    "sound_epic_save":     False,
    "sound_save":          False,
    "snd_file_goal_scored":   "",
    "snd_file_goal_conceded": "",
    "snd_file_crossbar":      "",
    "snd_file_demo_me":       "",
    "snd_file_demo_opponent": "",
    "snd_file_epic_save":     "",
    "snd_file_save":          "",
    "result_overlay_enabled": True,
    "result_overlay_theme":   "auto",
}

# ─────────────────────────────────────────────────────────────────────────────
#  COULEURS & STYLE
# ─────────────────────────────────────────────────────────────────────────────
C_BG    = "#0A0C10"
C_BG2   = "#12151C"
C_BG3   = "#1A1E2A"
C_BLUE  = "#1A8CFF"
C_ORG   = "#FF6B00"
C_TEXT  = "#E8ECF4"
C_MUTE  = "#5A6275"
C_GREEN = "#3AE08A"
C_GOLD  = "#FFD700"

APP_STYLE = f"""
QWidget {{ background:transparent; color:{C_TEXT};
           font-family:'Rajdhani','Segoe UI',sans-serif; font-size:12px; }}
QMainWindow {{ background:transparent; }}
QTabWidget {{ background:transparent; }}
QTabWidget::pane {{ border:1px solid {C_BG3}; background:rgba(12,14,20,0.80); }}
QTabBar::tab {{ background:rgba(18,20,28,0.88); color:{C_MUTE}; padding:8px 14px;
                border:none; font-size:10px; font-weight:700; letter-spacing:1px; }}
QTabBar::tab:selected {{ background:rgba(28,32,46,0.96); color:{C_TEXT};
                         border-bottom:2px solid {C_BLUE}; }}
QTabBar::tab:hover:!selected {{ color:{C_TEXT}; }}
QLineEdit, QComboBox {{ background:{C_BG3}; color:{C_TEXT};
                        border:1px solid {C_BG3}; border-radius:4px;
                        padding:5px 9px; font-size:11px; }}
QLineEdit:focus, QComboBox:focus {{ border:1px solid {C_BLUE}; }}
QComboBox::drop-down {{ border:none; padding-right:8px; }}
QComboBox QAbstractItemView {{ background:{C_BG3}; color:{C_TEXT};
                               selection-background-color:{C_BLUE}; outline:none; }}
QTextEdit {{ background:{C_BG3}; color:{C_MUTE}; border:none;
             font-family:'Courier New',monospace; font-size:9px; }}
QScrollBar:vertical {{ background:{C_BG2}; width:5px; border:none; }}
QScrollBar::handle:vertical {{ background:{C_BG3}; border-radius:2px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
QCheckBox {{ color:{C_TEXT}; font-size:11px; spacing:8px; }}
QCheckBox::indicator {{ width:16px; height:16px; border-radius:3px;
                        border:1px solid {C_BG3}; background:{C_BG3}; }}
QCheckBox::indicator:checked {{ background:{C_BLUE}; border-color:{C_BLUE}; }}
QScrollArea {{ background:transparent; border:none; }}
QScrollArea > QWidget > QWidget {{ background:transparent; }}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS UI
# ─────────────────────────────────────────────────────────────────────────────
def card(parent=None, bg=C_BG2):
    f = QFrame(parent)
    f.setStyleSheet(f"QFrame{{background:{bg};border-radius:6px;}}")
    return f

def lbl(text, color=C_MUTE, size=9, bold=False, parent=None):
    w = QLabel(text, parent)
    weight = "700" if bold else "400"
    w.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{weight};"
                    f"background:transparent;letter-spacing:1px;")
    return w

def btn(text, bg=C_BG3, fg=C_TEXT, size=10, bold=True, parent=None):
    w = QPushButton(text, parent)
    w.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    weight = "700" if bold else "400"
    w.setStyleSheet(f"""
        QPushButton{{background:{bg};color:{fg};border:none;border-radius:4px;
                     padding:5px 12px;font-size:{size}px;font-weight:{weight};}}
        QPushButton:hover{{background:{bg}cc;}}
        QPushButton:pressed{{background:{bg}99;}}
    """)
    return w

def hsep(parent=None):
    s = QFrame(parent)
    s.setFrameShape(QFrame.Shape.HLine)
    s.setFixedHeight(1)
    s.setStyleSheet(f"background:{C_BG3};border:none;")
    return s


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
class Config:
    def __init__(self):
        self._d = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                self._d.update(json.load(f))
        except Exception:
            pass

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._d, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] save error: {e}")

    def __getitem__(self, k):    return self._d[k]
    def __setitem__(self, k, v): self._d[k] = v
    def get(self, k, d=None):   return self._d.get(k, d)


# ─────────────────────────────────────────────────────────────────────────────
#  SIGNAUX
# ─────────────────────────────────────────────────────────────────────────────
class AppSignals(QObject):
    status_changed  = pyqtSignal(str, str)
    player_detected = pyqtSignal(str, int)
    match_result    = pyqtSignal(str)
    log_event       = pyqtSignal(str)
    mmr_updated     = pyqtSignal()
    mmr_error       = pyqtSignal(str)
    players_updated = pyqtSignal(list)   # liste joueurs du match courant
    # Signaux inter-services (MatchService → MainApp, sans couplage PyQt UI)
    trigger_sound   = pyqtSignal(str)          # event_key (ex: "goal_scored")
    press_key_sig   = pyqtSignal(str, float)   # key_str, delay_seconds


# ─────────────────────────────────────────────────────────────────────────────
from overlay_widgets import *
from overlay_widgets import _CompactCard, _key_to_vk

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

        # ── Connexion StatsAPI ──────────────────────────────────────────────
        conn = card()
        cl = QHBoxLayout(conn); cl.setContentsMargins(12, 10, 12, 10)
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color:{C_MUTE};font-size:14px;background:transparent;")
        self._status_lbl = lbl("Non connecté")
        port_lbl = lbl("Port:")
        self._port_edit = QLineEdit(str(self.app.config["statsapi_port"]))
        self._port_edit.setFixedWidth(60)
        reconn_btn = btn("Reconnecter", bg=C_BG3, size=9)
        reconn_btn.clicked.connect(self.app.reconnect_statsapi)
        cl.addWidget(self._dot); cl.addSpacing(6); cl.addWidget(self._status_lbl)
        cl.addStretch(); cl.addWidget(port_lbl); cl.addSpacing(4)
        cl.addWidget(self._port_edit); cl.addSpacing(8); cl.addWidget(reconn_btn)
        root.addWidget(conn)

        # ── Infos joueur + MMR ─────────────────────────────────────────────
        info = card()
        il = QVBoxLayout(info); il.setContentsMargins(14, 12, 14, 12); il.setSpacing(7)

        row_player = QHBoxLayout()
        row_player.addWidget(lbl("JOUEUR DÉTECTÉ", C_MUTE, 8))
        self._player_lbl = lbl("--", C_TEXT, 11, True)
        row_player.addStretch(); row_player.addWidget(self._player_lbl)
        il.addLayout(row_player); il.addWidget(hsep())

        row_mmr = QHBoxLayout()
        row_mmr.addWidget(lbl("MMR"))
        self._mmr_lbl   = lbl("--",  C_GOLD, 16, True)
        self._delta_lbl = lbl("",    C_GREEN, 10, True)
        self._rank_lbl  = lbl("",    C_MUTE,   9)
        ref_btn = btn("↻", bg=C_BG3, size=12)
        ref_btn.setFixedSize(26, 26)
        ref_btn.clicked.connect(self.app.fetch_mmr_async)
        row_mmr.addStretch()
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
        il.addLayout(row_pl)
        root.addWidget(info)

        # ── W / L counters ─────────────────────────────────────────────────
        wl = QHBoxLayout(); wl.setSpacing(8)

        for side in ("win", "loss"):
            c_card = card()
            color  = C_BLUE if side == "win" else C_ORG
            label  = "VICTOIRES" if side == "win" else "DÉFAITES"
            bar    = QFrame(c_card); bar.setFixedHeight(3)
            bar.setStyleSheet(f"background:{color};border:none;")
            cl2 = QVBoxLayout(c_card); cl2.setContentsMargins(0,0,0,10)
            cl2.addWidget(bar)
            cl2.addWidget(lbl(label, color, 9), alignment=Qt.AlignmentFlag.AlignHCenter)
            count_lbl = QLabel("0"); count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_lbl.setStyleSheet(f"color:{color};font-size:52px;font-weight:700;background:transparent;")
            cl2.addWidget(count_lbl)
            brow = QHBoxLayout(); brow.setSpacing(6); brow.setContentsMargins(10,0,10,0)
            bp = btn("+", bg=C_BG3, size=14); bm = btn("−", bg=C_BG3, size=14)
            bp.clicked.connect(lambda _, s=side: self.app.add(s))
            bm.clicked.connect(lambda _, s=side: self.app.remove(s))
            brow.addWidget(bp); brow.addWidget(bm)
            cl2.addLayout(brow)
            wl.addWidget(c_card, 1)
            if side == "win":
                self._wins_lbl = count_lbl
                wl.addWidget(lbl("VS", C_MUTE, 13))
            else:
                self._losses_lbl = count_lbl
        root.addLayout(wl)

        # ── Win rate bar ────────────────────────────────────────────────────
        wr_card = card()
        wrc = QVBoxLayout(wr_card); wrc.setContentsMargins(14, 8, 14, 8); wrc.setSpacing(4)
        wr_top = QHBoxLayout()
        wr_top.addWidget(lbl("WIN RATE", C_MUTE, 9))
        self._wr_lbl = lbl("--", C_TEXT, 13, True)
        wr_top.addStretch(); wr_top.addWidget(self._wr_lbl)
        wrc.addLayout(wr_top)
        bar_bg = QFrame(); bar_bg.setFixedHeight(8)
        bar_bg.setStyleSheet(f"background:#1A0500;border-radius:4px;")
        bar_layout = QHBoxLayout(bar_bg); bar_layout.setContentsMargins(0,0,0,0)
        self._bar = QFrame(); self._bar.setFixedHeight(8)
        self._bar.setStyleSheet(f"background:{C_BLUE};border-radius:4px;")
        bar_layout.addWidget(self._bar); bar_layout.addStretch()
        wrc.addWidget(bar_bg)
        root.addWidget(wr_card)

        # ── Mini stats ──────────────────────────────────────────────────────
        ms = QHBoxLayout(); ms.setSpacing(6)
        self._total_lbl  = QLabel("0")
        self._streak_lbl = QLabel("--")
        self._clock_lbl  = QLabel("0:00")
        for caption, val_ref in [("TOTAL", self._total_lbl),
                                   ("STREAK", self._streak_lbl),
                                   ("DURÉE", self._clock_lbl)]:
            c = card(); cl3 = QVBoxLayout(c); cl3.setContentsMargins(8,8,8,8); cl3.setSpacing(2)
            cl3.addWidget(lbl(caption, C_MUTE, 8), alignment=Qt.AlignmentFlag.AlignHCenter)
            val_ref.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_ref.setStyleSheet(f"color:{C_TEXT};font-size:15px;font-weight:700;background:transparent;")
            cl3.addWidget(val_ref)
            ms.addWidget(c, 1)
        root.addLayout(ms)

        # ── Log StatsAPI ───────────────────────────────────────────────────
        dbg = card()
        dl = QVBoxLayout(dbg); dl.setContentsMargins(12, 8, 12, 10); dl.setSpacing(6)
        dl.addWidget(lbl("MESSAGES STATSAPI", C_MUTE, 8))
        self._log = QTextEdit(); self._log.setReadOnly(True); self._log.setFixedHeight(70)
        dl.addWidget(self._log)
        root.addWidget(dbg)

        reset_btn = btn("Réinitialiser la session", bg=C_BG, fg=C_MUTE, size=10)
        reset_btn.clicked.connect(self.app.reset_session)
        root.addWidget(reset_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

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
            self._wr_lbl.setText("--"); self._bar.setFixedWidth(0); self._streak_lbl.setText("--")
        else:
            wr = round(a.wins / total * 100)
            self._wr_lbl.setText(f"{wr}%")
            bar_parent = self._bar.parent()
            if bar_parent:
                self._bar.setFixedWidth(max(1, int(bar_parent.width() * wr / 100)))
            if a.streak > 1:
                self._streak_lbl.setText(f"{a.streak}{'W' if a.streak_type=='win' else 'L'}")
            else:
                self._streak_lbl.setText("--")

    def _on_mmr(self):
        d   = self.app.all_mmr.get(self.app.selected_playlist, {})
        mmr = d.get("mmr")
        self._mmr_lbl.setText(str(mmr) if mmr else "--")
        self._rank_lbl.setText(d.get("rank", ""))
        chg = d.get("mmr_change", 0)
        if chg != 0 and mmr:
            sign = "+" if chg > 0 else ""
            clr  = C_GREEN if chg > 0 else C_ORG
            self._delta_lbl.setText(f"{sign}{chg}")
            self._delta_lbl.setStyleSheet(f"color:{clr};font-size:9px;font-weight:700;background:transparent;")
        else:
            self._delta_lbl.setText("")
        self.app.highlight_playlist_btns(self._pl_btns)

    def _on_mmr_error(self, msg):
        self._mmr_lbl.setText("ERR")
        self._mmr_lbl.setStyleSheet(f"color:{C_ORG};font-size:16px;font-weight:700;background:transparent;")
        self._delta_lbl.setText("")
        self._rank_lbl.setText(msg[:40])
        self._rank_lbl.setStyleSheet(f"color:{C_ORG};font-size:9px;background:transparent;")

    def _on_log(self, msg):
        self._log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _tick_clock(self):
        elapsed = int(time.time() - self.app.session_start)
        m, s = divmod(elapsed, 60)
        self._clock_lbl.setText(f"{m}:{s:02d}")

    def get_port(self):
        return self._port_edit.text().strip()


# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 2 — JOUEURS EN MATCH
# ─────────────────────────────────────────────────────────────────────────────
class PlayersTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._players = []
        self._build()
        app_ref.signals.players_updated.connect(self._on_players)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(lbl("JOUEURS EN MATCH", C_MUTE, 9))
        header.addStretch()
        open_all_btn = btn("Ouvrir tous →", bg=C_BG3, size=9)
        open_all_btn.clicked.connect(self._open_all)
        header.addWidget(open_all_btn)
        root.addLayout(header)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidget(self._list_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;border:none;")
        root.addWidget(scroll, 1)

        hint = lbl("Clic sur → pour ouvrir le profil sur tracker.network", C_MUTE, 9)
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._show_empty()

    def _show_empty(self):
        self._clear_list()
        empty = lbl("Aucun match en cours", C_MUTE, 10)
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._list_layout.addWidget(empty)
        self._list_layout.addStretch()

    def _clear_list(self):
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_players(self, players):
        self._players = players
        if not players:
            self._show_empty()
            return

        self._clear_list()
        blues   = [p for p in players if p.get("TeamNum") == 0]
        oranges = [p for p in players if p.get("TeamNum") == 1]

        for team_name, team_color, team_players in [
            ("🔵  BLUE",   C_BLUE, blues),
            ("🟠  ORANGE", C_ORG,  oranges)
        ]:
            if team_players:
                self._list_layout.addWidget(lbl(team_name, team_color, 9, True))
                for p in team_players:
                    self._list_layout.addWidget(self._make_row(p, team_color))

        self._list_layout.addStretch()

    def _platform_from_id(self, primary_id):
        if primary_id.startswith("Steam|"):   return "steam"
        if primary_id.startswith("Epic|"):    return "epic"
        if primary_id.startswith("PS4|"):     return "ps4"
        if primary_id.startswith("XboxOne|"): return "xbox"
        if primary_id.startswith("Switch|"):  return "switch"
        return "epic"

    def _make_row(self, player, color):
        row = card(bg=C_BG2)
        row.setFixedHeight(54)
        rl = QHBoxLayout(row); rl.setContentsMargins(12, 8, 12, 8)

        platform = self._platform_from_id(player.get("PrimaryId", ""))
        plat_lbl = QLabel(platform.upper())
        plat_lbl.setStyleSheet(
            f"color:{C_BG};background:{C_MUTE};border-radius:3px;"
            f"padding:2px 5px;font-size:7px;font-weight:700;background:transparent;"
            f"color:{C_MUTE};border:1px solid {C_BG3};")

        name_lbl = lbl(player.get("Name", "?"), color, 12, True)
        stats_lbl = lbl(
            f"⚽ {player.get('Goals',0)}   🅰 {player.get('Assists',0)}   🛡 {player.get('Saves',0)}",
            C_MUTE, 9)

        open_btn = btn("→", bg=C_BG3, size=11)
        open_btn.setFixedSize(30, 30)
        open_btn.clicked.connect(
            lambda _, n=player.get("Name",""), pl=platform: self._open_profile(n, pl))

        rl.addWidget(plat_lbl); rl.addSpacing(8)
        vl = QVBoxLayout(); vl.setSpacing(2); vl.setContentsMargins(0,0,0,0)
        vl.addWidget(name_lbl); vl.addWidget(stats_lbl)
        rl.addLayout(vl); rl.addStretch(); rl.addWidget(open_btn)
        return row

    def _open_profile(self, name, platform):
        url = (f"https://rocketleague.tracker.network/rocket-league/profile"
               f"/{platform}/{urllib.parse.quote(name)}/overview")
        QDesktopServices.openUrl(QUrl(url))

    def _open_all(self):
        for p in self._players:
            pl = self._platform_from_id(p.get("PrimaryId", ""))
            self._open_profile(p.get("Name", ""), pl)


# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 3 — OVERLAY
# ─────────────────────────────────────────────────────────────────────────────
class OverlayTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(12)

        # ── Toggle ────────────────────────────────────────────────────────
        tog_card = card()
        tl = QVBoxLayout(tog_card); tl.setContentsMargins(16,16,16,16); tl.setSpacing(8)
        tl.addWidget(lbl("OVERLAY", C_MUTE, 9))
        self._toggle_btn = btn("▶  ACTIVER L'OVERLAY", bg=C_BG3, fg=C_TEXT, size=12)
        self._toggle_btn.setFixedHeight(44)
        self._toggle_btn.clicked.connect(self._toggle)
        tl.addWidget(self._toggle_btn)
        tl.addWidget(lbl("Double-clic sur l'overlay pour changer de mode", C_MUTE, 9))
        root.addWidget(tog_card)

        # ── Mode compact/bannière ─────────────────────────────────────────
        mode_card = card()
        ml = QVBoxLayout(mode_card); ml.setContentsMargins(16,14,16,16); ml.setSpacing(10)
        ml.addWidget(lbl("FORMAT", C_MUTE, 9))
        r_mode = QHBoxLayout()
        r_mode.addWidget(lbl("Type d'overlay", C_TEXT, 11))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            "compact  (224×172)",
            "bannière RL  (440×68)",
            "bannière classic  (380×62)",
            "pill  (340×36)  — minimaliste",
            "neon  (260×140)  — cyberpunk",
            "sidebar  (108×260)  — vertical",
            "gauge  (200×200)  — arc winrate",
            "ticker  (640×26)  — défilant TV",
            "glass  (300×110)  — glassmorphism",
            "scoreboard  (380×88)  — Blue vs Orange",
            "HUD  (320×130)  — militaire FPS",
            "vivid  (400×78)  — gradient saturé",
        ])
        self._MODE_MAP = {
            0: "compact",
            1: "banner",
            2: "banner_classic",
            3: "pill",
            4: "neon",
            5: "sidebar",
            6: "gauge",
            7: "ticker",
            8: "glassmorph",
            9: "scoreboard",
            10: "hud",
            11: "vivid",
        }
        self._MODE_REVERSE = {v: k for k, v in self._MODE_MAP.items()}
        self._mode_combo.setFixedWidth(200)
        self._mode_combo.currentIndexChanged.connect(
            lambda i: self._set_mode(self._MODE_MAP[i]))
        r_mode.addStretch(); r_mode.addWidget(self._mode_combo)
        ml.addLayout(r_mode)
        root.addWidget(mode_card)

        # ── Mode affichage MMR ────────────────────────────────────────────
        mmr_card = card()
        mml = QVBoxLayout(mmr_card); mml.setContentsMargins(16,14,16,16); mml.setSpacing(8)
        mml.addWidget(lbl("AFFICHAGE MMR", C_MUTE, 9))
        self._mmr_btns = {}
        for mode, label in [
            ("both",  "MMR + Delta  (ex: 1234  +24)"),
            ("mmr",   "MMR uniquement  (ex: 1234)"),
            ("delta", "Delta uniquement  (ex: +24)"),
        ]:
            b = btn(label, bg=C_BG3, fg=C_MUTE, size=10)
            b.setFixedHeight(34)
            b.clicked.connect(lambda _, m=mode: self._set_mmr_mode(m))
            mml.addWidget(b); self._mmr_btns[mode] = b
        root.addWidget(mmr_card)

        # ── Preview ───────────────────────────────────────────────────────
        prev_card = card()
        pl = QVBoxLayout(prev_card); pl.setContentsMargins(16,14,16,16); pl.setSpacing(8)
        pl.addWidget(lbl("APERÇU COMPACT", C_MUTE, 9))
        prev_inner = QHBoxLayout()
        self._preview = _CompactCard(); self._preview.setEnabled(False)
        prev_inner.addStretch(); prev_inner.addWidget(self._preview); prev_inner.addStretch()
        pl.addLayout(prev_inner)
        root.addWidget(prev_card)
        root.addStretch()

        self._active = False
        saved_mode = self.app.config.get("overlay_mode", "compact")
        self._mode_combo.setCurrentIndex(self._MODE_REVERSE.get(saved_mode, 0))
        self._set_mode(saved_mode)
        self._set_mmr_mode(self.app.config.get("mmr_display_mode", "both"))

    def _toggle(self):
        self._active = not self._active
        if self._active:
            self.app.overlay_win.show()
            self._toggle_btn.setText("■  DÉSACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(f"""
                QPushButton{{background:{C_ORG};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:12px;font-weight:700;}}
                QPushButton:hover{{background:#e06000;}}""")
        else:
            self.app.overlay_win.hide()
            self._toggle_btn.setText("▶  ACTIVER L'OVERLAY")
            self._toggle_btn.setStyleSheet(f"""
                QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;
                             padding:5px 12px;font-size:12px;font-weight:700;}}
                QPushButton:hover{{background:{C_BG3}cc;}}""")

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
                f"QPushButton{{background:{C_BLUE if active else C_BG3};"
                f"color:{C_TEXT if active else C_MUTE};border:none;border-radius:4px;"
                f"padding:5px 12px;font-size:10px;font-weight:700;}}"
                + ("" if active else f"QPushButton:hover{{color:{C_TEXT};}}"))

    def refresh_preview(self, stats):
        self._preview.update_stats(stats, self.app.config.get("mmr_display_mode", "both"))



# ─────────────────────────────────────────────────────────────────────────────
#  KEY CAPTURE — Dialog + Widget
# ─────────────────────────────────────────────────────────────────────────────

# Mapping Qt key codes → pyautogui key names
_QT_KEY_MAP = {
    Qt.Key.Key_Space:        "space",
    Qt.Key.Key_Return:       "return",
    Qt.Key.Key_Enter:        "return",
    Qt.Key.Key_Escape:       "escape",
    Qt.Key.Key_Tab:          "tab",
    Qt.Key.Key_Backspace:    "backspace",
    Qt.Key.Key_Delete:       "delete",
    Qt.Key.Key_Up:           "up",
    Qt.Key.Key_Down:         "down",
    Qt.Key.Key_Left:         "left",
    Qt.Key.Key_Right:        "right",
    Qt.Key.Key_F1:  "f1",  Qt.Key.Key_F2:  "f2",  Qt.Key.Key_F3:  "f3",
    Qt.Key.Key_F4:  "f4",  Qt.Key.Key_F5:  "f5",  Qt.Key.Key_F6:  "f6",
    Qt.Key.Key_F7:  "f7",  Qt.Key.Key_F8:  "f8",  Qt.Key.Key_F9:  "f9",
    Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
    Qt.Key.Key_Home:    "home",  Qt.Key.Key_End:      "end",
    Qt.Key.Key_PageUp:  "pageup", Qt.Key.Key_PageDown: "pagedown",
    Qt.Key.Key_Insert:  "insert",
}


class KeyCaptureDialog(QDialog):
    """Fenêtre de capture : attend un appui clavier ou manette."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enregistrer une touche")
        self.setFixedSize(320, 190)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(f"background:{C_BG2};border:2px solid {C_BLUE};border-radius:8px;")
        self.captured_key = None
        self._listening   = True
        self._gamepad_timer = None
        self._build()
        if PYGAME_AVAILABLE:
            self._start_gamepad_poll()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 20)
        lay.setSpacing(14)

        title = QLabel("ENREGISTRER UNE TOUCHE")
        title.setStyleSheet(f"color:{C_BLUE};font-size:10px;font-weight:700;"
                            f"letter-spacing:2px;background:transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        self._hint = QLabel("Appuie sur une touche clavier\nou un bouton manette…")
        self._hint.setStyleSheet(f"color:{C_TEXT};font-size:12px;background:transparent;")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setWordWrap(True)
        lay.addWidget(self._hint)

        if PYGAME_AVAILABLE:
            try:
                pygame.init(); pygame.joystick.init()
                count = pygame.joystick.get_count()
            except Exception:
                count = 0
            if count == 0:
                self._hint.setText("Appuie sur une touche clavier…\n(aucune manette détectée)")
        else:
            self._hint.setText("Appuie sur une touche clavier…\n(pip install pygame pour manette)")

        cancel_btn = btn("Annuler", bg=C_BG3, fg=C_MUTE, size=10)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

    def _start_gamepad_poll(self):
        try:
            pygame.init()
            pygame.joystick.init()
            self._joysticks = [pygame.joystick.Joystick(i)
                               for i in range(pygame.joystick.get_count())]
            for j in self._joysticks:
                j.init()
            self._gamepad_timer = QTimer(self)
            self._gamepad_timer.timeout.connect(self._poll_gamepad)
            self._gamepad_timer.start(16)
        except Exception:
            pass

    def _poll_gamepad(self):
        try:
            pygame.event.pump()
            for ev in pygame.event.get():
                if ev.type == pygame.JOYBUTTONDOWN and self._listening:
                    if self._gamepad_timer:
                        self._gamepad_timer.stop()
                    self._captured(f"joy_btn_{ev.button}",
                                   f"🎮  Bouton manette {ev.button}")
                    return
        except Exception:
            pass

    def keyPressEvent(self, event):
        if not self._listening:
            return
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
                   Qt.Key.Key_Meta, Qt.Key.Key_CapsLock):
            return
        name = _QT_KEY_MAP.get(key)
        if name is None and 0x20 <= key <= 0x7E:
            name = chr(key).lower()
        if name:
            if self._gamepad_timer:
                self._gamepad_timer.stop()
            self._captured(f"key:{name}", f"⌨  {name.upper()}")

    def _captured(self, key, label):
        self._listening = False
        self.captured_key = key
        self._hint.setText(f"✓  {label}")
        QTimer.singleShot(300, self.accept)

    def closeEvent(self, event):
        self._listening = False
        if self._gamepad_timer:
            self._gamepad_timer.stop()
        super().closeEvent(event)


def _key_display(key_str):
    """Formate une clé pour affichage."""
    if not key_str:
        return "—"
    if key_str.startswith("key:"):
        return f"⌨  {key_str[4:].upper()}"
    if key_str.startswith("joy_btn_"):
        return f"🎮  Btn {key_str.split('_')[2]}"
    return f"⌨  {key_str.upper()}"   # legacy


class KeyCaptureWidget(QWidget):
    """Affiche la touche courante + bouton Enregistrer."""
    key_changed = pyqtSignal(str)

    def __init__(self, key_val="", parent=None):
        super().__init__(parent)
        self._key = key_val
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._display = QLabel(_key_display(key_val))
        self._display.setFixedWidth(140)
        self._display.setStyleSheet(
            f"background:{C_BG3};color:{C_TEXT};border-radius:4px;"
            f"padding:5px 9px;font-size:11px;border:1px solid {C_BG3};")

        self._rec_btn = QPushButton("🎯  Enregistrer")
        self._rec_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._rec_btn.setStyleSheet(f"""
            QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;
                         padding:5px 10px;font-size:9px;font-weight:700;}}
            QPushButton:hover{{background:{C_BLUE};color:{C_TEXT};}}
        """)
        self._rec_btn.clicked.connect(self._start_capture)

        lay.addWidget(self._display)
        lay.addWidget(self._rec_btn)

    def _start_capture(self):
        dlg = KeyCaptureDialog(self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.captured_key:
            self._key = dlg.captured_key
            self._display.setText(_key_display(dlg.captured_key))
            self.key_changed.emit(dlg.captured_key)

    def value(self):
        return self._key


# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 4 — AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────
class AutomationTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(12)

        # ── Avertissements dépendances ────────────────────────────────────
        if not PYAUTOGUI_AVAILABLE:
            warn = card(bg="#2A0E00")
            wl = QVBoxLayout(warn); wl.setContentsMargins(16,14,16,14)
            wl.addWidget(lbl("⚠  pyautogui non installé", C_ORG, 11, True))
            wl.addWidget(lbl("pip install pyautogui", C_TEXT, 10))
            root.addWidget(warn)

        if PYGAME_AVAILABLE:
            pygame.init(); pygame.joystick.init()
            n = pygame.joystick.get_count()
            joy_txt = f"🎮  {n} manette(s) détectée(s)" if n else "🎮  Aucune manette détectée"
            joy_info = card(bg=C_BG2)
            jl = QVBoxLayout(joy_info); jl.setContentsMargins(14,8,14,8)
            jl.addWidget(lbl(joy_txt, C_GREEN if n else C_MUTE, 9))
            root.addWidget(joy_info)
        else:
            warn2 = card(bg="#1A1400")
            w2l = QVBoxLayout(warn2); w2l.setContentsMargins(16,10,16,10)
            w2l.addWidget(lbl("🎮  Manette : pip install pygame  +  vgamepad", C_MUTE, 9))
            root.addWidget(warn2)

        def _parse_delay(v, default):
            try:    return float(v.replace(",", "."))
            except: return default

        def _delay_row(label, cfg_key, default):
            """Crée une ligne label + champ délai (sec, virgule acceptée)."""
            row = QHBoxLayout()
            row.addWidget(lbl(label, C_TEXT, 10))
            row.addStretch()
            field = QLineEdit(str(self.app.config.get(cfg_key, default)))
            field.setFixedWidth(70)
            field.setAlignment(Qt.AlignmentFlag.AlignCenter)
            field.textChanged.connect(
                lambda v, k=cfg_key, d=default:
                    self.app.config.__setitem__(k, _parse_delay(v, d)))
            sec_lbl = lbl("sec", C_MUTE, 9)
            row.addWidget(field); row.addWidget(sec_lbl)
            return row

        def _key_row(label, cfg_key, default):
            """Crée une ligne label + KeyCaptureWidget."""
            row = QHBoxLayout()
            row.addWidget(lbl(label, C_TEXT, 10))
            row.addStretch()
            w = KeyCaptureWidget(self.app.config.get(cfg_key, default))
            w.key_changed.connect(lambda v, k=cfg_key: self.app.config.__setitem__(k, v))
            row.addWidget(w)
            return row

        # ── Skip Replay ───────────────────────────────────────────────────
        sr_card = card()
        sl = QVBoxLayout(sr_card); sl.setContentsMargins(16,14,16,16); sl.setSpacing(10)
        sl.addWidget(lbl("SKIP REPLAY AUTO", C_MUTE, 9))

        self._skip_cb = QCheckBox("Activer le skip replay automatique")
        self._skip_cb.setChecked(bool(self.app.config.get("auto_skip_replay", False)))
        self._skip_cb.toggled.connect(lambda v: self.app.config.__setitem__("auto_skip_replay", v))
        sl.addWidget(self._skip_cb)

        sl.addLayout(_key_row("Touche de skip :", "skip_replay_key", "key:space"))
        sl.addLayout(_delay_row("Délai avant skip (0 = immédiat) :", "skip_replay_delay", 0))
        sl.addWidget(lbl("Ajuste le délai si le skip est trop tôt ou trop tard.", C_MUTE, 8))
        root.addWidget(sr_card)

        # ── Auto Queue ────────────────────────────────────────────────────
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

        # ── Auto Freeplay ─────────────────────────────────────────────────
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

        # ── Players Overlay hotkey ────────────────────────────────────────
        po_card = card()
        pol = QVBoxLayout(po_card); pol.setContentsMargins(16,14,16,16); pol.setSpacing(10)
        pol.addWidget(lbl("OVERLAY JOUEURS  (hotkey)", C_MUTE, 9))
        pol.addWidget(lbl(
            "Appuie sur cette touche en jeu pour afficher / masquer\n"
            "le mini-overlay avec les pseudos des joueurs du match.",
            C_TEXT, 9))
        pol.addLayout(_key_row("Touche overlay joueurs :", "players_overlay_key", "key:f7"))
        root.addWidget(po_card)

        save_btn = btn("💾  Sauvegarder", bg=C_BLUE, fg=C_TEXT, size=10)
        save_btn.clicked.connect(self.app.config.save)
        root.addWidget(save_btn)
        root.addStretch()



# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 5 — SONS
# ─────────────────────────────────────────────────────────────────────────────

_SOUND_EVENTS = [
    ("goal_scored",   "🎯  But marqué"),
    ("goal_conceded", "💀  But encaissé"),
    ("crossbar",      "🏐  Poteau / Barre"),
    ("demo_me",       "💥  Démoli (toi)"),
    ("demo_opponent", "🔥  Démolition adverse"),
    ("epic_save",     "🧤  Epic Save"),
    ("save",          "🛡  Save"),
]

class SoundTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(10)

        if not PYGAME_AVAILABLE:
            warn = card(bg="#2A0E00")
            wl = QVBoxLayout(warn); wl.setContentsMargins(16, 12, 16, 12)
            wl.addWidget(lbl("⚠  pygame non installe", C_ORG, 11, True))
            wl.addWidget(lbl("pip install pygame", C_TEXT, 10))
            root.addWidget(warn)

        header = card(bg=C_BG2)
        hl = QVBoxLayout(header); hl.setContentsMargins(14, 10, 14, 10)
        hl.addWidget(lbl("Place tes fichiers .mp3 / .wav dans le meme dossier que l exe.", C_MUTE, 8))
        root.addWidget(header)

        for key, label in _SOUND_EVENTS:
            cfg_en  = f"sound_{key}"
            cfg_file = f"snd_file_{key}"

            c = card()
            cl = QVBoxLayout(c); cl.setContentsMargins(14, 12, 14, 12); cl.setSpacing(8)

            # Ligne 1 : checkbox + label
            cb = QCheckBox(label)
            cb.setChecked(bool(self.app.config.get(cfg_en, True)))
            cb.toggled.connect(lambda v, k=cfg_en: self.app.config.__setitem__(k, v))
            cl.addWidget(cb)

            # Ligne 2 : champ fichier + bouton parcourir + test
            file_row = QHBoxLayout(); file_row.setSpacing(6)

            field = QLineEdit(self.app.config.get(cfg_file, ""))
            field.setPlaceholderText("son.wav  ou  chemin complet")
            field.setStyleSheet(
                f"background:{C_BG3};color:{C_TEXT};border:none;border-radius:4px;"
                f"padding:4px 8px;font-size:10px;")
            field.textChanged.connect(lambda v, k=cfg_file: self.app.config.__setitem__(k, v.strip()))

            browse_btn = QPushButton("📂")
            browse_btn.setFixedWidth(34)
            browse_btn.setToolTip("Choisir un fichier son")
            browse_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_TEXT};border:none;"
                f"border-radius:4px;padding:4px;font-size:11px;}}"
                f"QPushButton:hover{{background:{C_BLUE};}}")
            browse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            browse_btn.clicked.connect(lambda _, f=field, k=cfg_file: self._browse(f, k))

            test_btn = QPushButton("▶")
            test_btn.setFixedWidth(34)
            test_btn.setToolTip("Tester le son")
            test_btn.setStyleSheet(
                f"QPushButton{{background:{C_BG3};color:{C_GREEN};border:none;"
                f"border-radius:4px;padding:4px;font-size:11px;}}"
                f"QPushButton:hover{{background:{C_BG3};color:white;}}")
            test_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            test_btn.clicked.connect(lambda _, f=field: self.app._play_sound(f.text().strip()))

            file_row.addWidget(field)
            file_row.addWidget(browse_btn)
            file_row.addWidget(test_btn)
            cl.addLayout(file_row)
            root.addWidget(c)

        save_btn = btn("💾  Sauvegarder", bg=C_BLUE, fg=C_TEXT, size=10)
        save_btn.clicked.connect(self.app.config.save)
        root.addWidget(save_btn)
        root.addStretch()

    def _browse(self, field, cfg_key):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier son", BASE_DIR,
            "Fichiers audio (*.wav *.mp3 *.ogg *.flac);;Tous (*)")
        if path:
            # Stocker le nom de fichier relatif si dans le meme dossier
            rel = os.path.relpath(path, BASE_DIR)
            if not rel.startswith(".."):
                path = rel
            field.setText(path)
            self.app.config[cfg_key] = path
            self.app.config.save()

# ─────────────────────────────────────────────────────────────────────────────
#  ONGLET 5 — PARAMÈTRES
# ─────────────────────────────────────────────────────────────────────────────
class SettingsTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 16)
        root.setSpacing(12)

        # ── Joueur ────────────────────────────────────────────────────────
        jcard = card()
        jl = QVBoxLayout(jcard); jl.setContentsMargins(16,14,16,16); jl.setSpacing(8)
        jl.addWidget(lbl("JOUEUR", C_MUTE, 9))

        r1 = QHBoxLayout()
        r1.addWidget(lbl("Plateforme", C_TEXT, 11))
        self._platform = QComboBox()
        self._platform.addItems(["epic", "steam", "ps4", "xbox", "switch"])
        self._platform.setCurrentText(self.app.config["platform"])
        self._platform.setFixedWidth(110)
        r1.addStretch(); r1.addWidget(self._platform)
        jl.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(lbl("Pseudo (exact)", C_TEXT, 11))
        self._username = QLineEdit(self.app.config["username"])
        self._username.setFixedWidth(180)
        r2.addStretch(); r2.addWidget(self._username)
        jl.addLayout(r2)
        root.addWidget(jcard)

        # ── Overlay résultat ──────────────────────────────────────────────
        ocard = card()
        ol = QVBoxLayout(ocard); ol.setContentsMargins(16,14,16,16); ol.setSpacing(8)
        ol.addWidget(lbl("OVERLAY VICTOIRE / DÉFAITE", C_MUTE, 9))

        r_on = QHBoxLayout()
        r_on.addWidget(lbl("Activer l'overlay résultat", C_TEXT, 11))
        self._result_overlay_enabled = QCheckBox()
        self._result_overlay_enabled.setChecked(self.app.config.get("result_overlay_enabled", True))
        r_on.addStretch(); r_on.addWidget(self._result_overlay_enabled)
        ol.addLayout(r_on)

        r_th = QHBoxLayout()
        r_th.addWidget(lbl("Thème", C_TEXT, 11))
        self._result_theme = QComboBox()
        self._result_theme.addItems(["auto", "rl_classic", "victory", "defeat", "neon", "dark_minimal"])
        self._result_theme.setCurrentText(self.app.config.get("result_overlay_theme", "auto"))
        self._result_theme.setFixedWidth(130)
        r_th.addStretch(); r_th.addWidget(self._result_theme)
        ol.addLayout(r_th)
        root.addWidget(ocard)

        # ── StatsAPI setup ────────────────────────────────────────────────
        api_card = card(bg="#091409")
        al = QVBoxLayout(api_card); al.setContentsMargins(16,14,16,16); al.setSpacing(8)
        al.addWidget(lbl("⚙  STATSAPI — CONFIGURATION OBLIGATOIRE", C_GREEN, 9, True))
        al.addWidget(lbl("Édite ce fichier AVANT de lancer Rocket League :", C_TEXT, 10))
        al.addWidget(lbl("TAGame\\Config\\DefaultStatsAPI.ini", C_GOLD, 10, True))

        ini_preview = QTextEdit()
        ini_preview.setReadOnly(True); ini_preview.setFixedHeight(62)
        ini_preview.setText("[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123")
        al.addWidget(ini_preview)

        open_btn = btn("📂  Ouvrir le dossier Config de RL", bg=C_BG3, size=10)
        open_btn.clicked.connect(self._open_rl_config)
        al.addWidget(open_btn)

        auto_btn = btn("⚡  Configurer automatiquement le .ini", bg=C_GREEN, fg="#000000", size=10)
        auto_btn.clicked.connect(self._auto_configure_ini)
        al.addWidget(auto_btn)

        self._ini_status = lbl("", C_GREEN, 9)
        self._ini_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(self._ini_status)
        root.addWidget(api_card)

        # ── Tracker.network ───────────────────────────────────────────────
        tcard = card()
        tl = QVBoxLayout(tcard); tl.setContentsMargins(16,14,16,14); tl.setSpacing(6)
        tl.addWidget(lbl("RLSTATS.NET (Scraping Chrome)", C_MUTE, 9))
        tl.addWidget(lbl("✓ Scraping automatique via Selenium — pas d'API key nécessaire", C_GREEN, 9))
        tl.addWidget(lbl("⚠  Google Chrome doit être installé sur la machine", C_ORG, 9))
        root.addWidget(tcard)

        save_btn = btn("💾  Sauvegarder les paramètres", bg=C_BLUE, fg=C_TEXT, size=12)
        save_btn.setFixedHeight(42)
        save_btn.clicked.connect(self._save)
        root.addWidget(save_btn)

        self._save_lbl = lbl("", C_GREEN, 10)
        self._save_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._save_lbl)
        root.addStretch()

    def _open_rl_config(self):
        paths = [
            r"C:\Program Files\Epic Games\rocketleague\TAGame\Config",
            r"C:\Program Files (x86)\Steam\steamapps\common\rocketleague\TAGame\Config",
        ]
        for p in paths:
            if os.path.exists(p):
                QDesktopServices.openUrl(QUrl.fromLocalFile(p))
                return
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.expanduser("~")))

    def _auto_configure_ini(self):
        """Écrit DefaultStatsAPI.ini automatiquement dans tous les dossiers RL trouvés."""
        ini_content = "[TAGame.MatchStatsExporter_TA]\nPacketSendRate=30\nPort=49123\n"
        search_roots = [
            r"C:\Program Files\Epic Games",
            r"C:\Program Files (x86)\Epic Games",
            r"C:\Program Files (x86)\Steam\steamapps\common",
            r"C:\Program Files\Steam\steamapps\common",
        ]
        # Aussi chercher via Steam libraryfolders.vdf
        steam_dirs = []
        vdf_paths = [
            r"C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf",
            r"C:\Program Files\Steam\steamapps\libraryfolders.vdf",
        ]
        for vdf in vdf_paths:
            if os.path.exists(vdf):
                try:
                    for line in open(vdf, encoding="utf-8", errors="replace"):
                        line = line.strip()
                        if '"path"' in line.lower():
                            p = line.split('"')[-2]
                            candidate = os.path.join(p, "steamapps", "common")
                            if os.path.exists(candidate):
                                steam_dirs.append(candidate)
                except Exception:
                    pass
        search_roots += steam_dirs

        found = []
        for root in search_roots:
            if not os.path.exists(root):
                continue
            for folder in os.listdir(root):
                cfg_dir = os.path.join(root, folder, "TAGame", "Config")
                if os.path.exists(cfg_dir):
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
            self._ini_status.setText(f"✓  Configuré dans {len(found)} dossier(s) RL")
        else:
            self._ini_status.setStyleSheet(f"color:{C_ORG};font-size:9px;")
            self._ini_status.setText("⚠  Dossier Rocket League introuvable — configure manuellement")
        QTimer.singleShot(5000, lambda: self._ini_status.setText(""))

    def _save(self):
        self.app.config["platform"]               = self._platform.currentText()
        self.app.config["username"]               = self._username.text().strip()
        self.app.config["result_overlay_enabled"] = self._result_overlay_enabled.isChecked()
        self.app.config["result_overlay_theme"]   = self._result_theme.currentText()
        self.app.config.save()
        self._save_lbl.setText("✓  Sauvegardé !")
        QTimer.singleShot(2500, lambda: self._save_lbl.setText(""))
        self.app.fetch_mmr_async()


def _sim_gamepad_button(btn_num):
    """Simule un bouton Xbox via vgamepad (ViGEm requis)."""
    if not VGAMEPAD_AVAILABLE:
        return
    try:
        _BTN_MAP = {
            0: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
            1: vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
            2: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
            3: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
            4: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
            5: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
            6: vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
            7: vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
            8: vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
            9: vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        }
        xbox_btn = _BTN_MAP.get(btn_num, vg.XUSB_BUTTON.XUSB_GAMEPAD_A)
        gp = vg.VX360Gamepad()
        gp.press_button(button=xbox_btn)
        gp.update()
        time.sleep(0.1)
        gp.release_button(button=xbox_btn)
        gp.update()
    except Exception as e:
        print(f"[vgamepad] {e}")



# ─────────────────────────────────────────────────────────────────────────────
#  SERVICE 1 — MATCH  (état de jeu + parsing StatsAPI, zéro PyQt UI)
# ─────────────────────────────────────────────────────────────────────────────
class MatchService:
    """Gère l'état de session (W/L/streak), la connexion TCP StatsAPI
    et le parsing de tous les events du jeu.

    N'importe aucun widget PyQt — communique uniquement via AppSignals.
    """

    def __init__(self, config: "Config", signals: "AppSignals"):
        self.config  = config
        self.signals = signals

        # ── Session ──────────────────────────────────────────────────────
        self.wins          = 0
        self.losses        = 0
        self.streak        = 0
        self.streak_type   = None
        self.history       = []
        self.session_start = time.time()

        # ── Match en cours ───────────────────────────────────────────────
        self.my_team              = None
        self._last_known_my_team  = None   # persiste entre MatchEnded et MatchDestroyed
        self.team_scores          = {}
        self._last_scores         = {}
        self.current_players      = []
        self.detected_player_name = ""
        self._goal_counts         = {0: 0, 1: 0}
        self._prev_tgt_stats      = {}
        self._match_result_saved  = False  # True dès que MatchEnded a enregistré un résultat
        self._match_started       = False  # True dès que RoundStarted/CountdownBegin reçu
        # ── Connexion ────────────────────────────────────────────────────
        self._running  = True
        self._tcp_sock = None

    # ── Session ──────────────────────────────────────────────────────────
    def add(self, t, auto=False):
        if t == "win": self.wins += 1
        else:          self.losses += 1
        if self.streak_type == t: self.streak += 1
        else: self.streak = 1; self.streak_type = t
        self.history.insert(0, (t, time.strftime("%H:%M:%S"), auto))
        self.signals.match_result.emit(t)

    def remove(self, t):
        if t == "win"  and self.wins   > 0: self.wins   -= 1
        elif t == "loss" and self.losses > 0: self.losses -= 1
        else: return
        for i, h in enumerate(self.history):
            if h[0] == t: self.history.pop(i); break
        self._recalc_streak()
        self.signals.match_result.emit(t)

    def _recalc_streak(self):
        if not self.history:
            self.streak = 0; self.streak_type = None; return
        self.streak_type = self.history[0][0]; self.streak = 0
        for h in self.history:
            if h[0] == self.streak_type: self.streak += 1
            else: break

    def reset_session(self, mmr_service=None):
        self.wins = 0; self.losses = 0; self.history = []
        self.streak = 0; self.streak_type = None
        self.session_start = time.time()
        self.signals.match_result.emit("reset")
        if mmr_service:
            mmr_service.reset_deltas()
            self.signals.mmr_updated.emit()

    # ── StatsAPI TCP ──────────────────────────────────────────────────────
    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False
        if self._tcp_sock:
            try: self._tcp_sock.close()
            except: pass
            self._tcp_sock = None

    def restart(self, port=None):
        self.stop()
        time.sleep(0.25)
        if port is not None:
            self.config["statsapi_port"] = port
        self.start()

    def _loop(self):
        port = self.config["statsapi_port"]
        self.signals.status_changed.emit("", f"Connexion StatsAPI port {port}…")
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(("127.0.0.1", port))
            sock.settimeout(None)
            self._tcp_sock = sock
            self.signals.status_changed.emit("connected", f"StatsAPI connecté · port {port}")
            buf = b""
            while self._running:
                try:    chunk = sock.recv(4096)
                except OSError: break
                if not chunk: break
                buf += chunk
                while buf:
                    start = buf.find(b"{")
                    if start == -1: buf = b""; break
                    buf = buf[start:]
                    depth = end = 0; in_str = escaped = False
                    for i, bv in enumerate(buf):
                        c = chr(bv)
                        if escaped: escaped = False; continue
                        if c == "\\" and in_str: escaped = True; continue
                        if c == '"': in_str = not in_str; continue
                        if in_str: continue
                        if c == "{": depth += 1
                        elif c == "}":
                            depth -= 1
                            if depth == 0: end = i; break
                    if end == 0 and depth != 0: break
                    msg = buf[:end + 1]; buf = buf[end + 1:]
                    try:
                        self.signals.log_event.emit(msg.decode(errors="replace")[:80])
                    except RuntimeError:
                        return
                    try:
                        self._process_event(json.loads(msg))
                    except Exception as e:
                        try: self.signals.log_event.emit(f"ERR parse: {e}")
                        except RuntimeError: return

        except ConnectionRefusedError:
            if not self._running: return
            try: self.signals.status_changed.emit("error", "Connexion refusée — lance RL + SOS plugin")
            except RuntimeError: return
        except socket.timeout:
            if not self._running: return
            try: self.signals.status_changed.emit("error", "Timeout — SOS plugin actif ?")
            except RuntimeError: return
        except Exception as e:
            if not self._running: return
            try: self.signals.status_changed.emit("error", f"Erreur: {str(e)[:50]}")
            except RuntimeError: return
        finally:
            if sock:
                try: sock.close()
                except: pass
            self._tcp_sock = None; self.my_team = None
            try: self.signals.status_changed.emit("error", "Déconnecté")
            except RuntimeError: pass

        if self._running:
            time.sleep(3)
            self.signals.log_event.emit("Reconnexion StatsAPI…")
            self._loop()

    def _process_event(self, outer: dict):
        event = outer.get("Event", "")
        inner = outer.get("Data", {})
        if isinstance(inner, str):
            try: inner = json.loads(inner)
            except: return

        # ── UpdateState ───────────────────────────────────────────────────
        if event == "UpdateState":
            game    = inner.get("Game", {})
            players = inner.get("Players", [])

            new_names = [p.get("Name") for p in players]
            old_names = [p.get("Name") for p in self.current_players]
            if new_names != old_names:
                self.current_players = players
                self.signals.players_updated.emit(players)

            for team in game.get("Teams", []):
                tnum  = team["TeamNum"]
                score = team["Score"]
                prev  = self._last_scores.get(tnum, -1)
                if prev >= 0 and score > prev:
                    self._goal_counts[tnum] = self._goal_counts.get(tnum, 0) + 1
                    if self.my_team is not None:
                        snd = "goal_scored" if tnum == self.my_team else "goal_conceded"
                        self.signals.trigger_sound.emit(snd)
                    if self.config.get("auto_skip_replay"):
                        key   = self.config.get("skip_replay_key", "key:space")
                        delay = float(self.config.get("skip_replay_delay", 0))
                        self.signals.log_event.emit(
                            f"[Auto] But ! Skip dans {delay:.1f}s → {_key_display(key)}")
                        self.signals.press_key_sig.emit(key, delay)
                self._last_scores[tnum] = score
                self.team_scores[tnum]  = score

            if self.my_team is None:
                platform    = self.config.get("platform", "epic").lower()
                _PLAT_PREFIX = {
                    "epic":   "Epic|",
                    "steam":  "Steam|",
                    "ps4":    "PS4|",
                    "xbox":   "XboxOne|",
                    "switch": "Switch|",
                }
                plat_prefix = _PLAT_PREFIX.get(platform, "Epic|")
                known_name  = (self.config.get("username") or
                               self.detected_player_name or "").strip().lower()
                for p in players:
                    matched = False
                    pid = p.get("PrimaryId", "")
                    if pid.startswith(plat_prefix):
                        if known_name:
                            matched = p.get("Name", "").strip().lower() == known_name
                        else:
                            # Compter les joueurs de cette plateforme par équipe.
                            # Fonctionne en 1v1, 2v2 et 3v3 : si tu es le seul
                            # joueur Epic/Steam dans ton équipe, c'est toi.
                            team_plat_counts = {}
                            for x in players:
                                if x.get("PrimaryId", "").startswith(plat_prefix):
                                    t = x.get("TeamNum")
                                    team_plat_counts[t] = team_plat_counts.get(t, 0) + 1
                            p_team = p.get("TeamNum")
                            matched = (pid.startswith(plat_prefix) and
                                       team_plat_counts.get(p_team, 0) == 1)
                    if not matched and known_name:
                        matched = p.get("Name", "").strip().lower() == known_name
                    if matched:
                        self.my_team = p.get("TeamNum")
                        self._last_known_my_team = self.my_team
                        self.detected_player_name = p.get("Name", "")
                        self.signals.player_detected.emit(self.detected_player_name, self.my_team)
                        break

                # bHasTarget fallback — UNIQUEMENT si la cible a des champs spectateur
                # (Boost, Speed…) dans la liste joueurs, confirmant qu'elle est dans
                # NOTRE équipe (ces champs ne sont visibles que pour sa propre équipe).
                # Sans cette vérification, la transition fin-de-replay peut pointer
                # la caméra sur le buteur adverse → équipe erronée détectée.
                if self.my_team is None and game.get("bHasTarget") and not game.get("bReplay"):
                    tgt      = game.get("Target", {})
                    tgt_name = tgt.get("Name", "")
                    tgt_team = tgt.get("TeamNum")
                    if tgt_name and tgt_team is not None:
                        for p in players:
                            if p.get("Name") == tgt_name and "Boost" in p:
                                self.my_team = tgt_team
                                self._last_known_my_team = tgt_team
                                if not self.detected_player_name:
                                    self.detected_player_name = tgt_name
                                self.signals.player_detected.emit(tgt_name, tgt_team)
                                break

        # ── GoalScored ────────────────────────────────────────────────────
        elif event == "GoalScored":
            pass  # géré via UpdateState (plus fiable)

        elif event == "MatchCreated":
            # Nouvelle partie qui commence. Si l'ancienne partie n'a pas eu de
            # MatchEnded (abandon, crash…), calculer son résultat MAINTENANT,
            # pendant que my_team et team_scores sont encore valides pour elle.
            # On ne peut plus attendre MatchDestroyed car d'ici là l'état aura
            # été écrasé par la nouvelle partie.
            if not self._match_result_saved and self._match_started:
                my = self.my_team or self._last_known_my_team
                if my is not None and self.team_scores:
                    my_score  = self.team_scores.get(my, 0)
                    opp_score = self.team_scores.get(1 - my, 0)
                    if my_score != opp_score:
                        result = "win" if my_score > opp_score else "loss"
                        self.signals.log_event.emit(
                            f"MatchCreated (résultat parti précédente déduit) → {result.upper()}"
                            f" ({my_score}-{opp_score})")
                        self.signals.match_result.emit("__auto__" + result)
            # Réinitialisation complète pour la nouvelle partie
            self._match_result_saved = False
            self._match_started      = False
            self.my_team             = None
            self._last_known_my_team = None
            self.team_scores         = {}
            self._last_scores        = {}
            self._goal_counts        = {0: 0, 1: 0}
            self.current_players     = []

        elif event in ("MatchInitialized",):
            self._match_result_saved = False

        elif event in ("RoundStarted", "CountdownBegin"):
            self._match_result_saved = False
            self._match_started      = True   # le jeu a vraiment commencé

        # ── StatfeedEvent — demos, saves, epic saves ──────────────────────
        elif event == "StatfeedEvent":
            ev_name     = inner.get("EventName", "")
            main_target = inner.get("MainTarget", {})
            sec_target  = inner.get("SecondaryTarget", {})
            my_name     = self.detected_player_name

            if ev_name == "Demolish":
                if sec_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("demo_me")
                elif main_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("demo_opponent")
            elif ev_name in ("Save", "AerialSave", "AerialSaveReward"):
                if main_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("save")
            elif ev_name in ("EpicSave", "EpicAerialSave"):
                if main_target.get("Name") == my_name:
                    self.signals.trigger_sound.emit("epic_save")

        # ── CrossbarHit ───────────────────────────────────────────────────
        elif event == "CrossbarHit":
            self.signals.trigger_sound.emit("crossbar")

        # ── MatchEnded ────────────────────────────────────────────────────
        elif event == "MatchEnded":
            winner = inner.get("WinnerTeamNum")
            my     = self.my_team

            # Fallback 1 : équipe mémorisée pendant le match
            if my is None:
                my = self._last_known_my_team

            # Fallback 2 : cherche par pseudo dans la dernière liste connue
            if my is None and self.current_players:
                known = (self.config.get("username") or
                         self.detected_player_name or "").strip().lower()
                if known:
                    for p in self.current_players:
                        if p.get("Name", "").strip().lower() == known:
                            my = p.get("TeamNum"); break
                if my is None:
                    for p in self.current_players:
                        if "Boost" in p and "Speed" in p:
                            my = p.get("TeamNum"); break

            if winner is not None and my is not None:
                my_score  = self.team_scores.get(my, 0)
                opp_score = self.team_scores.get(1 - my, 0)
                if my_score > opp_score:      result = "win"
                elif opp_score > my_score:    result = "loss"
                else: result = "win" if winner == my else "loss"
                self.signals.log_event.emit(
                    f"MatchEnded → {result.upper()} ({my_score}-{opp_score})"
                    f"{' [ff/forfait]' if my_score + opp_score == 0 else ''}")
                self.signals.match_result.emit("__auto__" + result)
                self._match_result_saved = True
            else:
                self.signals.log_event.emit(
                    f"MatchEnded ignoré — my_team={my} winner={winner}")

            self.my_team        = None
            self.team_scores    = {}
            self._last_scores   = {}
            self._goal_counts   = {0: 0, 1: 0}
            self._match_started = False

        # ── MatchDestroyed ────────────────────────────────────────────────
        elif event == "MatchDestroyed":
            # Si MatchEnded n'a jamais été reçu (quitte pendant replay/podium),
            # on tente de déduire le résultat depuis les scores connus.
            # GARDE : _match_started doit être True pour qu'on ait vraiment joué
            # un round — évite les faux résultats quand MatchDestroyed d'une
            # ancienne partie arrive après que la nouvelle partie a déjà démarré.
            if not self._match_result_saved and self._match_started:
                my = self.my_team or self._last_known_my_team
                if my is not None and self.team_scores:
                    my_score  = self.team_scores.get(my, 0)
                    opp_score = self.team_scores.get(1 - my, 0)
                    if my_score != opp_score:
                        result = "win" if my_score > opp_score else "loss"
                        self.signals.log_event.emit(
                            f"MatchDestroyed (sans MatchEnded) → {result.upper()}"
                            f" ({my_score}-{opp_score})")
                        self.signals.match_result.emit("__auto__" + result)
                    else:
                        self.signals.log_event.emit(
                            "MatchDestroyed sans MatchEnded — score nul, résultat ignoré")
                else:
                    self.signals.log_event.emit(
                        "MatchDestroyed sans MatchEnded — équipe inconnue, résultat ignoré")

            self.my_team              = None
            self._last_known_my_team  = None
            self.team_scores          = {}
            self._last_scores         = {}
            self._goal_counts         = {0: 0, 1: 0}
            self._prev_tgt_stats      = {}
            self._match_result_saved  = False
            self._match_started       = False
            self.current_players      = []
            self.signals.players_updated.emit([])

        elif event in ("PodiumStart", "GoalReplayStart"):
            pass


# ─────────────────────────────────────────────────────────────────────────────
#  SERVICE 2 — MMR  (Selenium scraping + retry + cache disque, zéro PyQt UI)
# ─────────────────────────────────────────────────────────────────────────────
class MMRService:
    """Scrape le MMR via Selenium avec 3 tentatives et cache JSON local.

    N'importe aucun widget PyQt — communique uniquement via AppSignals.
    """

    _CACHE_PATH  = os.path.join(BASE_DIR, "mmr_cache.json")
    _MAX_RETRIES = 3
    _JS = r"""
return (function() {
    var out = { duel: null, doubles: null, standard: null, debug: [] };
    var blockSkills = document.querySelector('div.block-skills');
    if (!blockSkills) { out.debug.push('ERR: div.block-skills not found'); return out; }
    var table = blockSkills.querySelector('table');
    if (!table) { out.debug.push('ERR: table not found'); return out; }
    var colMap = {};
    Array.from(table.querySelectorAll('th')).forEach(function(th, i) {
        var h = th.textContent.toLowerCase();
        if      (h.indexOf('1v1')!=-1||h.indexOf('duel')!=-1)     colMap[i]='duel';
        else if (h.indexOf('2v2')!=-1||h.indexOf('doubles')!=-1)  colMap[i]='doubles';
        else if (h.indexOf('3v3')!=-1||h.indexOf('standard')!=-1) colMap[i]='standard';
    });
    Array.from(table.querySelectorAll('tr')).forEach(function(row) {
        if (!row.querySelector('mmr')) return;
        Array.from(row.querySelectorAll('td')).forEach(function(td, i) {
            var key = colMap[i];
            if (!key || out[key]!==null) return;
            var m = td.innerHTML.match(/<\/mmr[^>]*>\s*(\d+)\s*<mmr/i);
            if (m) {
                var val = parseInt(m[1], 10);
                if (val>=100 && val<=3000) { out[key]=val; }
                else { out.debug.push(key+' hors plage: '+val); }
            } else { out.debug.push(key+' no match'); }
        });
    });
    return out;
})();
"""

    def __init__(self, config: "Config", signals: "AppSignals"):
        self.config            = config
        self.signals           = signals
        self.selected_playlist = "3v3"
        self.all_mmr = {k: {"mmr": None, "mmr_start": None, "mmr_change": 0, "rank": ""}
                        for k in PLAYLIST_NAMES}
        self._load_cache()

    # ── Cache ─────────────────────────────────────────────────────────────
    def _load_cache(self):
        try:
            with open(self._CACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for k in PLAYLIST_NAMES:
                if k in data:
                    cached_mmr = data[k].get("mmr")
                    self.all_mmr[k]["mmr"]       = cached_mmr
                    self.all_mmr[k]["mmr_start"] = cached_mmr  # delta repart de zéro
                    self.all_mmr[k]["rank"]      = data[k].get("rank", "")
        except Exception:
            pass  # premier lancement ou cache corrompu, pas grave

    def _save_cache(self):
        try:
            data = {k: {"mmr": v["mmr"], "rank": v.get("rank", "")}
                    for k, v in self.all_mmr.items() if v["mmr"] is not None}
            with open(self._CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def reset_deltas(self):
        """Appelé en début de session : repart le delta depuis le MMR actuel."""
        for d in self.all_mmr.values():
            d["mmr_start"] = d["mmr"]
            d["mmr_change"] = 0

    # ── Fetch avec retry ──────────────────────────────────────────────────
    def fetch_async(self, player_name=""):
        threading.Thread(target=self._fetch, args=(player_name,), daemon=True).start()

    def _fetch(self, player_name=""):
        username = self.config["username"] or player_name
        if not username:
            return

        if not SELENIUM_AVAILABLE:
            self.signals.mmr_error.emit("Selenium non disponible")
            return

        platform = self.config["platform"]
        _RLSTATS_SLUG = {
            "epic":   "Epic",
            "steam":  "Steam",
            "ps4":    "PS4",
            "xbox":   "XboxOne",
            "switch": "Switch",
        }
        plat_cap = _RLSTATS_SLUG.get(platform, "Epic")
        url      = f"https://rlstats.net/profile/{plat_cap}/{urllib.parse.quote(username)}"

        for attempt in range(1, self._MAX_RETRIES + 1):
            driver = None
            try:
                options = Options()
                options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--window-size=1280,900")
                options.add_argument(
                    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

                if WEBDRIVER_MANAGER_AVAILABLE:
                    driver = webdriver.Chrome(
                        service=ChromeService(ChromeDriverManager().install()),
                        options=options)
                else:
                    driver = webdriver.Chrome(options=options)

                self.signals.log_event.emit(
                    f"[MMR] Tentative {attempt}/{self._MAX_RETRIES} — {username} ({plat_cap})…")
                driver.get(url)
                time.sleep(6)

                result = driver.execute_script(self._JS)
                if result is None:
                    raise RuntimeError("JS returned None — page bloquée ou structure inattendue")

                for dbg in (result.get("debug") or []):
                    self.signals.log_event.emit(f"[MMR-dbg] {dbg}")

                mmr_map = {}
                if result.get("duel"):     mmr_map["1v1"] = int(result["duel"])
                if result.get("doubles"):  mmr_map["2v2"] = int(result["doubles"])
                if result.get("standard"): mmr_map["3v3"] = int(result["standard"])

                if not mmr_map:
                    raise RuntimeError(f"MMR introuvable pour {username}")

                for key, mmr in mmr_map.items():
                    d = self.all_mmr[key]
                    d["mmr_start"]  = mmr if d["mmr_start"] is None else d["mmr_start"]
                    d["mmr_change"] = mmr - d["mmr_start"]
                    d["mmr"]        = mmr
                    self.signals.log_event.emit(f"[{key}] MMR: {mmr}")

                self._save_cache()
                self.signals.mmr_updated.emit()
                self.signals.log_event.emit("✓ MMR mis à jour (rlstats.net)")
                return  # succès — on sort de la boucle retry

            except Exception as e:
                self.signals.log_event.emit(
                    f"[MMR] Erreur tentative {attempt}: {str(e)[:60]}")
                if attempt < self._MAX_RETRIES:
                    time.sleep(4 * attempt)  # backoff linéaire
                else:
                    self.signals.mmr_error.emit(
                        f"Échec après {self._MAX_RETRIES} tentatives: {str(e)[:55]}")
            finally:
                if driver:
                    try: driver.quit()
                    except: pass


# ─────────────────────────────────────────────────────────────────────────────
#  APPLICATION PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────
class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BakkesMod v2")
        self.setFixedWidth(440)
        self.setMinimumHeight(660)

        self.config  = Config()
        self.signals = AppSignals()

        # ── Services (logique métier, sans PyQt UI) ───────────────────────
        self.match = MatchService(self.config, self.signals)
        self.mmr   = MMRService(self.config, self.signals)

        # ── UI ────────────────────────────────────────────────────────────
        self.overlay_win         = OverlayWindow()
        self.players_overlay_win = PlayersOverlayWindow()
        self.result_overlay      = ResultOverlay()

        # ── Fond SVG — widget racine qui contient tout ────────────────────
        bg_theme = self.config.get("main_bg_theme", "dark_minimal")
        self._bg_widget = SvgBackground(bg_theme)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        self.tracker_tab  = TrackerTab(self)
        self.players_tab  = PlayersTab(self)
        self.overlay_tab  = OverlayTab(self)
        self.auto_tab     = AutomationTab(self)
        self.sound_tab    = SoundTab(self)
        self.settings_tab = SettingsTab(self)

        scroll = QScrollArea()
        scroll.setWidget(self.tracker_tab)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;border:none;")

        tabs.addTab(scroll,              "📊 TRACKER")
        tabs.addTab(self.players_tab,    "👥 JOUEURS")
        tabs.addTab(self.overlay_tab,    "🖥 OVERLAY")
        tabs.addTab(self.auto_tab,       "⚡ AUTO")
        tabs.addTab(self.sound_tab,      "🔊 SONS")
        tabs.addTab(self.settings_tab,   "⚙ PARAMS")
        self._bg_widget.add_widget(tabs)
        self.setCentralWidget(self._bg_widget)

        # ── Connexions de signaux ─────────────────────────────────────────
        self.signals.player_detected.connect(
            lambda name, _: setattr(self.match, "detected_player_name", name))
        self.signals.match_result.connect(self._handle_auto_match)
        self.signals.players_updated.connect(self.players_overlay_win.update_players)
        self.signals.trigger_sound.connect(self._trigger_sound)
        self.signals.press_key_sig.connect(self._handle_press_key)

        self._overlay_timer = QTimer(self)
        self._overlay_timer.timeout.connect(self._push_overlay)
        self._overlay_timer.start(REFRESH_MS)

        self._running = True
        self._start_http_server()
        self.match.start()
        self._start_hotkey_listener()
        self.fetch_mmr_async()

    # ── Property shims — rétrocompatibilité avec les onglets UI ──────────
    @property
    def wins(self):               return self.match.wins
    @property
    def losses(self):             return self.match.losses
    @property
    def streak(self):             return self.match.streak
    @property
    def streak_type(self):        return self.match.streak_type
    @property
    def history(self):            return self.match.history
    @property
    def session_start(self):      return self.match.session_start
    @property
    def detected_player_name(self): return self.match.detected_player_name
    @property
    def all_mmr(self):            return self.mmr.all_mmr
    @property
    def selected_playlist(self):  return self.mmr.selected_playlist

    # ── Délégation vers MatchService ──────────────────────────────────────
    def add(self, t, auto=False):
        self.match.add(t, auto)
        QTimer.singleShot(10000, self.fetch_mmr_async)
        if self.config.get("auto_queue"):
            delay_q = int(float(self.config.get("queue_delay", 2.0)) * 1000)
            QTimer.singleShot(delay_q, self._do_queue_action)
        if self.config.get("auto_freeplay"):
            delay_f = int(float(self.config.get("freeplay_delay", 3.0)) * 1000)
            QTimer.singleShot(delay_f, self._do_freeplay_action)

    def remove(self, t):      self.match.remove(t)
    def reset_session(self):  self.match.reset_session(self.mmr)

    def select_playlist(self, key):
        self.mmr.selected_playlist = key
        self.signals.mmr_updated.emit()

    def highlight_playlist_btns(self, btns):
        for k, b in btns.items():
            active = k == self.mmr.selected_playlist
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};"
                f"color:{C_TEXT if active else C_MUTE};border:none;"
                f"border-radius:4px;padding:5px 12px;font-size:9px;font-weight:700;}}"
                + ("" if active else f"QPushButton:hover{{color:{C_TEXT};}}"))

    def fetch_mmr_async(self):
        self.mmr.fetch_async(self.match.detected_player_name)

    def reconnect_statsapi(self):
        port_str = self.tracker_tab.get_port()
        try:   port = int(port_str)
        except ValueError: port = self.config["statsapi_port"]
        self.match.restart(port)

    # ── Handlers de signaux ───────────────────────────────────────────────
    def _handle_auto_match(self, val):
        if val.startswith("__auto__"):
            result = val[8:]
            self.add(result, auto=True)
            if self.config.get("result_overlay_enabled", True):
                theme = self.config.get("result_overlay_theme", "auto")
                self.result_overlay.show_result(result, theme)
            # Push SSE vers OBS overlay
            stats = self._build_stats_dict()
            stats["result"] = result
            self._push_sse("result", stats)

    def _trigger_sound(self, event_key: str):
        """Reçu depuis MatchService via signal — joue le son si activé."""
        if not self.config.get(f"sound_{event_key}", True):
            return
        f = self.config.get(f"snd_file_{event_key}", "")
        if f:
            self._play_sound(f)

    def _handle_press_key(self, key_str: str, delay: float):
        """Reçu depuis MatchService via signal — appuie sur la touche."""
        def _do():
            if delay > 0: time.sleep(delay)
            self._press_key(key_str)
        threading.Thread(target=_do, daemon=True).start()

    def _play_sound(self, file_str):
        if not PYGAME_AVAILABLE or not file_str:
            return
        def _play(f=file_str):
            try:
                path = f if os.path.isabs(f) else os.path.join(BASE_DIR, f)
                if not os.path.exists(path):
                    self.signals.log_event.emit(f"[Son] Fichier introuvable: {f}")
                    return
                pygame.mixer.init()
                snd = pygame.mixer.Sound(path)
                snd.play()
                ms = int(snd.get_length() * 1000) + 100
                pygame.time.wait(min(ms, 10000))
            except Exception as e:
                self.signals.log_event.emit(f"[Son] Erreur: {e}")
        threading.Thread(target=_play, daemon=True).start()

    def _press_key(self, key_str):
        if not key_str:
            return
        try:
            if key_str.startswith("key:"):
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.press(key_str[4:])
            elif key_str.startswith("joy_btn_"):
                btn_num = int(key_str.split("_")[2])
                if VGAMEPAD_AVAILABLE:
                    _sim_gamepad_button(btn_num)
                    self.signals.log_event.emit(f"[Auto] Manette bouton {btn_num}")
                else:
                    self.signals.log_event.emit(
                        "[Auto] vgamepad requis — pip install vgamepad")
            else:
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.press(key_str)
        except Exception as e:
            self.signals.log_event.emit(f"[Auto] Erreur touche: {e}")

    def _do_queue_action(self):
        key = self.config.get("queue_key", "key:return")
        self.signals.log_event.emit(f"[Auto] Rejouer → {_key_display(key)}")
        threading.Thread(target=lambda: self._press_key(key), daemon=True).start()

    def _do_freeplay_action(self):
        key = self.config.get("freeplay_key", "key:f")
        self.signals.log_event.emit(f"[Auto] Freeplay → {_key_display(key)}")
        threading.Thread(target=lambda: self._press_key(key), daemon=True).start()

    # ── Overlay stats ─────────────────────────────────────────────────────
    def _build_stats_dict(self):
        total = self.wins + self.losses
        wr    = round(self.wins / total * 100) if total > 0 else 0
        d     = self.mmr.all_mmr.get(self.mmr.selected_playlist, {})
        return {
            "wins":        self.wins,
            "losses":      self.losses,
            "total":       total,
            "winrate":     wr,
            "streak_val":  self.streak,
            "streak_type": self.streak_type or "",
            "mmr":         d.get("mmr"),
            "mmr_change":  d.get("mmr_change", 0),
            "rank":        d.get("rank", ""),
        }

    def _push_overlay(self):
        stats = self._build_stats_dict()
        self.overlay_win.update_stats(stats)
        self.overlay_tab.refresh_preview(stats)
        self._push_sse("stats", stats)

    # ── Players overlay hotkey ────────────────────────────────────────────
    def _start_hotkey_listener(self):
        threading.Thread(target=self._hotkey_loop, daemon=True).start()

    def _hotkey_loop(self):
        if sys.platform != "win32":
            return
        try:
            import ctypes
        except ImportError:
            return
        prev_pressed = False
        while self.match._running:
            time.sleep(0.04)
            key_str = self.config.get("players_overlay_key", "key:f7")
            vk = _key_to_vk(key_str)
            if vk is None:
                continue
            state   = ctypes.windll.user32.GetAsyncKeyState(vk)
            pressed = bool(state & 0x8000)
            if pressed and not prev_pressed:
                QTimer.singleShot(0, self._toggle_players_overlay)
            prev_pressed = pressed

    def _toggle_players_overlay(self):
        if self.players_overlay_win.isVisible():
            self.players_overlay_win.hide()
        else:
            self.players_overlay_win.show()

    # ── HTTP server ───────────────────────────────────────────────────────
    def closeEvent(self, event):
        """Arrête le thread websocket avant que Qt détruise les objets C++."""
        self.match.stop()
        self.overlay_win.close()
        self.players_overlay_win.close()
        self.result_overlay.hide()
        super().closeEvent(event)

    # ── Répertoire des overlays externes ─────────────────────────────────────
    OVERLAYS_DIR = os.path.join(BASE_DIR, "overlays")

    @staticmethod
    def _load_overlay(name: str) -> bytes:
        """Charge un fichier HTML depuis overlays/<name>.
        Cherche d'abord overlays/<name>, puis overlays/<name>.html.
        Retourne les bytes ou b'' si introuvable."""
        base = MainApp.OVERLAYS_DIR
        for candidate in [os.path.join(base, name),
                          os.path.join(base, name + ".html")]:
            try:
                with open(candidate, "rb") as f:
                    return f.read()
            except FileNotFoundError:
                pass
        return b""

    def _start_http_server(self):
        app = self
        app._sse_clients = []   # liste des wfile en attente d'events SSE

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                # Sert n'importe quel *.html depuis le dossier overlays/
                # Ex: /overlay.html       -> overlays/overlay.html
                #     /my_overlay.html    -> overlays/my_overlay.html
                path = self.path.lstrip("/")
                if path.endswith(".html") and "/" not in path:
                    data = app._load_overlay(path)
                    if data:
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Cache-Control", "no-store")
                        self.end_headers(); self.wfile.write(data)
                    else:
                        msg = f"Overlay '{path}' introuvable dans overlays/".encode()
                        self.send_response(404)
                        self.send_header("Content-Type", "text/plain")
                        self.end_headers(); self.wfile.write(msg)

                elif self.path == "/stats":
                    payload = json.dumps(app._build_stats_dict()).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers(); self.wfile.write(payload)

                elif self.path == "/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()
                    # Envoie les stats actuelles immédiatement
                    try:
                        data = json.dumps(app._build_stats_dict())
                        self.wfile.write(f"event: stats\ndata: {data}\n\n".encode())
                        self.wfile.flush()
                    except Exception:
                        return
                    app._sse_clients.append(self.wfile)
                    # Reste en attente jusqu'à déconnexion
                    try:
                        while True:
                            import time; time.sleep(15)
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                    except Exception:
                        pass
                    finally:
                        try: app._sse_clients.remove(self.wfile)
                        except ValueError: pass

                else:
                    self.send_response(404); self.end_headers()

            def log_message(self, *a): pass

        def run():
            try:
                HTTPServer(("0.0.0.0", OVERLAY_PORT), Handler).serve_forever()
            except Exception as e:
                print(f"[HTTP] {e}")
        threading.Thread(target=run, daemon=True).start()

    def _push_sse(self, event_type: str, data: dict):
        """Envoie un event SSE à tous les clients OBS connectés."""
        if not hasattr(self, "_sse_clients"):
            return
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()
        dead = []
        for wfile in list(self._sse_clients):
            try:
                wfile.write(msg); wfile.flush()
            except Exception:
                dead.append(wfile)
        for w in dead:
            try: self._sse_clients.remove(w)
            except ValueError: pass

#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    font = QFont(); font.setFamily("Segoe UI"); font.setPointSize(10)
    app.setFont(font)

    # ── Chargement du logo ───────────────────────────────────────────────
    # Priorité 1 : fichier logo.* dans le même dossier que l exe
    # Priorité 2 : icône embarquée dans le code (toujours présente)
    from PyQt6.QtGui import QPixmap
    icon = None

    for name in ["logo.png", "logo.ico", "logo.jpg", "logo.jpeg", "logo.bmp", "logo.webp"]:
        candidate = os.path.join(BASE_DIR, name)
        if os.path.exists(candidate):
            px = QPixmap(candidate)
            if not px.isNull():
                icon = QIcon(px)
                break

    if icon is None:
        # Fallback : icône embarquée en base64
        import base64
        px = QPixmap()
        px.loadFromData(base64.b64decode(_DEFAULT_ICON_B64))
        if not px.isNull():
            icon = QIcon(px)

    if icon:
        app.setWindowIcon(icon)

    win = MainApp()
    if icon:
        win.setWindowIcon(icon)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
