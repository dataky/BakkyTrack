# gamepad_state.py — Lecture manette : XInput (Xbox) puis pygame.joystick (PlayStation, etc.)
#
# Usage :
#   from gamepad_state import get_gamepad_state
#
#   st = get_gamepad_state()      # None si aucune manette
#   if st:
#       gp = st.Gamepad
#       print(gp.wButtons, gp.bLeftTrigger, gp.sThumbLX)

import ctypes
import sys


# ---------------------------------------------------------------------------
# Structures XInput (Windows SDK) — utilisées comme format de sortie commun
# ---------------------------------------------------------------------------

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons",       ctypes.c_uint16),  # Masques boutons (voir constantes XBTN_*)
        ("bLeftTrigger",   ctypes.c_uint8),   # Gâchette gauche  : 0-255
        ("bRightTrigger",  ctypes.c_uint8),   # Gâchette droite  : 0-255
        ("sThumbLX",       ctypes.c_int16),   # Stick gauche X   : -32768..+32767
        ("sThumbLY",       ctypes.c_int16),   # Stick gauche Y   : -32768..+32767
        ("sThumbRX",       ctypes.c_int16),   # Stick droit  X   : -32768..+32767
        ("sThumbRY",       ctypes.c_int16),   # Stick droit  Y   : -32768..+32767
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_uint32),
        ("Gamepad",        XINPUT_GAMEPAD),
    ]


# Masques de boutons XInput (champ wButtons)
XBTN_DPAD_UP        = 0x0001
XBTN_DPAD_DOWN      = 0x0002
XBTN_DPAD_LEFT      = 0x0004
XBTN_DPAD_RIGHT     = 0x0008
XBTN_START          = 0x0010
XBTN_BACK           = 0x0020
XBTN_LEFT_THUMB     = 0x0040
XBTN_RIGHT_THUMB    = 0x0080
XBTN_LEFT_SHOULDER  = 0x0100
XBTN_RIGHT_SHOULDER = 0x0200
XBTN_A              = 0x1000
XBTN_B              = 0x2000
XBTN_X              = 0x4000
XBTN_Y              = 0x8000


# ---------------------------------------------------------------------------
# Backend XInput (Windows — manettes Xbox ou émulation Xbox)
# ---------------------------------------------------------------------------

_xinput = None
if sys.platform == "win32":
    for _lib in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
        try:
            _xinput = getattr(ctypes.windll, _lib)
            break
        except OSError:
            pass


def _poll_xinput(user_index: int = 0):
    """Retourne un XINPUT_STATE via XInput, ou None si indisponible / manette absente."""
    if not _xinput:
        return None
    st = XINPUT_STATE()
    if _xinput.XInputGetState(user_index, ctypes.byref(st)) != 0:
        return None
    return st


# ---------------------------------------------------------------------------
# Backend pygame.joystick (DualShock 4, DualSense, Switch Pro, générique…)
# ---------------------------------------------------------------------------

try:
    import pygame as _pygame
except ImportError:
    _pygame = None

_joy_inited = False
_joy_pkt    = 0

# Correspondance index bouton pygame → masque XInput
# Disposition typique DualShock 4 / DualSense sous SDL/pygame :
#   0=Croix  1=Rond  2=Carré   3=Triangle
#   4=Share  5=PS    6=Options
#   7=L3     8=R3    9=L1     10=R1
#  11=D↑    12=D↓  13=D←    14=D→
_JOY_BTN_MAP = (
    ( 0, XBTN_A),              # Croix      → A
    ( 1, XBTN_B),              # Rond       → B
    ( 2, XBTN_X),              # Carré      → X
    ( 3, XBTN_Y),              # Triangle   → Y
    ( 4, XBTN_BACK),           # Share      → Back
    ( 6, XBTN_START),          # Options    → Start
    ( 7, XBTN_LEFT_THUMB),     # L3
    ( 8, XBTN_RIGHT_THUMB),    # R3
    ( 9, XBTN_LEFT_SHOULDER),  # L1         → LB
    (10, XBTN_RIGHT_SHOULDER), # R1         → RB
    (11, XBTN_DPAD_UP),
    (12, XBTN_DPAD_DOWN),
    (13, XBTN_DPAD_LEFT),
    (14, XBTN_DPAD_RIGHT),
)

# Index des axes pygame pour DualShock 4 / DualSense :
#   0=LX  1=LY  2=RX  3=RY  4=L2  5=R2
# Les triggers SDL sont dans [-1.0, +1.0] : -1.0 = relâché, +1.0 = enfoncé.
_AXIS_LX = 0
_AXIS_LY = 1
_AXIS_RX = 2
_AXIS_RY = 3
_AXIS_L2 = 4
_AXIS_R2 = 5


