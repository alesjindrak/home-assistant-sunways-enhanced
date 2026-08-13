"""Constants for the Sunways integration."""

from __future__ import annotations
from enum import StrEnum

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower

DOMAIN = "sunways"

MANUFACTURER = "Sunways"

CONF_STATION_ID = "station_id"
CONF_INITIAL_TOKEN = "initial_token"

class Units(StrEnum):
    """Available sensor units."""

    W = "W"
    KW = "kW"
    KWH = "kWh"
    MWH = "MWh"
    KWP = "kWp"

class SensorKeys(StrEnum):
    """Available sensors."""

    SOLAR_POWER = "solar_power"
    INSTALLED_POWER = "installed_power"
    EFFICIENCY = "efficiency"
    BATTERY_SOC = "battery_soc"
    BATTERY_CHARGING_POWER = "battery_charging_power"
    BATTERY_DISCHARGING_POWER = "battery_discharging_power"
    BATTERY_DIRECTION = "battery_direction"
    GRID_DIRECTION = "grid_direction"
    LOAD_DIRECTION = "load_direction"
    SOLAR_DIRECTION = "solar_direction"
    BACKUP_DIRECTION = "backup_direction"
    BACKUP_POWER = "backup_power"
    RSSI = "rssi"
    STATION_STATUS = "station_status"
    LOAD_POWER = "load_power"
    GRID_POWER_CONSUMPTION = "grid_power_consumption"
    GRID_POWER_RETURN = "grid_power_return"
    DAILY_GENERATION = "daily_generation"
    MONTHLY_GENERATION = "monthly_generation"
    YEARLY_GENERATION = "yearly_generation"
    TOTAL_GENERATION = "total_generation"


