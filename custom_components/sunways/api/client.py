"""Simple HTTP client for the Sunways REST user API."""

from typing import Any, NamedTuple
from aiohttp.client import ClientSession

from .connection import (
    SunwaysApiConnection,
    TokenJar,
    API_STATION_LIST,
    API_STATION_OVERVIEW
)


class SunwaysStation(NamedTuple):
    """Identifies a station registered for the user at sunways."""

    name: str
    id: str


class SunwaysStationOverview:
    """Overview of a PV station."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    @property
    def id(self) -> str:
        """ID of the station."""
        return self._data["id"]

    @property
    def solar_power(self) -> float:
        return self._data["pac"]

    @property
    def solar_power_unit(self) -> str:
        return self._data["pacUnit"]

    @property    
    def installed_power(self) -> float:
        return self._data["instatlledPower"]

    @property
    def installed_power_unit(self) -> str:
        return self._data["instatlledPowerUnit"]

    @property
    def solar_installed_ratio(self) -> float:
        return self._data["powerRatio"]

    @staticmethod
    def _as_float(value: Any) -> float | None:
        """Convert a portal value to float without breaking an update."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _number(self, *keys: str) -> float | None:
        """Return the first numeric value present under one of the keys."""
        for key in keys:
            value = self._as_float(self._data.get(key))
            if value is not None:
                return value
        return None

    def _active(self, key: str) -> bool:
        """Return whether a portal direction flag is active."""
        return self._data.get(key) in (1, True, "1", "true", "True")

    @property
    def battery_soc(self) -> float | None:
        """Return battery state of charge in percent."""
        return self._number("soc", "SOC")

    @property
    def battery_charging_power(self) -> float:
        """Return battery charging power."""
        power = self._number("batteryP", "batteryPOrgion") or 0.0
        return abs(power) if self._active("arrowInverterBattery") else 0.0

    @property
    def battery_discharging_power(self) -> float:
        """Return battery discharging power."""
        power = self._number("batteryP", "batteryPOrgion") or 0.0
        return abs(power) if self._active("arrowBatteryInverter") else 0.0

    @property
    def battery_power_unit(self) -> str:
        """Return the battery power unit."""
        return self._data.get("batteryPUnit") or "W"

    @property
    def battery_direction(self) -> str:
        """Return the current battery energy-flow direction."""
        if self._active("arrowInverterBattery"):
            return "charging"
        if self._active("arrowBatteryInverter"):
            return "discharging"
        return "idle"

    @property
    def grid_direction(self) -> str:
        """Return the current grid energy-flow direction."""
        if self._active("arrowGridInverter"):
            return "importing"
        if self._active("arrowInverterGrid"):
            return "exporting"
        return "idle"

    @property
    def load_direction(self) -> str:
        """Return the current load energy-flow direction."""
        if self._active("arrowInverterLoad"):
            return "consuming"
        if self._active("arrowLoadInverter"):
            return "returning"
        return "idle"

    @property
    def solar_direction(self) -> str:
        """Return whether the PV modules are producing."""
        return "producing" if self._active("arrowModuleInverter") else "idle"

    @property
    def backup_direction(self) -> str:
        """Return the generator/backup energy-flow direction."""
        if self._active("arrowGeneratorAndBackupInverter"):
            return "to_inverter"
        if self._active("arrowGeneratorAndBackup"):
            return "to_backup"
        return "idle"

    @property
    def backup_power(self) -> float | None:
        """Return EPS/backup output power."""
        return self._number(
            "totalBackupPower",
            "totalBackupPowerOrgin",
            "totalBackupP",
            "generatorBackupPower",
        )

    @property
    def backup_power_unit(self) -> str:
        """Return the EPS/backup power unit."""
        return (
            self._data.get("totalBackupPowerUnit")
            or self._data.get("generatorBackupPowerUnit")
            or "W"
        )

    @property
    def rssi(self) -> float | None:
        """Return the raw logger signal-strength value."""
        return self._number("rssi")

    @property
    def station_status(self) -> str | int | None:
        """Return the most descriptive station status available."""
        return (
            self._data.get("stationStatusTip")
            or self._data.get("stationStatus")
            or self._data.get("status")
        )

    @property
    def load_power(self) -> float:
        return self._data["pLoad"]

    @property
    def load_power_unit(self) -> str:
        return self._data["pLoadUnit"]
    
    @property
    def grid_power_consumption(self) -> float:
        return self._data["pmeterTotal"] if self._data["arrowGridInverter"] == 1 else 0.0
    
    @property
    def grid_power_return(self) -> float:
        return self._data["pmeterTotal"] if self._data["arrowInverterGrid"] == 1 else 0.0
    
    @property
    def grid_power_unit(self) -> float:
        return self._data["pmeterTotalUnit"]

    @property
    def daily_generation(self) -> float:
        return self._data["eDay"]

    @property
    def daily_generation_unit(self) -> str:
        return self._data["eDayUnit"]

    @property
    def monthly_generation(self) -> float:
        return self._data["eMonth"]

    @property
    def monthly_generation_unit(self) -> str:
        return self._data["eMonthUnit"]

    @property
    def yearly_generation(self) -> float:
        return self._data["eYear"]

    @property
    def yearly_generation_unit(self) -> str:
        return self._data["eYearUnit"]

    @property
    def total_generation(self) -> float:
        return self._data["eTotal"]

    @property
    def total_generation_unit(self) -> str:
        return self._data["eTotalUnit"]


class SunwaysClient:
    """
    Simple client for Sunways API
    """

    def __init__(
        self,
        email: str,
        password: str,
        websession: ClientSession,
        token_jar: TokenJar | None = None
    ):
        self._api = SunwaysApiConnection(email, password, websession, token_jar)

    async def __aenter__(self):
        await self._api.__aenter__()
        return self

    async def __aexit__(self, *args) -> bool:
        """Call when the client is disposed."""
        # Close the web session, if we created it (i.e. it was not passed in)
        return await self._api.__aexit__(*args)

    async def get_stations(self) -> list[SunwaysStation]:
        """Get the availabile stations."""
        result = await self._api.request("get", API_STATION_LIST)

        stations = [SunwaysStation(s["name"], s["id"]) for s in result["records"]]
        return stations

    async def get_station_overview(self, station_id: str) -> SunwaysStationOverview:
        """Get the overview of a single station."""
        result = await self._api.request("get", API_STATION_OVERVIEW, {'id': station_id})

        station = SunwaysStationOverview(result)
        return station
