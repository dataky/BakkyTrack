# 🚀 BakkyTrack

**Companion Rocket League avec overlay in-game, suivi MMR, automation et sons personnalisés.**  
Compatible BakkesMod v2 — StatsAPI + WebSocket.

---

## ✨ Fonctionnalités

### Onglets principaux

| Onglet | Description |
|--------|-------------|
| 📊 **Stats** | Suivi W/L, MMR et série de victoires/défaites en temps réel |
| 👥 **Match** | Liste des joueurs du match en cours — clic pour ouvrir leur profil tracker.network |
| 🖥 **Overlay** | Overlay in-game multi-styles, affichage MMR configurable (raccourci clavier ou bouton manette) |
| ⚡ **Auto** | Skip replay automatique, auto-queue, retour en freeplay — touches configurables |
| 🔊 **Sons** | Sons personnalisés sur les événements (but marqué/encaissé, crossbar, démo, save épique…) |
| ⚙ **Options** | Plateforme, pseudo, ports, thème d'arrière-plan, mode streamer |

### Overlays in-game

**Overlay principal (hold-to-show)** — affiché en maintenant une touche clavier ou un bouton manette, avec 12 styles visuels :

`Compact` · `Bannière` · `Bannière Classic` · `Pill` · `Neon` · `Sidebar` · `Gauge` · `Ticker` · `Glassmorphism` · `Scoreboard` · `HUD` · `Vivid`

**Overlay Tab MMR** — affiche le MMR des joueurs du match pendant la partie (peak optionnel, playlists 1v1 / 2v2 / 3v3 ou meilleure).

**Overlay résultat** — s'affiche automatiquement à la fin de chaque partie avec un thème SVG : `auto` · `victory` · `defeat` · `neon` · `dark_minimal` · `rl_classic`.

**Overlay joueurs** — fenêtre flottante indépendante listant tous les joueurs du match avec leur MMR.

**Overlay manette** — représentation visuelle en temps réel des inputs (deux modes : avec fond / transparent). Compatible Xbox (XInput) et PlayStation (DualShock / DualSense via SDL).

### Mode Streamer

Barre dédiée activable depuis les options — permet de couper le son système pendant un stream, de masquer les infos sensibles et de gérer les overlays sans quitter le jeu.

### Serveur OBS (HTTP)

BakkyTrack expose un serveur HTTP local sur le **port 49124** pour les overlays de stream :

| Endpoint | Description |
|----------|-------------|
| `GET /stats` | Snapshot JSON des stats actuelles |
| `GET /events` | Flux SSE temps réel (Server-Sent Events) |
| `GET /<nom>.html` | Sert tout fichier HTML depuis le dossier `overlays/` |

---

## 📦 Prérequis

