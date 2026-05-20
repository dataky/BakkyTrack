"""Epic Games Store authentication client."""
import base64
import json
from typing import Optional
from dataclasses import dataclass
from urllib.parse import quote

import httpx


# Constants
EGS_USER_AGENT = "UELauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit"
EGS_CLIENT_ID = "34a02cf8f4414e29b15921876da36f9a"
EGS_CLIENT_SECRET = "daafbccc737745039dffe53d94fc76cf"
EGS_OAUTH_URL = "account-public-service-prod03.ol.epicgames.com"
EOS_AUTH_HEADER = "eHl6YTc4OTFwNUQ3czlSNkdtNm1vVEhXR2xvZXJwN0I6S25oMThkdTROVmxGcyszdVErWlBwRENWdG8wV1lmNHlYUDgrT2N3VnQxbw=="
EOS_DEPLOYMENT_ID = "da32ae9c12ae40e8a112c52e1f17f3ba"  # Rocket League


@dataclass
class TokenResponse:
    """Epic Games Store token response."""

    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: str
    token_type: str
    client_id: str
    internal_client: bool
    client_service: str
    account_id: str
    display_name: str
    app: str
    in_app_id: str
    device_id: Optional[str] = None


@dataclass
class EOSTokenResponse:
    """Epic Online Services token response."""

    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: str
    refresh_expires_in: int
    refresh_expires_at: str
    token_type: str
    scope: str
    client_id: str
    application_id: str
    account_id: str
    merged_accounts: list
    acr: str
    auth_time: str
    id_token: Optional[str] = None
    selected_account_id: Optional[str] = None


