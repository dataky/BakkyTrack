# gamepad_state.py — Version corrigée avec mapping complet PS4 / PS5 Raw
import ctypes
import sys

# ------------------------- XInput (Xbox et émulation) -------------------------
class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_uint16),
        ("bLeftTrigger", ctypes.c_uint8),
        ("bRightTrigger", ctypes.c_uint8),
        ("sThumbLX", ctypes.c_int16),
        ("sThumbLY", ctypes.c_int16),
        ("sThumbRX", ctypes.c_int16),
        ("sThumbRY", ctypes.c_int16),
    ]

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_uint32),
        ("Gamepad", XINPUT_GAMEPAD),
    ]

_xinput = None
if sys.platform == "win32":
    for _lib in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            _xinput = getattr(ctypes.windll, _lib)
            break
        except OSError:
            pass

def _poll_xinput(user_index=0):
    if not _xinput:
        return None
    st = XINPUT_STATE()
    ret = _xinput.XInputGetState(user_index, ctypes.byref(st))
    if ret != 0:
        return None
    return st

# ------------------------- pygame (Manettes PS4/PS5/Switch) -------------------
try:
    import pygame as _pg
except ImportError:
    _pg = None

_joy_initialized = False

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# ── MAPPINGS BOUTONS ─────────────────────────────────────────────────────────
#
# Deux variantes selon le mode SDL détecté par le nom de la manette :
#
# ── MODE A : PS4 Raw (Linux/SDL, "PS4 Controller") — 16 boutons, 0 hat ──────
#   0=Croix   1=Rond   2=Carré   3=Triangle
#   4=Share   5=PS     6=Options
#   7=L3      8=R3
#   9=L1     10=R1
#  11=Haut   12=Bas   13=Gauche  14=Droite   ← D-pad en boutons
#  15=Pavé tactile
#  Axes : 0=LX  1=LY  2=L2  3=RX  4=RY  5=R2
#
# ── MODE B : PS5 Raw (Linux/SDL, "Wireless Controller") — 13 boutons, 1 hat ─
#   0=Croix   1=Rond   2=Carré   3=Triangle
#   4=L1      5=R1
#   6=L2(dig) 7=R2(dig)   ← redondants avec les axes 2/5, ignorés ici
#   8=Create  9=Options  10=PS   11=L3  12=R3  13=Pavé tactile (si présent)
#  Hat 0 : D-pad (SDL convention : hy=1→Haut, hy=-1→Bas, hx=-1→Gauche, hx=1→Droite)
#  Axes : 0=LX  1=LY  2=L2  3=RX  4=RY  5=R2
#
# Masques XInput étendus (bits non-standard pour PS/Touchpad) :
#   0x0400 = bouton PS / Guide   (pas d'équivalent XInput officiel)
#   0x0800 = Pavé tactile click  (pas d'équivalent XInput officiel)
# ─────────────────────────────────────────────────────────────────────────────

# PS4 Raw — SDL pygame GameController (16 boutons, 6 axes, 0 hat)
_PS4_BTN_MAP = {
    0:  0x1000,  # Croix (X)       → A
    1:  0x2000,  # Rond  (O)       → B
    2:  0x4000,  # Carré           → X
    3:  0x8000,  # Triangle        → Y
    4:  0x0020,  # Share           → Back
    5:  0x0400,  # Bouton PS       → Guide (bit étendu)
    6:  0x0010,  # Options         → Start
    7:  0x0040,  # L3
    8:  0x0080,  # R3
    9:  0x0100,  # L1 (LB)
    10: 0x0200,  # R1 (RB)
    # 11-14 : D-pad traité via boutons dans _poll_joystick (mode PS4)
    15: 0x0800,  # Pavé tactile    → bit étendu
}

# Boutons D-pad spécifiques au mode PS4 (exposés comme boutons, pas hat)
_PS4_DPAD_BTN = {
    11: 0x0001,  # Haut
    12: 0x0002,  # Bas
    13: 0x0004,  # Gauche
    14: 0x0008,  # Droite
}

