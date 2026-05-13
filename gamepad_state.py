# gamepad_state.py — Version corrigée pour manettes PlayStation "Raw"
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

# ── CORRECTIF BOUTONS ────────────────────────────────────────────────────────
# Sur DS4/DualSense en mode "Raw" via pygame/SDL sous Windows :
#   0=Carré  1=Croix  2=Rond  3=Triangle
#   4=L1  5=R1  6=L2(digital)  7=R2(digital)
#   8=Share/Create  9=Options  10=L3  11=R3  12=PS  13=Pavé tactile
#
# Sur certains systèmes (Linux / drivers différents) l'ordre peut être :
#   0=Croix  1=Rond  2=Carré  3=Triangle  …
# → Si les boutons sont toujours inversés, échangez les indices ci-dessous.
# ─────────────────────────────────────────────────────────────────────────────
_PS_BTN_MAP = {
    1:  0x1000,  # Croix     → A
    2:  0x2000,  # Rond      → B
    0:  0x4000,  # Carré     → X
    3:  0x8000,  # Triangle  → Y
    8:  0x0020,  # Share/Create → Back
    9:  0x0010,  # Options   → Start
    10: 0x0040,  # L3
    11: 0x0080,  # R3
    4:  0x0100,  # L1
    5:  0x0200,  # R1
}

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

# ── CORRECTIF PRINCIPAL : cache du joystick ───────────────────────────────
# BUG ORIGINAL : `_pg.joystick.Joystick(0)` était recréé à CHAQUE appel.
# SDL réinitialise alors l'objet et renvoie des états à zéro.
# Solution : instancier une seule fois et réutiliser l'objet.
_cached_joy = None
_cached_joy_count = 0

def _get_joy():
    """Retourne le joystick 0 mis en cache, ou None si absent."""
    global _cached_joy, _cached_joy_count
    if not _ensure_joy():
        return None

    count = _pg.joystick.get_count()

    # Manette débranchée → on vide le cache
    if count == 0:
        _cached_joy = None
        _cached_joy_count = 0
        return None

    # Nouvelle manette branchée (ou premier accès) → on (ré)initialise
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

def _poll_joystick():
    try:
        _pg.event.pump()
    except Exception:
        pass

    joy = _get_joy()
    if joy is None:
        return None

    st = XINPUT_STATE()
    gp = st.Gamepad

    # 1. BOUTONS
    w = 0
    num_btns = joy.get_numbuttons()
    for ps_idx, x_mask in _PS_BTN_MAP.items():
        if ps_idx < num_btns and joy.get_button(ps_idx):
            w |= x_mask

    # 2. D-PAD (Hat)
    if joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        if hy ==  1: w |= 0x0001  # Haut
        if hy == -1: w |= 0x0002  # Bas
        if hx == -1: w |= 0x0004  # Gauche
        if hx ==  1: w |= 0x0008  # Droite

    gp.wButtons = w

    # 3. AXES
    def get_ax(i):
        return joy.get_axis(i) if i < joy.get_numaxes() else 0.0

    # Stick gauche — identique sur toutes les variantes
    gp.sThumbLX = int(max(-32768, min(32767,  get_ax(0) * 32767)))
    gp.sThumbLY = int(max(-32768, min(32767, -get_ax(1) * 32767)))

    n = joy.get_numaxes()

    if n >= 6:
        # ── CORRECTIF AXES DS4/DualSense sous Windows (6 axes) ──────────────
        # BUG ORIGINAL : axes 2 et 5 utilisés pour le stick droit,
        #                axes 3 et 4 pour les gâchettes → INVERSÉ !
        #
        # Ordre réel SDL/pygame en mode Raw :
        #   0 = LX   1 = LY   2 = L2 (-1→1)
        #   3 = RX   4 = RY   5 = R2 (-1→1)
        # ─────────────────────────────────────────────────────────────────────
        gp.sThumbRX = int(max(-32768, min(32767,  get_ax(3) * 32767)))
        gp.sThumbRY = int(max(-32768, min(32767, -get_ax(4) * 32767)))

        # Gâchettes : -1.0 au repos → +1.0 complètement enfoncées
        l2_raw = (get_ax(2) + 1.0) / 2.0
        r2_raw = (get_ax(5) + 1.0) / 2.0
        gp.bLeftTrigger  = int(l2_raw * 255)
        gp.bRightTrigger = int(r2_raw * 255)

    elif n >= 4:
        # Fallback : manettes génériques 4 axes (RX=2, RY=3, pas de gâchettes)
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
    Affiche en temps réel les indices/valeurs bruts de tous les axes et boutons,
    ce qui permet de corriger le mapping si besoin.
    """
    import time
    if not _ensure_joy():
        print("pygame non disponible."); return
    print("En attente d'une manette… (Ctrl+C pour quitter)")
    while True:
        try:
            _pg.event.pump()
        except Exception:
            pass
        joy = _get_joy()
        if joy is None:
            print("\r  [aucune manette]", end="", flush=True)
            time.sleep(0.2); continue
        axes = [round(joy.get_axis(i), 3) for i in range(joy.get_numaxes())]
        btns = [joy.get_button(i) for i in range(joy.get_numbuttons())]
        hats = [joy.get_hat(i) for i in range(joy.get_numhats())]
        line = f"\rAxes={axes}  Btns={btns}  Hats={hats}   "
        print(line, end="", flush=True)
        time.sleep(0.05)

if __name__ == "__main__":
    print_raw_state()