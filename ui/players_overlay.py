"""ui/players_overlay.py — Mini overlay joueurs (hotkey F7 par défaut)."""
import sys, time, urllib.parse
from PyQt6.QtGui import QCursor, QColor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
)
from PyQt6.QtGui import QDesktopServices
from style import C_BG3, C_BLUE, C_ORG, C_TEXT, C_MUTE, card, lbl
from overlay_widgets import _GlassCard
from utils import enforce_topmost
from config import platform_from_id, id_from_primary_id, PLATFORM_SLUGS


class PlayersOverlayWindow(QMainWindow):
    def __init__(self, sound=None, db=None):
        super().__init__()
        self._sound = sound
        self._db = db
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.BypassWindowManagerHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(210)
        self._players  = []
        self._drag_pos = None
        cont = QWidget()
        cont.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(cont)
        outer = QVBoxLayout(cont); outer.setContentsMargins(0,0,0,0)
        self._card = _GlassCard()
        self._card_lay = QVBoxLayout(self._card)
        self._card_lay.setContentsMargins(10,10,10,10); self._card_lay.setSpacing(4)
        hdr = QHBoxLayout()
        title = QLabel("JOUEURS")
        title.setStyleSheet(f"color:{C_MUTE};font-size:8px;font-weight:700;letter-spacing:1.5px;background:transparent;")
        hint_lbl = QLabel("clic = tracker")
        hint_lbl.setStyleSheet(f"color:{C_BG3};font-size:7px;background:transparent;")
        close_btn = QPushButton("✕"); close_btn.setFixedSize(16,16)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{C_MUTE};border:none;font-size:9px;}}QPushButton:hover{{color:{C_TEXT};}}")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(title); hdr.addSpacing(6); hdr.addWidget(hint_lbl); hdr.addStretch(); hdr.addWidget(close_btn)
        self._card_lay.addLayout(hdr)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C_BG3};border:none;"); self._card_lay.addWidget(sep)
        self._players_widget = QWidget(); self._players_widget.setStyleSheet("background:transparent;")
        self._plist = QVBoxLayout(self._players_widget); self._plist.setSpacing(1); self._plist.setContentsMargins(0,4,0,4)
        self._card_lay.addWidget(self._players_widget); outer.addWidget(self._card)
        self._card.mousePressEvent  = self._mouse_press
        self._card.mouseMoveEvent   = self._mouse_move
        self._card.mouseReleaseEvent = lambda e: None
        self._topmost_timer = QTimer(self)
        self._topmost_timer.timeout.connect(self._enforce_topmost)
        self._topmost_timer.start(2000)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(lambda: self.update_players(self._players))
        self._refresh_empty()

    def _mouse_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _mouse_move(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def showEvent(self, e):
        super().showEvent(e); self._enforce_topmost()
        self._refresh_timer.start(1500)
        
    def hideEvent(self, e):
        super().hideEvent(e)
        self._refresh_timer.stop()

    def _enforce_topmost(self):
        enforce_topmost(self)

    def _clear_plist(self):
        while self._plist.count():
            item = self._plist.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _refresh_empty(self):
        self._clear_plist()
        e = QLabel("Aucun match en cours")
        e.setStyleSheet(f"color:{C_MUTE};font-size:9px;background:transparent;")
        e.setAlignment(Qt.AlignmentFlag.AlignCenter); self._plist.addWidget(e); self.adjustSize()

    _TRACKER_COOLDOWN_S = 3
    _tracker_last_open: dict = {}
    _URL_SLUG = PLATFORM_SLUGS

    def update_players(self, players):
        self._players = players; self._clear_plist()
        if not players:
            e = QLabel("Aucun match en cours")
            e.setStyleSheet(f"color:{C_MUTE};font-size:9px;background:transparent;")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter); self._plist.addWidget(e); self.adjustSize(); return
        blues   = [p for p in players if p.get("TeamNum") == 0]
        oranges = [p for p in players if p.get("TeamNum") == 1]
        for team_name, team_color, team_players in [("🔵  BLUE", C_BLUE, blues), ("🟠  ORANGE", C_ORG, oranges)]:
            if not team_players: continue
            tl = QLabel(team_name)
            tl.setStyleSheet(f"color:{team_color};font-size:8px;font-weight:700;letter-spacing:1px;background:transparent;")
            self._plist.addWidget(tl)
            for p in team_players:
                name       = p.get("Name", "?")
                primary_id = p.get("PrimaryId", "")
                platform   = self._platform_from_id(primary_id)
                raw_id     = self._id_from_primary_id(primary_id) or name
                user_id    = raw_id if platform == "steam" else name
                
                is_smurf = False
                if self._sound:
                    entry = self._sound.ingame_stats_cache.get(primary_id)
                    if entry and entry.get("status") == "ok":
                        is_smurf = entry.get("is_smurf", False)
                smurf_icon = " ⚠️ Smurf?" if is_smurf else ""
                
                record_str = ""
                if self._db:
                    rec = self._db.get_encounter_record(name)
                    vs_total = rec["vs_wins"] + rec["vs_losses"]
                    with_total = rec["with_wins"] + rec["with_losses"]
                    if vs_total > 0 or with_total > 0:
                        parts = []
                        if vs_total > 0:
                            parts.append(f"vs:{rec['vs_wins']}V-{rec['vs_losses']}D")
                        if with_total > 0:
                            parts.append(f"with:{rec['with_wins']}V-{rec['with_losses']}D")
                        record_str = f" [{', '.join(parts)}]"
                
                pb = QPushButton(name + smurf_icon + record_str)
                pb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                pb.setStyleSheet(f"QPushButton{{background:transparent;color:{team_color};border:none;text-align:left;font-size:12px;font-weight:700;padding:2px 6px;letter-spacing:0.3px;}}QPushButton:hover{{color:{C_TEXT};background:{C_BG3};border-radius:3px;}}")
                pb.clicked.connect(lambda _, uid=user_id, pl=platform: self._open_profile(uid, pl))
                self._plist.addWidget(pb)
        self.adjustSize()

    def _platform_from_id(self, primary_id):
        return platform_from_id(primary_id)

    def _id_from_primary_id(self, primary_id):
        return id_from_primary_id(primary_id)

    def _open_profile(self, user_id, platform):
        now = time.time(); last = self._tracker_last_open.get(user_id, 0)
        if now - last < self._TRACKER_COOLDOWN_S: return
        self._tracker_last_open[user_id] = now
        slug = self._URL_SLUG.get(platform, platform)
        url = (f"https://rocketleague.tracker.network/rocket-league/profile/{slug}/{urllib.parse.quote(user_id)}/overview")
        QDesktopServices.openUrl(QUrl(url))