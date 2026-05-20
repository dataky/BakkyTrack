"""PsyNet HTTP API client for Rocket League."""
import base64
import hmac
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx

from .requestid import RequestIDCounter
from .playerid import PlayerID


# Constants
BASE_URL = "https://api.rlpp.psynet.gg/rpc"
GAME_VERSION = "260506.26700.517210"
FEATURE_SET = "PrimeUpdate58_1"
PSY_BUILD_ID = "-1652286008"
PSY_SIG_KEY = "c338bd36fb8c42b1a431d30add939fc7"
PING_INTERVAL = 20.0  # seconds
PONG_TIMEOUT = 10.0   # seconds


@dataclass
class PsyNetError(Exception):
    """PsyNet API error."""

    type: str
    message: str

    def __str__(self) -> str:
        return f"{self.type}: {self.message}"


class PsyNet:
    """PsyNet represents the HTTP API client for initial authentication.

    See PsyNetRPC for the WebSocket client used for all game API interactions.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize PsyNet client.

        Args:
            logger: Optional logger instance
        """
        self.client = httpx.Client(timeout=30.0)
        self.request_id = RequestIDCounter()
        self.logger = logger or logging.getLogger(__name__)

    def __del__(self):
        """Close the HTTP client on cleanup."""
        try:
            self.client.close()
        except Exception:
            pass

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def _generate_psy_sig(self, body: bytes) -> str:
        """Generate HMAC-SHA256 signature for request body.

        Args:
            body: Request body as bytes

        Returns:
            Base64-encoded signature
        """
        h = hmac.new(PSY_SIG_KEY.encode(), digestmod=hashlib.sha256)
        h.update(b"-")
        h.update(body)
        return base64.b64encode(h.digest()).decode()

    def _post_json(self, path: List[str], params: Any, result_type: type) -> Any:
        """Send a POST request to the PsyNet API.

        Args:
            path: URL path components
            params: Request parameters
            result_type: Expected result type

        Returns:
            Parsed response result

        Raises:
            PsyNetError: If the API returns an error
            Exception: For other errors
        """
        url = f"{BASE_URL}/{'/'.join(path)}"

        body = json.dumps(params).encode()

        self.logger.debug(f"Sending HTTP request to {url}: {body.decode()}")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"RL Win/{GAME_VERSION} gzip (x86_64-pc-win32) curl-7.67.0 Schannel",
            "PsyBuildID": PSY_BUILD_ID,
            "PsyEnvironment": "Prod",
            "PsyRequestID": self.request_id.get_id(),
            "PsySig": self._generate_psy_sig(body),
        }

        response = self.client.post(url, headers=headers, content=body)

        if response.status_code != 200:
            raise Exception(f"Unexpected status: {response.status_code}")

        resp_data = response.json()
        self.logger.debug(f"Received HTTP response: {resp_data}")

        if "Error" in resp_data and resp_data["Error"]:
            error = resp_data["Error"]
            raise PsyNetError(type=error.get("Type", ""), message=error.get("Message", ""))

        return resp_data.get("Result")

    async def _post_json_async(self, path: List[str], params: Any, result_type: type) -> Any:
        """Send an async POST request to the PsyNet API.

        Args:
            path: URL path components
            params: Request parameters
            result_type: Expected result type

        Returns:
            Parsed response result

        Raises:
            PsyNetError: If the API returns an error
            Exception: For other errors
        """
        url = f"{BASE_URL}/{'/'.join(path)}"

        body = json.dumps(params).encode()

        self.logger.debug(f"Sending HTTP request to {url}: {body.decode()}")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"RL Win/{GAME_VERSION} gzip (x86_64-pc-win32) curl-7.67.0 Schannel",
            "PsyBuildID": PSY_BUILD_ID,
            "PsyEnvironment": "Prod",
            "PsyRequestID": self.request_id.get_id(),
            "PsySig": self._generate_psy_sig(body),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, content=body)

        if response.status_code != 200:
            raise Exception(f"Unexpected status: {response.status_code}")

        resp_data = response.json()
        self.logger.debug(f"Received HTTP response: {resp_data}")

        if "Error" in resp_data and resp_data["Error"]:
            error = resp_data["Error"]
            raise PsyNetError(type=error.get("Type", ""), message=error.get("Message", ""))

        return resp_data.get("Result")


def new_psy_net(logger: Optional[logging.Logger] = None) -> PsyNet:
    """Create a new PsyNet client.

    Args:
        logger: Optional logger instance

    Returns:
        PsyNet client instance
    """
    return PsyNet(logger=logger)
