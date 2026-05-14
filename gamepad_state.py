# gamepad_state.py
#
# IMPORTANT — intégration avec un overlay / boucle pygame existante :
#
#   Dans ta boucle principale, appelle UNE FOIS par frame :
#       gamepad_state.pump()          ← met à jour l'état SDL2
#   Puis autant de fois que tu veux :
#       st = gamepad_state.get_gamepad_state()
#
#   Si tu as déjà pygame.event.get() ou pygame.event.pump() dans ta boucle,
#   tu n'as PAS besoin d'appeler gamepad_state.pump() en plus.

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

_initialized = False
_cached_ctrl = None

# Constantes SDL2 (enum SDL_GameControllerButton / Axis)
_CB_A=0; _CB_B=1; _CB_X=2; _CB_Y=3
_CB_BACK=4; _CB_GUIDE=5; _CB_START=6
_CB_L3=7; _CB_R3=8; _CB_LB=9; _CB_RB=10
_CB_DUP=11; _CB_DDOWN=12; _CB_DLEFT=13; _CB_DRIGHT=14

_CA_LX=0; _CA_LY=1; _CA_RX=2; _CA_RY=3; _CA_LT=4; _CA_RT=5

_BTN_MASKS = {
    _CB_DUP:   0x0001, _CB_DDOWN: 0x0002,
    _CB_DLEFT: 0x0004, _CB_DRIGHT:0x0008,
    _CB_BACK:  0x0020, _CB_START: 0x0010,
    _CB_L3:    0x0040, _CB_R3:    0x0080,
    _CB_LB:    0x0100, _CB_RB:    0x0200,
    _CB_GUIDE: 0x0400,
    _CB_A:     0x1000, _CB_B:     0x2000,
    _CB_X:     0x4000, _CB_Y:     0x8000,
}

# Mappings additionnels pour SDL2 (PS4/PS5) – au cas où la base interne est vide
_PS_SDL2_MAPPINGS = [
    # DualShock 4 (USB / Bluetooth)
    "030000004c050000cc09000000000000,Sony DualShock 4,a:b0,b:b1,back:b8,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b12,leftshoulder:b4,leftstick:b10,lefttrigger:a3,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b11,righttrigger:a4,rightx:a2,righty:a5,start:b9,x:b2,y:b3,platform:Windows",
    # DualSense
    "030000004c0500002669000000000000,Sony DualSense,a:b0,b:b1,back:b8,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b12,leftshoulder:b4,leftstick:b10,lefttrigger:a3,leftx:a0,lefty:a1,rightshoulder:b5,rightstick:b11,righttrigger:a4,rightx:a2,righty:a5,start:b9,x:b2,y:b3,platform:Windows",
]

def _load_ps_mappings_sdl2():
    """Ajoute les mappings PS4/PS5 à la base SDL2 si elle existe."""
    if not _HAS_SDL2 or _sdl2ctrl is None:
        return
    try:
        mapping_db = _sdl2ctrl.ControllerMappingDB()
        for mapping in _PS_SDL2_MAPPINGS:
            mapping_db.add_mapping(mapping)
    except Exception:
        pass

def _init():
    global _initialized
    if _initialized or not _HAS_SDL2:
        return _HAS_SDL2
    try:
        _pg.init()
        _pg.joystick.init()
        _sdl2ctrl.init()
        _load_ps_mappings_sdl2()   # ← ajout des mappings PS manquants
        _initialized = True
    except Exception:
        pass
    return _initialized

def pump():
    """
    Met à jour l'état SDL2 des manettes.

    Appelle cette fonction UNE FOIS par frame dans ta boucle principale,
    AVANT d'appeler get_gamepad_state().

    Si ta boucle appelle déjà pygame.event.get() ou pygame.event.pump(),
    tu n'as PAS besoin d'appeler cette fonction.

    NE PAS appeler depuis un thread secondaire.
    """
    if _pg is not None:
        try:
            _pg.event.pump()
        except Exception:
            pass

