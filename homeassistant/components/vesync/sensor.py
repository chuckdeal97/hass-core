"""Support for voltage, power & energy sensors for VeSync outlets."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from pyvesync.vesyncbasedevice import VeSyncBaseDevice

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

from .common import (
    DEVICE_HELPER,
    VeSyncBaseEntity,
    VeSyncEntityDescriptionFactory,
    get_domain_data,
)
from .const import VS_DISCOVERY, VS_SENSORS

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


class VeSyncSensorEntity(VeSyncBaseEntity, SensorEntity):
    """Representation of a sensor describing a VeSync device."""

    entity_description: VeSyncSensorEntityDescription

    def __init__(
        self,
        device: VeSyncBaseDevice,
        description: VeSyncSensorEntityDescription,
    ) -> None:
        """Initialize the VeSync sensor entity."""
        super().__init__(device)
        self.entity_description = description
        self._attr_name = f"{super().name} {description.name}"
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.device)


class VeSyncEnergySensorEntity(VeSyncSensorEntity):
    """Representation of an energy sensor describing a VeSync device."""

    def update(self) -> None:
        """Run the update function defined for the sensor."""
        self.device.update()
        self.device.update_energy()


class AirQualityEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncSensorEntity]
    ]
):
    """Create an entity description for a device that supports air quality sensor."""

    object_class = VeSyncSensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="air-quality",
            name="Air Quality",
            value_fn=lambda device: device.details["air_quality"],
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.has_feature(device, "details", "air_quality")


class CurrentPowerEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncEnergySensorEntity]
    ]
):
    """Create an entity description for a device that supports current power sensor."""

    object_class = VeSyncEnergySensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="power",
            name="Current Power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda device: device.details["power"],
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.is_outlet(device.device_type)


class EnergyMonthlyEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncEnergySensorEntity]
    ]
):
    """Create an entity description for a device that supports energy use weekly sensor."""

    object_class = VeSyncEnergySensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="energy-monthly",
            name="Energy Use Monthly",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=lambda device: device.monthly_energy_total,
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.is_outlet(device.device_type)


class EnergyTodayEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncEnergySensorEntity]
    ]
):
    """Create an entity description for a device that supports energy use today sensor."""

    object_class = VeSyncEnergySensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="energy",
            name="Energy Use Today",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=lambda device: device.energy_today,
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.is_outlet(device.device_type)


class EnergyWeeklyEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncEnergySensorEntity]
    ]
):
    """Create an entity description for a device that supports energy use weekly sensor."""

    object_class = VeSyncEnergySensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="energy-weekly",
            name="Energy Use Weekly",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=lambda device: device.weekly_energy_total,
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.is_outlet(device.device_type)


class EnergyYearlyEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncEnergySensorEntity]
    ]
):
    """Create an entity description for a device that supports energy use weekly sensor."""

    object_class = VeSyncEnergySensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="energy-yearly",
            name="Energy Use Yearly",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=lambda device: device.yearly_energy_total,
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.is_outlet(device.device_type)


class FilterLifeEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncSensorEntity]
    ]
):
    """Create an entity description for a device that supports filter life sensor."""

    object_class = VeSyncSensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="filter-life",
            name="Filter Life",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda device: device.filter_life,
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return hasattr(device, "filter_life")


class HumidityEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncSensorEntity]
    ]
):
    """Create an entity description for a device that supports humidity sensor."""

    object_class = VeSyncSensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="humidity",
            name="Humidity",
            device_class=SensorDeviceClass.HUMIDITY,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda device: device.details["humidity"],
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return "humidity" in device.details


class PM25EntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncSensorEntity]
    ]
):
    """Create an entity description for a device that supports air quality value sensor."""

    object_class = VeSyncSensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="pm25",
            name="PM2.5",
            device_class=SensorDeviceClass.PM25,
            native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda device: device.details["air_quality_value"],
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.has_feature(device, "details", "air_quality_value")


class VoltageEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSensorEntityDescription, type[VeSyncEnergySensorEntity]
    ]
):
    """Create an entity description for a device that supports energy use weekly sensor."""

    object_class = VeSyncEnergySensorEntity

    def create(self, device: VeSyncBaseDevice) -> VeSyncSensorEntityDescription:
        """Create a VeSyncSensorEntityDescription."""
        return VeSyncSensorEntityDescription(
            key="voltage",
            name="Current Voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda device: device.details["voltage"],
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports this sensor."""
        return DEVICE_HELPER.is_outlet(device.device_type)


_FACTORIES: list[VeSyncEntityDescriptionFactory] = [
    AirQualityEntityDescriptionFactory(),
    CurrentPowerEntityDescriptionFactory(),
    EnergyMonthlyEntityDescriptionFactory(),
    EnergyTodayEntityDescriptionFactory(),
    EnergyWeeklyEntityDescriptionFactory(),
    EnergyYearlyEntityDescriptionFactory(),
    FilterLifeEntityDescriptionFactory(),
    HumidityEntityDescriptionFactory(),
    PM25EntityDescriptionFactory(),
    VoltageEntityDescriptionFactory(),
]


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
            supported = False
            for factory in _FACTORIES:
                if factory.supports(dev):
                    supported = True
                    entities.append(factory.object_class(dev, factory.create(dev)))

            if not supported:
                # if no factory supported a property of the device
                _LOGGER.debug(
                    "%s - No sensors found for device type - %s",
                    dev.device_name,
                    dev.device_type,
                )

        async_add_entities(entities, update_before_add=True)

    discover(get_domain_data(hass, config_entry, VS_SENSORS))

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_SENSORS), discover)
    )
