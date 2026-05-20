import hashlib
import hmac
import time

# Clés extraites du binaire RL (XOR-déchiffrées, voir b9llach/rlapi-py)
HMAC_KEY_AUTH = b""  # À remplir depuis le repo b9llach
HMAC_KEY_WS   = b""  # À remplir depuis le repo b9llach

def make_signature(key: bytes, method: str, path: str, body: bytes) -> str:
    """Génère la signature PsySig pour une requête."""
    timestamp = str(int(time.time()))
    message = f"{method}\n{path}\n{timestamp}\n".encode() + body
    sig = hmac.new(key, message, hashlib.sha256).hexdigest()
    return f"{timestamp}:{sig}"

def make_ws_signature(key: bytes, service: str, body: bytes) -> str:
    """Génère la signature PsySig pour un message WebSocket."""
    timestamp = str(int(time.time()))
    message = f"{service}\n{timestamp}\n".encode() + body
    sig = hmac.new(key, message, hashlib.sha256).hexdigest()
    return f"{timestamp}:{sig}"