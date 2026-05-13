"""ui/main_window.py — MainApp (QMainWindow)."""
import os, sys, time, json, threading, base64
from http.server import HTTPServer, BaseHTTPRequestHandler

try: import pyautogui; PYAUTOGUI_AVAILABLE = True
except ImportError: PYAUTOGUI_AVAILABLE = False

from PyQt6.QtCore    import Qt, QTimer, QUrl
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QTabWidget, QScrollArea, QFrame,
)
from PyQt6.QtGui import QPixmap, QIcon, QColor, QFont

from config import Config, BASE_DIR, OVERLAY_PORT, REFRESH_MS, DEFAULT_ICON_B64
from style import APP_STYLE, C_BG, C_TEXT, C_MUTE
from signals import AppSignals
from services.match import MatchService
from services.mmr import MMRService
from services.sound import SoundService
from utils import (
    _key_display, _key_to_vk, SvgBackground, ResultOverlay, _github_auto_update,
)
from ui.tabs import TrackerTab, PlayersTab, OverlayTab, AutomationTab, SoundTab, SettingsTab
from ui.ingame_overlay import InGameMMROverlay
from ui.players_overlay import PlayersOverlayWindow
from ui.controller_overlay import ControllerOverlay
from ui.streamer_bar import StreamerModeBar

