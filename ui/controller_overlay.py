"""ui/controller_overlay.py — ControllerOverlay + _CtrlCanvas."""
import sys, math
from PyQt6.QtCore    import Qt, QPointF, QRectF, QTimer
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtGui     import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont
from style import C_MUTE, C_BLUE, C_ORG, C_TEXT

# ── Import de get_gamepad_state ──────────────────────────────────────────
import os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from gamepad_state import get_gamepad_state
# ────────────────────────────────────────────────────────────────────────


class _CtrlCanvas(QWidget):
    W    = 280
    H_BG = 200
    H_TR = 176
    _LB = 0x0100; _RB = 0x0200
    _A  = 0x1000; _B  = 0x2000; _X  = 0x4000; _Y  = 0x8000

    def __init__(self, mode="with_bg"):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._mode  = mode; self._state = None; self._update_size()

    def _update_size(self):
        h = self.H_BG if self._mode == "with_bg" else self.H_TR
        self.setFixedSize(self.W, h)

    def set_mode(self, mode):
        self._mode = mode; self._update_size(); self.update()

    def set_state(self, s):
        self._state = s; self.update()

    def _top(self):
        return 28 if self._mode == "with_bg" else 4

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height(); top = self._top()
        if self._mode == "with_bg":
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(34,36,46,240)))
            p.drawRoundedRect(0,0,W,H,8,8)
            font_t = QFont(); font_t.setPointSize(8); font_t.setWeight(QFont.Weight.Bold)
            p.setFont(font_t); p.setPen(QColor(190,193,205))
            p.drawText(QRectF(0,0,W-28,24), Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter, "Controller Overlay")
            p.setPen(QColor(120,125,140)); font_x = QFont(); font_x.setPointSize(8); p.setFont(font_x)
            p.drawText(QRectF(W-24,0,20,24), Qt.AlignmentFlag.AlignCenter, "✕")
            p.setPen(QPen(QColor(50,54,68),1)); p.drawLine(0,24,W,24)
        if self._state is None:
            font_n = QFont(); font_n.setPointSize(9); p.setFont(font_n); p.setPen(QColor(C_MUTE))
            p.drawText(QRectF(0,top,W,H-top), Qt.AlignmentFlag.AlignCenter, "Aucune manette détectée"); p.end(); return
        gp = self._state.Gamepad; btns = gp.wButtons
        lt = gp.bLeftTrigger/255.0; rt = gp.bRightTrigger/255.0
        lx = gp.sThumbLX/32768.0; ly = -gp.sThumbLY/32768.0
        rw, rh = 90, 22; lx0 = 12; rx0 = W-12-rw
        self._draw_btn_rect(p, lx0, top, "LT", lt, analog=True)
        self._draw_btn_rect(p, lx0, top+28, "LB", bool(btns & self._LB), analog=False)
        self._draw_btn_rect(p, rx0, top, "RT", rt, analog=True)
        self._draw_btn_rect(p, rx0, top+28, "RB", bool(btns & self._RB), analog=False)
        stick_cx = lx0+rw//2; stick_cy = top+28+rh+10+46
        self._draw_stick(p, stick_cx, stick_cy, lx, ly, R=46)
        abxy_cx = rx0+rw//2; abxy_cy = stick_cy
        self._draw_abxy(p, abxy_cx, abxy_cy, btns); p.end()

    def _draw_btn_rect(self, p, x, y, label, value, analog):
        rw, rh = 90, 22
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(55,58,72)))
        p.drawRoundedRect(QRectF(x,y,rw,rh),4,4)
        fill = float(value) if analog else (1.0 if value else 0.0)
        if fill > 0.02:
            fill_w = max(6.0, rw*fill)
            col = QColor("#4a9eff") if analog else QColor(200,205,220)
            p.setBrush(QBrush(col)); p.drawRoundedRect(QRectF(x,y,fill_w,rh),4,4)
        fn = QFont(); fn.setPointSize(8); fn.setWeight(QFont.Weight.Bold); p.setFont(fn)
        pressed = fill > 0.05; p.setPen(QColor(255,255,255) if pressed else QColor(155,160,175))
        p.drawText(QRectF(x,y,rw,rh), Qt.AlignmentFlag.AlignCenter, label)

    def _draw_stick(self, p, cx, cy, dx, dy, R=46):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(18,20,28,255)))
        p.drawEllipse(QPointF(cx,cy),R,R)
        p.setPen(QPen(QColor(65,70,88),2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx,cy),R,R)
        p.setPen(QPen(QColor(50,56,74),1))
        p.drawLine(QPointF(cx-R+4,cy), QPointF(cx+R-4,cy))
        p.drawLine(QPointF(cx,cy-R+4), QPointF(cx,cy+R-4))
        DEAD = 0.1; travel = R-14; mag = math.hypot(dx,dy)
        if mag <= DEAD: ux, uy = 0.0, 0.0
        else: m = min(mag,1.0); nm = (m-DEAD)/(1.0-DEAD); s = nm/mag; ux, uy = dx*s, dy*s
        moving = mag > DEAD; px = cx+ux*travel; py = cy+uy*travel
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(0,0,0,70)))
        p.drawEllipse(QPointF(px+1,py+2),16,16)
        ball_col = QColor("#5ab4ff") if moving else QColor(110,118,145)
        p.setBrush(QBrush(ball_col)); p.setPen(QPen(QColor(180,185,200,80),1))
        p.drawEllipse(QPointF(px,py),16,16)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(QColor(255,255,255,45)))
        p.drawEllipse(QPointF(px-4,py-4),6,6)

    def _draw_abxy(self, p, cx, cy, btns):
        D = 30; R = 15
        layout = [("Y", self._Y, 0, -D, "#FFD700"), ("B", self._B, D, 0, "#FF3D57"),
                  ("A", self._A, 0, D, "#3AE08A"), ("X", self._X, -D, 0, "#1A8CFF")]
        fn = QFont(); fn.setPointSize(8); fn.setWeight(QFont.Weight.Black); p.setFont(fn)
        for label, mask, ox, oy, color in layout:
            pressed = bool(btns & mask); bx = cx+ox; by = cy+oy; col = QColor(color)
            p.setPen(Qt.PenStyle.NoPen)
            if pressed:
                h_col = QColor(color); h_col.setAlpha(60); p.setBrush(QBrush(h_col))
                p.drawEllipse(QPointF(bx,by), R+6, R+6); p.setBrush(QBrush(col))
            else:
                tint = QColor(color); tint.setAlpha(40); p.setBrush(QBrush(tint))
            p.setPen(QPen(col,1.5)); p.drawEllipse(QPointF(bx,by), R, R)
            p.setPen(QColor(255,255,255,255 if pressed else 210) if pressed else col)
            p.drawText(QRectF(bx-R,by-R,R*2,R*2), Qt.AlignmentFlag.AlignCenter, label)


class ControllerOverlay(QMainWindow):
    def __init__(self, mode="with_bg"):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool | Qt.WindowType.BypassWindowManagerHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._canvas = _CtrlCanvas(mode); self.setCentralWidget(self._canvas)
        self.setFixedSize(self._canvas.width(), self._canvas.height())
        self._drag_pos = None
        self._canvas.mousePressEvent = self._mp; self._canvas.mouseMoveEvent = self._mm
        self._poll_timer = QTimer(self); self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(16)
        self._top_timer = QTimer(self); self._top_timer.timeout.connect(self._enforce_topmost)
        self._top_timer.start(2000)

    def _mp(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _mm(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def showEvent(self, e):
        super().showEvent(e); self._enforce_topmost()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right()-self.width()-20, screen.bottom()-self.height()-60)

    def _enforce_topmost(self):
        if sys.platform != "win32" or not self.isVisible(): return
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0003)
            GWL_EXSTYLE = -20
            ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | 0x00080000 | 0x08000000 | 0x00000008)
        except Exception: pass

    def _poll(self):
        state = get_gamepad_state(0); self._canvas.set_state(state)

    def set_mode(self, mode):
        self._canvas.set_mode(mode); self.setFixedSize(self._canvas.width(), self._canvas.height())