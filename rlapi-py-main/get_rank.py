#!/usr/bin/env python3
"""
get_rank.py — Rocket League : ranks + dump complet.
Login entièrement automatisé (serveur local capture la redirection OAuth).

Usage :
    python get_rank.py --login                   # première fois (ou token expiré)
    python get_rank.py epic   <pseudo_ou_id>
    python get_rank.py steam  <steamID64>
    python get_rank.py ps4    <pseudo_psn>
"""
import asyncio
import sys
import os
import re
import json
import logging
import datetime
import time
import ctypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rlapi.egs      import EGS
from rlapi.psynet   import PsyNet, PsyNetError
from rlapi.auth     import auth_player
from rlapi.playerid import Platform, new_player_id
from rlapi.client   import RocketLeagueClient

# ── Fichier de config local ───────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rl_tokens.json")

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(f"  💾 Tokens sauvegardés → {CONFIG_FILE}")

def is_token_expired(cfg: dict, margin_seconds: int = 300) -> bool:
    exp = cfg.get("expires_at")
    if not exp:
        return True
    return time.time() >= (exp - margin_seconds)

# ── Clipboard and UI Automation Helpers for Windows ──────────────────────
def get_clipboard_text() -> str:
    """Reads UNICODE text from Windows clipboard natively using ctypes."""
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.OpenClipboard(None):
        return ""
    try:
        # CF_UNICODETEXT = 13
        h_data = user32.GetClipboardData(13)
        if not h_data:
            return ""
        ptr = kernel32.GlobalLock(h_data)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str):
    """Writes UNICODE text to Windows clipboard natively using ctypes."""
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.OpenClipboard(None):
        return
    try:
        user32.EmptyClipboard()
        # CF_UNICODETEXT = 13
        h_global = kernel32.GlobalAlloc(0x0002, (len(text) + 1) * 2) # GMEM_MOVEABLE = 2
        ptr = kernel32.GlobalLock(h_global)
        ctypes.memmove(ptr, text, (len(text) + 1) * 2)
        kernel32.GlobalUnlock(h_global)
        user32.SetClipboardData(13, h_global)
    finally:
        user32.CloseClipboard()


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]


def is_real_desktop_window(hwnd) -> bool:
    """Verifies that the window is visible and actually large enough to be a browser."""
    import ctypes
    user32 = ctypes.windll.user32
    if not user32.IsWindowVisible(hwnd):
        return False
    rect = RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        return width > 400 and height > 400
    return False


def activate_previous_window() -> bool:
    """Uses Windows Z-Order to find the window active right before the terminal and focuses it."""
    import ctypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    console_hwnd = user32.GetForegroundWindow()
    if not console_hwnd:
        console_hwnd = kernel32.GetConsoleWindow()
        
    hwnd = console_hwnd
    # GW_HWNDNEXT = 2
    for _ in range(50):
        hwnd = user32.GetWindow(hwnd, 2)
        if not hwnd:
            break
        if is_real_desktop_window(hwnd):
            user32.ShowWindow(hwnd, 9) # SW_RESTORE
            time.sleep(0.1)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.5) # Wait for OS window transition
            return True
    return False


def activate_browser_window() -> bool:
    """Fallback: Finds any running browser window by title/process and brings it to the foreground."""
    import ctypes
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    
    browser_hwnd = [None]
    
    def enum_windows_callback(hwnd, lParam):
        if is_real_desktop_window(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()
                if any(x in title for x in ("epic games", "chrome", "edge", "firefox", "opera", "brave")):
                    browser_hwnd[0] = hwnd
                    return False
        return True

    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    
    hwnd = browser_hwnd[0]
    if hwnd:
        user32.ShowWindow(hwnd, 9) # SW_RESTORE
        time.sleep(0.1)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5) # Wait for OS window transition
        return True
    return False


