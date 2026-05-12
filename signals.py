"""signals.py — Signaux inter-services (QObject, zéro dépendance UI)."""
from PyQt6.QtCore import QObject, pyqtSignal


class AppSignals(QObject):
    status_changed   = pyqtSignal(str, str)
    player_detected  = pyqtSignal(str, int)
    match_result     = pyqtSignal(str)
    log_event        = pyqtSignal(str)
    mmr_updated      = pyqtSignal()
    mmr_error        = pyqtSignal(str)
    players_updated  = pyqtSignal(list)
    trigger_sound    = pyqtSignal(str)
    press_key_sig    = pyqtSignal(str, float)
    game_phase_changed = pyqtSignal(str)