# gamepad_state.py
#
# IMPORTANT — intégration avec un overlay / boucle pygame existante :
#
#   Dans ta boucle principale, appelle UNE FOIS par frame :
#       gamepad_state.pump()          ← met à jour l'état pygame (fallback joystick)
#   Puis autant de fois que tu veux :
#       st = gamepad_state.get_gamepad_state()
#
#   Si tu utilises uniquement le backend dualsense-controller (DualSense PS5),
#   pump() n'est pas nécessaire — la lib tourne dans son propre thread.
#
#   Si tu as déjà pygame.event.get() ou pygame.event.pump() dans ta boucle,
#   tu n'as PAS besoin d'appeler gamepad_state.pump() en plus.

import ctypes, sys, os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# ── 0. dualsense-controller (PS5 DualSense natif — priorité maximale) ────────
#
#   pip install dualsense-controller
#
#   Ce backend lit directement le HID USB/Bluetooth de la DualSense sans
#   passer par XInput ni SDL2. Il fonctionne sur Windows, macOS et Linux
#   (udev rules requises sur Linux : voir README du projet).
#
#   Mapping utilisé : Mapping.NORMALIZED
#       sticks   → float  -1.0 .. 1.0   (Y déjà inversé par la lib)
#       triggers → float   0.0 .. 1.0
#       boutons  → bool    .pressed
#
#   La lib tourne dans un thread interne ; on lit juste la dernière valeur
#   disponible à chaque frame — aucun appel bloquant.

try:
    from dualsense_controller import DualSenseController as _DSC
    from dualsense_controller.api.DualSenseController import Mapping as _DSCMapping
    _HAS_DSC = True
except (ImportError, OSError):
    # ImportError : dualsense-controller pas installé
    # OSError     : hidapi DLL/SO introuvable (pip install hidapi)
    _DSC = _DSCMapping = None
    _HAS_DSC = False

_dsc_instance: "_DSC | None" = None
_dsc_active   = False
import time
_dsc_last_scan_time = 0.0
_DSC_SCAN_INTERVAL = 3.0  # limit device enumeration to once every 3 seconds if not active

def _dsc_init() -> bool:
    """Tente d'activer la DualSense via dualsense-controller. Idempotent et bridé dans le temps."""
    global _dsc_instance, _dsc_active, _dsc_last_scan_time
    if not _HAS_DSC:
        return False
    if _dsc_active and _dsc_instance is not None and _dsc_instance.is_active:
        return True
    
    # Throttle scan rate to prevent high CPU / micro-stutters from continuous USB/HID device enumeration
    now = time.time()
    if now - _dsc_last_scan_time < _DSC_SCAN_INTERVAL:
        return False
    _dsc_last_scan_time = now

    try:
        devs = _DSC.enumerate_devices()
        if not devs:
            return False
        if _dsc_instance is not None:
            try:
                _dsc_instance.deactivate()
            except Exception:
                pass
        _dsc_instance = _DSC(
            mapping=_DSCMapping.NORMALIZED,   # sticks -1..1, triggers 0..1
            left_joystick_deadzone=0,
            right_joystick_deadzone=0,
            left_trigger_deadzone=0,
            right_trigger_deadzone=0,
        )
        _dsc_instance.activate()
        _dsc_active = True
        return True
    except Exception:
        _dsc_instance = None
        _dsc_active   = False
        return False

