"""Update coordinatior for the Sunways integration."""

from datetime import timedelta
import logging
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api.client import SunwaysClient, SunwaysStationOverview
from .api.exceptions import SunwaysClientException
from .const import SensorKeys

SCAN_INTERVAL = timedelta(seconds=60)

DETAIL_SENSOR_PATHS = {
    SensorKeys.PV_VOLTAGE_1: "vpv1",
    SensorKeys.PV_VOLTAGE_2: "vpv2",
    SensorKeys.PV_CURRENT_1: "ipv1",
    SensorKeys.PV_CURRENT_2: "ipv2",
    SensorKeys.GRID_VOLTAGE_L1: "vgridPhaseA",
    SensorKeys.GRID_VOLTAGE_L2: "vgridPhaseB",
    SensorKeys.GRID_VOLTAGE_L3: "vgridPhaseC",
    SensorKeys.GRID_CURRENT_L1: "igridPhaseA",
    SensorKeys.GRID_CURRENT_L2: "igridPhaseB",
    SensorKeys.GRID_CURRENT_L3: "igridPhaseC",
    SensorKeys.GRID_FREQUENCY: "fgrid",
    SensorKeys.EPS_VOLTAGE_L1: "backupAV",
    SensorKeys.EPS_VOLTAGE_L2: "backupBV",
    SensorKeys.EPS_VOLTAGE_L3: "backupCV",
    SensorKeys.EPS_CURRENT_L1: "backupAI",
    SensorKeys.EPS_CURRENT_L2: "backupBI",
    SensorKeys.EPS_CURRENT_L3: "backupCI",
    SensorKeys.EPS_FREQUENCY_L1: "backupAF",
    SensorKeys.EPS_FREQUENCY_L2: "backupBF",
    SensorKeys.EPS_FREQUENCY_L3: "backupCF",
    SensorKeys.BATTERY_SOH: "soh",
    SensorKeys.BATTERY_VOLTAGE: "batteryV",
    SensorKeys.BATTERY_CURRENT: "batteryI",
    SensorKeys.BATTERY_MIN_CELL_VOLTAGE: "minCellVoltage",
    SensorKeys.BATTERY_MAX_CELL_VOLTAGE: "maxCellVoltage",
    SensorKeys.BATTERY_CHARGE_CURRENT_LIMIT: "iChargingLimit",
    SensorKeys.BATTERY_DISCHARGE_CURRENT_LIMIT: "iDischargeLimit",
    SensorKeys.INVERTER_TEMPERATURE: "temperature1",
    SensorKeys.BATTERY_TEMPERATURE: "bmsPackTemperature",
}


def convert_to_kilo(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    unit = unit or "W"
    if unit.startswith('k'):
        return value
    if unit.startswith('M'):
        return value * 1000
    return round(value / 1000, 2)

def convert_to_mega(value: float | None, unit: str) -> float:
    if value is None:
        return 0.0
    if unit.startswith('k'):
        return round(value / 1000, 2)
    if unit.startswith('M'):
        return value
    return round(value / 1000 / 1000, 2)


class SunwaysStationOverviewUpdateCoordinator(DataUpdateCoordinator[SunwaysStationOverview]):
    """Coordinator for getting details about the station."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        client: SunwaysClient,
        station_id: str
    ) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            logger,
            name="Sunways API Data - Station",
            update_interval=SCAN_INTERVAL,
        )
        self._client = client
        self._station_id = station_id
        self._logger = logger
        self._detail_values = {key: None for key in DETAIL_SENSOR_PATHS}
        self._consecutive_overview_failures = 0

    async def _async_update_data(self):
        """Fetch data from API endpoint."""

        try:
            async with asyncio.timeout(10):
                overview = await self._client.get_station_overview(self._station_id)
            self._consecutive_overview_failures = 0
            sensors = {
                        SensorKeys.SOLAR_POWER: convert_to_kilo(overview.solar_power, overview.solar_power_unit),
                        SensorKeys.INSTALLED_POWER: convert_to_kilo(overview.installed_power, overview.installed_power_unit),
                        SensorKeys.EFFICIENCY: overview.solar_installed_ratio if overview.solar_installed_ratio else 0.0,
                        SensorKeys.BATTERY_SOC: overview.battery_soc,
                        SensorKeys.BATTERY_CHARGING_POWER: convert_to_kilo(overview.battery_charging_power, overview.battery_power_unit),
                        SensorKeys.BATTERY_DISCHARGING_POWER: convert_to_kilo(overview.battery_discharging_power, overview.battery_power_unit),
                        SensorKeys.BATTERY_DIRECTION: overview.battery_direction,
                        SensorKeys.GRID_DIRECTION: overview.grid_direction,
                        SensorKeys.LOAD_DIRECTION: overview.load_direction,
                        SensorKeys.SOLAR_DIRECTION: overview.solar_direction,
                        SensorKeys.BACKUP_DIRECTION: overview.backup_direction,
                        SensorKeys.BACKUP_POWER: convert_to_kilo(overview.backup_power, overview.backup_power_unit),
                        SensorKeys.RSSI: overview.rssi,
                        SensorKeys.STATION_STATUS: overview.station_status,
                        SensorKeys.LOAD_POWER: convert_to_kilo(overview.load_power, overview.load_power_unit),
                        SensorKeys.GRID_POWER_CONSUMPTION: convert_to_kilo(overview.grid_power_consumption, overview.grid_power_unit),
                        SensorKeys.GRID_POWER_RETURN: convert_to_kilo(overview.grid_power_return, overview.grid_power_unit),
                        SensorKeys.DAILY_GENERATION: convert_to_kilo(overview.daily_generation, overview.daily_generation_unit),
                        SensorKeys.MONTHLY_GENERATION: convert_to_kilo(overview.monthly_generation, overview.monthly_generation_unit),
                        SensorKeys.YEARLY_GENERATION: convert_to_mega(overview.yearly_generation, overview.yearly_generation_unit),
                        SensorKeys.TOTAL_GENERATION: convert_to_mega(overview.total_generation, overview.total_generation_unit),
            }

            # Detailed data is refreshed every minute too, but it is isolated
            # from the overview update. A slow or empty curve response keeps
            # the most recent valid values instead of making entities vanish.
            sensors.update(self._detail_values)
            try:
                async with asyncio.timeout(10):
                    realtime = await self._client.get_device_realtime(self._station_id)
                for sensor_key, iec_path in DETAIL_SENSOR_PATHS.items():
                    value = realtime.value(iec_path)
                    if value is not None:
                        self._detail_values[sensor_key] = value
                sensors.update(self._detail_values)
            except (SunwaysClientException, TimeoutError) as err:
                self._logger.warning(
                    "Sunways detailed device data is temporarily unavailable; "
                    "keeping the previous values: %s",
                    err,
                )
            except Exception as err:  # Keep optional detail failures isolated.
                self._logger.exception(
                    "Unexpected Sunways detailed-data error; keeping the "
                    "previous values: %s",
                    err,
                )

            return {
                'id': self._station_id,
                'sensors': sensors,
            }
        except (SunwaysClientException, TimeoutError) as err:
            self._consecutive_overview_failures += 1
            if self.data is not None and self._consecutive_overview_failures < 3:
                self._logger.warning(
                    "Sunways overview update failed (%s/3); keeping the previous "
                    "values: %s",
                    self._consecutive_overview_failures,
                    err,
                )
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}") from err
