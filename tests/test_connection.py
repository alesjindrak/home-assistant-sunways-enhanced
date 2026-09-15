"""Exercise authentication recovery and busy responses without portal access."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import AsyncMock, call, patch


@patch.dict(sys.modules)
def load_connection():
    """Load the real API code without importing Home Assistant."""
    root = Path(__file__).parents[1] / "custom_components" / "sunways" / "api"
    package = types.ModuleType("connection_tests")
    package.__path__ = [str(root)]
    sys.modules[package.__name__] = package
    spec = importlib.util.spec_from_file_location(
        "connection_tests.connection", root / "connection.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


API = load_connection()
EXPIRED = "auth_20000000003"


class Response:
    """HTTP response fixture including the actual portal envelope."""

    content_type = "application/json"
    status = 200

    def __init__(self, code="1000000", data=None, token=None):
        self.content = {"code": code, "msg": "test response", "data": data}
        self.headers = {} if token is None else {"token": token}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, **kwargs):
        return self.content


class Session:
    """Record every HTTP call and return a deterministic response sequence."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class ConnectionTest(unittest.IsolatedAsyncioTestCase):
    def connection(self, *responses, age=0):
        self.session = Session(*responses)
        self.api = API.SunwaysApiConnection(
            "test@example.invalid", "test-password", self.session,
            API.TokenJar("old-token", time.time() - age),
        )
        return self.api

    async def test_fresh_token_expiration_reauthenticates_and_replays_payload(self):
        api = self.connection(
            Response(EXPIRED), Response(token="new-token"), Response(data={"ok": True})
        )
        result = await api.request(
            "post", API.API_DEVICE_REALTIME, params={"id": "station"},
            json={"iecPath": ["vpv1"]}, data=None,
        )
        self.assertEqual({"ok": True}, result)
        first, login, replay = self.session.calls
        self.assertTrue(login[1].endswith(API._API_LOGIN))
        self.assertNotIn("token", login[2]["headers"])
        self.assertEqual(first[:2], replay[:2])
        for key in ("params", "json", "data"):
            self.assertEqual(first[2][key], replay[2][key])
        self.assertEqual("new-token", replay[2]["headers"]["token"])
        self.assertEqual("token=new-token", replay[2]["headers"]["Cookie"])

    async def test_repeated_expiration_is_bounded_and_discards_token(self):
        api = self.connection(Response(EXPIRED), Response(token="new"), Response(EXPIRED))
        with self.assertRaises(API.LoginFailed):
            await api.request("get", API.API_STATION_OVERVIEW)
        self.assertEqual(3, len(self.session.calls))
        self.assertIsNone(api._token_jar)

    async def test_bad_credentials_are_not_retried(self):
        api = self.connection(Response(EXPIRED), Response("auth_bad_credentials"))
        with self.assertRaises(API.LoginFailed):
            await api.request("get", API.API_STATION_OVERVIEW)
        self.assertEqual(2, len(self.session.calls))
        self.assertIsNone(api._token_jar)

    async def test_missing_login_token_is_not_accepted(self):
        api = self.connection(Response(EXPIRED), Response())
        with self.assertRaises(API.LoginFailed):
            await api.request("get", API.API_STATION_OVERVIEW)
        self.assertEqual(2, len(self.session.calls))

    async def test_busy_retries_string_and_integer_codes_without_login(self):
        api = self.connection(Response("3010107"), Response(3010107), Response(data=42))
        with patch.object(API.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            self.assertEqual(42, await api.request("get", API.API_STATION_OVERVIEW))
        self.assertEqual([call(1), call(2)], sleep.await_args_list)
        self.assertEqual(3, len(self.session.calls))
        self.assertTrue(all(c[1].endswith(API.API_STATION_OVERVIEW) for c in self.session.calls))
        self.assertEqual("old-token", api._token_jar.token)

    async def test_persistent_busy_stops_after_three_attempts(self):
        api = self.connection(*(Response("3010107") for _ in range(3)))
        with patch.object(API.asyncio, "sleep", new_callable=AsyncMock) as sleep:
            with self.assertRaises(API.SystemBusy):
                await api.request("get", API.API_STATION_OVERVIEW)
        self.assertEqual(2, sleep.await_count)
        self.assertEqual(3, len(self.session.calls))

    async def test_busy_login_can_recover(self):
        api = self.connection(
            Response(EXPIRED), Response("3010107"),
            Response(token="new"), Response(data=42),
        )
        with patch.object(API.asyncio, "sleep", new_callable=AsyncMock):
            self.assertEqual(42, await api.request("get", API.API_STATION_OVERVIEW))
        self.assertTrue(self.session.calls[1][1].endswith(API._API_LOGIN))
        self.assertTrue(self.session.calls[2][1].endswith(API._API_LOGIN))

    async def test_busy_token_validation_does_not_trigger_login(self):
        api = self.connection(
            Response("3010107"), Response(data={"userInfo": {"id": "user"}}),
            Response(data=42), age=7200,
        )
        with patch.object(API.asyncio, "sleep", new_callable=AsyncMock):
            self.assertEqual(42, await api.request("get", API.API_STATION_OVERVIEW))
        self.assertFalse(any(c[1].endswith(API._API_LOGIN) for c in self.session.calls))

    async def test_persistent_busy_validation_keeps_token_and_propagates(self):
        api = self.connection(*(Response("3010107") for _ in range(3)), age=7200)
        with patch.object(API.asyncio, "sleep", new_callable=AsyncMock):
            with self.assertRaises(API.SystemBusy):
                await api.request("get", API.API_STATION_OVERVIEW)
        self.assertEqual("old-token", api._token_jar.token)
        self.assertTrue(all(c[1].endswith(API._API_AUTH_INFO) for c in self.session.calls))

    async def test_expired_validation_logs_in_and_resets_ttl(self):
        api = self.connection(
            Response(EXPIRED), Response(token="new"), Response(data=42), age=18000,
        )
        api._token_ttl = 14400
        self.assertEqual(42, await api.request("get", API.API_STATION_OVERVIEW))
        self.assertEqual(API.ASSUMED_TOKEN_LIFETIME, api._token_ttl)

    async def test_unrelated_errors_are_not_retried(self):
        api = self.connection(Response("unexpected_code"))
        with self.assertRaises(API.RequestFailed):
            await api.request("get", API.API_STATION_OVERVIEW)
        self.assertEqual(1, len(self.session.calls))

    async def test_network_error_during_validation_does_not_login(self):
        api = self.connection(API.client_exceptions.ClientConnectionError(), age=7200)
        with self.assertRaises(API.ConnectionFailed):
            await api.request("get", API.API_STATION_OVERVIEW)
        self.assertEqual(1, len(self.session.calls))

    async def test_cancellation_during_validation_propagates(self):
        api = self.connection(asyncio.CancelledError(), age=7200)
        with self.assertRaises(asyncio.CancelledError):
            await api.request("get", API.API_STATION_OVERVIEW)
        self.assertFalse(api._request_lock.locked())
        self.assertEqual(1, len(self.session.calls))

    async def test_cancellation_during_backoff_propagates(self):
        api = self.connection(Response("3010107"))
        with patch.object(API.asyncio, "sleep", side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):
                await api.request("get", API.API_STATION_OVERVIEW)
        self.assertFalse(api._request_lock.locked())
        self.assertEqual(1, len(self.session.calls))

    async def test_concurrent_requests_share_one_login(self):
        entered = asyncio.Event()
        release = asyncio.Event()

        class SlowExpired(Response):
            async def json(self, **kwargs):
                entered.set()
                await release.wait()
                return await super().json(**kwargs)

        api = self.connection(
            SlowExpired(EXPIRED), Response(token="new"), Response(data=1), Response(data=2)
        )
        first = asyncio.create_task(api.request("get", API.API_STATION_OVERVIEW))
        await asyncio.wait_for(entered.wait(), 1)
        second = asyncio.create_task(api.request("get", API.API_DEVICE_REALTIME))
        await asyncio.sleep(0)
        self.assertEqual(1, len(self.session.calls))
        release.set()
        self.assertEqual([1, 2], await asyncio.wait_for(asyncio.gather(first, second), 1))
        self.assertEqual(1, sum(c[1].endswith(API._API_LOGIN) for c in self.session.calls))
        self.assertEqual("new", self.session.calls[-1][2]["headers"]["token"])

    async def test_no_initial_token_logs_in_once(self):
        api = self.connection(Response(token="new"), Response(data=42))
        api._token_jar = None
        self.assertEqual(42, await api.request("get", API.API_STATION_OVERVIEW))
        self.assertEqual(2, len(self.session.calls))


if __name__ == "__main__":
    unittest.main()
