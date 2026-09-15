"""Internal Sunways client."""

import asyncio
import hashlib
import base64
import time
from typing import Any
from dataclasses import dataclass, asdict

from urllib.parse import urljoin
from aiohttp import Payload, client_exceptions, CookieJar
from aiohttp.client import ClientSession

from .exceptions import (
    ConnectionFailed,
    LoginFailed,
    RequestFailed,
    SystemBusy,
)


_API_HOST = "https://api.sunways-portal.com"
_API_LOGIN = "/monitor/auth/login"
_API_AUTH_INFO = "/monitor/auth/info?useFor=1"

API_STATION_LIST = "/monitor/core/power/station/monitoring/getPage"
API_STATION_OVERVIEW = "/monitor/core/power/station/overview/getSingleStationOverview"
API_DEVICE_LIST = "/monitor/core/device/getListByStation/{station_id}"
API_DEVICE_REALTIME = "/monitor/core/curve/device/queryRealTimeData"


ASSUMED_TOKEN_LIFETIME = 60 * 60
BUSY_RETRY_DELAYS = (1, 2)


@dataclass
class TokenJar:
    token: str | None = None
    issued: float | None = 0.0

    dict = asdict


class SunwaysApiConnection:
    """Low level Sunways API client."""

    _token_ttl: float
    _token_jar: TokenJar | None
    _own_session: bool
    _station_id: str
    _default_headers: dict

    def __init__(
        self,
        email: str,
        password: str,
        websession: ClientSession,
        token_jar: TokenJar | None = None
    ):
        self._url = _API_HOST
        self._email = email
        self._password = password
        self._session = websession
        self._default_headers = {'ver': "pc"}
        self._verify_ssl = True
        self._token_jar = token_jar
        self._token_ttl = ASSUMED_TOKEN_LIFETIME
        self._request_lock = asyncio.Lock()

    async def _get_session(self) -> ClientSession:
        if self._session is None:
            self._own_session = True
            jar = CookieJar(unsafe=True)
            self._session = ClientSession(cookie_jar=jar)
        return self._session

    async def __aenter__(self):
        try:
            await self.login()
            return self
        except Exception as error:
            if self._own_session:
                await self.close()
            raise error

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Call when the client is disposed."""
        # Close the web session, if we created it (i.e. it was not passed in)
        if self._own_session:
            await self.close()
        return False

    async def close(self):
        """Close the current web session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def login(self):
        """Call to login and store token."""
        async with self._request_lock:
            await self._login()

    async def _login(self):
        """Authenticate while the caller holds the request lock."""
        self._token_jar = None
        self._token_ttl = ASSUMED_TOKEN_LIFETIME

        encoded_password = self._encode_password(self._password)
        auth = {"email": self._email, "password": encoded_password, "channel": 1}
        await self._do_request("post", _API_LOGIN, json=auth)
        if self._token_jar is None or not self._token_jar.token:
            raise LoginFailed(-1, "Login response did not contain a token")

    async def _check_login(self) -> bool:
        """Check token validity."""
        if (
            self._token_jar is None
            or not self._token_jar.token
            or self._token_jar.issued is None
        ):
            return False
        
        current_lifetime = time.time() - self._token_jar.issued

        if current_lifetime < self._token_ttl:
            # Assume TTL good for a login to remain active
            return True

        try:
            response = await self._do_request("get", _API_AUTH_INFO)
            if response.get("userInfo"):
                # Extend token ttl
                self._token_ttl += ASSUMED_TOKEN_LIFETIME
                return True
        except LoginFailed:
            self._token_jar = None

        return False

    async def request(self, method: str, end_point: str, params=None, json=None, data: Payload | None = None) -> Any:
        """Perform a request to the API, with authentication"""

        # Serialize authentication and requests so a second refresh cannot
        # invalidate the token that an in-flight request is using.
        async with self._request_lock:
            if not await self._check_login():
                await self._login()

            for attempt in range(2):
                try:
                    return await self._do_request(
                        method, end_point, params=params, json=json, data=data
                    )
                except LoginFailed:
                    self._token_jar = None
                    if attempt:
                        raise
                    # The server can expire a token before our assumed TTL.
                    # Reauthenticate once and replay the original request.
                    await self._login()

    async def _do_request(self, method: str, end_point: str, params=None, json=None, data: Payload | None = None) -> Any:
        """Retry explicit temporary busy responses with a bounded backoff."""
        for attempt in range(len(BUSY_RETRY_DELAYS) + 1):
            try:
                return await self._do_request_once(
                    method, end_point, params=params, json=json, data=data
                )
            except SystemBusy:
                if attempt == len(BUSY_RETRY_DELAYS):
                    raise
                await asyncio.sleep(BUSY_RETRY_DELAYS[attempt])

    async def _do_request_once(self, method: str, end_point: str, params=None, json=None, data: Payload | None = None) -> Any:
        """Perform a request to the API, and unpack the response."""

        url = urljoin(self._url, end_point)
        session = await self._get_session()

        # Note: We need to push back the token in the 'Cookie' and the 'token' header
        headers = self._default_headers.copy()
        if end_point != _API_LOGIN and self._token_jar:
            headers["token"] = self._token_jar.token
            # todo make session.cookie_jar.update_cookies work
            headers["Cookie"] = f"token={self._token_jar.token}"

        try:
            async with session.request(
                method,
                url,
                params=params,
                headers=headers,
                json=json,
                data=data,
                ssl=self._verify_ssl,
            ) as response:
                if response.status != 200:
                    if response.content_type == "application/json":
                        content = await response.json(encoding="utf-8")
                        self._check_application_errors(content)

                    raise RequestFailed(response.status, "HTTP Request Error")

                # If something goes wrong with the login session, HTTP 200 is returned :/
                if response.content_type != "application/json":
                    raise RequestFailed(0, "Invalid response body")

                content = await response.json(encoding="utf-8")
                self._check_application_errors(content)

                # The JWT token is returned in the header in login response
                if "token" in response.headers:
                    response_token = response.headers["token"]
                    self._token_jar = TokenJar(response_token, time.time())
                    self._token_ttl = ASSUMED_TOKEN_LIFETIME

                # Unpack response data
                if "data" in content:
                    return content["data"]
                return content

        except client_exceptions.ClientConnectionError as err:
            raise ConnectionFailed(err) from err
        except client_exceptions.ClientError as err:
            raise RequestFailed(0, f"Unexpected error: {err}") from None

    def _check_application_errors(self, response):
        if not isinstance(response, dict):
            return
        if "code" not in response:
            raise RequestFailed(-1, "Unexpected response: " + str(response))
        code = str(response["code"])
        if code == "1000000":
            return
        message = response.get("msg", "Unknown API error")
        if code.lower().startswith("auth_"):
            raise LoginFailed(code, message)
        if code == "3010107":
            raise SystemBusy(code, message)
        raise RequestFailed(code, message)
    
    def _encode_password(self, password: str) -> str:
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        return base64.b64encode(md5_hash.encode()).decode()
