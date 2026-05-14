# gamepad_state.py — Version SDL2 Controller (mapping universel PS4/PS5/Xbox)
#
# Stratégie :
#   1. Windows  → XInput (Xbox natif et émulation)
#   2. Partout  → pygame._sdl2.controller  (API haut-niveau, mapping normalisé)
#      SDL2 traduit automatiquement les indices bruts PS4/PS5/Switch → nommage Xbox.
#      Plus aucun mapping à la main : un seul code pour toutes les manettes.
#   3. Fallback → pygame.joystick  (si la manette n'est pas reconnue par SDL2 Controller)
#
# Boutons SDL2 Controller  →  masque XInput émulé :
#   A (Croix)          → 0x1000    B (Rond)           → 0x2000
#   X (Carré)          → 0x4000    Y (Triangle)        → 0x8000
#   BACK (Share/Create)→ 0x0020    START (Options)     → 0x0010
#   GUIDE (PS)         → 0x0400   (bit étendu)
#   LEFTSHOULDER (L1)  → 0x0100   RIGHTSHOULDER (R1)  → 0x0200
#   LEFTSTICK  (L3)    → 0x0040   RIGHTSTICK  (R3)    → 0x0080
#   DPAD_UP            → 0x0001   DPAD_DOWN           → 0x0002
#   DPAD_LEFT          → 0x0004   DPAD_RIGHT          → 0x0008
#   L2/R2 analogiques  → bLeftTrigger / bRightTrigger  (0..255)

import ctypes
import sys
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# ══════════════════════════════════════════════════════════════════════════════
# Structures XInput
# ══════════════════════════════════════════════════════════════════════════════

class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons",      ctypes.c_uint16),
        ("bLeftTrigger",  ctypes.c_uint8),
        ("bRightTrigger", ctypes.c_uint8),
        ("sThumbLX",      ctypes.c_int16),
        ("sThumbLY",      ctypes.c_int16),
        ("sThumbRX",      ctypes.c_int16),
        ("sThumbRY",      ctypes.c_int16),
    ]

class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.c_uint32),
        ("Gamepad",        XINPUT_GAMEPAD),
    ]

# ══════════════════════════════════════════════════════════════════════════════
# 1. XInput (Windows / Xbox)
# ══════════════════════════════════════════════════════════════════════════════

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
    if _xinput.XInputGetState(user_index, ctypes.byref(st)) != 0:
        return None
    return st

# ══════════════════════════════════════════════════════════════════════════════
# 2. pygame._sdl2.controller  (API haut-niveau — mapping normalisé)
# ══════════════════════════════════════════════════════════════════════════════

try:
    import pygame as _pg
    from pygame._sdl2 import controller as _sdl2ctrl
    _HAS_SDL2_CTRL = True
except ImportError:
    _pg = None
    _sdl2ctrl = None
    _HAS_SDL2_CTRL = False

_ctrl_initialized = False
_cached_ctrl      = None

# ── Constantes SDL2 Controller (entiers, compatibles pygame 2.x) ─────────────
# Boutons
_CB_A             = 0   # Croix  / A
_CB_B             = 1   # Rond   / B
_CB_X             = 2   # Carré  / X
_CB_Y             = 3   # Triangle / Y
_CB_BACK          = 4   # Share / Create / View
_CB_GUIDE         = 5   # Bouton PS / Home / Xbox
_CB_START         = 6   # Options / Menu
_CB_LEFTSTICK     = 7   # L3
_CB_RIGHTSTICK    = 8   # R3
_CB_LEFTSHOULDER  = 9   # L1 / LB
_CB_RIGHTSHOULDER = 10  # R1 / RB
_CB_DPAD_UP       = 11
_CB_DPAD_DOWN     = 12
_CB_DPAD_LEFT     = 13
_CB_DPAD_RIGHT    = 14
_CB_MAX           = 15  # sentinelle

# Axes
_CA_LEFTX         = 0
_CA_LEFTY         = 1
_CA_RIGHTX        = 2
_CA_RIGHTY        = 3
_CA_TRIGLEFT      = 4   # L2  (0 … +32767)
_CA_TRIGRIGHT     = 5   # R2  (0 … +32767)

# Table bouton SDL2 → masque XInput émulé
_CTRL_BTN_MAP = {
    _CB_A:             0x1000,
    _CB_B:             0x2000,
    _CB_X:             0x4000,
    _CB_Y:             0x8000,
    _CB_BACK:          0x0020,
    _CB_START:         0x0010,
    _CB_GUIDE:         0x0400,
    _CB_LEFTSTICK:     0x0040,
    _CB_RIGHTSTICK:    0x0080,
    _CB_LEFTSHOULDER:  0x0100,
    _CB_RIGHTSHOULDER: 0x0200,
    _CB_DPAD_UP:       0x0001,
    _CB_DPAD_DOWN:     0x0002,
    _CB_DPAD_LEFT:     0x0004,
    _CB_DPAD_RIGHT:    0x0008,
}


