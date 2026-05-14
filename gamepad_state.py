# gamepad_state.py
import ctypes, sys, os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# ── Structures XInput ────────────────────────────────────────────────────────

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

# ── 1. XInput (Windows) ──────────────────────────────────────────────────────

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
    return st if _xinput.XInputGetState(user_index, ctypes.byref(st)) == 0 else None

# ── 2. pygame SDL2 Controller ────────────────────────────────────────────────

try:
    import pygame as _pg
    from pygame._sdl2 import controller as _sdl2ctrl
    _HAS_SDL2 = True
except ImportError:
    _pg = _sdl2ctrl = None
    _HAS_SDL2 = False

_initialized  = False
_cached_ctrl  = None

# Constantes SDL2 (valeurs enum SDL_GameControllerButton / Axis)
_CB = dict(A=0, B=1, X=2, Y=3,
           BACK=4, GUIDE=5, START=6,
           L3=7, R3=8,
           LB=9, RB=10,
           DUP=11, DDOWN=12, DLEFT=13, DRIGHT=14)

_CA = dict(LX=0, LY=1, RX=2, RY=3, LT=4, RT=5)

# Masques XInput émulés
_BTN_MASKS = {
    _CB["DUP"]:   0x0001, _CB["DDOWN"]: 0x0002,
    _CB["DLEFT"]: 0x0004, _CB["DRIGHT"]:0x0008,
    _CB["BACK"]:  0x0020, _CB["START"]: 0x0010,
    _CB["L3"]:    0x0040, _CB["R3"]:    0x0080,
    _CB["LB"]:    0x0100, _CB["RB"]:    0x0200,
    _CB["GUIDE"]: 0x0400,
    _CB["A"]:     0x1000, _CB["B"]:     0x2000,
    _CB["X"]:     0x4000, _CB["Y"]:     0x8000,
}


def _init():
    global _initialized
    if _initialized or not _HAS_SDL2:
        return _HAS_SDL2
    try:
        _pg.init()
        _pg.joystick.init()
        _sdl2ctrl.init()
        _initialized = True
    except Exception:
        pass
    return _initialized


def _get_ctrl():
    """Retourne le Controller SDL2 mis en cache. Ne pompe PAS les events ici."""
    global _cached_ctrl
    if not _init():
        return None

    # Cache encore valide ?
    if _cached_ctrl is not None:
        try:
            if _cached_ctrl.attached():
                return _cached_ctrl
        except Exception:
            pass
        _cached_ctrl = None

    # Chercher une manette reconnue SDL2
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


