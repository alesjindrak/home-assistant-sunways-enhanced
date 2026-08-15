"""Tests for transient Sunways coordinator failures."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys
import types
import unittest


class FakeCoordinator:
    """Minimal Home Assistant coordinator stub."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, *args, **kwargs):
        self.data = None


class FakeUpdateFailed(Exception):
    """Home Assistant update error stub."""


def load_coordinator_module():
    """Load coordinator.py without a Home Assistant installation."""
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    sys.modules["homeassistant"] = homeassistant
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant.core"] = core
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator.DataUpdateCoordinator = FakeCoordinator
    update_coordinator.UpdateFailed = FakeUpdateFailed
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator

    package = sys.modules.setdefault("sunways", types.ModuleType("sunways"))
    package.__path__ = []
    api_package = sys.modules.setdefault("sunways.api", types.ModuleType("sunways.api"))
    api_package.__path__ = []
    client = types.ModuleType("sunways.api.client")
    client.SunwaysClient = object
    client.SunwaysStationOverview = object
    sys.modules["sunways.api.client"] = client
    exceptions = types.ModuleType("sunways.api.exceptions")
    exceptions.SunwaysClientException = type("SunwaysClientException", (Exception,), {})
    sys.modules["sunways.api.exceptions"] = exceptions

    key_names = (
        "SOLAR_POWER INSTALLED_POWER EFFICIENCY BATTERY_SOC "
        "BATTERY_CHARGING_POWER BATTERY_DISCHARGING_POWER BATTERY_DIRECTION "
        "GRID_DIRECTION LOAD_DIRECTION SOLAR_DIRECTION BACKUP_DIRECTION "
        "BACKUP_POWER RSSI STATION_STATUS LOAD_POWER GRID_POWER_CONSUMPTION "
        "GRID_POWER_RETURN DAILY_GENERATION MONTHLY_GENERATION YEARLY_GENERATION "
        "TOTAL_GENERATION PV_VOLTAGE_1 PV_VOLTAGE_2 PV_CURRENT_1 PV_CURRENT_2 "
        "GRID_VOLTAGE_L1 GRID_VOLTAGE_L2 GRID_VOLTAGE_L3 GRID_CURRENT_L1 "
        "GRID_CURRENT_L2 GRID_CURRENT_L3 GRID_FREQUENCY EPS_VOLTAGE_L1 "
        "EPS_VOLTAGE_L2 EPS_VOLTAGE_L3 EPS_CURRENT_L1 EPS_CURRENT_L2 "
        "EPS_CURRENT_L3 EPS_FREQUENCY_L1 EPS_FREQUENCY_L2 EPS_FREQUENCY_L3 "
        "BATTERY_SOH BATTERY_VOLTAGE BATTERY_CURRENT BATTERY_MIN_CELL_VOLTAGE "
        "BATTERY_MAX_CELL_VOLTAGE BATTERY_CHARGE_CURRENT_LIMIT "
        "BATTERY_DISCHARGE_CURRENT_LIMIT INVERTER_TEMPERATURE BATTERY_TEMPERATURE"
    ).split()
    sensor_keys = type("SensorKeys", (), {name: name.lower() for name in key_names})
    const = types.ModuleType("sunways.const")
    const.SensorKeys = sensor_keys
    sys.modules["sunways.const"] = const

    path = (
        Path(__file__).parents[1]
        / "custom_components"
        / "sunways"
        / "coordinator.py"
    )
    spec = importlib.util.spec_from_file_location("sunways.coordinator", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COORDINATOR = load_coordinator_module()


class Overview:
    """Complete station overview fixture."""

    solar_power = 1000
    solar_power_unit = "W"
    installed_power = 10000
    installed_power_unit = "W"
    solar_installed_ratio = 10
    battery_soc = 50
    battery_charging_power = 0
    battery_discharging_power = 0
    battery_power_unit = "W"
    battery_direction = "idle"
    grid_direction = "idle"
    load_direction = "consuming"
    solar_direction = "producing"
    backup_direction = "idle"
    backup_power = 0
    backup_power_unit = "W"
    rssi = -60
    station_status = "Running"
    load_power = 500
    load_power_unit = "W"
    grid_power_consumption = 0
    grid_power_return = 0
    grid_power_unit = "W"
    daily_generation = 5
    daily_generation_unit = "kWh"
    monthly_generation = 50
    monthly_generation_unit = "kWh"
    yearly_generation = 1000
    yearly_generation_unit = "kWh"
    total_generation = 5000
    total_generation_unit = "kWh"


class Realtime:
    """Detailed response fixture."""

    def __init__(self, values):
        self._values = values

    def value(self, key):
        return self._values.get(key)


class Client:
    """Switchable Sunways client fixture."""

    overview_error = None
    realtime_error = None
    realtime_values = {"vgridPhaseA": 230.5}

    async def get_station_overview(self, station_id):
        if self.overview_error:
            raise self.overview_error
        return Overview()

    async def get_device_realtime(self, station_id):
        if self.realtime_error:
            raise self.realtime_error
        return Realtime(self.realtime_values)


class CoordinatorFailureTest(unittest.IsolatedAsyncioTestCase):
    """Verify that short cloud failures do not create one-minute gaps."""

    def test_fast_polling_interval(self):
        self.assertEqual(30, COORDINATOR.SCAN_INTERVAL.total_seconds())

    async def test_detail_timeout_keeps_overview_and_previous_detail(self):
        client = Client()
        coordinator = COORDINATOR.SunwaysStationOverviewUpdateCoordinator(
            None, logging.getLogger(__name__), client, "station"
        )

        first = await coordinator._async_update_data()
        coordinator.data = first
        self.assertEqual("producing", first["sensors"]["solar_direction"])
        self.assertEqual(230.5, first["sensors"]["grid_voltage_l1"])

        client.realtime_error = TimeoutError()
        second = await coordinator._async_update_data()
        self.assertEqual("producing", second["sensors"]["solar_direction"])
        self.assertEqual(230.5, second["sensors"]["grid_voltage_l1"])

    async def test_two_overview_failures_keep_last_update(self):
        client = Client()
        coordinator = COORDINATOR.SunwaysStationOverviewUpdateCoordinator(
            None, logging.getLogger(__name__), client, "station"
        )
        coordinator.data = await coordinator._async_update_data()
        client.overview_error = TimeoutError()

        self.assertIs(coordinator.data, await coordinator._async_update_data())
        self.assertIs(coordinator.data, await coordinator._async_update_data())
        with self.assertRaises(FakeUpdateFailed):
            await coordinator._async_update_data()


if __name__ == "__main__":
    unittest.main()