def _ensure_ctrl():
    global _ctrl_initialized
    if not _HAS_SDL2_CTRL or _pg is None:
        return False
    if not _ctrl_initialized:
        try:
            _pg.init()
            _pg.joystick.init()
            _sdl2ctrl.init()
            _ctrl_initialized = True
        except Exception:
            return False
    return True


def _get_ctrl():
    """Retourne un Controller SDL2 mis en cache, ou None."""
    global _cached_ctrl

    if not _ensure_ctrl():
        return None

    try:
        _pg.event.pump()
    except Exception:
        pass

    # Vérifier la validité du cache
    if _cached_ctrl is not None:
        try:
            if _cached_ctrl.attached():
                return _cached_ctrl
        except Exception:
            pass
        _cached_ctrl = None

    # Chercher la première manette reconnue comme Controller SDL2
    for i in range(_pg.joystick.get_count()):
        try:
            if not _sdl2ctrl.is_controller(i):
                continue
            joy  = _pg.joystick.Joystick(i)
            ctrl = _sdl2ctrl.Controller.from_joystick(joy)
            if ctrl.attached():
                _cached_ctrl = ctrl
                return ctrl
        except Exception:
            continue

    return None


def _poll_sdl2_controller():
    ctrl = _get_ctrl()
    if ctrl is None:
        return None

    st = XINPUT_STATE()
    gp = st.Gamepad

    # Boutons
    w = 0
    for btn_id, mask in _CTRL_BTN_MAP.items():
        try:
            if ctrl.get_button(btn_id):
                w |= mask
        except Exception:
            pass
    gp.wButtons = w

    # Sticks  (SDL2 Controller : -32768 … +32767)
    def ax(i):
        try:
            return ctrl.get_axis(i)
        except Exception:
            return 0

    gp.sThumbLX =  ax(_CA_LEFTX)
    gp.sThumbLY = -ax(_CA_LEFTY)   # Y inversé : SDL haut=-32768, XInput haut=+32767
    gp.sThumbRX =  ax(_CA_RIGHTX)
    gp.sThumbRY = -ax(_CA_RIGHTY)

    # Gâchettes (SDL2 Controller : 0 … +32767)
    gp.bLeftTrigger  = int(max(0, ax(_CA_TRIGLEFT))  * 255 // 32767)
    gp.bRightTrigger = int(max(0, ax(_CA_TRIGRIGHT)) * 255 // 32767)

    st.dwPacketNumber = 1
    return st

# ══════════════════════════════════════════════════════════════════════════════
# 3. Fallback : pygame.joystick brut
#    Utilisé uniquement si SDL2 Controller ne reconnaît pas la manette.
#    Mappings officiels pygame 2 :
#      PS4 Raw — 6 axes, 16 boutons, 0 hat
#      PS5 Raw — 6 axes, 13 boutons, 1 hat
#    Ref : https://www.pygame.org/docs/ref/joystick.html
# ══════════════════════════════════════════════════════════════════════════════

_PS4_FALLBACK = {
    0:  0x1000,  # Croix
    1:  0x2000,  # Rond
    2:  0x4000,  # Carré
    3:  0x8000,  # Triangle
    4:  0x0020,  # Share
    5:  0x0400,  # PS
    6:  0x0010,  # Options
    7:  0x0040,  # L3
    8:  0x0080,  # R3
    9:  0x0100,  # L1
    10: 0x0200,  # R1
    11: 0x0001,  # D-pad Haut  (bouton en mode PS4)
    12: 0x0002,  # D-pad Bas
    13: 0x0004,  # D-pad Gauche
    14: 0x0008,  # D-pad Droite
    15: 0x0800,  # Touchpad
}

_PS5_FALLBACK = {
    0:  0x1000,  # Croix
    1:  0x2000,  # Rond
    2:  0x4000,  # Carré
    3:  0x8000,  # Triangle
    4:  0x0100,  # L1
    5:  0x0200,  # R1
    # 6=L2 digital, 7=R2 digital → redondants avec axes, ignorés
    8:  0x0020,  # Create
    9:  0x0010,  # Options
    10: 0x0400,  # PS
    11: 0x0040,  # L3
    12: 0x0080,  # R3
}

_cached_joy_fb    = None
_cached_joy_count = 0

def _get_joy_fallback():
    global _cached_joy_fb, _cached_joy_count
    if _pg is None:
        return None
    count = _pg.joystick.get_count()
    if count == 0:
        _cached_joy_fb = None
        return None
    if _cached_joy_fb is None or count != _cached_joy_count:
        try:
            joy = _pg.joystick.Joystick(0)
            joy.init()
            _cached_joy_fb    = joy
            _cached_joy_count = count
        except Exception:
            _cached_joy_fb = None
    return _cached_joy_fb


def _norm_trigger(val: float) -> float:
    return (val + 1.0) / 2.0 if val < 0.0 else val


def _poll_joystick_fallback():
    try:
        _pg.event.pump()
    except Exception:
        pass
    joy = _get_joy_fallback()
    if joy is None:
        return None

    name    = joy.get_name().lower()
    is_ps5  = "dualsense" in name or "wireless controller" in name
    btn_map = _PS5_FALLBACK if is_ps5 else _PS4_FALLBACK
    use_hat = is_ps5

    st = XINPUT_STATE()
    gp = st.Gamepad
    w  = 0
    nb = joy.get_numbuttons()

    for idx, mask in btn_map.items():
        if idx < nb and joy.get_button(idx):
            w |= mask

    if use_hat and joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        if hy ==  1: w |= 0x0001
        if hy == -1: w |= 0x0002
        if hx == -1: w |= 0x0004
        if hx ==  1: w |= 0x0008

    gp.wButtons = w

    def ax(i):
        return joy.get_axis(i) if i < joy.get_numaxes() else 0.0

    gp.sThumbLX = int(max(-32768, min(32767,  ax(0) * 32767)))
    gp.sThumbLY = int(max(-32768, min(32767, -ax(1) * 32767)))
    n = joy.get_numaxes()
    if n >= 6:
        gp.sThumbRX      = int(max(-32768, min(32767,  ax(3) * 32767)))
        gp.sThumbRY      = int(max(-32768, min(32767, -ax(4) * 32767)))
        gp.bLeftTrigger  = int(_norm_trigger(ax(2)) * 255)
        gp.bRightTrigger = int(_norm_trigger(ax(5)) * 255)
    elif n >= 4:
        gp.sThumbRX = int(max(-32768, min(32767,  ax(2) * 32767)))
        gp.sThumbRY = int(max(-32768, min(32767, -ax(3) * 32767)))

    st.dwPacketNumber = 1
    return st

# ══════════════════════════════════════════════════════════════════════════════
# API publique
# ══════════════════════════════════════════════════════════════════════════════

def get_gamepad_state(user_index=0):
    """
    Retourne un XINPUT_STATE ou None si aucune manette n'est connectée.
    Ordre de priorité :
      1. XInput        (Windows — Xbox et manettes émulées)
      2. SDL2 Controller (PS4, PS5, Switch, Xbox sur Linux/Mac — mapping normalisé)
      3. Joystick brut  (fallback officiel pygame 2 pour PS4/PS5)
    """
    if sys.platform == "win32":
        st = _poll_xinput(user_index)
        if st is not None:
            return st

    st = _poll_sdl2_controller()
    if st is not None:
        return st

    return _poll_joystick_fallback()

# ══════════════════════════════════════════════════════════════════════════════
# Outil de diagnostic
# ══════════════════════════════════════════════════════════════════════════════

def print_raw_state():
    """
    Boucle de debug en temps réel.
    Affiche le mode actif, le nom de la manette, et toutes les valeurs brutes.
    Utilisation :  python gamepad_state.py
    """
    import time
    if not _ensure_ctrl() and _pg is None:
        print("pygame non disponible."); return

    print("En attente d'une manette… (Ctrl+C pour quitter)\n")
    last_name = None

    while True:
        try:
            _pg.event.pump()
        except Exception:
            pass

        ctrl = _get_ctrl()
        joy  = _get_joy_fallback()

        if ctrl is None and joy is None:
            print("\r  [aucune manette]", end="", flush=True)
            time.sleep(0.2)
            continue

        if ctrl is not None:
            mode = "sdl2_controller (normalisé)"
            name = _sdl2ctrl.name_forindex(0) or "?"
        else:
            mode = "joystick fallback (brut)"
            name = joy.get_name()

        if name != last_name:
            print(f"\n>>> Manette : '{name}'")
            print(f"    Mode    : {mode}")
            if ctrl is not None:
                print("    Boutons : A=Croix B=Rond X=Carré Y=Triangle")
                print("              BACK=Share/Create START=Options GUIDE=PS")
                print("              LB=L1 RB=R1 L3=stick-gauche R3=stick-droit")
                print("              DPAD_UP/DOWN/LEFT/RIGHT = D-pad")
            last_name = name

        if ctrl is not None:
            btn_names = ["A","B","X","Y","BACK","GUIDE","START",
                         "L3","R3","LB","RB","↑","↓","←","→"]
            pressed = [btn_names[i] for i in range(_CB_MAX) if ctrl.get_button(i)]
            axes    = {
                "LX":  round(ctrl.get_axis(_CA_LEFTX)  / 32767, 2),
                "LY":  round(ctrl.get_axis(_CA_LEFTY)  / 32767, 2),
                "RX":  round(ctrl.get_axis(_CA_RIGHTX) / 32767, 2),
                "RY":  round(ctrl.get_axis(_CA_RIGHTY) / 32767, 2),
                "L2":  round(ctrl.get_axis(_CA_TRIGLEFT)  / 32767, 2),
                "R2":  round(ctrl.get_axis(_CA_TRIGRIGHT) / 32767, 2),
            }
            print(f"\rAppuyés={pressed}  Axes={axes}   ", end="", flush=True)
        else:
            axes = [round(joy.get_axis(i), 3) for i in range(joy.get_numaxes())]
            btns = [joy.get_button(i) for i in range(joy.get_numbuttons())]
            hats = [joy.get_hat(i)    for i in range(joy.get_numhats())]
            print(f"\rAxes={axes}  Btns={btns}  Hats={hats}   ", end="", flush=True)

        time.sleep(0.05)


if __name__ == "__main__":
    print_raw_state()