class EGS:
    """EGS provides an authentication layer for Epic Games Store.

    Largely adapted from https://github.com/derrod/legendary
    """

    def __init__(self):
        """Initialize EGS client."""
        self.client = httpx.Client(timeout=30.0)

    def __del__(self):
        """Close the HTTP client on cleanup."""
        try:
            self.client.close()
        except Exception:
            pass

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def get_auth_url(self) -> str:
        """Get the EGS login URL for manual browser authentication.

        Returns:
            Authentication URL
        """
        return f"https://www.epicgames.com/id/api/redirect?clientId={EGS_CLIENT_ID}&responseType=code"

    def authenticate_with_code(self, auth_code: str) -> TokenResponse:
        """Authenticate with EGS using an authorization code.

        Args:
            auth_code: Authorization code from browser login

        Returns:
            Token response

        Raises:
            Exception: If authentication fails
        """
        return self._request_token({
            "grant_type": "authorization_code",
            "code": auth_code,
            "token_type": "eg1",
        })

    def authenticate_with_refresh_token(self, refresh_token: str) -> TokenResponse:
        """Authenticate with EGS using a refresh token.

        Args:
            refresh_token: Refresh token from previous authentication

        Returns:
            Token response

        Raises:
            Exception: If authentication fails
        """
        return self._request_token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "token_type": "eg1",
        })

    def _request_token(self, params: dict) -> TokenResponse:
        """Request an authentication token from EGS.

        Args:
            params: Request parameters

        Returns:
            Token response

        Raises:
            Exception: If the request fails
        """
        url = f"https://{EGS_OAUTH_URL}/account/api/oauth/token"

        auth_string = f"{EGS_CLIENT_ID}:{EGS_CLIENT_SECRET}"
        auth_header = "Basic " + base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": EGS_USER_AGENT,
            "Authorization": auth_header,
        }

        response = self.client.post(url, headers=headers, data=params)

        if response.status_code != 200:
            try:
                error_data = response.json()
                error_code = error_data.get("errorCode", "")
                error_message = error_data.get("errorMessage", "")
                raise Exception(f"Authentication failed: {response.status_code}, {error_code} - {error_message}")
            except json.JSONDecodeError:
                raise Exception(f"Authentication failed: {response.status_code}")

        data = response.json()
        return TokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            expires_at=data["expires_at"],
            token_type=data["token_type"],
            client_id=data["client_id"],
            internal_client=data["internal_client"],
            client_service=data["client_service"],
            account_id=data["account_id"],
            display_name=data["displayName"],
            app=data["app"],
            in_app_id=data["in_app_id"],
            device_id=data.get("device_id"),
        )

    def get_exchange_code(self, access_token: str) -> str:
        """Convert an EGS access token into an exchange code for EOS.

        Args:
            access_token: EGS access token

        Returns:
            Exchange code

        Raises:
            Exception: If the request fails
        """
        url = f"https://{EGS_OAUTH_URL}/account/api/oauth/exchange"

        headers = {
            "Authorization": f"bearer {access_token}",
            "User-Agent": EGS_USER_AGENT,
        }

        response = self.client.get(url, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Unexpected status code: {response.status_code}")

        data = response.json()
        return data["code"]

    def exchange_eos_token(self, exchange_code: str) -> EOSTokenResponse:
        """Exchange an exchange code for an EOS authentication token.

        Args:
            exchange_code: Exchange code from get_exchange_code

        Returns:
            EOS token response

        Raises:
            Exception: If the request fails
        """
        return self._request_eos_token({
            "grant_type": "exchange_code",
            "exchange_code": exchange_code,
        })

    def exchange_eos_token_from_steam(self, steam_ticket: str) -> EOSTokenResponse:
        """Exchange a Steam session ticket for an EOS authentication token.

        Args:
            steam_ticket: Steam session ticket

        Returns:
            EOS token response

        Raises:
            Exception: If the request fails
        """
        return self._request_eos_token({
            "grant_type": "external_auth",
            "external_auth_type": "steam_session_ticket",
            "external_auth_token": steam_ticket,
        })

    def refresh_eos_token(self, refresh_token: str) -> EOSTokenResponse:
        """Refresh an EOS authentication token using a refresh token.

        Args:
            refresh_token: EOS refresh token

        Returns:
            EOS token response

        Raises:
            Exception: If the request fails
        """
        return self._request_eos_token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })

    def _request_eos_token(self, params: dict) -> EOSTokenResponse:
        """Request an EOS authentication token.

        Args:
            params: Request parameters

        Returns:
            EOS token response

        Raises:
            Exception: If the request fails
        """
        url = "https://api.epicgames.dev/epic/oauth/v2/token"

        params["deployment_id"] = EOS_DEPLOYMENT_ID
        params["scope"] = "basic_profile friends_list presence friends_management"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {EOS_AUTH_HEADER}",
            "User-Agent": EGS_USER_AGENT,
        }

        response = self.client.post(url, headers=headers, data=params)

        if response.status_code != 200:
            raise Exception(f"Unexpected status code: {response.status_code}")

        data = response.json()
        return EOSTokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            expires_at=data["expires_at"],
            refresh_expires_in=data["refresh_expires_in"],
            refresh_expires_at=data["refresh_expires_at"],
            token_type=data["token_type"],
            scope=data["scope"],
            client_id=data["client_id"],
            application_id=data["application_id"],
            account_id=data["account_id"],
            merged_accounts=data["merged_accounts"],
            acr=data["acr"],
            auth_time=data["auth_time"],
            id_token=data.get("id_token"),
            selected_account_id=data.get("selected_account_id"),
        )

    def revoke_eos_token(self, access_token: str) -> None:
        """Revoke an EOS authentication token.

        Args:
            access_token: EOS access token to revoke

        Raises:
            Exception: If the request fails
        """
        url = "https://api.epicgames.dev/epic/oauth/v2/revoke"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": EGS_USER_AGENT,
        }

        params = {"token": access_token}

        response = self.client.post(url, headers=headers, data=params)

        if response.status_code != 204:
            raise Exception(f"Unexpected status code: {response.status_code}")


def new_egs() -> EGS:
    """Create a new EGS client.

    Returns:
        EGS client instance
    """
    return EGS()