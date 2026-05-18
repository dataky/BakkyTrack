import threading
import time

try:
    import obsws_python as obs
    OBSWS_AVAILABLE = True
except ImportError:
    OBSWS_AVAILABLE = False


class OBSWebSocketService:
    def __init__(self, config, signals):
        self.config = config
        self.signals = signals
        self.client = None

        # threading.Event pour la thread-safety : .set(), .clear(), .is_set(), .wait()
        self._connected = threading.Event()
        # Verrou pour protéger l'accès à self.client
        self._lock = threading.Lock()
        # Empêche plusieurs tentatives de connexion simultanées
        self._connecting = threading.Event()

        self.signals.game_phase_changed.connect(self._on_phase_changed)

    # ──────────────────────────────────────────────
    # Connexion
    # ──────────────────────────────────────────────

    def connect(self):
        """Lance une connexion asynchrone. Sans effet si déjà connecté ou en cours."""
        if not OBSWS_AVAILABLE or not self.config.get("obs_ws_enabled", False):
            return
        if self._connected.is_set() or self._connecting.is_set():
            return

        threading.Thread(target=self._do_connect, daemon=True).start()

    def _do_connect(self):
        self._connecting.set()
        try:
            host     = self.config.get("obs_ws_host",     "localhost")
            port     = self.config.get("obs_ws_port",     4455)
            password = self.config.get("obs_ws_password", "")

            client = obs.ReqClient(host=host, port=port, password=password, timeout=3)

            with self._lock:
                self.client = client

            self._connected.set()
            self.signals.log_event.emit("[OBS] Connecté au WebSocket.")

        except Exception as e:
            self._connected.clear()
            self.signals.log_event.emit(f"[OBS] Erreur de connexion: {e}")

        finally:
            self._connecting.clear()

    # ──────────────────────────────────────────────
    # Déconnexion
    # ──────────────────────────────────────────────

    def disconnect(self):
        """Ferme proprement la connexion WebSocket."""
        self._connected.clear()
        with self._lock:
            if self.client is not None:
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                self.client = None

    # ──────────────────────────────────────────────
    # Changement de scène
    # ──────────────────────────────────────────────

    def switch_scene(self, scene_name: str):
        """Change la scène active dans OBS (asynchrone)."""
        if not self._connected.is_set():
            return
        threading.Thread(
            target=self._do_switch_scene,
            args=(scene_name,),
            daemon=True,
        ).start()

    def _do_switch_scene(self, scene_name: str):
        with self._lock:
            client = self.client

        if client is None:
            return

        try:
            client.set_current_program_scene(scene_name)
            self.signals.log_event.emit(f"[OBS] Scène changée: {scene_name}")
        except Exception as e:
            self.signals.log_event.emit(f"[OBS] Erreur changement scène: {e}")
            self.disconnect()

    # ──────────────────────────────────────────────
    # Slot : changement de phase de jeu
    # ──────────────────────────────────────────────

    def _on_phase_changed(self, phase: str):
        if not self.config.get("obs_ws_enabled", False):
            return

        # Tout dans un thread pour ne jamais bloquer le thread du signal Qt
        threading.Thread(
            target=self._handle_phase,
            args=(phase,),
            daemon=True,
        ).start()

    def _handle_phase(self, phase: str):
        # Connexion si nécessaire, puis attente réelle (plus de sleep arbitraire)
        if not self._connected.is_set():
            self.connect()
            connected = self._connected.wait(timeout=5)
            if not connected:
                self.signals.log_event.emit("[OBS] Timeout: impossible de se connecter pour changer de scène.")
                return

        scene_key   = "obs_scene_ingame"  if phase == "ingame" else "obs_scene_outgame"
        scene_default = "In-Game"         if phase == "ingame" else "Lobby"
        scene = self.config.get(scene_key, scene_default)

        if scene:
            self._do_switch_scene(scene)