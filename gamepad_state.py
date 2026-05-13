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
# Layout détecté sur ce système (Linux / SDL Raw — variante B) :
#   0=Croix(X)  1=Rond(O)  2=Carré  3=Triangle
#   4=L2(digital)  5=R2(digital)  6=L1  7=R1
#   8=Share/Create  9=Options  10=L3  11=R3  12=PS  13=Pavé tactile
#
# Note : L2/R2 analogiques sont lus sur les axes 2 et 5 (_poll_joystick).
#        Les boutons digitaux 4/5 sont ignorés (redondants avec les axes).
# ─────────────────────────────────────────────────────────────────────────────
_PS_BTN_MAP = {
    0:  0x1000,  # Croix (X)     → A
    1:  0x2000,  # Rond  (O)     → B
    2:  0x4000,  # Carré         → X
    3:  0x8000,  # Triangle      → Y
    8:  0x0020,  # Share/Create  → Back
    9:  0x0010,  # Options       → Start
    10: 0x0040,  # L3
    11: 0x0080,  # R3
    6:  0x0100,  # L1  (LB)
    7:  0x0200,  # R1  (RB)
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

def _norm_trigger(val: float) -> float:
    """
    Normalise une gâchette analogique en [0.0, 1.0].

    Deux comportements selon le driver SDL :
      • Repos à -1.0  → plage -1 … +1  →  (val + 1) / 2
      • Repos à  0.0  → plage  0 … +1  →  val  (utilisé directement)

    La branche est choisie sur le signe de val : si val < 0 le driver
    utilise bien la convention -1/+1 ; sinon on est déjà en 0/+1.
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
        # Ordre réel SDL/pygame en mode Raw (DS4/DualSense) :
        #   0=LX  1=LY  2=L2  3=RX  4=RY  5=R2
        gp.sThumbRX = int(max(-32768, min(32767,  get_ax(3) * 32767)))
        gp.sThumbRY = int(max(-32768, min(32767, -get_ax(4) * 32767)))

        # ── CORRECTIF GÂCHETTES ──────────────────────────────────────────────
        # Certains drivers renvoient -1→+1 (repos=-1), d'autres 0→+1 (repos=0).
        # _norm_trigger() gère les deux automatiquement.
        # ─────────────────────────────────────────────────────────────────────
        gp.bLeftTrigger  = int(_norm_trigger(get_ax(2)) * 255)
        gp.bRightTrigger = int(_norm_trigger(get_ax(5)) * 255)

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
