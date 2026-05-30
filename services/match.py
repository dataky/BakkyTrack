"""services/match.py — MatchService : StatsAPI TCP, parsing events, session W/L."""
import time, socket, json, threading
from signals import AppSignals
from utils import _key_display


_B_OPEN      = ord('{')
_B_CLOSE     = ord('}')
_B_QUOTE     = ord('"')
_B_BACKSLASH = ord('\\')


class MatchService:
    def __init__(self, config, signals: AppSignals):
        self.config  = config
        self.signals = signals
        self.wins          = 0
        self.losses        = 0
        self.streak        = 0
        self.streak_type   = None
        self.history       = []
        self.session_start = time.time()
        self.my_team              = None
        self._last_known_my_team  = None
        self.team_scores          = {}
        self._last_scores         = {}
        self.current_players         = []
        self._current_player_names   = ()
        self.current_game_state      = {}
        self.detected_player_name    = ""
        self.detected_player_primary_id = ""
        self._goal_counts         = {0: 0, 1: 0}
        self._prev_tgt_stats      = {}
        self._match_result_saved  = False
        self._match_started       = False
        self._had_opponent        = False
        self._last_update_log_t   = 0.0
        self._running  = True
        self._tcp_sock = None

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
        while self._running:
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
                            if escaped:          escaped = False; continue
                            if bv == _B_BACKSLASH and in_str: escaped = True; continue
                            if bv == _B_QUOTE:   in_str = not in_str; continue
                            if in_str:           continue
                            if bv == _B_OPEN:    depth += 1
                            elif bv == _B_CLOSE:
                                depth -= 1
                                if depth == 0: end = i; break
                        if end == 0 and depth != 0: break
                        msg = buf[:end + 1]; buf = buf[end + 1:]
                        try:
                            _now = time.monotonic()
                            _is_update = b'"UpdateState"' in msg[:60]
                            if not _is_update or (_now - self._last_update_log_t) >= 1.0:
                                _decoded = msg.decode(errors="replace")
                                self.signals.log_event.emit(_decoded[:80])
                                if _is_update:
                                    self._last_update_log_t = _now
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
                try: self.signals.log_event.emit("Reconnexion StatsAPI…")
                except RuntimeError: return

    def _process_event(self, outer: dict):
        event = outer.get("Event", "")
        inner = outer.get("Data", {})
        if isinstance(inner, str):
            try: inner = json.loads(inner)
            except: return

        if event == "UpdateState":
            game    = inner.get("Game", {})
            players = inner.get("Players", [])
            self.current_game_state = game
            self.current_players = players
            _ball_speed_kmh = game.get("Ball", {}).get("Speed", 0.0)
            self.signals.ball_speed_updated.emit(round(_ball_speed_kmh, 3))
            new_names = tuple(p.get("Name") for p in players)
            if new_names != self._current_player_names:
                self._current_player_names = new_names
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
            teams_with_players = {p.get("TeamNum") for p in players}
            if 0 in teams_with_players and 1 in teams_with_players:
                if not self._had_opponent:
                    self._had_opponent = True
                    if self._match_started:
                        self.signals.game_phase_changed.emit("ingame")
            if self.my_team is None:
                platform    = self.config.get("platform", "epic").lower()
                _PLAT_PREFIX = {
                    "epic": "Epic|", "steam": "Steam|",
                    "ps4": "PS4|", "xbox": "XboxOne|", "switch": "Switch|",
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
                        raw_pid = p.get("PrimaryId", "")
                        if platform == "steam" and raw_pid.startswith("Steam|"):
                            self.detected_player_name = raw_pid.split("|", 1)[1]
                        else:
                            self.detected_player_name = p.get("Name", "")
                        self.detected_player_primary_id = raw_pid
                        self.signals.player_detected.emit(self.detected_player_name, self.my_team)
                        # Emission du nouveau signal avec PrimaryId
                        self.signals.player_detected_with_id.emit(self.detected_player_name, self.my_team, self.detected_player_primary_id)
                        break
                if self.my_team is None and game.get("bHasTarget") and not game.get("bReplay"):
                    tgt          = game.get("Target", {})
                    tgt_name     = tgt.get("Name", "")
                    tgt_team     = tgt.get("TeamNum")
                    tgt_shortcut = tgt.get("Shortcut", 0)
                    if tgt_team is not None:
                        matched_player = None
                        if tgt_shortcut:
                            for p in players:
                                if p.get("Shortcut") == tgt_shortcut and "Boost" in p:
                                    matched_player = p; break
                        if matched_player is None and tgt_name:
                            for p in players:
                                if p.get("Name") == tgt_name and "Boost" in p:
                                    matched_player = p; break
                        if matched_player is not None:
                            self.my_team = tgt_team
                            self._last_known_my_team = tgt_team
                            if not self.detected_player_name:
                                _mp_pid = matched_player.get("PrimaryId", "")
                                _plat = self.config.get("platform", "epic").lower()
                                if _plat == "steam" and _mp_pid.startswith("Steam|"):
                                    self.detected_player_name = _mp_pid.split("|", 1)[1]
                                else:
                                    self.detected_player_name = matched_player.get("Name", "")
                            if not self.detected_player_primary_id:
                                self.detected_player_primary_id = matched_player.get("PrimaryId", "")
                            self.signals.player_detected.emit(
                                matched_player.get("Name", tgt_name), tgt_team)
                            # Emission du nouveau signal avec PrimaryId
                            self.signals.player_detected_with_id.emit(
                                self.detected_player_name, self.my_team, self.detected_player_primary_id)

        elif event == "GoalScored":
            pass

        elif event == "MatchCreated":
            if (not self._match_result_saved and self._match_started
                    and self._had_opponent):
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
            self._match_result_saved = False
            self._match_started      = False
            self._had_opponent       = False
            self.my_team             = None
            self._last_known_my_team = None
            self.team_scores         = {}
            self._last_scores        = {}
            self._goal_counts        = {0: 0, 1: 0}
            self.current_players         = []
            self._current_player_names   = ()
            self.signals.game_phase_changed.emit("lobby")

        elif event in ("MatchInitialized",):
            self._match_result_saved = False

        elif event in ("RoundStarted", "CountdownBegin"):
            self._match_result_saved = False
            self._match_started      = True
            if self._had_opponent:
                self.signals.game_phase_changed.emit("ingame")

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

        elif event == "CrossbarHit":
            self.signals.trigger_sound.emit("crossbar")

        elif event == "MatchEnded":
            winner = inner.get("WinnerTeamNum")
            my     = self.my_team
            if my is None:
                my = self._last_known_my_team
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
            self._match_started = False
            self.signals.game_phase_changed.emit("lobby")

        elif event == "MatchDestroyed":
            if (not self._match_result_saved and self._match_started
                    and self._had_opponent):
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
            self._prev_tgt_stats      = {}
            self._match_result_saved  = False
            self._match_started       = False
            self._had_opponent        = False
            self.current_players         = []
            self._current_player_names   = ()
            self.signals.players_updated.emit([])
            self.signals.game_phase_changed.emit("lobby")

        elif event in ("PodiumStart", "GoalReplayStart"):
            pass