def simulate_select_all_and_copy():
    """Simulates Ctrl+A followed by Ctrl+C to copy webpage text."""
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(0x11, 0, 0, 0) # Ctrl down
    time.sleep(0.05)
    user32.keybd_event(0x41, 0, 0, 0) # A down
    time.sleep(0.05)
    user32.keybd_event(0x41, 0, 2, 0) # A up
    time.sleep(0.05)
    user32.keybd_event(0x43, 0, 0, 0) # C down
    time.sleep(0.05)
    user32.keybd_event(0x43, 0, 2, 0) # C up
    time.sleep(0.05)
    user32.keybd_event(0x11, 0, 2, 0) # Ctrl up


def simulate_copy_url():
    """Simulates Ctrl+L followed by Ctrl+C to copy the address bar URL."""
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(0x11, 0, 0, 0) # Ctrl down
    time.sleep(0.05)
    user32.keybd_event(0x4C, 0, 0, 0) # L down
    time.sleep(0.05)
    user32.keybd_event(0x4C, 0, 2, 0) # L up
    time.sleep(0.05)
    user32.keybd_event(0x43, 0, 0, 0) # C down
    time.sleep(0.05)
    user32.keybd_event(0x43, 0, 2, 0) # C up
    time.sleep(0.05)
    user32.keybd_event(0x11, 0, 2, 0) # Ctrl up


