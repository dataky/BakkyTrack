from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath
from PyQt6.QtCore import Qt, QRectF
from style import C_MUTE, C_TEXT, C_BLUE, C_BG2, lbl, card

class MMRGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.history = []

    def set_data(self, history):
        self.history = list(reversed(history)) # Chronological order
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # Background
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 0))
        
        if not self.history:
            painter.setPen(QColor(C_MUTE))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Pas assez de données pour le graphique")
            painter.end()
            return
            
        if len(self.history) == 1:
            painter.setPen(QColor(C_MUTE))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Jouez un autre match pour voir la courbe")
            painter.end()
            return

        # Prepare data
        mmr_values = [m.get("mmr_end", 0) for m in self.history if m.get("mmr_end")]
        if not mmr_values:
            painter.end()
            return
            
        min_mmr = min(mmr_values) - 15
        max_mmr = max(mmr_values) + 15
        diff = max(1, max_mmr - min_mmr)
        
        # Grid and axes
        margin_x = 40
        margin_y = 20
        graph_w = w - margin_x * 2
        graph_h = h - margin_y * 2
        
        painter.setPen(QPen(QColor(C_MUTE), 1, Qt.PenStyle.DashLine))
        # Draw min, mid, max lines
        for val in [min_mmr, (min_mmr+max_mmr)//2, max_mmr]:
            y = margin_y + graph_h - ((val - min_mmr) / diff) * graph_h
            painter.drawLine(margin_x, int(y), w - margin_x, int(y))
            painter.setPen(QColor(C_TEXT))
            painter.drawText(5, int(y) + 4, str(int(val)))
            painter.setPen(QPen(QColor(C_MUTE), 1, Qt.PenStyle.DashLine))

        # Draw path
        path = QPainterPath()
        point_radius = 4
        
        step_x = graph_w / (len(mmr_values) - 1)
        
        points_to_draw = []
        for i, val in enumerate(mmr_values):
            x = margin_x + i * step_x
            y = margin_y + graph_h - ((val - min_mmr) / diff) * graph_h
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
            points_to_draw.append((x, y, self.history[i].get("result") == "win"))

        # Line
        painter.setPen(QPen(QColor(C_BLUE), 2))
        painter.drawPath(path)
        
        # Points
        for x, y, is_win in points_to_draw:
            clr = QColor("#00e676") if is_win else QColor("#ff3d57")
            painter.setBrush(clr)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRectF(x - point_radius, y - point_radius, point_radius*2, point_radius*2))
            
        painter.end()

class GraphTab(QWidget):
    def __init__(self, app_ref):
        super().__init__()
        self.app = app_ref
        self._build()
        self.app.signals.match_result.connect(self._refresh)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(lbl("ÉVOLUTION DU MMR", C_MUTE, 9, True))
        header.addStretch()
        
        self._pl_btns = {}
        for key in ("3v3", "2v2", "1v1"):
            b = QPushButton(key)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedWidth(40)
            b.setFixedHeight(26)
            b.setCheckable(True)
            if key == "3v3": b.setChecked(True)
            b.clicked.connect(lambda _, k=key: self._set_playlist(k))
            header.addWidget(b)
            self._pl_btns[key] = b
            
        self._update_btn_styles()
        root.addLayout(header)
        
        self.graph_card = card()
        gl = QVBoxLayout(self.graph_card)
        gl.setContentsMargins(8, 12, 8, 12)
        
        self.graph = MMRGraphWidget()
        gl.addWidget(self.graph)
        
        root.addWidget(self.graph_card)
        root.addStretch()

    def _set_playlist(self, key):
        for k, b in self._pl_btns.items():
            b.setChecked(k == key)
        self._update_btn_styles()
        self._refresh()

    def _update_btn_styles(self):
        for k, b in self._pl_btns.items():
            active = b.isChecked()
            b.setStyleSheet(
                f"QPushButton{{background:{C_BLUE if active else C_BG2};"
                f"color:{C_TEXT if active else C_MUTE};border:none;border-radius:4px;"
                f"font-size:10px;font-weight:700;}}"
                + ("" if active else f"QPushButton:hover{{color:{C_TEXT};}}")
            )

    def _refresh(self, _=None):
        if not hasattr(self.app, 'db'):
            return
        
        pl_key = "3v3"
        for k, b in self._pl_btns.items():
            if b.isChecked():
                pl_key = k
                break
                
        playlist_name = {"1v1": "Ranked Duel 1v1", "2v2": "Ranked Doubles 2v2", "3v3": "Ranked Standard 3v3"}.get(pl_key, pl_key)
        
        history = self.app.db.get_history(limit=20)
        filtered_history = [h for h in history if h.get("playlist") == playlist_name]
        
        self.graph.set_data(filtered_history)
