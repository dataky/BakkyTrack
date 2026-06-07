import os
import sys
import time
import json
import urllib.request
import urllib.error
import threading
import subprocess
from config import BASE_DIR, SSL_CTX, SSL_CTX_NOVERIFY
from version import __version__

class UpdaterService:
    def __init__(self, config, signals):
        self.config = config
        self.signals = signals
        self._current_version = __version__.lstrip('v')
        self._check_thread = None
        self._download_thread = None

    def check_for_updates(self):
        """Lance la vérification des mises à jour en arrière-plan."""
        repo = self.config.get("github_repo", "")
        if not repo:
            self.signals.log_event.emit("[Updater] Aucun dépôt GitHub configuré pour l'auto-update.")
            return

        self._check_thread = threading.Thread(target=self._check_worker, args=(repo,), daemon=True)
        self._check_thread.start()

    def _check_worker(self, repo):
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        headers = {"User-Agent": "BakkyTrack-Updater"}
        try:
            req = urllib.request.Request(url, headers=headers)
            ctx = SSL_CTX if SSL_CTX is not None else SSL_CTX_NOVERIFY
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            latest_tag = data.get("tag_name", "").lstrip('v')
            
            # Comparaison de version simplifiée
            if self._is_newer(latest_tag, self._current_version):
                assets = data.get("assets", [])
                exe_asset = None
                for asset in assets:
                    if asset.get("name", "").endswith(".exe"):
                        exe_asset = asset
                        break
                
                if exe_asset:
                    download_url = exe_asset.get("browser_download_url")
                    notes = data.get("body", "Nouvelle version disponible !")
                    self.signals.log_event.emit(f"[Updater] Nouvelle version {latest_tag} trouvée.")
                    self.signals.update_available.emit(latest_tag, notes, download_url)
                else:
                    self.signals.log_event.emit(f"[Updater] Version {latest_tag} trouvée mais aucun .exe dans les assets.")
            else:
                self.signals.log_event.emit("[Updater] L'application est à jour.")

        except Exception as e:
            self.signals.log_event.emit(f"[Updater] Erreur lors de la vérification : {e}")

    def _is_newer(self, latest, current):
        """Compare deux versions ex: '2.3.0' > '2.2.0'"""
        try:
            l_parts = [int(x) for x in latest.split('.')]
            c_parts = [int(x) for x in current.split('.')]
            # Pad avec des zéros si les longueurs sont différentes
            length = max(len(l_parts), len(c_parts))
            l_parts += [0] * (length - len(l_parts))
            c_parts += [0] * (length - len(c_parts))
            return l_parts > c_parts
        except Exception:
            return latest != current

    def download_update(self, download_url):
        """Lance le téléchargement de la mise à jour en arrière-plan."""
        if self._download_thread and self._download_thread.is_alive():
            return
        
        self._download_thread = threading.Thread(target=self._download_worker, args=(download_url,), daemon=True)
        self._download_thread.start()

    def _download_worker(self, url):
        try:
            headers = {"User-Agent": "BakkyTrack-Updater"}
            req = urllib.request.Request(url, headers=headers)
            ctx = SSL_CTX if SSL_CTX is not None else SSL_CTX_NOVERIFY
            
            # Déterminer le chemin de destination
            # On le met dans %LOCALAPPDATA%/BakkyTrack/update/
            update_dir = os.path.join(os.environ.get('LOCALAPPDATA', BASE_DIR), "BakkyTrack", "update")
            os.makedirs(update_dir, exist_ok=True)
            dest_path = os.path.join(update_dir, "BakkyTrack_update.exe")

            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                total_size = int(resp.getheader('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192

                with open(dest_path, 'wb') as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            self.signals.update_download_progress.emit(percent)

            self.signals.log_event.emit(f"[Updater] Téléchargement terminé : {dest_path}")
            self.signals.update_downloaded.emit(dest_path)

        except Exception as e:
            self.signals.log_event.emit(f"[Updater] Erreur de téléchargement : {e}")
            self.signals.update_error.emit(str(e))

    def apply_update_and_restart(self, new_exe_path):
        """
        Génère un script batch pour remplacer l'exécutable courant par le nouveau,
        puis lance ce script et quitte l'application.
        """
        if not sys.platform == "win32" or getattr(sys, 'frozen', False) is False:
            self.signals.log_event.emit("[Updater] L'application n'est pas un exécutable packagé. Mise à jour automatique annulée.")
            return

        current_exe = sys.executable
        bat_path = os.path.join(os.environ.get('LOCALAPPDATA', BASE_DIR), "BakkyTrack", "update_script.bat")

        bat_content = f"""@echo off
echo Mise a jour de BakkyTrack en cours...
echo Veuillez patienter...
ping 127.0.0.1 -n 3 > nul

:: Essayer de supprimer l'ancien fichier
:loop
del /Q "{current_exe}"
if exist "{current_exe}" (
    ping 127.0.0.1 -n 2 > nul
    goto loop
)

:: Copier le nouveau
copy /Y "{new_exe_path}" "{current_exe}"

:: Lancer le nouveau
start "" "{current_exe}"

:: Supprimer le fichier de telechargement
del /Q "{new_exe_path}"

:: Supprimer ce script lui-meme
del "%~f0"
"""
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            
            self.signals.log_event.emit("[Updater] Lancement du script de mise à jour...")
            # Lancer le .bat en mode détaché (creationflags=0x08000000 = CREATE_NO_WINDOW)
            subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Quitter l'application
            import PyQt6.QtWidgets
            PyQt6.QtWidgets.QApplication.quit()
        except Exception as e:
            self.signals.log_event.emit(f"[Updater] Erreur lors de l'application de la maj : {e}")
            self.signals.update_error.emit(f"Erreur d'installation : {e}")
