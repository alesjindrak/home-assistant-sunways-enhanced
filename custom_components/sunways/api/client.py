"""Simple HTTP client for the Sunways REST user API."""

from datetime import datetime
from typing import Any, NamedTuple
from aiohttp.client import ClientSession

from .connection import (
    SunwaysApiConnection,
    TokenJar,
    API_DEVICE_LIST,
    API_DEVICE_REALTIME,
    API_STATION_LIST,
    API_STATION_OVERVIEW
)


REALTIME_PATHS = (
    "vpv1", "vpv2", "ipv1", "ipv2",
    "vgridPhaseA", "vgridPhaseB", "vgridPhaseC",
    "igridPhaseA", "igridPhaseB", "igridPhaseC", "fgrid",
    "activePowerA", "activePowerB", "activePowerC",
    "backupAV", "backupBV", "backupCV",
    "backupAI", "backupBI", "backupCI",
    "backupAF", "backupBF", "backupCF",
    "soh", "batteryV", "batteryI", "minCellVoltage", "maxCellVoltage",
    "iChargingLimit", "iDischargeLimit",
    "temperature1", "bmsPackTemperature",
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


class SunwaysDeviceRealtime:
    """Latest detailed inverter values returned by the device curve API."""

    def __init__(self, data: list[dict[str, Any]] | None):
        self._values: dict[str, float] = {}
        # Walk backwards and keep the newest value available for every key.
        for point in reversed(data or []):
            values = point.get("data") or {}
            for key, value in values.items():
                if key not in self._values:
                    number = SunwaysStationOverview._as_float(value)
                    if number is not None:
                        self._values[key] = number

    def value(self, key: str) -> float | None:
        """Return the latest numeric value for an IEC path."""
        return self._values.get(key)

    @property
    def values(self) -> dict[str, float]:
        """Return a copy of all latest values."""
        return self._values.copy()


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
        self._device_sn_cache: dict[str, str] = {}

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

    async def get_station_device_sn(self, station_id: str) -> str | None:
        """Return the first inverter serial number registered at a station."""
        if station_id in self._device_sn_cache:
            return self._device_sn_cache[station_id]

        result = await self._api.request(
            "get", API_DEVICE_LIST.format(station_id=station_id)
        )
        devices: list[dict[str, Any]] = []

        def collect_devices(value: Any) -> None:
            """Find device dictionaries in any portal response wrapper."""
            if isinstance(value, dict):
                if value.get("deviceSn") or value.get("serialNum"):
                    devices.append(value)
                for child in value.values():
                    if isinstance(child, (dict, list)):
                        collect_devices(child)
            elif isinstance(value, list):
                for child in value:
                    collect_devices(child)

        collect_devices(result)

        # Device type 2 is an inverter. Fall back to any item carrying a serial.
        inverter = next((d for d in devices if d.get("deviceType") == 2), None)
        device = inverter or next(
            (d for d in devices if d.get("deviceSn") or d.get("serialNum")), None
        )
        if device is None:
            return None

        serial = device.get("deviceSn") or device.get("serialNum")
        if serial:
            self._device_sn_cache[station_id] = str(serial)
            return str(serial)
        return None

    async def get_device_realtime(
        self,
        station_id: str,
        iec_paths: tuple[str, ...] = REALTIME_PATHS,
    ) -> SunwaysDeviceRealtime:
        """Get latest detailed inverter values for a station."""
        device_sn = await self.get_station_device_sn(station_id)
        if device_sn is None:
            return SunwaysDeviceRealtime([])

        now = datetime.now().astimezone()
        offset = now.utcoffset()
        offset_minutes = int(offset.total_seconds() / 60) if offset else 0
        payload = {
            "deviceSn": device_sn,
            "stationId": station_id,
            "iecPath": list(iec_paths),
            "time": now.date().isoformat(),
            "timeZoneOffset": offset_minutes,
        }
        result = await self._api.request(
            "post", API_DEVICE_REALTIME, json=payload
        )
        return SunwaysDeviceRealtime(result if isinstance(result, list) else [])
