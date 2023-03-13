"""Support for voltage, power & energy sensors for VeSync outlets."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from pyvesync.vesyncbasedevice import VeSyncBaseDevice
from pyvesync.vesyncoutlet import VeSyncOutlet

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .common import DEVICE_HELPER, VeSyncBaseEntity, get_domain_data
from .const import SKU_TO_BASE_DEVICE, VS_DISCOVERY, VS_SENSORS

_LOGGER = logging.getLogger(__name__)


@dataclass
class VeSyncSensorEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[VeSyncBaseDevice], StateType]


@dataclass
class VeSyncSensorEntityDescription(
    SensorEntityDescription, VeSyncSensorEntityDescriptionMixin
):
    """Describe VeSync sensor entity."""

    exists_fn: Callable[[VeSyncBaseDevice], bool] = lambda _: True
    update_fn: Callable[[VeSyncBaseDevice], None] = lambda _: None


def update_energy(device: VeSyncOutlet):
    """Update outlet details and energy usage."""
    device.update()
    device.update_energy()


def sku_supported(device: VeSyncBaseDevice, supported):
    """Get the base device of which a device is an instance."""
    return SKU_TO_BASE_DEVICE.get(device.device_type) in supported


FILTER_LIFE_SUPPORTED = ["LV-PUR131S", "Core200S", "Core300S", "Core400S", "Core600S"]
AIR_QUALITY_SUPPORTED = ["LV-PUR131S", "Core300S", "Core400S", "Core600S"]
PM25_SUPPORTED = ["Core300S", "Core400S", "Core600S"]

SENSORS: tuple[VeSyncSensorEntityDescription, ...] = (
    VeSyncSensorEntityDescription(
        key="filter-life",
        name="Filter Life",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: device.filter_life,
        exists_fn=lambda device: sku_supported(device, FILTER_LIFE_SUPPORTED),
    ),
    VeSyncSensorEntityDescription(
        key="air-quality",
        name="Air Quality",
        value_fn=lambda device: device.details["air_quality"],
        exists_fn=lambda device: sku_supported(device, AIR_QUALITY_SUPPORTED),
    ),
    VeSyncSensorEntityDescription(
        key="pm25",
        name="PM2.5",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.details["air_quality_value"],
        exists_fn=lambda device: sku_supported(device, PM25_SUPPORTED),
    ),
    VeSyncSensorEntityDescription(
        key="power",
        name="current power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.details["power"],
        update_fn=update_energy,
        exists_fn=lambda device: DEVICE_HELPER.is_outlet(device.device_type),
    ),
    VeSyncSensorEntityDescription(
        key="energy",
        name="energy use today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.energy_today,
        update_fn=update_energy,
        exists_fn=lambda device: DEVICE_HELPER.is_outlet(device.device_type),
    ),
    VeSyncSensorEntityDescription(
        key="energy-weekly",
        name="energy use weekly",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.weekly_energy_total,
        update_fn=update_energy,
        exists_fn=lambda device: DEVICE_HELPER.is_outlet(device.device_type),
    ),
    VeSyncSensorEntityDescription(
        key="energy-monthly",
        name="energy use monthly",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.monthly_energy_total,
        update_fn=update_energy,
        exists_fn=lambda device: DEVICE_HELPER.is_outlet(device.device_type),
    ),
    VeSyncSensorEntityDescription(
        key="energy-yearly",
        name="energy use yearly",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda device: device.yearly_energy_total,
        update_fn=update_energy,
        exists_fn=lambda device: DEVICE_HELPER.is_outlet(device.device_type),
    ),
    VeSyncSensorEntityDescription(
        key="voltage",
        name="current voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.details["voltage"],
        update_fn=update_energy,
        exists_fn=lambda device: DEVICE_HELPER.is_outlet(device.device_type),
    ),
    # Humidifier - VeSyncHumid200300S
    VeSyncSensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.details["humidity"],
        exists_fn=lambda device: "humidity" in device.details,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""

    @callback
    def discover(devices: list):
        """Add new devices to platform."""
        entities = []
        for dev in devices:
            for description in SENSORS:
                if description.exists_fn(dev):
                    entities.append(VeSyncSensorEntity(dev, description))

        async_add_entities(entities, update_before_add=True)

    discover(get_domain_data(hass, config_entry, VS_SENSORS))

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_SENSORS), discover)
    )


class VeSyncSensorEntity(VeSyncBaseEntity, SensorEntity):
    """Representation of a sensor describing a VeSync device."""

    entity_description: VeSyncSensorEntityDescription

    def __init__(
        self,
        device: VeSyncBaseDevice,
        description: VeSyncSensorEntityDescription,
    ) -> None:
        """Initialize the VeSync outlet device."""
        super().__init__(device)
        self.entity_description = description
        self._attr_name = f"{super().name} {description.name}"
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.device)

    def update(self) -> None:
        """Run the update function defined for the sensor."""
        return self.entity_description.update_fn(self.device)
