# gamepad_state.py — Lecture manette : XInput (Xbox) puis SDL Gamepad (PlayStation, etc.)
import ctypes
import sys

# Même disposition mémoire que XINPUT_GAMEPAD / XINPUT_STATE (Windows SDK)


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


def _poll_xinput(user_index: int = 0):
    if not _xinput:
        return None
    st = XINPUT_STATE()
    if _xinput.XInputGetState(user_index, ctypes.byref(st)) != 0:
        return None
    return st


try:
    import pygame as _pygame
except ImportError:
    _pygame = None

_sdl_ctrl = None
_sdl_inited = False
_sdl_pkt = 0


def _sdl_controller_module():
    if _pygame is None:
        return None
    try:
        from pygame._sdl2 import controller as sdlc
        return sdlc
    except Exception:
        return None


def _ensure_sdl():
    global _sdl_inited
    sdlc = _sdl_controller_module()
    if sdlc is None:
        return None
    if not _sdl_inited:
        try:
            _pygame.init()
            sdlc.init()
            _sdl_inited = True
        except Exception:
            return None
    return sdlc


# Indices SDL_GameControllerButton → masques XInput (wButtons)
_SDL_BTN_TO_XINPUT = (
    (0, 0x1000),   # A  (Sud / Croix PS)
    (1, 0x2000),   # B  (Est / Cercle)
    (2, 0x4000),   # X  (Ouest / Carré)
    (3, 0x8000),   # Y  (Nord / Triangle)
    (4, 0x0020),   # Back / Share
    (6, 0x0010),   # Start / Options
    (7, 0x0040),   # L3
    (8, 0x0080),   # R3
    (9, 0x0100),   # LB / L1
    (10, 0x0200),  # RB / R1
    (11, 0x0001),  # D-pad haut
    (12, 0x0002),
    (13, 0x0004),
    (14, 0x0008),
)


def _clamp_i16(v: int) -> int:
    if v > 32767:
        return 32767
    if v < -32768:
        return -32768
    return v


def _trigger_byte(axis_val: int) -> int:
    v = max(0, min(32767, axis_val))
    return int(v * 255 / 32767)


def _poll_sdl():
    """Premier gamepad SDL, mappé sur la disposition Xbox (compatible touches XInput)."""
    global _sdl_ctrl, _sdl_pkt
    sdlc = _ensure_sdl()
    if not sdlc:
        return None
    try:
        n = sdlc.get_count()
    except Exception:
        return None
    if n <= 0:
        _sdl_ctrl = None
        return None

    if _sdl_ctrl is not None:
        try:
            if hasattr(_sdl_ctrl, "attached") and not _sdl_ctrl.attached:
                _sdl_ctrl = None
        except Exception:
            _sdl_ctrl = None

    if _sdl_ctrl is None:
        try:
            _sdl_ctrl = sdlc.Controller(0)
        except Exception:
            return None

    ctrl = _sdl_ctrl
    try:
        ctrl.get_button(0)
    except Exception:
        _sdl_ctrl = None
        return None

    _sdl_pkt = (_sdl_pkt + 1) & 0xFFFFFFFF
    st = XINPUT_STATE()
    st.dwPacketNumber = _sdl_pkt
    gp = st.Gamepad

    w = 0
    for bi, mask in _SDL_BTN_TO_XINPUT:
        try:
            if ctrl.get_button(bi):
                w |= mask
        except Exception:
            pass
    gp.wButtons = w

    def ax(i):
        try:
            return _clamp_i16(int(ctrl.get_axis(i)))
        except Exception:
            return 0

    gp.sThumbLX = ax(0)
    gp.sThumbLY = ax(1)
    gp.sThumbRX = ax(2)
    gp.sThumbRY = ax(3)
    gp.bLeftTrigger = _trigger_byte(ax(4))
    gp.bRightTrigger = _trigger_byte(ax(5))
    return st


def get_gamepad_state(user_index: int = 0):
    """
    État manette au format XInput.
    Essaie d'abord XInput (manette Xbox / émulation), puis SDL (DualShock, DualSense, etc.).
    """
    st = _poll_xinput(user_index)
    if st is not None:
        return st
    return _poll_sdl()
