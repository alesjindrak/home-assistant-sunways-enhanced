"""Tests for the station-overview data model."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


def load_client_module():
    """Load client.py without requiring a Home Assistant installation."""
    package = types.ModuleType("sunways")
    package.__path__ = []
    sys.modules["sunways"] = package

    api_package = types.ModuleType("sunways.api")
    api_package.__path__ = []
    sys.modules["sunways.api"] = api_package

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.__path__ = []
    sys.modules["aiohttp"] = aiohttp
    aiohttp_client = types.ModuleType("aiohttp.client")
    aiohttp_client.ClientSession = object
    sys.modules["aiohttp.client"] = aiohttp_client

    connection = types.ModuleType("sunways.api.connection")
    connection.SunwaysApiConnection = object
    connection.TokenJar = object
    connection.API_STATION_LIST = "/stations"
    connection.API_STATION_OVERVIEW = "/overview"
    connection.API_DEVICE_LIST = "/devices/{station_id}"
    connection.API_DEVICE_REALTIME = "/realtime"
    sys.modules["sunways.api.connection"] = connection

    path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "sunways"
        / "api"
        / "client.py"
    )
    spec = importlib.util.spec_from_file_location("sunways.api.client", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CLIENT = load_client_module()


def base_payload() -> dict:
    """Return the fields required by the original overview model."""
    return {
        "id": "station",
        "pac": 0,
        "pacUnit": "W",
        "instatlledPower": 0,
        "instatlledPowerUnit": "W",
        "powerRatio": 0,
        "pLoad": 0,
        "pLoadUnit": "W",
        "pmeterTotal": 0,
        "pmeterTotalUnit": "W",
        "arrowGridInverter": 0,
        "arrowInverterGrid": 0,
        "eDay": 0,
        "eDayUnit": "kWh",
        "eMonth": 0,
        "eMonthUnit": "kWh",
        "eYear": 0,
        "eYearUnit": "kWh",
        "eTotal": 0,
        "eTotalUnit": "kWh",
    }


class StationOverviewTest(unittest.TestCase):
    """Test enhanced overview properties."""

    def test_charging_and_optional_values(self):
        overview = CLIENT.SunwaysStationOverview(
            base_payload()
            | {
                "soc": "73",
                "batteryP": "-2500",
                "batteryPUnit": "W",
                "arrowInverterBattery": 1,
                "arrowBatteryInverter": 0,
                "arrowInverterLoad": 1,
                "arrowModuleInverter": 1,
                "totalBackupPower": "850",
                "totalBackupPowerUnit": "W",
                "rssi": "-61",
                "stationStatusTip": "Running",
            }
        )

        self.assertEqual(73, overview.battery_soc)
        self.assertEqual(2500, overview.battery_charging_power)
        self.assertEqual(0, overview.battery_discharging_power)
        self.assertEqual("charging", overview.battery_direction)
        self.assertEqual("consuming", overview.load_direction)
        self.assertEqual("producing", overview.solar_direction)
        self.assertEqual(850, overview.backup_power)
        self.assertEqual(-61, overview.rssi)
        self.assertEqual("Running", overview.station_status)

    def test_missing_optional_values_are_safe(self):
        overview = CLIENT.SunwaysStationOverview(base_payload())

        self.assertIsNone(overview.battery_soc)
        self.assertEqual("idle", overview.battery_direction)
        self.assertIsNone(overview.backup_power)


class DeviceRealtimeTest(unittest.TestCase):
    """Test extraction of the newest detailed values."""

    def test_latest_values_are_merged_across_points(self):
        realtime = CLIENT.SunwaysDeviceRealtime(
            [
                {"dataTime": 1000, "data": {"vpv1": 240.1, "batteryV": 50.2}},
                {"dataTime": 2000, "data": {"vpv1": "245.6", "batteryV": None}},
                {"dataTime": 3000, "data": {}},
            ]
        )

        self.assertEqual(245.6, realtime.value("vpv1"))
        self.assertEqual(50.2, realtime.value("batteryV"))
        self.assertIsNone(realtime.value("notSupported"))

    def test_invalid_values_are_ignored(self):
        realtime = CLIENT.SunwaysDeviceRealtime(
            [{"data": {"vpv1": "offline", "vpv2": ""}}]
        )

        self.assertEqual({}, realtime.values)


class ClientDetailedApiTest(unittest.IsolatedAsyncioTestCase):
    """Test detailed API discovery and request payload."""

    async def test_device_discovery_and_realtime_request(self):
        calls = []

        class FakeApi:
            async def request(self, method, endpoint, **kwargs):
                calls.append((method, endpoint, kwargs))
                if endpoint.startswith("/devices/"):
                    return {"items": [{"deviceType": 2, "deviceSn": "TEST-SN"}]}
                return [{"dataTime": 1, "data": {"vpv1": 251.4}}]

        client = CLIENT.SunwaysClient.__new__(CLIENT.SunwaysClient)
        client._api = FakeApi()
        client._device_sn_cache = {}

        result = await client.get_device_realtime("TEST-STATION", ("vpv1",))

        self.assertEqual(251.4, result.value("vpv1"))
        self.assertEqual("post", calls[1][0])
        self.assertEqual("TEST-SN", calls[1][2]["json"]["deviceSn"])
        self.assertEqual("TEST-STATION", calls[1][2]["json"]["stationId"])
        self.assertEqual(["vpv1"], calls[1][2]["json"]["iecPath"])


if __name__ == "__main__":
    unittest.main()