def _ensure_joy() -> bool:
    """Initialise pygame + joystick une seule fois. Retourne False si pygame absent."""
    global _joy_inited
    if _pygame is None:
        return False
    if not _joy_inited:
        try:
            if not _pygame.get_init():
                _pygame.init()
            _pygame.joystick.init()
            _joy_inited = True
        except Exception:
            return False
    return True


def _clamp_i16(v: int) -> int:
    return max(-32768, min(32767, v))


def _float_to_i16(f: float) -> int:
    """Axe pygame [-1.0, +1.0] → entier signé 16 bits."""
    return _clamp_i16(int(f * 32767))


def _trigger_to_byte(f: float) -> int:
    """
    Trigger SDL [-1.0 relâché … +1.0 enfoncé] → octet 0-255.
    La correction +1/2 est indispensable car SDL initialise les triggers à -1.0.
    """
    normalized = max(0.0, min(1.0, (f + 1.0) / 2.0))
    return int(normalized * 255)


def _poll_joystick(user_index: int = 0):
    """Lit la manette via pygame.joystick et renvoie un XINPUT_STATE synthétique."""
    global _joy_pkt
    if not _ensure_joy():
        return None

    try:
        _pygame.event.pump()
        count = _pygame.joystick.get_count()
    except Exception:
        return None

    if count <= user_index:
        return None

    try:
        joy = _pygame.joystick.Joystick(user_index)
        if not joy.get_init():
            joy.init()
    except Exception:
        return None

    _joy_pkt = (_joy_pkt + 1) & 0xFFFFFFFF
    st = XINPUT_STATE()
    st.dwPacketNumber = _joy_pkt
    gp = st.Gamepad

    # --- Boutons ---
    num_btns = joy.get_numbuttons()
    w = 0
    for bi, mask in _JOY_BTN_MAP:
        try:
            if bi < num_btns and joy.get_button(bi):
                w |= mask
        except Exception:
            pass
    gp.wButtons = w

    # --- Axes ---
    num_axes = joy.get_numaxes()

    def ax(i: int) -> float:
        try:
            return joy.get_axis(i) if i < num_axes else 0.0
        except Exception:
            return 0.0

    gp.sThumbLX      = _float_to_i16(ax(_AXIS_LX))
    gp.sThumbLY      = _float_to_i16(ax(_AXIS_LY))
    gp.sThumbRX      = _float_to_i16(ax(_AXIS_RX))
    gp.sThumbRY      = _float_to_i16(ax(_AXIS_RY))
    gp.bLeftTrigger  = _trigger_to_byte(ax(_AXIS_L2))
    gp.bRightTrigger = _trigger_to_byte(ax(_AXIS_R2))

    return st


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def get_gamepad_state(user_index: int = 0):
    """
    Retourne l'état de la manette au format XINPUT_STATE.

    Priorité :
      1. XInput natif (Windows, manettes Xbox ou mode émulation Xbox)
      2. pygame.joystick (DualShock 4, DualSense, Switch Pro, manettes génériques)

    Retourne None si aucune manette n'est connectée ou si pygame n'est pas installé.

    Exemple :
        st = get_gamepad_state()
        if st:
            gp = st.Gamepad
            if gp.wButtons & XBTN_A:
                print("Bouton A / Croix pressé")
            print(f"Stick gauche X : {gp.sThumbLX}")
            print(f"Gâchette gauche : {gp.bLeftTrigger}")
    """
    st = _poll_xinput(user_index)
    if st is not None:
        return st
    return _poll_joystick(user_index)


def is_button_pressed(state: XINPUT_STATE, button_mask: int) -> bool:
    """Raccourci : teste un masque de bouton sur un état déjà récupéré."""
    if state is None:
        return False
    return bool(state.Gamepad.wButtons & button_mask)


def get_left_stick(state: XINPUT_STATE) -> tuple[float, float]:
    """Retourne (x, y) du stick gauche normalisé dans [-1.0, +1.0]."""
    if state is None:
        return (0.0, 0.0)
    gp = state.Gamepad
    return (gp.sThumbLX / 32767.0, gp.sThumbLY / 32767.0)


def get_right_stick(state: XINPUT_STATE) -> tuple[float, float]:
    """Retourne (x, y) du stick droit normalisé dans [-1.0, +1.0]."""
    if state is None:
        return (0.0, 0.0)
    gp = state.Gamepad
    return (gp.sThumbRX / 32767.0, gp.sThumbRY / 32767.0)


def get_triggers(state: XINPUT_STATE) -> tuple[float, float]:
    """Retourne (gauche, droite) des gâchettes normalisées dans [0.0, 1.0]."""
    if state is None:
        return (0.0, 0.0)
    gp = state.Gamepad
    return (gp.bLeftTrigger / 255.0, gp.bRightTrigger / 255.0)