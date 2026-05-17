"""services/mmr.py — MMRService : tracker.gg HTTP."""
import os, time, json, threading, urllib.parse, urllib.request, urllib.error
from config import BASE_DIR, SSL_CTX, PLAYLIST_NAMES, RANKS, TRACKER_HEADERS, PLATFORM_SLUGS
from signals import AppSignals


class MMRService:
    _CACHE_PATH  = os.path.join(BASE_DIR, "mmr_cache.json")
    _MAX_RETRIES = 3
    _RETRY_WAIT  = 4

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
            data = {
                k: {"mmr": v["mmr"], "rank": v.get("rank", ""),
                    "tier_id": v.get("tier_id", 0), "div_id": v.get("div_id", 0),
                    **({"peak_mmr": v["peak_mmr"]} if v.get("peak_mmr") else {})}
                for k, v in self.all_mmr.items() if v["mmr"] is not None
            }
            with open(self._CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def reset_deltas(self):
        for d in self.all_mmr.values():
            d["mmr_start"] = d["mmr"]
            d["mmr_change"] = 0

    _FETCH_COOLDOWN_S = 300
    _last_fetch_time  = 0.0

    def fetch_async(self, player_name="", player_primary_id="", force=False):
        now = time.time()
        if not force:
            elapsed = now - MMRService._last_fetch_time
            remaining = self._FETCH_COOLDOWN_S - elapsed
            if remaining > 0:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                self.signals.log_event.emit(
                    f"[MMR] Cooldown actif — prochain fetch dans {mins}m{secs:02d}s")
                return
        MMRService._last_fetch_time = now
        threading.Thread(target=self._fetch, args=(player_name, player_primary_id), daemon=True).start()

    def _fetch(self, player_name="", player_primary_id=""):
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
                for seg in data["data"].get("segments", []):
                    if seg.get("type") != "peak-rating":
                        continue
                    pid      = seg.get("attributes", {}).get("playlistId")
                    pl_key   = self._PLAYLIST_IDS.get(pid)
                    peak_val = seg.get("stats", {}).get("peakRating", {}).get("value")
                    if pl_key and peak_val:
                        self.all_mmr[pl_key]["peak_mmr"] = int(peak_val)
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