def _poll_dualsense() -> "XINPUT_STATE | None":
    """
    Lit l'état courant de la DualSense via dualsense-controller et le
    retourne sous forme de XINPUT_STATE normalisé.

    Les sticks sont en float -1..1 (NORMALIZED) → convertis en int16.
    Les triggers sont en float 0..1 → convertis en uint8.
    Le Y des sticks est déjà inversé par la lib (haut = positif).
    """
    if not _dsc_init():
        return None
    dc = _dsc_instance
    if dc is None or not dc.is_active:
        return None
    try:
        st = XINPUT_STATE()
        gp = st.Gamepad

        # ── Boutons face ──────────────────────────────────────────────
        w = 0
        if dc.btn_cross.pressed:    w |= 0x1000  # A
        if dc.btn_circle.pressed:   w |= 0x2000  # B
        if dc.btn_square.pressed:   w |= 0x4000  # X
        if dc.btn_triangle.pressed: w |= 0x8000  # Y

        # ── Boutons épaules ───────────────────────────────────────────
        if dc.btn_l1.pressed:       w |= 0x0100  # LB
        if dc.btn_r1.pressed:       w |= 0x0200  # RB

        # ── Sticks (click) ────────────────────────────────────────────
        if dc.btn_l3.pressed:       w |= 0x0040  # L3
        if dc.btn_r3.pressed:       w |= 0x0080  # R3

        # ── Boutons système ───────────────────────────────────────────
        if dc.btn_create.pressed:   w |= 0x0020  # Create/Share → Back
        if dc.btn_options.pressed:  w |= 0x0010  # Options      → Start
        if dc.btn_ps.pressed:       w |= 0x0400  # PS Logo      → Guide

        # ── D-Pad ─────────────────────────────────────────────────────
        if dc.btn_up.pressed:       w |= 0x0001
        if dc.btn_down.pressed:     w |= 0x0002
        if dc.btn_left.pressed:     w |= 0x0004
        if dc.btn_right.pressed:    w |= 0x0008

        gp.wButtons = w

        # ── Sticks analogiques (NORMALIZED : -1.0 .. 1.0) ────────────
        def _stick(v: float) -> int:
            return int(max(-32768, min(32767, v * 32767)))

        lx = dc.left_stick_x.value  or 0.0
        ly = dc.left_stick_y.value  or 0.0   # déjà "haut = positif" en NORMALIZED
        rx = dc.right_stick_x.value or 0.0
        ry = dc.right_stick_y.value or 0.0

        gp.sThumbLX =  _stick(lx)
        gp.sThumbLY =  _stick(ly)   # pas de réinversion : NORMALIZED le fait
        gp.sThumbRX =  _stick(rx)
        gp.sThumbRY =  _stick(ry)

        # ── Gâchettes analogiques (NORMALIZED : 0.0 .. 1.0) ──────────
        def _trig(v: float) -> int:
            return int(max(0, min(255, (v or 0.0) * 255)))

        gp.bLeftTrigger  = _trig(dc.left_trigger.value)
        gp.bRightTrigger = _trig(dc.right_trigger.value)

        st.dwPacketNumber = 1
        return st

    except Exception:
        # Connexion perdue : on réinitialise au prochain appel
        global _dsc_active
        _dsc_active = False
        return None

def dsc_set_lightbar(r: int, g: int, b: int) -> None:
    """
    Change la couleur de la lightbar de la DualSense (0-255 par canal).
    N'a aucun effet si la manette n'est pas connectée via ce backend.
    """
    if _dsc_instance is not None and _dsc_instance.is_active:
        try:
            _dsc_instance.lightbar.set_color(r, g, b)
        except Exception:
            pass

def dsc_set_rumble(left: int, right: int) -> None:
    """
    Déclenche un retour haptique (0-255 par moteur).
    N'a aucun effet si la manette n'est pas connectée via ce backend.
    """
    if _dsc_instance is not None and _dsc_instance.is_active:
        try:
            _dsc_instance.left_rumble.set(left)
            _dsc_instance.right_rumble.set(right)
        except Exception:
            pass

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

# ── 2. pygame (joystick brut — fallback uniquement) ──────────────────────────

try:
    import pygame as _pg
    _pg.init()
    _pg.joystick.init()
    _HAS_PG = True
except ImportError:
    _pg = None
    _HAS_PG = False

