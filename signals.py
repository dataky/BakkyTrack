from PyQt6.QtCore import QObject, pyqtSignal

class AppSignals(QObject):
    """Signaux globaux de l'application."""
    log_event = pyqtSignal(str)
    status_changed = pyqtSignal(str, str)  # (type, message)
    mmr_updated = pyqtSignal()
    mmr_error = pyqtSignal(str)
    match_result = pyqtSignal(str)  # 'win', 'loss', 'reset', '__auto__win', ...
    player_detected = pyqtSignal(str, int)  # (name, team)
    player_detected_with_id = pyqtSignal(str, int, str)  # (name, team, primary_id)   <-- NOUVEAU
    players_updated = pyqtSignal(list)
    ball_speed_updated = pyqtSignal(float)
    game_phase_changed = pyqtSignal(str)  # 'lobby', 'ingame'
    trigger_sound = pyqtSignal(str)      # 'goal_scored', 'demo_me', ...
    press_key_sig = pyqtSignal(str, float)  # (key_name, delay)
    
    # Signaux Updater
    update_available = pyqtSignal(str, str, str)  # (version, release_notes, download_url)
    update_download_progress = pyqtSignal(int)    # pourcentage (0-100)
    update_downloaded = pyqtSignal(str)           # (chemin_fichier_telecharge)
    update_error = pyqtSignal(str)                # (message_erreur)