from overlay_widgets import OverlayWindow, _CompactCard
from gamepad_state import get_gamepad_state


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BakkyTrack")
        self.setFixedWidth(468)
        self.setMinimumHeight(660)
        self.config  = Config()
        self.signals = AppSignals()
        self.match   = MatchService(self.config, self.signals)
        self.mmr     = MMRService(self.config, self.signals)
        self.sound   = SoundService(self.config, self.signals)
        self.overlay_win         = OverlayWindow()
        self.players_overlay_win = PlayersOverlayWindow()
        self.result_overlay      = ResultOverlay()
        self.ingame_mmr_overlay  = InGameMMROverlay()
        self.ingame_mmr_overlay.set_show_peak(self.config.get("tab_show_peak", True))
        self.controller_overlay  = ControllerOverlay(
            self.config.get("controller_overlay_mode", "with_bg"))
        if self.config.get("controller_overlay_enabled", False):
            self.controller_overlay.show()
        self.streamer_bar        = StreamerModeBar()
        self._overlay_hold_active = False
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
        scroll = QScrollArea(); scroll.setWidget(self.tracker_tab)
        scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent;border:none;")
        sound_scroll = QScrollArea(); sound_scroll.setWidget(self.sound_tab)
        sound_scroll.setWidgetResizable(True); sound_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sound_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sound_scroll.setStyleSheet("background:transparent;border:none;")
        settings_scroll = QScrollArea(); settings_scroll.setWidget(self.settings_tab)
        settings_scroll.setWidgetResizable(True); settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        settings_scroll.setStyleSheet("background:transparent;border:none;")
        tabs.addTab(scroll,              "📊  Stats")
        tabs.addTab(self.players_tab,    "👥  Match")
        tabs.addTab(self.overlay_tab,    "🖥  Overlay")
        tabs.addTab(self.auto_tab,       "⚡  Auto")
        tabs.addTab(sound_scroll,        "🔊  Sons")
        tabs.addTab(settings_scroll,     "⚙  Options")
        self._bg_widget.add_widget(tabs)
        self.setCentralWidget(self._bg_widget)
        self.signals.player_detected.connect(
            lambda name, _: setattr(self.match, "detected_player_name", name))
        self.signals.match_result.connect(self._handle_auto_match)
        self.signals.players_updated.connect(self.players_overlay_win.update_players)
        self.signals.players_updated.connect(self._on_players_for_ingame)
        self.signals.trigger_sound.connect(self._trigger_sound)
        self.signals.press_key_sig.connect(self._handle_press_key)
        self.signals.game_phase_changed.connect(self._on_game_phase_changed)
        self.signals.mmr_updated.connect(self._refresh_own_ingame_cache)
        self._overlay_timer = QTimer(self)
        self._overlay_timer.timeout.connect(self._push_overlay)
        self._overlay_timer.start(REFRESH_MS)
        self._ingame_timer = QTimer(self)
        self._ingame_timer.timeout.connect(self._push_ingame_overlay)
        self._ingame_timer.start(700)
        self._running = True
        self._last_sse_stats: dict = {}
        self._start_http_server()
        self.match.start()
        self._start_hotkey_listener()
        self.fetch_mmr_async(force=True)
        self.config["streamer_mode"] = False

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
        self.mmr.selected_playlist = key; self.signals.mmr_updated.emit()

    def highlight_playlist_btns(self, btns):
        from style import C_BLUE, C_BG3, C_TEXT, C_MUTE
        for k, b in btns.items():
            active = k == self.mmr.selected_playlist
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG3};"
                f"color:{C_TEXT if active else C_MUTE};border:none;border-radius:4px;"
                f"padding:5px 12px;font-size:9px;font-weight:700;}}"
                + ("" if active else f"QPushButton:hover{{color:{C_TEXT};}}"))

    def fetch_mmr_async(self, force=False):
        self.mmr.fetch_async(
            self.match.detected_player_name,
            self.match.detected_player_primary_id, force=force)

    def reconnect_statsapi(self):
        port_str = self.tracker_tab.get_port()
        try: port = int(port_str)
        except ValueError: port = self.config["statsapi_port"]
        self.match.restart(port)

    def _handle_auto_match(self, val):
        if val.startswith("__auto__"):
            result = val[8:]; self.add(result, auto=True)
            if self.config.get("result_overlay_enabled", True):
                theme = self.config.get("result_overlay_theme", "auto")
                self.result_overlay.show_result(result, theme)
            stats = self._build_stats_dict(); stats["result"] = result
            self._push_sse("result", stats)

    def _trigger_sound(self, event_key: str):
        self.sound.trigger_sound(event_key)

    def _handle_press_key(self, key_str: str, delay: float):
        def _do():
            if delay > 0: time.sleep(delay)
            self._press_key(key_str)
        threading.Thread(target=_do, daemon=True).start()

    def _play_sound(self, file_str):
        self.sound.play_sound(file_str)

    def _press_key(self, key_str):
        if not key_str: return
        try:
            if key_str.startswith("key:"):
                if PYAUTOGUI_AVAILABLE: pyautogui.press(key_str[4:])
            elif key_str.startswith("mouse:"):
                btn_name = key_str[6:]
                if PYAUTOGUI_AVAILABLE:
                    btn_map = {"left": "left", "right": "right", "middle": "middle", "x1": "left", "x2": "right"}
                    pyautogui.click(button=btn_map.get(btn_name, "left"))
                    self.signals.log_event.emit(f"[Auto] Souris {btn_name}")
            else:
                if PYAUTOGUI_AVAILABLE: pyautogui.press(key_str)
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

    def _on_game_phase_changed(self, phase: str):
        if not self.config.get("streamer_mode", False): return
        if phase == "lobby": self._apply_streamer_bar(True)
        elif phase == "ingame": self._apply_streamer_bar(False)

    def _apply_streamer_bar(self, show: bool):
        if show:
            self.streamer_bar.show(); self.sound.mute_system_audio()
        else:
            self.streamer_bar.hide(); self.sound.restore_system_audio()

    def _apply_streamer_mode(self, enabled: bool):
        if enabled:
            self._apply_streamer_bar(True)
            self.signals.log_event.emit("[Streamer] Mode activé — barre noire + mute son")
        else:
            self._apply_streamer_bar(False)
            self.signals.log_event.emit("[Streamer] Mode désactivé — son restauré")

    def _build_stats_dict(self):
        total = self.wins + self.losses
        wr    = round(self.wins / total * 100) if total > 0 else 0
        d     = self.mmr.all_mmr.get(self.mmr.selected_playlist, {})
        return {
            "wins": self.wins, "losses": self.losses, "total": total, "winrate": wr,
            "streak_val": self.streak, "streak_type": self.streak_type or "",
            "mmr": d.get("mmr"), "mmr_change": d.get("mmr_change", 0),
            "rank": d.get("rank", ""), "tier_id": d.get("tier_id", 0),
            "div_id": d.get("div_id", 0),
        }

    def _push_overlay(self):
        stats = self._build_stats_dict()
        self.overlay_win.update_stats(stats)
        self.overlay_tab.refresh_preview(stats)
        if stats != self._last_sse_stats:
            self._last_sse_stats = stats; self._push_sse("stats", stats)

    def _start_hotkey_listener(self):
        threading.Thread(target=self._hotkey_loop, daemon=True).start()
        threading.Thread(target=self._overlay_hold_loop, daemon=True).start()

    def _hotkey_loop(self):
        if sys.platform != "win32": return
        try: import ctypes
        except ImportError: return
        prev_pressed  = False; cached_key = None; cached_vk = None; _cfg_refresh = 0
        while self.match._running:
            time.sleep(0.04); _cfg_refresh += 1
            if _cfg_refresh >= 50:
                _cfg_refresh = 0
                new_key = self.config.get("players_overlay_key", "key:f7")
                if new_key != cached_key: cached_key = new_key; cached_vk = _key_to_vk(new_key)
            if cached_vk is None: continue
            state = ctypes.windll.user32.GetAsyncKeyState(cached_vk)
            pressed = bool(state & 0x8000)
            if pressed and not prev_pressed: QTimer.singleShot(0, self._toggle_players_overlay)
            prev_pressed = pressed

    def _toggle_players_overlay(self):
        if self.players_overlay_win.isVisible(): self.players_overlay_win.hide()
        else: self.players_overlay_win.show()

    _MMRSVC_TO_PL_ID = {"1v1": 10, "2v2": 11, "3v3": 13}

    def _mmrsvc_to_ingame_entry(self) -> dict:
        playlists = {}
        for key, pl_id in self._MMRSVC_TO_PL_ID.items():
            d = self.mmr.all_mmr.get(key, {})
            mmr_val = d.get("mmr")
            if mmr_val is not None:
                entry = {"mmr": mmr_val, "tier_name": d.get("rank", "Unranked"), "tier_id": d.get("tier_id", 0)}
                peak = d.get("peak_mmr")
                if peak: entry["peak_mmr"] = peak
                playlists[pl_id] = entry
        return {"status": "ok", "playlists": playlists, "timestamp": time.time()}

    def _refresh_own_ingame_cache(self):
        my_pid = self.match.detected_player_primary_id
        if my_pid:
            self.sound.refresh_own_ingame_cache(my_pid, self._mmrsvc_to_ingame_entry())

    def _on_players_for_ingame(self, players: list):
        my_pid = self.match.detected_player_primary_id
        self.sound.fetch_players_for_ingame(players, my_pid, self._mmrsvc_to_ingame_entry)

    def _ingame_stats_cache(self):
        return self.sound.ingame_stats_cache
    _ingame_stats_cache = property(_ingame_stats_cache)

    def _push_ingame_overlay(self):
        if not self.ingame_mmr_overlay.isVisible(): return
        self._do_overlay_refresh()

    def _is_overlay_hotkey_pressed(self) -> bool:
        if sys.platform != "win32": return False
        import ctypes
        htype = self.config.get("overlay_hotkey_type", "key")
        if htype == "controller":
            btn = self.config.get("overlay_hotkey_controller_btn", 0)
            if btn == 0: return False
            xi = get_gamepad_state()
            return bool(xi and (xi.Gamepad.wButtons & btn) == btn)
        else:
            key = self.config.get("overlay_hotkey_key", "key:tab")
            if not key: return False
            vk = _key_to_vk(key)
            if vk is None: return False
            return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)

    def _overlay_hold_loop(self):
        if sys.platform != "win32": return
        was_pressed = False; cfg_refresh = 0
        while self.match._running:
            time.sleep(0.04); cfg_refresh += 1
            if cfg_refresh >= 50: cfg_refresh = 0
            pressed = self._is_overlay_hotkey_pressed()
            if pressed and not was_pressed:
                QTimer.singleShot(0, self._on_overlay_hold_start)
            elif not pressed and was_pressed:
                QTimer.singleShot(0, self._on_overlay_hold_end)
            was_pressed = pressed

    def _on_overlay_hold_start(self):
        if not self.ingame_mmr_overlay.isVisible():
            self._overlay_hold_active = True
            self._do_overlay_refresh(); self.ingame_mmr_overlay.show()
            if not hasattr(self, "_overlay_hold_refresh_timer"):
                self._overlay_hold_refresh_timer = QTimer(self)
                self._overlay_hold_refresh_timer.timeout.connect(self._do_overlay_refresh)
            self._overlay_hold_refresh_timer.start(1000)

    def _do_overlay_refresh(self):
        self.ingame_mmr_overlay.set_data(
            self.match.current_players, self.sound.ingame_stats_cache,
            self.mmr.selected_playlist,
            rank_mode=self.config.get("tab_rank_mode", "2v2"),
            game_state=self.match.current_game_state)
        self.ingame_mmr_overlay._rebuild()

    def _on_overlay_hold_end(self):
        if getattr(self, "_overlay_hold_active", False):
            self._overlay_hold_active = False
            if hasattr(self, "_overlay_hold_refresh_timer"):
                self._overlay_hold_refresh_timer.stop()
            self.ingame_mmr_overlay.hide()

    def closeEvent(self, event):
        try: self.config.save()
        except Exception: pass
        try: self._overlay_timer.stop()
        except Exception: pass
        self.match.stop()
        for w in (self.overlay_win, self.players_overlay_win, self.result_overlay,
                  self.ingame_mmr_overlay, self.controller_overlay, self.streamer_bar):
            try: w.close()
            except Exception: pass
        try: self.sound.restore_system_audio()
        except Exception: pass
        try:
            import pygame as _pg
            if _pg.mixer.get_init(): _pg.mixer.quit(); _pg.quit()
        except Exception: pass
        super().closeEvent(event)

    OVERLAYS_DIR = os.path.join(BASE_DIR, "overlays")

    @staticmethod
    def _load_overlay(name: str) -> bytes:
        base = MainApp.OVERLAYS_DIR
        for candidate in [os.path.join(base, name), os.path.join(base, name + ".html")]:
            try:
                with open(candidate, "rb") as f: return f.read()
            except FileNotFoundError: pass
        return b""

    def _start_http_server(self):
        app = self
        app._sse_clients = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = self.path.lstrip("/")
                if path.endswith(".html") and "/" not in path:
                    data = app._load_overlay(path)
                    if data:
                        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(data)
                    else:
                        msg = f"Overlay '{path}' introuvable dans overlays/".encode()
                        self.send_response(404); self.send_header("Content-Type", "text/plain")
                        self.end_headers(); self.wfile.write(msg)
                elif self.path == "/stats":
                    payload = json.dumps(app._build_stats_dict()).encode()
                    self.send_response(200); self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*"); self.end_headers(); self.wfile.write(payload)
                elif self.path == "/events":
                    self.send_response(200); self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Connection", "keep-alive"); self.end_headers()
                    try:
                        data = json.dumps(app._build_stats_dict())
                        self.wfile.write(f"event: stats\ndata: {data}\n\n".encode()); self.wfile.flush()
                    except Exception: return
                    app._sse_clients.append(self.wfile)
                    try:
                        while True:
                            import time; time.sleep(15)
                            self.wfile.write(b": keepalive\n\n"); self.wfile.flush()
                    except Exception: pass
                    finally:
                        try: app._sse_clients.remove(self.wfile)
                        except ValueError: pass
                else:
                    self.send_response(404); self.end_headers()

            def log_message(self, *a): pass

        def run():
            try: HTTPServer(("0.0.0.0", OVERLAY_PORT), Handler).serve_forever()
            except Exception as e: print(f"[HTTP] {e}")
        threading.Thread(target=run, daemon=True).start()

    def _push_sse(self, event_type: str, data: dict):
        if not hasattr(self, "_sse_clients"): return
        msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()
        dead = []
        for wfile in list(self._sse_clients):
            try: wfile.write(msg); wfile.flush()
            except Exception: dead.append(wfile)
        for w in dead:
            try: self._sse_clients.remove(w)
            except ValueError: pass