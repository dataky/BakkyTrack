import urllib.request
import urllib.error
import json
import threading

class DiscordWebhookService:
    def __init__(self, config, signals):
        self.config = config
        self.signals = signals

    def send_match_result(self, result, my_score, opp_score, mmr_change):
        url = self.config.get("webhook_url", "").strip()
        if not self.config.get("webhook_enabled", False) or not url:
            return
            
        def _send():
            try:
                color = 0x00e676 if result == "win" else 0xff3d57
                title = "Victoire!" if result == "win" else "Défaite"
                sign = "+" if mmr_change > 0 else ""
                
                payload = {
                    "username": "BakkyTrack",
                    "embeds": [{
                        "title": f"Match Terminé : {title}",
                        "color": color,
                        "fields": [
                            {"name": "Score", "value": f"{my_score} - {opp_score}", "inline": True},
                            {"name": "MMR", "value": f"{sign}{mmr_change}", "inline": True}
                        ]
                    }]
                }
                
                req = urllib.request.Request(
                    url, 
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'User-Agent': 'BakkyTrack', 'Content-Type': 'application/json'}
                )
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    pass
                self.signals.log_event.emit("[Webhook] Résultat envoyé avec succès.")
            except Exception as e:
                self.signals.log_event.emit(f"[Webhook] Erreur d'envoi: {e}")
                
        threading.Thread(target=_send, daemon=True).start()