# PS5 Raw — SDL joystick (13 boutons, 6 axes, 1 hat)
_PS5_BTN_MAP = {
    0:  0x1000,  # Croix (X)       → A
    1:  0x2000,  # Rond  (O)       → B
    2:  0x4000,  # Carré           → X
    3:  0x8000,  # Triangle        → Y
    4:  0x0100,  # L1 (LB)
    5:  0x0200,  # R1 (RB)
    # 6 & 7 : L2/R2 digitaux — redondants avec les axes 2/5, ignorés
    8:  0x0020,  # Create          → Back
    9:  0x0010,  # Options         → Start
    10: 0x0400,  # Bouton PS       → Guide (bit étendu)
    11: 0x0040,  # L3
    12: 0x0080,  # R3
    13: 0x0800,  # Pavé tactile    → bit étendu (présent sur certains modèles)
}


def _detect_ps_mode(joy):
    """
    Retourne 'ps4', 'ps5' ou 'generic' selon le nom SDL du joystick.
    Le nom est en minuscules pour la comparaison.
    """
    try:
        name = joy.get_name().lower()
    except Exception:
        return "generic"

    if "ps5" in name or "dualsense" in name or "wireless controller" in name:
        return "ps5"
    if "ps4" in name or "dualshock 4" in name or "ps4 controller" in name:
        return "ps4"
    return "generic"


def _ensure_joy():
    global _joy_initialized
    if _pg is None:
        return False
    if not _joy_initialized:
        try:
            _pg.init()
            _pg.joystick.init()
            _joy_initialized = True
        except Exception:
            return False
    return True


# ── Cache du joystick ─────────────────────────────────────────────────────────
_cached_joy = None
_cached_joy_count = 0

def _get_joy():
    """Retourne le joystick 0 mis en cache, ou None si absent."""
    global _cached_joy, _cached_joy_count
    if not _ensure_joy():
        return None

    count = _pg.joystick.get_count()

    if count == 0:
        _cached_joy = None
        _cached_joy_count = 0
        return None

    if _cached_joy is None or count != _cached_joy_count:
        try:
            joy = _pg.joystick.Joystick(0)
            joy.init()
            _cached_joy = joy
            _cached_joy_count = count
        except Exception:
            _cached_joy = None
            return None

    return _cached_joy
# ─────────────────────────────────────────────────────────────────────────────


def _norm_trigger(val: float) -> float:
    """
    Normalise une gâchette analogique en [0.0, 1.0].
    Gère les deux conventions SDL :
      • Repos à -1.0  → plage -1 … +1  →  (val + 1) / 2
      • Repos à  0.0  → plage  0 … +1  →  val
    """
    if val < 0.0:
        return (val + 1.0) / 2.0
    return val


