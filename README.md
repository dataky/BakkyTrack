# 🚀 BakkyTrack

**Tracker Rocket League avec overlay en temps réel, automation et sons personnalisés.**  
Compatible avec l'API BakkesMod v2 (StatsAPI + WebSocket).

---

## ✨ Fonctionnalités

| Onglet | Description |
|--------|-------------|
| 📊 **Tracker** | Suivi W/L, MMR et série de victoires/défaites en temps réel |
| 👥 **Joueurs** | Liste des joueurs du match en cours — clic pour ouvrir leur profil tracker.network |
| 🖥️ **Overlay** | Overlay in-game (mode compact ou bannière), affichage MMR configurable |
| 🤖 **Auto** | Skip replay automatique, auto-queue, retour en freeplay — touches configurables |
| 🔊 **Sons** | Sons personnalisés sur les événements (but marqué/encaissé, crossbar, démo, save épique…) |
| ⚙️ **Paramètres** | Plateforme, pseudo, port StatsAPI, thèmes |

### Overlay OBS (HTTP Server)
BakkyTrack expose un serveur HTTP local sur le **port 49124** pour les overlays de stream :

- `GET /stats` — snapshot JSON des stats actuelles
- `GET /events` — flux SSE en temps réel (Server-Sent Events)
- `GET /<nom>.html` — sert n'importe quel fichier HTML du dossier `overlays/`

---

## 📦 Prérequis

- **Python 3.10+**
- **BakkesMod** avec le plugin *StatsAPI* activé (port par défaut `49123`)
- **Windows** (certaines fonctionnalités utilisent l'API Win32)

---

## 🔧 Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/<ton-pseudo>/bakkytrack.git
cd bakkytrack

# 2. Installer les dépendances
pip install PyQt6 websocket-client pyautogui pygame vgamepad certifi

# 3. Lancer l'application
python rl_tracker.py
```

> **Note :** `pyautogui`, `pygame`, `vgamepad` et `websocket-client` sont optionnels.  
> L'application se lance et désactive gracieusement les fonctionnalités manquantes.

---

## 🗂️ Structure du projet

```
bakkytrack/
├── rl_tracker.py          # Application principale + logique BakkesMod
├── overlay_widgets.py     # Tous les widgets overlay (PyQt6)
├── config.json            # Généré automatiquement au premier lancement
├── overlays/              # Fichiers HTML servis à OBS
│   ├── overlay.html
│   └── compact.py         # Overlay compact (chargé dynamiquement)
├── themes/                # Fonds SVG des overlays (victory, defeat, neon…)
│   ├── rl_classic.svg
│   ├── victory.svg
│   ├── defeat.svg
│   ├── neon.svg
│   └── dark_minimal.svg
└── all rank/              # Icônes de rang (0.png → 23.png)
```

---

## ⚙️ Configuration

Le fichier `config.json` est créé automatiquement. Les principaux réglages :

```json
{
  "platform":         "epic",
  "username":         "TonPseudo",
  "statsapi_port":    49123,
  "overlay_mode":     "compact",
  "mmr_display_mode": "both",
  "auto_skip_replay": false,
  "auto_queue":       false,
  "sound_goal_scored": false
}
```

| Clé | Valeurs | Description |
|-----|---------|-------------|
| `platform` | `epic` `steam` `ps4` `xbox` `switch` | Plateforme de jeu |
| `overlay_mode` | `compact` `banner` | Style de l'overlay in-game |
| `mmr_display_mode` | `both` `mmr` `rank` | Ce qui s'affiche dans l'overlay |
| `auto_skip_replay` | `true/false` | Skip automatique des replays |
| `skip_replay_key` | `key:k` | Touche pour skip replay |

---

## 🎮 Overlays OBS

1. Dans OBS, ajouter une source **Navigateur**
2. URL : `http://localhost:49124/overlay.html`
3. Placer n'importe quel fichier HTML dans le dossier `overlays/` pour le servir automatiquement

Les overlays reçoivent les stats via **SSE** (`/events`) pour des mises à jour en temps réel sans polling.

---

## 🔌 Dépendances

| Package | Usage | Requis |
|---------|-------|--------|
| `PyQt6` | Interface graphique | ✅ Oui |
| `websocket-client` | Connexion BakkesMod WebSocket | Recommandé |
| `pyautogui` | Automation clavier (auto-skip, queue…) | Optionnel |
| `pygame` | Lecture des sons personnalisés | Optionnel |
| `vgamepad` | Émulation de manette virtuelle | Optionnel |
| `certifi` | Certificats SSL (fix PyInstaller) | Optionnel |

---

## 🏗️ Build exécutable (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name BakkyTrack rl_tracker.py
```

L'exécutable généré détecte automatiquement son répertoire pour charger `config.json`, les thèmes et les overlays.

---

## 📄 Licence

MIT — libre d'utilisation et de modification.
