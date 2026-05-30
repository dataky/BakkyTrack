# 📊 BakkyTrack - Ultimate Rocket League Companion Suite

**BakkyTrack** est une suite d'outils et d'automatisation ultra-complète conçue en Python (PyQt6) pour Rocket League sous Windows. Conçu à la fois pour les compétiteurs acharnés et les streamers, il apporte des fonctionnalités avancées dignes de BakkesMod sans compromettre les performances de votre PC.

---

## ✨ Fonctionnalités Majeures

### 🎮 1. L'Overlay de Scoreboard en Jeu (Touche TAB)
* **MMR en direct** : Affiche directement le MMR actuel de chaque joueur à côté de son nom sur le tableau des scores natif du jeu (lorsque vous maintenez la touche `TAB`).
* **Suivi du Peak** : Affiche également le record de MMR atteint par chaque joueur (ex : `peak[1520]`) pour évaluer instantanément le niveau réel de vos adversaires.
* **Placement Intelligent & Dynamique** : Le positionnement des textes s'adapte automatiquement à votre résolution d'écran (1080p, 1440p, 4K, 21:9) et se cale précisément sur les lignes Bleu et Orange de l'interface Rocket League.
* **Icônes de Rangs et de Playlists** : Affiche de magnifiques badges de rang et de playlist pour identifier d'un coup d'œil le statut de chacun.

### 🕵️ 2. Détection Anti-Smurf & Overlay Lobby
* **Alerte Smurfs multi-niveaux** : Notre algorithme analyse le profil des joueurs en temps réel et s'adapte selon leur rang :
  - **Champion et +** : moins de **250 victoires** OU TRN Score **< 150 000**.
  - **Diamant & Platine** : moins de **120 victoires** OU TRN Score **< 80 000**.
  L'application affiche alors un symbole d'avertissement **`⚠️ Smurf?`** à côté du pseudo si les critères de suspicion sont validés.
* **Overlay Joueurs (Touche F7)** : Un overlay flottant en verre dépoli liste tous les joueurs actuellement présents dans votre match, séparés par équipe.
* **Lien de Profil Rapide** : Cliquez sur le nom d'un joueur dans la liste pour ouvrir instantanément sa fiche de statistiques complète sur `tracker.network` dans votre navigateur par défaut.

### 🖥️ 3. Overlays Flottants de Bureau & Personnalisables
* **Thèmes Multiples** : Choisissez votre style visuel en double-cliquant sur l'overlay :
  - **Scoreboard** : Design bi-ton Bleu vs Orange typé Rocket League avec barre centrale.
  - **Glassmorphism** : Verre dépoli moderne avec reflets 3D et barre de winrate dynamique.
  - **HUD** : Style tactique militaire (effet CRT avec lignes de balayage CRT vertes).
  - **Vivid** : Blocs de couleurs modernes et ultra-saturés.
  - **Compact** : Une ligne défilante sobre et fluide.
* **Overlay Manette** : Affichez les pressions de touches de votre manette en temps réel (Xbox / PlayStation) avec styles transparent ou avec fond. Parfait pour les streams ou l'entraînement.
* **Overlay Vitesse Balle** : Affiche en temps réel la vitesse exacte de la balle en km/h à l'écran lors de vos entraînements ou matchs.
* **Sauvegarde de Position** : Tous les overlays se souviennent précisément de leur position sur l'écran au redémarrage de l'application !

### 🔊 4. Soundpad Événementiel & Mode Streamer
L'application analyse le trafic de données du jeu pour déclencher des sons personnalisés (au format `.wav`/`.mp3`) lors des temps forts du match :
- Buts marqués par vous / Buts encaissés
- Arrêts simples / Arrêts épiques
- Démolitions subies / Démolitions infligées
- Tirs sur la barre transversale (*Crossbar*)
- **Mode Streamer intelligent** : Baisse ou coupe automatiquement les sons système ou musicaux pour éviter les droits d'auteur sur vos streams en cas de but.

### ⚡ 5. Automatisations & Macros
* **Auto-GG** : Tape instantanément et valide votre message personnalisé (ex: `gg`) à la fin exacte de la partie.
* **Auto-Queue** : Relance automatiquement une recherche de partie pour minimiser le temps d'attente.
* **Auto-Skip Replays** : Presse automatiquement la touche pour passer les ralentis de buts dès qu'ils commencent.
* **Auto-Freeplay** : Vous envoie automatiquement en entraînement libre à la fin d'un match.

### 🌐 6. Serveur API local HTTP & SSE (Web Source)
BakkyTrack intègre un micro-serveur HTTP sur le port **8000** qui tourne en arrière-plan :
- **Flux SSE (`/events`)** : Envoie des mises à jour de stats en temps réel (Server-Sent Events) pour alimenter des pages web tierces ou des sources de navigateur OBS.
- **REST API (`/stats`)** : Renvoie un payload JSON complet de vos données de session.

### 💾 7. Historique Local SQLite
* Enregistre chaque match dans une base de données locale sécurisée (`SQLite`) pour conserver un suivi fiable de toutes vos sessions de jeu.

---

## 🚀 Installation & Démarrage

### 1. Prérequis
Vous devez disposer de **Python 3.11+** et installer les dépendances nécessaires dans votre terminal :
```bash
pip install PyQt6 pygame pyautogui requests obsws-python pyyaml
```

### 2. Lancement
```bash
python main.py
```

---

## ⚙️ Configuration Rapide

1. **Pseudo** : Dans l'onglet `Options`, renseignez votre plateforme (Epic, Steam...) et votre pseudo exact.
2. **Lancer le jeu** : Démarrez Rocket League. BakkyTrack détectera automatiquement le jeu et commencera le suivi.
3. **Webhook Discord** : Dans l'onglet `Options`, cochez "Envoyer le résultat sur Discord" et collez votre lien de Webhook Discord pour recevoir des récapitulatifs automatiques de vos matchs.
4. **Changement de Scène OBS** : Configurez votre OBS WebSocket (Host, Port, Mot de passe) pour que le logiciel change de scène entre vos phases en jeu (`In-Game`) et dans le lobby (`Lobby`).