def pump():
    """
    Met à jour l'état pygame des manettes (fallback joystick brut).

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

# ── 3. Fallback joystick brut ────────────────────────────────────────────────
#
# Mappings officiels pygame.joystick (source : docs pygame v2.6) :
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │  DualShock 4 — 6 axes, 16 boutons (reconnu "PS4 Controller")       │
# │  Btn  0=Cross  1=Circle  2=Square  3=Triangle                       │
# │  Btn  4=Share  5=PS  6=Options  7=L3  8=R3  9=L1  10=R1            │
# │  Btn 11=D↑  12=D↓  13=D←  14=D→  15=Touchpad                      │
# │  Axe  0=LX  1=LY  2=RX  3=RY  4=L2  5=R2                          │
# ├─────────────────────────────────────────────────────────────────────┤
# │  DualSense — 6 axes, 13 boutons, 1 hat (D-pad via hat 0)           │
# │  Btn  0=Cross  1=Circle  2=Square  3=Triangle                       │
# │  Btn  4=L1  5=R1  6=L2(digital)  7=R2(digital)                     │
# │  Btn  8=Share  9=Options  10=PS  11=L3  12=R3                      │
# │  Axe  0=LX  1=LY  2=RX  3=RY  4=L2  5=R2                          │
# └─────────────────────────────────────────────────────────────────────┘

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
    """
    Normalise une valeur de gâchette en [0, 1].
    SDL2 joystick reporte les gâchettes PS en [-1, 1] (repos = -1).
    """
    if v < 0.0:
        return (v + 1.0) / 2.0
    return v

def _poll_fallback():
    """
    Fallback joystick brut avec mappings corrects DS4 et DualSense.
    Mappings basés sur la documentation officielle pygame v2.6.
    """
    joy = _get_joy_fb()
    if joy is None:
        return None

    name = joy.get_name().lower()
    is_ps = any(term in name for term in (
        "wireless controller", "dualshock", "dualsense", "playstation",
        "sony", "ps4", "ps5", "ps4 controller"
    ))

    if not is_ps:
        return None

    # Détection DS4 vs DS5 :
    # Le DualSense se présente comme "Sony Interactive Entertainment Wireless Controller"
    # ou contient "dualsense". Le DS4 se présente comme "PS4 Controller" ou "Wireless Controller".
    is_ds5 = "dualsense" in name or ("wireless controller" in name and joy.get_numbuttons() <= 13)

    nb  = joy.get_numbuttons()
    w   = 0

    if is_ds5:
        # ── DualSense (PS5) ──────────────────────────────────────────
        # 13 boutons + 1 hat pour le D-pad
        DS5_BUTTON_MAP = {
            0:  0x1000,  # Cross     → A
            1:  0x2000,  # Circle    → B
            2:  0x4000,  # Square    → X
            3:  0x8000,  # Triangle  → Y
            4:  0x0100,  # L1        → LB
            5:  0x0200,  # R1        → RB
            # 6 = L2 digital : ignoré (géré via axe 4)
            # 7 = R2 digital : ignoré (géré via axe 5)
            8:  0x0020,  # Share     → Back
            9:  0x0010,  # Options   → Start
            10: 0x0400,  # PS        → Guide
            11: 0x0040,  # L3        → L3
            12: 0x0080,  # R3        → R3
        }
        for idx, mask in DS5_BUTTON_MAP.items():
            if idx < nb and joy.get_button(idx):
                w |= mask

        # D-pad via hat (DualSense uniquement)
        if joy.get_numhats() > 0:
            hx, hy = joy.get_hat(0)
            if hy ==  1: w |= 0x0001  # up
            if hy == -1: w |= 0x0002  # down
            if hx == -1: w |= 0x0004  # left
            if hx ==  1: w |= 0x0008  # right

    else:
        # ── DualShock 4 (PS4) ────────────────────────────────────────
        # 16 boutons, D-pad en boutons 11-14 (et parfois aussi via hat)
        DS4_BUTTON_MAP = {
            0:  0x1000,  # Cross     → A
            1:  0x2000,  # Circle    → B
            2:  0x4000,  # Square    → X
            3:  0x8000,  # Triangle  → Y
            4:  0x0020,  # Share     → Back
            5:  0x0400,  # PS        → Guide
            6:  0x0010,  # Options   → Start
            7:  0x0040,  # L3        → L3
            8:  0x0080,  # R3        → R3
            9:  0x0100,  # L1        → LB
            10: 0x0200,  # R1        → RB
            11: 0x0001,  # D↑        → DUP
            12: 0x0002,  # D↓        → DDOWN
            13: 0x0004,  # D←        → DLEFT
            14: 0x0008,  # D→        → DRIGHT
            # 15 = Touchpad — pas de correspondance XInput
        }
        for idx, mask in DS4_BUTTON_MAP.items():
            if idx < nb and joy.get_button(idx):
                w |= mask

        # Certains drivers exposent aussi le D-pad via hat (redondant mais sûr)
        if joy.get_numhats() > 0 and not (w & 0x000F):
            hx, hy = joy.get_hat(0)
            if hy ==  1: w |= 0x0001
            if hy == -1: w |= 0x0002
            if hx == -1: w |= 0x0004
            if hx ==  1: w |= 0x0008

    st = XINPUT_STATE()
    gp = st.Gamepad
    gp.wButtons = w

    # ── Axes (identiques DS4 et DS5) ─────────────────────────────────
    # Axe 0=LX  1=LY  2=RX  3=RY  4=L2  5=R2
    num_axes = joy.get_numaxes()
    def ax(i):
        return joy.get_axis(i) if i < num_axes else 0.0

    gp.sThumbLX = int(max(-32768, min(32767,  ax(0) * 32767)))
    gp.sThumbLY = int(max(-32768, min(32767, -ax(1) * 32767)))  # Y inversé

    gp.sThumbRX = int(max(-32768, min(32767,  ax(2) * 32767)))
    gp.sThumbRY = int(max(-32768, min(32767, -ax(3) * 32767)))  # Y inversé

    # Gâchettes : axes 4 (L2) et 5 (R2)
    # SDL2 joystick les reporte en [-1, 1] avec -1 = relâché, 1 = enfoncé à fond
    lt_val = _norm_trig(ax(4)) if num_axes > 4 else 0.0
    rt_val = _norm_trig(ax(5)) if num_axes > 5 else 0.0
    gp.bLeftTrigger  = int(max(0, min(255, lt_val * 255)))
    gp.bRightTrigger = int(max(0, min(255, rt_val * 255)))

    st.dwPacketNumber = 1
    return st

# ── API publique ─────────────────────────────────────────────────────────────

def get_gamepad_state(user_index=0):
    """
    Retourne XINPUT_STATE ou None si aucune manette connectée.

    Ordre de priorité des backends :
      0. dualsense-controller  — DualSense PS5 via HID natif (pip install dualsense-controller)
      1. XInput                — Windows uniquement, toutes manettes XInput
      2. Joystick brut pygame  — fallback PS4/PS5 via pygame.joystick

    Assure-toi que pump() (ou pygame.event.get/pump) est appelé
    dans ta boucle principale AVANT cet appel.
    """
    # 0. dualsense-controller (DualSense natif — multiplateforme)
    st = _poll_dualsense()
    if st is not None:
        return st
    # 1. XInput (Windows)
    if sys.platform == "win32":
        st = _poll_xinput(user_index)
        if st is not None:
            return st
    # 2. Joystick brut (fallback PS4/PS5)
    return _poll_fallback()

# ── Diagnostic ───────────────────────────────────────────────────────────────

def print_raw_state():
    import time
    if not _HAS_PG and not _HAS_DSC:
        print("Aucun backend disponible (pygame et dualsense-controller manquants).")
        return
    print("En attente d'une manette… (Ctrl+C pour quitter)\n")
    last_name = None
    while True:
        pump()

        # ── Backend 0 : dualsense-controller ──────────────────────────
        if _dsc_init() and _dsc_instance is not None and _dsc_instance.is_active:
            dc = _dsc_instance
            name = "DualSense [dualsense-controller]"
            if name != last_name:
                print(f"\n>>> '{name}'  mode=dualsense_controller")
                last_name = name
            try:
                pressed = []
                btns = {
                    "Cross": dc.btn_cross, "Circle": dc.btn_circle,
                    "Square": dc.btn_square, "Triangle": dc.btn_triangle,
                    "L1": dc.btn_l1, "R1": dc.btn_r1,
                    "L3": dc.btn_l3, "R3": dc.btn_r3,
                    "Create": dc.btn_create, "Options": dc.btn_options,
                    "PS": dc.btn_ps,
                    "↑": dc.btn_up, "↓": dc.btn_down,
                    "←": dc.btn_left, "→": dc.btn_right,
                }
                for label, btn in btns.items():
                    if btn.pressed:
                        pressed.append(label)
                axes = {
                    "LX": round(dc.left_stick_x.value or 0, 3),
                    "LY": round(dc.left_stick_y.value or 0, 3),
                    "RX": round(dc.right_stick_x.value or 0, 3),
                    "RY": round(dc.right_stick_y.value or 0, 3),
                    "LT": round(dc.left_trigger.value or 0, 3),
                    "RT": round(dc.right_trigger.value or 0, 3),
                }
                print(f"\rAppuyés={pressed}  Axes={axes}   ", end="", flush=True)
            except Exception as e:
                print(f"\r[erreur lecture DualSense: {e}]", end="", flush=True)
            time.sleep(0.05)
            continue

        # ── Backend 1/2 : XInput / joystick brut ──────────────────────
        joy = _get_joy_fb()
        if joy is None:
            print("\r[aucune manette]", end="", flush=True)
            time.sleep(0.2)
            continue

        name = joy.get_name()
        if name != last_name:
            print(f"\n>>> '{name}'  mode=joystick_fallback")
            last_name = name

        axes = [round(joy.get_axis(i), 3) for i in range(joy.get_numaxes())]
        btns = [joy.get_button(i) for i in range(joy.get_numbuttons())]
        hats = [joy.get_hat(i) for i in range(joy.get_numhats())]
        print(f"\rAxes={axes}  Btns={btns}  Hats={hats}   ", end="", flush=True)
        time.sleep(0.05)

if __name__ == "__main__":
    print_raw_state()