def _poll_joystick():
    try:
        _pg.event.pump()
    except Exception:
        pass

    joy = _get_joy()
    if joy is None:
        return None

    mode = _detect_ps_mode(joy)
    st = XINPUT_STATE()
    gp = st.Gamepad

    w = 0
    num_btns = joy.get_numbuttons()

    # ── Sélection du mapping selon le mode ───────────────────────────────────
    if mode == "ps4":
        # Boutons principaux
        for ps_idx, x_mask in _PS4_BTN_MAP.items():
            if ps_idx < num_btns and joy.get_button(ps_idx):
                w |= x_mask
        # D-pad en boutons (mode PS4)
        for ps_idx, x_mask in _PS4_DPAD_BTN.items():
            if ps_idx < num_btns and joy.get_button(ps_idx):
                w |= x_mask

    elif mode == "ps5":
        # Boutons principaux
        for ps_idx, x_mask in _PS5_BTN_MAP.items():
            if ps_idx < num_btns and joy.get_button(ps_idx):
                w |= x_mask
        # D-pad via Hat (mode PS5)
        if joy.get_numhats() > 0:
            hx, hy = joy.get_hat(0)
            if hy ==  1: w |= 0x0001  # Haut
            if hy == -1: w |= 0x0002  # Bas
            if hx == -1: w |= 0x0004  # Gauche
            if hx ==  1: w |= 0x0008  # Droite

    else:
        # Fallback générique (layout "Raw variante B" d'origine)
        _GENERIC_BTN_MAP = {
            0:  0x1000,  # Croix
            1:  0x2000,  # Rond
            2:  0x4000,  # Carré
            3:  0x8000,  # Triangle
            6:  0x0100,  # L1
            7:  0x0200,  # R1
            8:  0x0020,  # Share/Create
            9:  0x0010,  # Options
            10: 0x0040,  # L3
            11: 0x0080,  # R3
            12: 0x0400,  # PS
            13: 0x0800,  # Touchpad
        }
        for ps_idx, x_mask in _GENERIC_BTN_MAP.items():
            if ps_idx < num_btns and joy.get_button(ps_idx):
                w |= x_mask
        # D-pad via Hat (fallback)
        if joy.get_numhats() > 0:
            hx, hy = joy.get_hat(0)
            if hy ==  1: w |= 0x0001
            if hy == -1: w |= 0x0002
            if hx == -1: w |= 0x0004
            if hx ==  1: w |= 0x0008

    gp.wButtons = w

    # ── Axes (communs PS4 / PS5 Raw : LX=0, LY=1, L2=2, RX=3, RY=4, R2=5) ─
    def get_ax(i):
        return joy.get_axis(i) if i < joy.get_numaxes() else 0.0

    gp.sThumbLX = int(max(-32768, min(32767,  get_ax(0) * 32767)))
    gp.sThumbLY = int(max(-32768, min(32767, -get_ax(1) * 32767)))

    n = joy.get_numaxes()

    if n >= 6:
        gp.sThumbRX = int(max(-32768, min(32767,  get_ax(3) * 32767)))
        gp.sThumbRY = int(max(-32768, min(32767, -get_ax(4) * 32767)))
        gp.bLeftTrigger  = int(_norm_trigger(get_ax(2)) * 255)
        gp.bRightTrigger = int(_norm_trigger(get_ax(5)) * 255)
    elif n >= 4:
        # Fallback : manettes génériques 4 axes
        gp.sThumbRX = int(max(-32768, min(32767,  get_ax(2) * 32767)))
        gp.sThumbRY = int(max(-32768, min(32767, -get_ax(3) * 32767)))

    st.dwPacketNumber = 1
    return st


# ------------------------- API publique -------------------------
def get_gamepad_state(user_index=0):
    # 1. Tenter XInput (Xbox / Manettes émulées)
    if sys.platform == "win32":
        st = _poll_xinput(user_index)
        if st is not None:
            return st

    # 2. Tenter Pygame (PS4, PS5, Switch, etc.)
    return _poll_joystick()


# ------------------------- Outil de diagnostic -------------------------
def print_raw_state():
    """
    Lance une boucle de debug dans le terminal.
    Lance avec :  python gamepad_state.py
    Affiche en temps réel :
      - Le nom SDL et le mode détecté (ps4 / ps5 / generic)
      - Les indices/valeurs bruts de tous les axes, boutons et hats
    """
    import time
    if not _ensure_joy():
        print("pygame non disponible."); return
    print("En attente d'une manette… (Ctrl+C pour quitter)")
    last_mode = None
    while True:
        try:
            _pg.event.pump()
        except Exception:
            pass
        joy = _get_joy()
        if joy is None:
            print("\r  [aucune manette]", end="", flush=True)
            time.sleep(0.2); continue

        mode = _detect_ps_mode(joy)
        if mode != last_mode:
            print(f"\n>>> Manette détectée : '{joy.get_name()}' → mode={mode}")
            last_mode = mode

        axes = [round(joy.get_axis(i), 3) for i in range(joy.get_numaxes())]
        btns = [joy.get_button(i) for i in range(joy.get_numbuttons())]
        hats = [joy.get_hat(i) for i in range(joy.get_numhats())]
        line = f"\rAxes={axes}  Btns={btns}  Hats={hats}   "
        print(line, end="", flush=True)
        time.sleep(0.05)

if __name__ == "__main__":
    print_raw_state()