def _poll_sdl2():
    # ── CORRECTIF CLÉ : event.pump() ICI, avant chaque lecture ──────────────
    # Sans ça, SDL2 ne met pas à jour l'état des boutons/axes entre deux appels.
    # Le relâchement d'un bouton n'était donc jamais détecté.
    try:
        _pg.event.pump()
    except Exception:
        pass
    # ─────────────────────────────────────────────────────────────────────────

    ctrl = _get_ctrl()
    if ctrl is None:
        return None

    st = XINPUT_STATE()
    gp = st.Gamepad

    # Boutons
    w = 0
    for btn, mask in _BTN_MASKS.items():
        try:
            if ctrl.get_button(btn):
                w |= mask
        except Exception:
            _cached_ctrl = None   # force ré-init au prochain appel
            return None
    gp.wButtons = w

    # Axes
    def ax(i):
        try:
            return ctrl.get_axis(i)
        except Exception:
            return 0

    # Sticks : SDL2 renvoie -32768…+32767, Y inversé (SDL haut = négatif)
    gp.sThumbLX =  ax(_CA["LX"])
    gp.sThumbLY = -ax(_CA["LY"])
    gp.sThumbRX =  ax(_CA["RX"])
    gp.sThumbRY = -ax(_CA["RY"])

    # Gâchettes : SDL2 Controller renvoie 0…+32767
    gp.bLeftTrigger  = int(max(0, ax(_CA["LT"])) * 255 // 32767)
    gp.bRightTrigger = int(max(0, ax(_CA["RT"])) * 255 // 32767)

    st.dwPacketNumber = 1
    return st

# ── 3. Fallback joystick brut (manettes non reconnues par SDL2 Controller) ───
# Mappings officiels pygame 2 :
# PS4 — 6 axes, 16 boutons, 0 hat  (ref: pygame.org/docs/ref/joystick.html)
# PS5 — 6 axes, 13 boutons, 1 hat

_PS4_MAP = {
    0:0x1000, 1:0x2000, 2:0x4000, 3:0x8000,  # Croix Rond Carré Triangle
    4:0x0020, 5:0x0400, 6:0x0010,             # Share PS Options
    7:0x0040, 8:0x0080,                        # L3 R3
    9:0x0100, 10:0x0200,                       # L1 R1
    11:0x0001,12:0x0002,13:0x0004,14:0x0008,  # D-pad (boutons PS4)
    15:0x0800,                                 # Touchpad
}

_PS5_MAP = {
    0:0x1000, 1:0x2000, 2:0x4000, 3:0x8000,  # Croix Rond Carré Triangle
    4:0x0100, 5:0x0200,                        # L1 R1
    # 6=L2dig 7=R2dig ignorés (redondants axes)
    8:0x0020, 9:0x0010, 10:0x0400,            # Create Options PS
    11:0x0040, 12:0x0080,                      # L3 R3
}

_fb_joy = None
_fb_cnt = 0

def _get_joy_fb():
    global _fb_joy, _fb_cnt
    if _pg is None:
        return None
    n = _pg.joystick.get_count()
    if n == 0:
        _fb_joy = None; return None
    if _fb_joy is None or n != _fb_cnt:
        try:
            j = _pg.joystick.Joystick(0); j.init()
            _fb_joy = j; _fb_cnt = n
        except Exception:
            _fb_joy = None
    return _fb_joy


def _norm_trig(v):
    return (v + 1.0) / 2.0 if v < 0.0 else v


def _poll_fallback():
    # event.pump() ici aussi pour le fallback
    try:
        _pg.event.pump()
    except Exception:
        pass

    joy = _get_joy_fb()
    if joy is None:
        return None

    name   = joy.get_name().lower()
    is_ps5 = "dualsense" in name or "wireless controller" in name
    bmap   = _PS5_MAP if is_ps5 else _PS4_MAP
    use_hat= is_ps5

    st = XINPUT_STATE()
    gp = st.Gamepad
    w  = 0
    nb = joy.get_numbuttons()

    for idx, mask in bmap.items():
        if idx < nb and joy.get_button(idx):
            w |= mask

    if use_hat and joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        if hy ==  1: w |= 0x0001
        if hy == -1: w |= 0x0002
        if hx == -1: w |= 0x0004
        if hx ==  1: w |= 0x0008

    gp.wButtons = w

    def ax(i): return joy.get_axis(i) if i < joy.get_numaxes() else 0.0
    gp.sThumbLX = int(max(-32768, min(32767,  ax(0)*32767)))
    gp.sThumbLY = int(max(-32768, min(32767, -ax(1)*32767)))
    n = joy.get_numaxes()
    if n >= 6:
        gp.sThumbRX      = int(max(-32768, min(32767,  ax(3)*32767)))
        gp.sThumbRY      = int(max(-32768, min(32767, -ax(4)*32767)))
        gp.bLeftTrigger  = int(_norm_trig(ax(2))*255)
        gp.bRightTrigger = int(_norm_trig(ax(5))*255)
    elif n >= 4:
        gp.sThumbRX = int(max(-32768, min(32767,  ax(2)*32767)))
        gp.sThumbRY = int(max(-32768, min(32767, -ax(3)*32767)))

    st.dwPacketNumber = 1
    return st

# ── API publique ─────────────────────────────────────────────────────────────

def get_gamepad_state(user_index=0):
    if sys.platform == "win32":
        st = _poll_xinput(user_index)
        if st is not None:
            return st
    st = _poll_sdl2()
    if st is not None:
        return st
    return _poll_fallback()

# ── Diagnostic ───────────────────────────────────────────────────────────────

def print_raw_state():
    import time
    if not _init() and _pg is None:
        print("pygame non disponible."); return
    print("En attente d'une manette… (Ctrl+C pour quitter)\n")
    last_name = None
    while True:
        # IMPORTANT : pump avant toute lecture
        try: _pg.event.pump()
        except Exception: pass

        ctrl = _get_ctrl()
        joy  = _get_joy_fb()

        if ctrl is None and joy is None:
            print("\r[aucune manette]", end="", flush=True)
            time.sleep(0.2); continue

        name = (_sdl2ctrl.name_forindex(0) or "?") if ctrl else joy.get_name()
        mode = "sdl2_controller" if ctrl else "joystick_fallback"
        if name != last_name:
            print(f"\n>>> '{name}'  mode={mode}")
            last_name = name

        if ctrl:
            labels = ["A","B","X","Y","BACK","GUIDE","START",
                      "L3","R3","LB","RB","↑","↓","←","→"]
            pressed = [labels[i] for i in range(15) if ctrl.get_button(i)]
            axes = {
                "LX": round(ctrl.get_axis(0)/32767,2),
                "LY": round(ctrl.get_axis(1)/32767,2),
                "RX": round(ctrl.get_axis(2)/32767,2),
                "RY": round(ctrl.get_axis(3)/32767,2),
                "LT": round(ctrl.get_axis(4)/32767,2),
                "RT": round(ctrl.get_axis(5)/32767,2),
            }
            print(f"\rAppuyés={pressed}  Axes={axes}   ", end="", flush=True)
        else:
            axes = [round(joy.get_axis(i),3) for i in range(joy.get_numaxes())]
            btns = [joy.get_button(i) for i in range(joy.get_numbuttons())]
            hats = [joy.get_hat(i) for i in range(joy.get_numhats())]
            print(f"\rAxes={axes}  Btns={btns}  Hats={hats}   ", end="", flush=True)
        time.sleep(0.05)

if __name__ == "__main__":
    print_raw_state()
