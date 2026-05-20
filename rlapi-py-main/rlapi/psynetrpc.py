"""PsyNetRPC WebSocket client for Rocket League API."""
import asyncio
import json
import logging
from enum import Enum, auto
from typing import Any, Dict, Optional
from dataclasses import dataclass

import websockets
from websockets.client import WebSocketClientProtocol

from .psynet import PSY_BUILD_ID, GAME_VERSION, PING_INTERVAL, PONG_TIMEOUT, PsyNetError
from .requestid import RequestIDCounter
from .playerid import PlayerID


class EventType(Enum):
    """Event type enumeration."""

    DISCONNECTED = auto()
    MESSAGE = auto()


@dataclass
class Event:
    """WebSocket event."""

    type: EventType
    content: str


@dataclass
class PsyResponse:
    """PsyNet response."""

    response_id: str
    result: Any
    error: Optional[Dict[str, str]] = None


class PsyNetRPC:
    """PsyNetRPC represents an authenticated WebSocket connection.

    This is the primary client for all game API interactions after authentication.
    """

    def __init__(
        self,
        ws_conn: WebSocketClientProtocol,
        local_player_id: PlayerID,
        psy_token: str,
        session_id: str,
        request_id: RequestIDCounter,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize PsyNetRPC client.

        Args:
            ws_conn: WebSocket connection
            local_player_id: Local player ID
            psy_token: PsyNet authentication token
            session_id: Session ID
            request_id: Request ID counter
            logger: Optional logger instance
        """
        self.ws_conn = ws_conn
        self.local_player_id = local_player_id
        self.psy_token = psy_token
        self.session_id = session_id
        self.request_id = request_id
        self.logger = logger or logging.getLogger(__name__)

        self._lock = asyncio.Lock()
        self._pending_reqs: Dict[str, asyncio.Queue] = {}
        self._pong_event = asyncio.Event()
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=32)
        self._connected = True
        self._ping_task: Optional[asyncio.Task] = None
        self._read_task: Optional[asyncio.Task] = None

    def is_connected(self) -> bool:
        """Check if the WebSocket connection is active.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.ws_conn is not None

    async def close(self) -> None:
        """Close the WebSocket connection."""
        async with self._lock:
            if self.ws_conn and self._connected:
                try:
                    await self.ws_conn.close(code=1000, reason="Normal closure")
                except Exception:
                    pass

                self._connected = False

                if self._ping_task:
                    self._ping_task.cancel()
                    self._ping_task = None

                if self._read_task:
                    self._read_task.cancel()
                    self._read_task = None

                for req_id, queue in list(self._pending_reqs.items()):
                    del self._pending_reqs[req_id]

        try:
            await self._event_queue.put(Event(type=EventType.DISCONNECTED, content=""))
        except asyncio.QueueFull:
            pass

    def _parse_message(self, message: str) -> PsyResponse:
        """Parse a WebSocket message.

        Args:
            message: Raw message string

        Returns:
            Parsed PsyResponse

        Raises:
            ValueError: If message format is invalid
        """
        delimiter = "\r\n\r\n"
        index = message.find(delimiter)
        if index == -1:
            raise ValueError("Message does not contain expected delimiter")

        headers_part = message[:index]
        json_payload = message[index + len(delimiter) :]

        headers = {}
        for line in headers_part.split("\r\n"):
            colon_index = line.find(":")
            if colon_index != -1:
                key = line[:colon_index].strip()
                value = line[colon_index + 1 :].strip()
                headers[key] = value

        response_id = headers.get("PsyResponseID", "")

        json_result = json.loads(json_payload)

        error = None
        if "Error" in json_result and json_result["Error"]:
            error = json_result["Error"]

        return PsyResponse(
            response_id=response_id,
            result=json_result.get("Result"),
            error=error,
        )

    def _build_message(self, headers: Dict[str, str], body: Optional[Any] = None) -> str:
        """Build a WebSocket message.

        Args:
            headers: Message headers
            body: Optional message body

        Returns:
            Formatted message string
        """
        from .psynet import PSY_SIG_KEY
        import hmac
        import hashlib
        import base64

        json_data = b""
        if body is not None:
            json_data = json.dumps(body).encode()

            # Generate PsySig
            h = hmac.new(PSY_SIG_KEY.encode(), digestmod=hashlib.sha256)
            h.update(b"-")
            h.update(json_data)
            headers["PsySig"] = base64.b64encode(h.digest()).decode()

        message_parts = []
        for key, value in headers.items():
            message_parts.append(f"{key}: {value}")

        message = "\r\n".join(message_parts) + "\r\n\r\n" + json_data.decode()
        return message

    async def _schedule_ping(self) -> None:
        """Schedule the next ping."""
        await asyncio.sleep(PING_INTERVAL)
        await self._send_ping()

    async def _send_ping(self) -> None:
        """Send a ping message and wait for pong."""
        ping_message = self._build_message({"PsyPing": ""}, None)

        async with self._lock:
            if not self._connected or not self.ws_conn:
                self.logger.error("Connection lost while preparing to ping")
                return

            try:
                await self.ws_conn.send(ping_message)
            except Exception as e:
                self.logger.error(f"Failed to send ping: {e}")
                return

        self.logger.debug("Sent ping")

        self._pong_event.clear()

        try:
            await asyncio.wait_for(self._pong_event.wait(), timeout=PONG_TIMEOUT)
            self.logger.debug("Received pong")
            self._ping_task = asyncio.create_task(self._schedule_ping())
        except asyncio.TimeoutError:
            self.logger.error("Pong timeout reached")
            await self.close()

    async def _read_messages(self) -> None:
        """Read messages from the WebSocket connection."""
        try:
            async for message in self.ws_conn:
                if isinstance(message, bytes):
                    message = message.decode()

                if message.startswith("PsyPong:"):
                    self._pong_event.set()
                    continue

                self.logger.debug(f"Received WebSocket response: {message}")

                try:
                    response = self._parse_message(message)

                    if response.response_id:
                        async with self._lock:
                            if response.response_id in self._pending_reqs:
                                queue = self._pending_reqs[response.response_id]
                                await queue.put(response)
                                continue

                    # Unhandled message - send as event
                    try:
                        await self._event_queue.put(Event(type=EventType.MESSAGE, content=message))
                    except asyncio.QueueFull:
                        self.logger.warning(f"Event queue full, dropping message")

                except Exception as e:
                    self.logger.error(f"Failed to parse PsyNet message: {e}, message: {message}")
                    try:
                        await self._event_queue.put(Event(type=EventType.MESSAGE, content=message))
                    except asyncio.QueueFull:
                        pass

        except Exception as e:
            self.logger.error(f"Failed to read WebSocket message: {e}")
        finally:
            await self.close()

    async def send_request_async(self, service: str, data: Any) -> asyncio.Queue:
        """Send a request asynchronously and return a queue for the response.

        Args:
            service: Service name (e.g., "Players/GetProfile v1")
            data: Request data

        Returns:
            Queue that will receive the response

        Raises:
            Exception: If not connected or send fails
        """
        if not self.is_connected():
            raise Exception("WebSocket connection not established")

        request_id = self.request_id.get_id()
        self.logger.debug(f"Sending WebSocket request {request_id} to {service}: {data}")

        resp_queue: asyncio.Queue[PsyResponse] = asyncio.Queue(maxsize=1)

        headers = {
            "PsyService": service,
            "PsyRequestID": request_id,
        }
        message = self._build_message(headers, data)

        async with self._lock:
            if not self._connected or not self.ws_conn:
                raise Exception("Connection lost while preparing to send")

            self._pending_reqs[request_id] = resp_queue

            try:
                await self.ws_conn.send(message)
            except Exception as e:
                del self._pending_reqs[request_id]
                raise Exception(f"Failed to send request: {e}")

        return resp_queue

    async def await_response(self, resp_queue: asyncio.Queue, timeout: Optional[float] = None) -> Any:
        """Wait for a response from a queue.

        Args:
            resp_queue: Response queue from send_request_async
            timeout: Optional timeout in seconds

        Returns:
            Response result

        Raises:
            PsyNetError: If the API returns an error
            asyncio.TimeoutError: If timeout is reached
        """
        try:
            response = await asyncio.wait_for(resp_queue.get(), timeout=timeout)

            if response.error:
                raise PsyNetError(
                    type=response.error.get("Type", ""),
                    message=response.error.get("Message", ""),
                )

            return response.result

        except asyncio.TimeoutError:
            raise

    async def send_request_sync(self, service: str, data: Any, timeout: Optional[float] = None) -> Any:
        """Send a request and wait for the response synchronously.

        Args:
            service: Service name (e.g., "Players/GetProfile v1")
            data: Request data
            timeout: Optional timeout in seconds

        Returns:
            Response result

        Raises:
            PsyNetError: If the API returns an error
            asyncio.TimeoutError: If timeout is reached
        """
        resp_queue = await self.send_request_async(service, data)
        return await self.await_response(resp_queue, timeout)

    def events(self) -> asyncio.Queue[Event]:
        """Get the event queue for receiving raw messages and connection events.

        Returns:
            Event queue
        """
        return self._event_queue

    def start_background_tasks(self) -> None:
        """Start background tasks for reading messages and sending pings."""
        self._read_task = asyncio.create_task(self._read_messages())
        self._ping_task = asyncio.create_task(self._schedule_ping())
