"""services/mmr.py — MMRService : tracker.gg + fallback RLAPI (singleton RLAPI)."""
import os, time, json, threading, urllib.parse, urllib.request, urllib.error
from config import BASE_DIR, SSL_CTX, PLAYLIST_NAMES, RANKS, TRACKER_HEADERS, PLATFORM_SLUGS
from signals import AppSignals
from services.mmr_fetcher_rlapi import RLAPIMmrFetcher


class MMRService:
    _CACHE_DIR   = os.path.join(os.environ.get('LOCALAPPDATA', BASE_DIR), "BakkyTrack")
    _CACHE_PATH  = os.path.join(_CACHE_DIR, "mmr_cache.json")
    _MAX_RETRIES = 3
    _RETRY_WAIT  = 4
    _PEAK_FETCH_INTERVAL = 300

    _RANKS = RANKS
    _PLAYLIST_IDS = {10: "1v1", 11: "2v2", 13: "3v3"}
    _PLATFORM_SLUG = PLATFORM_SLUGS

    def __init__(self, config, signals: AppSignals):
        self.config            = config
        self.signals           = signals
        self.selected_playlist = "3v3"
        self.all_mmr = {
            k: {"mmr": None, "mmr_start": None, "mmr_change": 0,
                "rank": "", "tier_id": 0, "div_id": 0, "peak_mmr": None}
            for k in PLAYLIST_NAMES
        }
        self._load_cache()
        self.detected_primary_id = None
        self._last_player_name = ""
        self._last_player_primary_id = ""
        self._fetch_lock = threading.Lock()
        self._peak_fetch_lock = threading.Lock()
        self._peak_refresh_timer = None
        self._first_peak_fetch_done = False
        # Connexion au signal de détection avec ID
        self.signals.player_detected_with_id.connect(self._on_player_detected)

    def _on_player_detected(self, name, team, primary_id):
        self.detected_primary_id = primary_id
        if name:
            self._last_player_name = name
        if primary_id:
            self._last_player_primary_id = primary_id
        self.signals.log_event.emit(f"[MMR] ID détecté en jeu: {primary_id}")

    def _tier_id(self, rank_name: str) -> int:
        try: return self._RANKS.index(rank_name)
        except ValueError: return 0

    def _div_id(self, div_name: str) -> int:
        return {"Division I": 1, "Division II": 2,
                "Division III": 3, "Division IV": 4}.get(div_name, 0)

    def _load_cache(self):
        try:
            with open(self._CACHE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for k in PLAYLIST_NAMES:
                if k in data:
                    cached_mmr = data[k].get("mmr")
                    self.all_mmr[k]["mmr"]       = cached_mmr
                    self.all_mmr[k]["mmr_start"] = cached_mmr
                    self.all_mmr[k]["rank"]      = data[k].get("rank", "")
                    self.all_mmr[k]["tier_id"]   = data[k].get("tier_id", 0)
                    self.all_mmr[k]["div_id"]    = data[k].get("div_id", 0)
                    peak = data[k].get("peak_mmr")
                    if peak:
                        self.all_mmr[k]["peak_mmr"] = peak
        except Exception:
            pass

    def _save_cache(self):
        try:
            os.makedirs(self._CACHE_DIR, exist_ok=True)
            data = {
                k: {"mmr": v["mmr"], "rank": v.get("rank", ""),
                    "tier_id": v.get("tier_id", 0), "div_id": v.get("div_id", 0),
                    **({"peak_mmr": v["peak_mmr"]} if v.get("peak_mmr") else {})}
                for k, v in self.all_mmr.items()
                if v["mmr"] is not None or v.get("peak_mmr") is not None
            }
            with open(self._CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def reset_deltas(self):
        for d in self.all_mmr.values():
            d["mmr_start"] = d["mmr"]
            d["mmr_change"] = 0

    _TRACKER_COOLDOWN_S = 300
    _last_tracker_fetch_time = 0.0

    def fetch_async(self, player_name="", player_primary_id="", force=False):
        # Éviter les appels concurrents
        if not self._fetch_lock.acquire(blocking=False):
            self.signals.log_event.emit("[MMR] Fetch déjà en cours, ignoré.")
            return
        try:
            preferred = self.config.get("mmr_source", "rlapi")

            if player_name:
                self._last_player_name = player_name
            if player_primary_id:
                self._last_player_primary_id = player_primary_id

            # Détecter si on a un nom d'utilisateur valide pour récupérer le Peak
            platform = self.config["platform"].lower()
            slug = self._PLATFORM_SLUG.get(platform, "epic")
            username = ""
            eff_id = player_primary_id or self.detected_primary_id or self._last_player_primary_id or ""
            if slug == "steam":
                if eff_id.startswith("Steam|"):
                    parts = eff_id.split("|")
                    username = parts[1] if len(parts) >= 2 else ""
            if not username:
                username = self.config["username"] or player_name or self._last_player_name or ""

            if username and not self._first_peak_fetch_done:
                self.fetch_peak_async(username, eff_id, force=True)
                self._first_peak_fetch_done = True

            if preferred != "rlapi":
                # Cooldown uniquement pour tracker.gg (évite les rate limits)
                now = time.time()
                if not force:
                    elapsed = now - MMRService._last_tracker_fetch_time
                    remaining = self._TRACKER_COOLDOWN_S - elapsed
                    if remaining > 0:
                        mins = int(remaining // 60)
                        secs = int(remaining % 60)
                        self.signals.log_event.emit(
                            f"[MMR] Cooldown tracker.gg — prochain fetch dans {mins}m{secs:02d}s")
                        return
                MMRService._last_tracker_fetch_time = now

            if preferred == "rlapi":
                threading.Thread(target=self._fetch_with_rlapi,
                                 args=(player_name, player_primary_id, force),
                                 daemon=True).start()
            else:
                threading.Thread(target=self._fetch_tracker,
                                 args=(player_name, player_primary_id),
                                 daemon=True).start()
        finally:
            self._fetch_lock.release()

    def _get_rlapi_fetcher(self) -> RLAPIMmrFetcher:
        """Retourne une instance singleton de RLAPIMmrFetcher."""
        if not hasattr(self, '_rlapi_fetcher') or self._rlapi_fetcher is None:
            self._rlapi_fetcher = RLAPIMmrFetcher(self.config, self.signals)
        return self._rlapi_fetcher

    def fetch_peak_async(self, player_name="", player_primary_id="", force=False):
        if not self._peak_fetch_lock.acquire(blocking=False):
            self.signals.log_event.emit("[MMR] Peak tracker déjà en cours, ignoré.")
            return

        def _worker():
            try:
                self._fetch_peak_tracker(player_name, player_primary_id, force)
            finally:
                self._peak_fetch_lock.release()

        threading.Thread(target=_worker, daemon=True).start()

    def _schedule_peak_refresh(self):
        if self._peak_refresh_timer is not None:
            try:
                self._peak_refresh_timer.cancel()
            except Exception:
                pass
        self._peak_refresh_timer = threading.Timer(self._PEAK_FETCH_INTERVAL, self.fetch_peak_async)
        self._peak_refresh_timer.daemon = True
        self._peak_refresh_timer.start()

    def _fetch_peak_tracker(self, player_name="", player_primary_id="", force=False):
        platform = self.config["platform"].lower()
        slug = self._PLATFORM_SLUG.get(platform, "epic")
        
        effective_primary_id = player_primary_id or self.detected_primary_id or self._last_player_primary_id or ""
        effective_player_name = player_name or self._last_player_name or ""

        if slug == "steam":
            if effective_primary_id.startswith("Steam|"):
                parts = effective_primary_id.split("|")
                username = parts[1] if len(parts) >= 2 else ""
            else:
                username = self.config["username"] or effective_player_name
            encoded = username
        else:
            username = self.config["username"] or effective_player_name
            encoded = urllib.parse.quote(username, safe="")
        if not username:
            self._schedule_peak_refresh()
            return

        url = (f"https://api.tracker.gg/api/v2/rocket-league/standard/profile"
               f"/{slug}/{encoded}")
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url, headers=TRACKER_HEADERS)
                self.signals.log_event.emit(
                    f"[MMR] Peak tracker tentative {attempt}/{self._MAX_RETRIES} — {username} ({slug})…")
                try:
                    with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                        raw = resp.read().decode("utf-8")
                except Exception:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if not isinstance(data.get("data"), dict):
                    raise ValueError("tracker.gg : pas de données de profil")

                updated = False
                for seg in data["data"].get("segments", []):
                    if seg.get("type") != "peak-rating":
                        continue
                    pid_val = seg.get("attributes", {}).get("playlistId")
                    pl_key = self._PLAYLIST_IDS.get(pid_val)
                    peak_val = seg.get("stats", {}).get("peakRating", {}).get("value")
                    if pl_key and peak_val:
                        self.all_mmr[pl_key]["peak_mmr"] = int(peak_val)
                        updated = True

                if updated:
                    self._save_cache()
                    self.signals.mmr_updated.emit()
                    self.signals.log_event.emit("✓ Peak RL tracker mis à jour")
                else:
                    self.signals.log_event.emit("[MMR] Peak tracker : aucun peak trouvé")
                self._schedule_peak_refresh()
                return
            except Exception as e:
                self.signals.log_event.emit(
                    f"[MMR] Peak tracker erreur tentative {attempt}: {str(e)[:60]}")
                if attempt < self._MAX_RETRIES:
                    time.sleep(self._RETRY_WAIT * attempt)
                    continue
                self.signals.mmr_error.emit(
                    f"Échec peak tracker après {self._MAX_RETRIES} tentatives: {str(e)[:55]}")
                self._schedule_peak_refresh()
                return

    def _fetch_with_rlapi(self, player_name="", player_primary_id="", force=False):
        effective_primary_id = self.detected_primary_id or player_primary_id
        platform = self.config["platform"].lower()
        username = self.config["username"] or player_name

        epic_id = None
        if effective_primary_id and effective_primary_id.startswith("Epic|"):
            parts = effective_primary_id.split("|")
            if len(parts) >= 2:
                epic_id = parts[1]
                self.signals.log_event.emit(f"[RLAPI] Utilisation de l'Epic ID détecté: {epic_id}")
        elif effective_primary_id and effective_primary_id.startswith("Steam|"):
            self.signals.log_event.emit("[RLAPI] PrimaryId Steam détecté, mais RLAPI préfère Epic — fallback tracker")
            self._fetch_tracker(player_name, player_primary_id)
            return

        if not epic_id and not username:
            self.signals.log_event.emit("[RLAPI] Pas d'identifiant utilisateur (pseudo ou ID).")
            return

        self.signals.log_event.emit("[RLAPI] Tentative de récupération MMR via RLAPI...")
        fetcher = self._get_rlapi_fetcher()  # singleton réutilisé
        try:
            if epic_id:
                data = fetcher.fetch_sync(username, platform, user_id=epic_id)
            else:
                data = fetcher.fetch_sync(username, platform)
        except Exception as e:
            self.signals.log_event.emit(f"[RLAPI] Échec: {str(e)[:80]} → fallback vers tracker.gg")
            self._fetch_tracker(player_name, player_primary_id)
            return

        for playlist_key, values in data.items():
            if playlist_key in self.all_mmr:
                d = self.all_mmr[playlist_key]
                d["mmr"] = values["mmr"]
                if d["mmr_start"] is None:
                    d["mmr_start"] = values["mmr"]
                d["mmr_change"] = d["mmr"] - (d["mmr_start"] or d["mmr"])
                d["rank"] = values["rank"]
                d["tier_id"] = values["tier_id"]
                d["div_id"] = values["div_id"]
        self._save_cache()
        self.signals.mmr_updated.emit()
        self.signals.log_event.emit("✓ MMR & Ranks mis à jour (RLAPI officiel)")

    def _fetch_tracker(self, player_name="", player_primary_id=""):
        """Ancienne méthode via tracker.gg (inchangée)."""
        platform = self.config["platform"].lower()
        slug     = self._PLATFORM_SLUG.get(platform, "epic")
        if slug == "steam":
            if player_primary_id.startswith("Steam|"):
                parts = player_primary_id.split("|")
                username = parts[1] if len(parts) >= 2 else ""
            else:
                username = self.config["username"] or player_name
            encoded = username
        else:
            username = self.config["username"] or player_name
            encoded = urllib.parse.quote(username, safe="")
        if not username:
            return
        url = (f"https://api.tracker.gg/api/v2/rocket-league/standard/profile"
               f"/{slug}/{encoded}")
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url, headers=TRACKER_HEADERS)
                self.signals.log_event.emit(
                    f"[MMR] Tentative {attempt}/{self._MAX_RETRIES}"
                    f" — {username} ({slug})…")
                try:
                    with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
                        raw = resp.read().decode("utf-8")
                except Exception:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if not isinstance(data.get("data"), dict):
                    raise ValueError("tracker.gg : pas de données de profil")
                updated = False
                for seg in data["data"].get("segments", []):
                    if seg.get("type") != "playlist":
                        continue
                    pid    = seg.get("attributes", {}).get("playlistId")
                    pl_key = self._PLAYLIST_IDS.get(pid)
                    if pl_key is None:
                        continue
                    s          = seg.get("stats", {})
                    tier_name  = s.get("tier",     {}).get("metadata", {}).get("name", "Unranked")
                    div_str    = s.get("division",  {}).get("metadata", {}).get("name", "")
                    mmr_val    = s.get("rating",    {}).get("value", 0)
                    tier_id    = self._tier_id(tier_name)
                    div_id     = self._div_id(div_str)
                    mmr        = int(mmr_val) if mmr_val else 0
                    d = self.all_mmr[pl_key]
                    d["mmr_start"]  = mmr if d["mmr_start"] is None else d["mmr_start"]
                    d["mmr_change"] = mmr - d["mmr_start"]
                    d["mmr"]        = mmr
                    d["rank"]       = tier_name
                    d["tier_id"]    = tier_id
                    d["div_id"]     = div_id
                    div_txt = f" {div_str}" if div_str else ""
                    self.signals.log_event.emit(
                        f"[{pl_key}] {tier_name}{div_txt} — MMR: {mmr}")
                    updated = True
                if not updated:
                    raise ValueError("Aucune playlist ranked trouvée dans le profil")
                self._save_cache()
                self.signals.mmr_updated.emit()
                self.signals.log_event.emit("✓ MMR & Ranks mis à jour (tracker.gg)")
                return
            except Exception as e:
                self.signals.log_event.emit(
                    f"[MMR] Erreur tentative {attempt}: {str(e)[:60]}")
                if attempt < self._MAX_RETRIES:
                    time.sleep(self._RETRY_WAIT * attempt)
                else:
                    self.signals.mmr_error.emit(
                        f"Échec après {self._MAX_RETRIES} tentatives: {str(e)[:55]}")