SENSOR_DESCRIPTIONS: dict[SensorKeys, SensorEntityDescription] = {
    SensorKeys.SOLAR_POWER: SensorEntityDescription(
        key=f"{SensorKeys.SOLAR_POWER}",
        name=f"{SensorKeys.SOLAR_POWER}",
        translation_key=f"{SensorKeys.SOLAR_POWER}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
    ),
    SensorKeys.INSTALLED_POWER: SensorEntityDescription(
        key=f"{SensorKeys.INSTALLED_POWER}",
        name=f"{SensorKeys.INSTALLED_POWER}",
        translation_key=f"{SensorKeys.INSTALLED_POWER}",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:solar-panel",
    ),
    SensorKeys.EFFICIENCY: SensorEntityDescription(
        key=f"{SensorKeys.EFFICIENCY}",
        name=f"{SensorKeys.EFFICIENCY}",
        translation_key=f"{SensorKeys.EFFICIENCY}",
        device_class=SensorDeviceClass.POWER_FACTOR,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:cart-percent",
    ),
    SensorKeys.BATTERY_SOC: SensorEntityDescription(
        key=f"{SensorKeys.BATTERY_SOC}",
        translation_key=f"{SensorKeys.BATTERY_SOC}",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    SensorKeys.BATTERY_CHARGING_POWER: SensorEntityDescription(
        key=f"{SensorKeys.BATTERY_CHARGING_POWER}",
        translation_key=f"{SensorKeys.BATTERY_CHARGING_POWER}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-up",
    ),
    SensorKeys.BATTERY_DISCHARGING_POWER: SensorEntityDescription(
        key=f"{SensorKeys.BATTERY_DISCHARGING_POWER}",
        translation_key=f"{SensorKeys.BATTERY_DISCHARGING_POWER}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-down",
    ),
    SensorKeys.BATTERY_DIRECTION: SensorEntityDescription(
        key=f"{SensorKeys.BATTERY_DIRECTION}",
        translation_key=f"{SensorKeys.BATTERY_DIRECTION}",
        icon="mdi:battery-sync",
    ),
    SensorKeys.GRID_DIRECTION: SensorEntityDescription(
        key=f"{SensorKeys.GRID_DIRECTION}",
        translation_key=f"{SensorKeys.GRID_DIRECTION}",
        icon="mdi:transmission-tower",
    ),
    SensorKeys.LOAD_DIRECTION: SensorEntityDescription(
        key=f"{SensorKeys.LOAD_DIRECTION}",
        translation_key=f"{SensorKeys.LOAD_DIRECTION}",
        icon="mdi:home-lightning-bolt",
    ),
    SensorKeys.SOLAR_DIRECTION: SensorEntityDescription(
        key=f"{SensorKeys.SOLAR_DIRECTION}",
        translation_key=f"{SensorKeys.SOLAR_DIRECTION}",
        icon="mdi:solar-power-variant",
    ),
    SensorKeys.BACKUP_DIRECTION: SensorEntityDescription(
        key=f"{SensorKeys.BACKUP_DIRECTION}",
        translation_key=f"{SensorKeys.BACKUP_DIRECTION}",
        icon="mdi:generator-portable",
    ),
    SensorKeys.BACKUP_POWER: SensorEntityDescription(
        key=f"{SensorKeys.BACKUP_POWER}",
        translation_key=f"{SensorKeys.BACKUP_POWER}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-plug-battery",
    ),
    SensorKeys.RSSI: SensorEntityDescription(
        key=f"{SensorKeys.RSSI}",
        translation_key=f"{SensorKeys.RSSI}",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi",
    ),
    SensorKeys.STATION_STATUS: SensorEntityDescription(
        key=f"{SensorKeys.STATION_STATUS}",
        translation_key=f"{SensorKeys.STATION_STATUS}",
        icon="mdi:solar-power-variant-outline",
    ),
    SensorKeys.LOAD_POWER: SensorEntityDescription(
        key=f"{SensorKeys.LOAD_POWER}",
        name=f"{SensorKeys.LOAD_POWER}",
        translation_key=f"{SensorKeys.LOAD_POWER}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt-outline",
    ),
    SensorKeys.GRID_POWER_CONSUMPTION: SensorEntityDescription(
        key=f"{SensorKeys.GRID_POWER_CONSUMPTION}",
        name=f"{SensorKeys.GRID_POWER_CONSUMPTION}",
        translation_key=f"{SensorKeys.GRID_POWER_CONSUMPTION}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-import",
    ),
    SensorKeys.GRID_POWER_RETURN: SensorEntityDescription(
        key=f"{SensorKeys.GRID_POWER_RETURN}",
        name=f"{SensorKeys.GRID_POWER_RETURN}",
        translation_key=f"{SensorKeys.GRID_POWER_RETURN}",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-export",
    ),
    SensorKeys.DAILY_GENERATION: SensorEntityDescription(
        key=f"{SensorKeys.DAILY_GENERATION}",
        name=f"{SensorKeys.DAILY_GENERATION}",
        translation_key=f"{SensorKeys.DAILY_GENERATION}",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:calendar-today",
    ),
    SensorKeys.MONTHLY_GENERATION: SensorEntityDescription(
        key=f"{SensorKeys.MONTHLY_GENERATION}",
        name=f"{SensorKeys.MONTHLY_GENERATION}",
        translation_key=f"{SensorKeys.MONTHLY_GENERATION}",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:calendar-month",
    ),
    SensorKeys.YEARLY_GENERATION: SensorEntityDescription(
        key=f"{SensorKeys.YEARLY_GENERATION}",
        name=f"{SensorKeys.YEARLY_GENERATION}",
        translation_key=f"{SensorKeys.YEARLY_GENERATION}",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:calendar-month",
    ),
    SensorKeys.TOTAL_GENERATION: SensorEntityDescription(
        key=f"{SensorKeys.TOTAL_GENERATION}",
        name=f"{SensorKeys.TOTAL_GENERATION}",
        translation_key=f"{SensorKeys.TOTAL_GENERATION}",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.MEGA_WATT_HOUR,
        suggested_display_precision=2,
        state_class=SensorStateClass.TOTAL,
        icon="mdi:calculator-variant",
    ),
}