def extract_auth_code(text: str) -> str:
    """Robustly parses the 32-character authorization code from text/URL."""
    if not text:
        return ""
    # 1. Search inside JSON parameter or URL parameter
    match = re.search(r'(?:code=|"authorizationCode"\s*:\s*")([0-9a-fA-F]{32})', text, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    # 2. Search for a standalone 32-character hex UUID
    match = re.search(r'\b([0-9a-fA-F]{32})\b', text)
    if match:
        return match.group(1).lower()
    return ""


# ── Login via vrai navigateur + Capture Automatique ──────────────────────
def do_login():
    """
    Ouvre le vrai navigateur de l'utilisateur sur la page Epic Games,
    puis extrait automatiquement le code d'autorisation depuis la page active.
    """
    import webbrowser

    print("=" * 60)
    print("  Epic Games — Connexion ultra-automatique")
    print("=" * 60)
    print("\n1. Ton navigateur va s'ouvrir sur la page Epic Games.")
    print("2. Connecte-toi normalement (avec ton compte et captcha).")
    print("3. Une fois connecté, tu verras le code (ou 'ce site est inaccessible').")
    print("4. Reviens ICI et appuie sur Entrée. Le script va récupérer le code")
    print("   tout seul dans ton navigateur ! 🪄\n")

    egs = EGS()
    login_url = egs.get_auth_url()
    egs.close()

    print("  🌐 Ouverture du navigateur...")
    try:
        webbrowser.open(login_url)
    except Exception as e:
        print(f"  ⚠️  Impossible d'ouvrir le navigateur : {e}")
        print(f"  Ouvre manuellement ce lien : {login_url}")

    input("\n👉 Appuie sur ENTRÉE une fois que tu es connecté sur le site...")

    print("  🪄 Capture automatique du code en cours...")
    
    auth_code = ""
    original_clipboard = ""
    
    try:
        # Sauvegarde le presse-papier original de l'utilisateur pour ne pas le polluer
        original_clipboard = get_clipboard_text()
        
        # Tente de focus la fenêtre précédente (le navigateur) via Z-order,
        # ou cherche un processus de navigateur si besoin.
        focused = activate_previous_window() or activate_browser_window()
        
        if focused:
            # Méthode A: Ctrl+A -> Ctrl+C (si le JSON s'affiche directement)
            simulate_select_all_and_copy()
            time.sleep(0.3)
            copied_text = get_clipboard_text()
            auth_code = extract_auth_code(copied_text)
            
            # Méthode B: Ctrl+L -> Ctrl+C (si redirigé vers l'URL localhost inatteignable)
            if not auth_code:
                simulate_copy_url()
                time.sleep(0.3)
                copied_url = get_clipboard_text()
                auth_code = extract_auth_code(copied_url)
                
            # Restaure le presse-papiers original de l'utilisateur
            set_clipboard_text(original_clipboard)
    except Exception as e:
        # Si bug ctypes, on ignore et on passe à la saisie manuelle
        pass

    # Focus à nouveau la console pour que l'utilisateur reprenne la main
    try:
        ctypes.windll.user32.SetForegroundWindow(ctypes.windll.kernel32.GetConsoleWindow())
    except Exception:
        pass

    # Si la capture auto a échoué, on demande uniquement le code
    if not auth_code:
        print("\n  ⚠️  La capture automatique a échoué.")
        print("  Copie et colle simplement ton code d'autorisation (authorizationCode) ci-dessous :")
        raw_input = input("  Colle le code ici : ").strip()
        auth_code = extract_auth_code(raw_input)

    if not auth_code:
        print("❌ Aucun code valide trouvé. Annulation.")
        sys.exit(1)

    print(f"  ✅ Code capturé avec succès : {auth_code}")

    # ── Échange du code → tokens ──────────────────────────────────────────
    print("\n  ⏳ Échange du code → token launcher...")
    egs = EGS()
    try:
        launcher_token = egs.authenticate_with_code(auth_code)
        print(f"  ✅ Connecté : {launcher_token.display_name}")

        print("  ⏳ Échange → token EOS Rocket League...")
        exchange_code = egs.get_exchange_code(launcher_token.access_token)
        eos_token = egs.exchange_eos_token(exchange_code)
        print("  ✅ Token EOS obtenu !")

        cfg = {
            "eos_token":         eos_token.access_token,
            "eos_refresh_token": eos_token.refresh_token,
            "epic_account_id":   eos_token.account_id,
            "account_name":      launcher_token.display_name,
            "expires_at":        time.time() + eos_token.expires_in,
        }
        save_config(cfg)
        print(f"\n✅ Prêt ! Lance :")
        print(f"   python get_rank.py epic {launcher_token.display_name}")
    except Exception as e:
        print(f"\n❌ Erreur lors de l'échange du code : {e}")
    finally:
        egs.close()


# ── Rafraîchissement automatique du token ────────────────────────────────
def refresh_token_if_needed(cfg: dict) -> dict:
    if not is_token_expired(cfg):
        return cfg

    refresh = cfg.get("eos_refresh_token")
    if not refresh:
        print("❌ Pas de refresh_token. Relance : python get_rank.py --login")
        sys.exit(1)

    print("  🔄 Token expiré — rafraîchissement automatique...")
    egs = EGS()
    try:
        new_eos = egs.refresh_eos_token(refresh)
        cfg["eos_token"]         = new_eos.access_token
        cfg["eos_refresh_token"] = new_eos.refresh_token
        cfg["expires_at"]        = time.time() + new_eos.expires_in
        save_config(cfg)
        print("  ✅ Token rafraîchi !")
        return cfg
    except Exception as e:
        print(f"  ⚠️  Refresh échoué ({e}) → re-login automatique...")
        do_login()
        return load_config()
    finally:
        egs.close()

# ── Résolution Epic pseudo → account ID ──────────────────────────────────
def resolve_epic_id(cfg: dict, display_name: str) -> str:
    account_name = cfg.get("account_name", "")
    epic_id      = cfg.get("epic_account_id", "")

    if account_name and display_name.lower() == account_name.lower():
        return epic_id

    print(f"  🔍 Recherche Epic ID pour '{display_name}'...")
    egs = EGS()
    try:
        for method in ("get_account_by_display_name", "get_player_by_display_name"):
            if hasattr(egs, method):
                profile = getattr(egs, method)(display_name)
                if profile:
                    print(f"  ✅ Epic ID : {profile.id}")
                    return profile.id
        print(f"  ❌ Pseudo introuvable : '{display_name}'")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ Erreur résolution : {e}")
        sys.exit(1)
    finally:
        egs.close()

# ── Affichage des ranks ───────────────────────────────────────────────────
TIER_NAMES = [
    "Unranked",
    "Bronze I", "Bronze II", "Bronze III",
    "Silver I", "Silver II", "Silver III",
    "Gold I", "Gold II", "Gold III",
    "Platinum I", "Platinum II", "Platinum III",
    "Diamond I", "Diamond II", "Diamond III",
    "Champion I", "Champion II", "Champion III",
    "Grand Champion I", "Grand Champion II", "Grand Champion III",
    "Supersonic Legend",
]
DIVISION_NAMES = ["I", "II", "III", "IV"]
PLAYLIST_NAMES = {
    0:  "Casual",
    10: "Duel 1v1",
    11: "Doubles 2v2",
    13: "Standard 3v3",
    27: "Hoops",
    28: "Rumble",
    29: "Dropshot",
    30: "Snow Day",
    34: "Tournois",
    61: "Heatseeker",
    63: "Quads 4v4",
}
PLATFORM_MAP = {
    "epic":   Platform.EPIC,
    "steam":  Platform.STEAM,
    "ps4":    Platform.PS4,
    "xbox":   Platform.XBOX,
    "switch": Platform.SWITCH,
}
UUID_RE = re.compile(r'^[0-9a-f]{32}$', re.IGNORECASE)

def tier_label(tier):
    return TIER_NAMES[tier] if 0 <= tier < len(TIER_NAMES) else f"Unknown ({tier})"

def div_label(div):
    return DIVISION_NAMES[div] if 0 <= div < len(DIVISION_NAMES) else str(div)

def playlist_label(pid):
    return PLAYLIST_NAMES.get(pid, f"Playlist {pid}")

def format_skill(skill):
    tier    = skill.get("Tier", 0)
    div     = skill.get("Division", 0)
    mu      = skill.get("Mu", 0.0)
    matches = skill.get("MatchesPlayed", 0)
    mmr     = mu * 20 + 100
    if tier == 0:
        return f"Unranked           ({mmr:,.2f} MMR) - {matches} match(s)"
    return f"{tier_label(tier):<18} Div {div_label(div):<3} ({mmr:,.2f} MMR) - {matches} match(s)"

def print_rank(player_name, platform_str, skills):
    sep = "─" * 80
    print(f"\n{sep}")
    print(f"  {player_name}  [{platform_str.upper()}]")
    print(sep)
    played = [s for s in skills if s.get("MatchesPlayed", 0) > 0 or s.get("Tier", 0) > 0]
    if not played:
        print("  Aucune partie classée.")
    for s in sorted(played, key=lambda x: x.get("Playlist", 0)):
        print(f"  {playlist_label(s.get('Playlist', 0)):<22} {format_skill(s)}")
    print(f"{sep}\n")

# ── Appel endpoint avec gestion d'erreur ─────────────────────────────────
async def call(label: str, coro, dump: dict):
    try:
        result = await coro
        dump[label] = result
        print(f"  ✅ {label}")
        return result
    except asyncio.TimeoutError:
        dump[label] = {"error": "Timeout"}
        print(f"  ⏱  {label}")
    except PsyNetError as e:
        dump[label] = {"error": str(e)}
        print(f"  ❌ {label:<35} {e}")
    except Exception as e:
        dump[label] = {"error": str(e)}
        print(f"  ❌ {label:<35} {e}")
    return None

# ── Fetch principal ───────────────────────────────────────────────────────
async def fetch_all(cfg: dict, target_platform: Platform, target_id: str):
    eos_token       = cfg["eos_token"]
    epic_account_id = cfg["epic_account_id"]
    account_name    = cfg.get("account_name")

    if target_platform == Platform.EPIC and not UUID_RE.match(target_id):
        target_id = resolve_epic_id(cfg, target_id)

    target     = new_player_id(target_platform, target_id)
    target_str = str(target)

    print("  Authentification...")
    psy_net = PsyNet(logger=logging.getLogger("psynet"))
    try:
        rpc = await auth_player(psy_net, eos_token, epic_account_id, account_name)
        client = RocketLeagueClient(
            ws_conn=rpc.ws_conn,
            local_player_id=rpc.local_player_id,
            psy_token=rpc.psy_token,
            session_id=rpc.session_id,
            request_id=rpc.request_id,
            logger=rpc.logger,
        )
        client._lock         = rpc._lock
        client._pending_reqs = rpc._pending_reqs
        client._pong_event   = rpc._pong_event
        client._event_queue  = rpc._event_queue
        client._connected    = rpc._connected
        client._ping_task    = rpc._ping_task
        client._read_task    = rpc._read_task
    except PsyNetError as e:
        print(f"  ❌ Auth échouée : {e}")
        psy_net.close()
        return

    print(f"  Player ID : {target_str}\n")

    dump = {
        "meta": {
            "target_id":    target_id,
            "player_id":    target_str,
            "platform":     target_platform.value,
            "account_name": account_name,
            "timestamp":    datetime.datetime.now().isoformat(),
        },
        "data": {}
    }
    d = dump["data"]

    try:
        TO = 15.0

        skills_raw = await call("Skills",         client.get_players_skills([target], TO),             d)
        await call("Profil",                       client.get_profiles([target], TO),                   d)
        await call("BanStatus",                    client.get_ban_status([target], TO),                 d)
        await call("ClubDuJoueur",                 client.get_player_club_details(target, TO),          d)
        await call("XP",                           client.get_xp(TO),                                   d)
        await call("Inventaire",                   client.get_player_products(0, TO),                   d)
        await call("Wallet",                       client.get_player_wallet(TO),                        d)
        await call("MatchHistory",                 client.get_match_history(TO),                        d)
        await call("Challenges",                   client.get_active_challenges(TO),                    d)
        await call("ClubInvites",                  client.get_club_invites(TO),                         d)
        await call("CreatorCode",                  client.get_creator_code(TO),                         d)
        await call("PartyInfo",                    client.get_player_party_info(TO),                    d)

        shops_raw = await call("Shops",            client.get_standard_shops(TO),                       d)
        if shops_raw:
            shop_ids = [s["ID"] for s in (shops_raw.get("Shops") or [])]
            if shop_ids:
                await call("ShopCatalogue",        client.get_shop_catalogue(shop_ids, TO),             d)
        await call("ShopNotifications",            client.get_shop_notifications(TO),                   d)
        await call("ContainerDropTable",           client.get_container_drop_table(TO),                 d)

        region = await call("TournamentRegion",    client.get_tournament_schedule_region(TO),           d)
        if region:
            await call("TournamentSchedule",       client.get_tournament_schedule(region, TO),          d)

        await call("TrainingPacks",                client.browse_training_data(False, TO),              d)
        await call("Regions",                      client.get_sub_regions(TO),                          d)
        await call("GameServerPing",               client.get_game_server_ping_list(TO),                d)

        ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"raw_{target_id}_{ts}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dump, f, indent=2, ensure_ascii=False)
        print(f"\n  💾 Dump complet → {filename}")

        if skills_raw:
            for player in (skills_raw if isinstance(skills_raw, list) else []):
                print_rank(target_id, target_platform.value, player.get("Skills", []))

    finally:
        await client.close()
        psy_net.close()

# ── Point d'entrée ────────────────────────────────────────────────────────
def main():
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("psynet").setLevel(logging.CRITICAL)

    if len(sys.argv) == 2 and sys.argv[1] == "--login":
        do_login()
        return

    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    platform_str = sys.argv[1].lower()
    player_id    = sys.argv[2]

    platform = PLATFORM_MAP.get(platform_str)
    if not platform:
        print(f"❌ Plateforme inconnue : '{platform_str}'")
        print(f"   Valeurs : {', '.join(PLATFORM_MAP)}")
        sys.exit(1)

    cfg = load_config()
    if not cfg.get("eos_token"):
        print("⚠️  Pas de token trouvé → login automatique...\n")
        do_login()
        cfg = load_config()

    cfg = refresh_token_if_needed(cfg)

    print(f"\n🎮 Rocket League Full Dump")
    print(f"   Cible    : {player_id}  ({platform_str.upper()})")
    print(f"   Compte   : {cfg.get('account_name', '?')}  ({cfg.get('epic_account_id', '?')})\n")

    asyncio.run(fetch_all(cfg, platform, player_id))


if __name__ == "__main__":
    main()