"""Request ID counter for PsyNet API requests."""
import threading


class RequestIDCounter:
    """Thread-safe request ID counter for generating unique request IDs."""

    def __init__(self):
        """Initialize the request ID counter."""
        self._value = 0
        self._lock = threading.Lock()

    def get_id(self) -> str:
        """Get the next request ID.

        Returns:
            A unique request ID string in the format 'PsyNetMessage_X_{counter}'
        """
        with self._lock:
            current_id = self._value
            self._value += 1
            return f"PsyNetMessage_X_{current_id}"