- **Python 3.10+**
- **Windows** (l'overlay manette et les automations utilisent des API Win32/XInput)

---

## 🔧 Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/<ton-pseudo>/bakkytrack.git
cd bakkytrack

# 2. Installer les dépendances
pip install PyQt6 websocket-client pyautogui pygame vgamepad certifi

# 3. Lancer
python rl_tracker.py
```

> `pyautogui`, `pygame`, `vgamepad`, `websocket-client` et `certifi` sont **optionnels** —  
> l'application démarre et désactive gracieusement les fonctionnalités manquantes.

---

## 🗂 Structure du projet

```
bakkytrack/
├── rl_tracker.py          # Application principale + logique BakkesMod
├── overlay_widgets.py     # Widgets overlay (PyQt6) — styles, overlays flottants
├── gamepad_state.py       # Lecture manette : XInput (Xbox) + SDL (PlayStation)
├── config.json            # Généré automatiquement au premier lancement
├── overlays/              # Fichiers HTML servis à OBS
│   └── overlay.html
├── themes/                # Fonds SVG de l'application et des overlays résultat
│   ├── rl_classic.svg
│   ├── victory.svg
│   ├── defeat.svg
│   ├── neon.svg
│   └── dark_minimal.svg
└── all rank/              # Icônes de rang (0.png → 23.png)
```

---

## ⚙ Configuration

`config.json` est créé automatiquement au premier lancement. Principaux réglages :

```json
{
  "platform":                    "epic",
  "username":                    "TonPseudo",
  "statsapi_port":               49123,
  "overlay_mode":                "compact",
  "mmr_display_mode":            "both",
  "overlay_hotkey_type":         "key",
  "overlay_hotkey_key":          "key:tab",
  "overlay_hotkey_controller_btn": 0,
  "tab_rank_mode":               "2v2",
  "tab_show_peak":               true,
  "controller_overlay_enabled":  false,
  "controller_overlay_mode":     "with_bg",
  "result_overlay_enabled":      true,
  "result_overlay_theme":        "auto",
  "auto_skip_replay":            false,
  "auto_queue":                  false,
  "auto_freeplay":               false,
  "streamer_mode":               false,
  "sound_goal_scored":           false
}
```

| Clé | Valeurs | Description |
|-----|---------|-------------|
| `platform` | `epic` `steam` `ps4` `xbox` `switch` | Plateforme de jeu |
| `overlay_mode` | `compact` `banner` `banner_classic` `pill` `neon` `sidebar` `gauge` `ticker` `glassmorphism` `scoreboard` `hud` `vivid` | Style de l'overlay in-game |
| `mmr_display_mode` | `both` `mmr` `rank` | Contenu affiché dans l'overlay |
| `overlay_hotkey_type` | `key` `controller` | Type de raccourci pour l'overlay |
| `tab_rank_mode` | `1v1` `2v2` `3v3` `best` | Playlist affichée dans l'overlay Tab |
| `controller_overlay_mode` | `with_bg` `transparent` | Style de l'overlay manette |
| `result_overlay_theme` | `auto` `victory` `defeat` `neon` `dark_minimal` `rl_classic` | Thème SVG de fin de partie |

---

## 🎮 Raccourcis overlay

La touche de l'overlay peut être une touche clavier **ou** un bouton manette (Xbox / PlayStation), capturée directement depuis l'interface via un dialog de bind.

Par défaut : **Tab** (maintien) pour l'overlay principal.

---

## 📺 Overlays OBS

1. Dans OBS, ajouter une source **Navigateur**
2. URL : `http://localhost:49124/overlay.html`
3. Tout fichier HTML déposé dans `overlays/` est automatiquement accessible

Les overlays reçoivent les mises à jour via **SSE** (`/events`) — pas de polling nécessaire.

---

## 🎮 Support manette

BakkyTrack lit les inputs manette via deux backends complémentaires :

- **XInput** (Windows) — manettes Xbox et tout périphérique en émulation XInput
- **SDL via pygame** — DualShock 4, DualSense, et autres manettes non-XInput

Le backend XInput est essayé en premier ; SDL prend le relais automatiquement si aucune manette XInput n'est détectée.

---

## 🔌 Dépendances

| Package | Usage | Requis |
|---------|-------|--------|
| `PyQt6` | Interface graphique + overlays | ✅ Oui |
| `websocket-client` | Connexion BakkesMod WebSocket | Recommandé |
| `pyautogui` | Automation clavier (auto-skip, queue, freeplay…) | Optionnel |
| `pygame` | Sons personnalisés + manettes SDL | Optionnel |
| `vgamepad` | Émulation de manette virtuelle | Optionnel |
| `certifi` | Certificats SSL (fix PyInstaller) | Optionnel |

---

## 🏗 Build exécutable (PyInstaller)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name BakkyTrack rl_tracker.py
```

L'exécutable détecte automatiquement son répertoire pour charger `config.json`, les thèmes, les overlays et les icônes de rang.

> Un seul exemplaire de BakkyTrack peut tourner à la fois — un second lancement affiche un avertissement et quitte proprement.

---

## 📄 Licence

MIT — libre d'utilisation et de modification.
