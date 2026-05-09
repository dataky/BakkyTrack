# 🎮 Template Prompt — Overlays RL Tracker (PyQt6)

Copie-colle ce bloc complet dans ton IA, puis remplace la section `[TA DEMANDE]` en bas.

---

## Contexte du projet

Je développe un tracker Rocket League en **Python / PyQt6**.  
L'application principale est `rl_tracker.py`, les widgets overlays sont dans `overlay_widgets.py`.

Les overlays sont chargés dynamiquement depuis le dossier `overlays/` comme **plugins Python**.  
Chaque plugin est un fichier `.py` indépendant qui expose :

```python
OVERLAY_NAME = "mon_overlay"          # identifiant unique (snake_case)
OVERLAY_SIZE = (largeur, hauteur)     # taille fixe en pixels
class Overlay(QWidget):               # classe principale
    def update_stats(self, d: dict, mmr_mode: str): ...
```

---

## Palette de couleurs (à respecter impérativement)

```python
C_BG    = "#0A0C10"   # fond principal
C_BG2   = "#12151C"   # fond carte
C_BG3   = "#1A1E2A"   # fond éléments
C_BLUE  = "#1A8CFF"   # bleu accent
C_ORG   = "#FF6B00"   # orange accent
C_TEXT  = "#E8ECF4"   # texte principal
C_MUTE  = "#5A6275"   # texte secondaire
C_GREEN = "#3AE08A"   # vert (victoire / positif)
C_GOLD  = "#FFD700"   # or (MMR)

# Utilisés dans les overlays "modernes" :
NEON_CYAN = "#00cfff"
WIN_GREEN = "#00e676"
LOSS_RED  = "#ff3d57"
```

---

## Dictionnaire de stats passé à `update_stats(d, mmr_mode)`

```python
d = {
    "wins":        int,    # victoires de la session
    "losses":      int,    # défaites de la session
    "total":       int,    # wins + losses
    "winrate":     int,    # pourcentage (0-100)
    "streak_val":  int,    # longueur de la streak courante
    "streak_type": str,    # "win" | "loss" | ""
    "mmr":         int | None,
    "mmr_change":  int,    # delta depuis début de session (positif ou négatif)
    "rank":        str,    # label rang ex: "Diamond II"
}

mmr_mode: str  # "both" | "mmr" | "delta"
# "both"  → afficher mmr ET delta
# "mmr"   → afficher mmr seulement
# "delta" → afficher delta seulement
```

---

## Imports disponibles dans un plugin overlay

```python
from PyQt6.QtCore    import Qt, QTimer, QRectF, QPointF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt6.QtGui import (
    QColor, QPainter, QBrush, QPen,
    QLinearGradient, QRadialGradient, QFont, QPolygonF
)
```

---

## Overlays existants (à ne pas dupliquer)

| Nom          | Taille     | Style                                  |
|--------------|------------|----------------------------------------|
| compact      | 224 × 172  | carte sombre, gradient top bleu→orange |
| banner       | 440 × 68   | bannière RL, coin coupé, barre winrate |
| banner_classic | 380 × 62 | bannière horizontale simple 5 blocs    |
| pill         | 340 × 36   | capsule minimaliste défilante          |
| neon         | 260 × 140  | cyberpunk cyan, halo radial            |
| sidebar      | 108 × 260  | vertical, accent gauche bleu→orange    |
| gauge        | 200 × 200  | arc de cercle winrate, MMR au centre   |
| ticker       | 640 × 26   | bande TV défilante                     |
| glassmorph   | 300 × 110  | glassmorphism, verre dépoli            |
| scoreboard   | 380 × 88   | Blue vs Orange, fond split             |
| hud          | 320 × 130  | militaire FPS, coins coupés, scan CRT  |
| vivid        | 400 × 78   | gradient saturé, 5 blocs colorés       |

---

## Conventions techniques des plugins

- La classe `Overlay` hérite de `QWidget`
- Appeler `self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)` si fond transparent
- Implémenter `paintEvent` pour tout dessin custom (fond, arcs, polygones…)
- Barre winrate calculée : `winrate = wins / (wins + losses)` → float 0.0 à 1.0
- `self._winrate` stocke ce float, `self.update()` force le repaint
- Ne jamais importer `overlay_widgets` depuis un plugin — l'overlay est standalone

---

## Structure minimale d'un plugin

```python
# overlays/mon_overlay.py

from PyQt6.QtCore    import Qt, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui     import QPainter, QColor, QBrush

OVERLAY_NAME = "mon_overlay"
OVERLAY_SIZE = (300, 100)

C_BG2   = "#12151C"
C_TEXT  = "#E8ECF4"
C_GREEN = "#3AE08A"
C_ORG   = "#FF6B00"

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(*OVERLAY_SIZE)
        self._winrate = 0.5
        self._build()

    def _build(self):
        # Construction des labels Qt ici
        pass

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Dessin custom ici
        p.end()

    def update_stats(self, d: dict, mmr_mode: str = "both"):
        wins   = d.get("wins", 0)
        losses = d.get("losses", 0)
        total  = wins + losses
        self._winrate = (wins / total) if total > 0 else 0.5
        self.update()  # repaint
        # Mise à jour des labels ici
```

---

## [TA DEMANDE]

> Remplace ce bloc par ta demande précise. Exemples :
>
> - "Crée un nouvel overlay appelé `retro` (320×120), style terminal années 80, texte vert phosphorescent sur fond noir, qui affiche MMR / W / L / Streak."
>
> - "Modifie l'overlay `neon` pour ajouter le rang sous le MMR."
>
> - "Ajoute une animation de pulsation sur la barre winrate de l'overlay `banner` quand la streak est ≥ 3."
>
> - "Crée un overlay `minimal` ultra-épuré (200×40) avec seulement W-L et le delta MMR en blanc sur fond noir semi-transparent."