def _get_ctrl():
    """Cache du Controller SDL2. Ne touche PAS aux events."""
    global _cached_ctrl
    if not _init():
        return None

    if _cached_ctrl is not None:
        try:
            if _cached_ctrl.attached():
                return _cached_ctrl
        except Exception:
            pass
        _cached_ctrl = None

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
    ctrl = _get_ctrl()
    if ctrl is None:
        return None

    st = XINPUT_STATE()
    gp = st.Gamepad

    w = 0
    for btn, mask in _BTN_MASKS.items():
        try:
            if ctrl.get_button(btn):
                w |= mask
        except Exception:
            global _cached_ctrl
            _cached_ctrl = None
            return None
    gp.wButtons = w

    def ax(i):
        try:    return ctrl.get_axis(i)
        except: return 0

    gp.sThumbLX =  ax(_CA_LX)
    gp.sThumbLY = -ax(_CA_LY)   # Y inversé
    gp.sThumbRX =  ax(_CA_RX)
    gp.sThumbRY = -ax(_CA_RY)

    gp.bLeftTrigger  = int(max(0, ax(_CA_LT)) * 255 // 32767)
    gp.bRightTrigger = int(max(0, ax(_CA_RT)) * 255 // 32767)

    st.dwPacketNumber = 1
    return st

# ── 3. Fallback joystick brut (CORRIGÉ pour PS4/PS5) ────────────────────────

_fb_joy = None
_fb_cnt = 0

def _get_joy_fb():
    global _fb_joy, _fb_cnt
    if _pg is None:
        return None
    n = _pg.joystick.get_count()
    if n == 0:
        _fb_joy = None
        return None
    if _fb_joy is None or n != _fb_cnt:
        try:
            j = _pg.joystick.Joystick(0)
            j.init()
            _fb_joy = j
            _fb_cnt = n
        except Exception:
            _fb_joy = None
    return _fb_joy

def _norm_trig(v):
    # v ∈ [-1, 1] pour les gâchettes en mode DirectInput
    # Sur PS4/PS5, les gâchettes sont sur [0, 1] mais parfois centrées à -1
    if v < 0.0:
        return (v + 1.0) / 2.0
    return v

def _poll_fallback():
    """
    Version corrigée pour les manettes PlayStation.
    Utilise les mappings réels de pygame.joystick (index de boutons standard).
    """
    joy = _get_joy_fb()
    if joy is None:
        return None

    name = joy.get_name().lower()
    # Détection étendue des manettes Sony
    is_ps = any(term in name for term in (
        "wireless controller", "dualshock", "dualsense", "playstation",
        "sony", "ps4", "ps5"
    ))

    if not is_ps:
        # Si ce n'est pas une manette Sony, on garde l'ancien comportement (très limité)
        # mais on ne va pas l'améliorer ici.
        return None

    # Mapping des boutons pygame.joystick (index) → masques XINPUT
    # Basé sur les tests réels avec DS4 et DualSense en mode DirectInput
    # (sans pilote Xbox)
    PS_BUTTON_MAP = {
        0: 0x1000,   # X (croix)   → A
        1: 0x2000,   # Circle      → B
        2: 0x4000,   # Square      → X
        3: 0x8000,   # Triangle    → Y
        4: 0x0100,   # L1          → LB
        5: 0x0200,   # R1          → RB
        6: 0x0040,   # L2          → L3 (attention: ce n'est pas idéal, mais faute de mieux)
        7: 0x0080,   # R2          → R3
        8: 0x0020,   # Share       → Back
        9: 0x0010,   # Options     → Start
        10: 0x0400,  # PS button   → Guide
        11: 0x0040,  # L3 (stick gauche enfoncé) → L3 (réel)
        12: 0x0080,  # R3 (stick droit enfoncé)  → R3 (réel)
        13: 0x0000,  # Touchpad (pas de correspondance XInput)
    }

    # Pour le D-Pad, beaucoup de manettes PS le présentent comme un "hat"
    # Sinon, les boutons individuels (14,15,16,17) peuvent exister.
    # On va gérer les deux.

    nb = joy.get_numbuttons()
    w = 0

    # Boutons standards
    for idx, mask in PS_BUTTON_MAP.items():
        if idx < nb and joy.get_button(idx):
            w |= mask

    # D-Pad via hat (le plus fiable)
    if joy.get_numhats() > 0:
        hx, hy = joy.get_hat(0)
        if hy ==  1: w |= 0x0001  # up
        if hy == -1: w |= 0x0002  # down
        if hx == -1: w |= 0x0004  # left
        if hx ==  1: w |= 0x0008  # right

    # Fallback : si le hat ne donne rien, on cherche les boutons du D-Pad
    # (généralement indices 14-17 sur DS4)
    if not (w & 0x000F):
        dpad_map = {14:0x0001, 15:0x0002, 16:0x0004, 17:0x0008}
        for idx, mask in dpad_map.items():
            if idx < nb and joy.get_button(idx):
                w |= mask

    st = XINPUT_STATE()
    gp = st.Gamepad
    gp.wButtons = w

    # Axes
    num_axes = joy.get_numaxes()
    def ax(i):
        return joy.get_axis(i) if i < num_axes else 0.0

    # Stick gauche (généralement axes 0,1)
    gp.sThumbLX = int(max(-32768, min(32767,  ax(0) * 32767)))
    gp.sThumbLY = int(max(-32768, min(32767, -ax(1) * 32767)))  # Y inversé

    # Stick droit (axes 2,3 sur DS4/DS5)
    if num_axes >= 4:
        gp.sThumbRX = int(max(-32768, min(32767,  ax(2) * 32767)))
        gp.sThumbRY = int(max(-32768, min(32767, -ax(3) * 32767)))
    else:
        gp.sThumbRX = 0
        gp.sThumbRY = 0

    # Gâchettes : sur DS4/DS5 ce sont les axes 4 et 5 (en mode DirectInput)
    # Valeurs brutes: L2 = axe 4, R2 = axe 5, intervalle [0,1] (parfois [-1,1])
    lt_val = 0.0
    rt_val = 0.0
    if num_axes >= 5:
        lt_val = _norm_trig(ax(4))
        rt_val = _norm_trig(ax(5))
    gp.bLeftTrigger  = int(max(0, min(255, lt_val * 255)))
    gp.bRightTrigger = int(max(0, min(255, rt_val * 255)))

    st.dwPacketNumber = 1
    return st

# ── API publique ─────────────────────────────────────────────────────────────

def get_gamepad_state(user_index=0):
    """
    Retourne XINPUT_STATE ou None si aucune manette connectée.

    Assure-toi que pump() (ou pygame.event.get/pump) est appelé
    dans ta boucle principale AVANT cet appel.
    """
    if sys.platform == "win32":
        st = _poll_xinput(user_index)
        if st is not None:
            return st
    st = _poll_sdl2()
    if st is not None:
        return st
    return _poll_fallback()

# ── Diagnostic (optionnel, amélioré pour afficher les noms réels) ────────────

def print_raw_state():
    import time
    if not _init() and _pg is None:
        print("pygame non disponible.")
        return
    print("En attente d'une manette… (Ctrl+C pour quitter)\n")
    last_name = None
    while True:
        pump()
        ctrl = _get_ctrl()
        joy  = _get_joy_fb()

        if ctrl is None and joy is None:
            print("\r[aucune manette]", end="", flush=True)
            time.sleep(0.2)
            continue

        name = None
        mode = ""
        if ctrl:
            try:
                name = _sdl2ctrl.name_forindex(0)
            except:
                name = "Unknown SDL2 Controller"
            mode = "sdl2_controller"
        elif joy:
            name = joy.get_name()
            mode = "joystick_fallback"

        if name != last_name:
            print(f"\n>>> '{name}'  mode={mode}")
            last_name = name

        # Affichage compact pour le diagnostic
        if ctrl:
            labels = ["A","B","X","Y","BACK","GUIDE","START","L3","R3","LB","RB","↑","↓","←","→"]
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
