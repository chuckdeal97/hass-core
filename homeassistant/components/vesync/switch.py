"""Support for VeSync switches."""
from dataclasses import dataclass
import logging
from typing import Any

from pyvesync.vesyncbasedevice import VeSyncBaseDevice
from pyvesync.vesyncoutlet import VeSyncOutlet
from pyvesync.vesyncswitch import VeSyncSwitch

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import (
    DEVICE_HELPER,
    VeSyncDevice,
    VeSyncEntityDescriptionFactory,
    get_domain_data,
)
from .const import VS_DISCOVERY, VS_SWITCHES

_LOGGER = logging.getLogger(__name__)


@dataclass
class VeSyncSwitchEntityDescription(SwitchEntityDescription):
    """Describe VeSync switch entity."""

    device_class: SwitchDeviceClass | None = SwitchDeviceClass.SWITCH
    icon: str | None = "mdi:light-switch"


@dataclass
class VeSyncOutletEntityDescription(VeSyncSwitchEntityDescription):
    """Describe VeSync outlet entity."""

    device_class: SwitchDeviceClass | None = SwitchDeviceClass.OUTLET
    icon: str | None = "mdi-power-socket"


class VeSyncBaseSwitch(VeSyncDevice, SwitchEntity):
    """Base class for VeSync switch Device Representations."""

    entity_description: VeSyncSwitchEntityDescription

    def __init__(
        self,
        switch: VeSyncSwitch | VeSyncOutlet,
        description: VeSyncSwitchEntityDescription,
    ) -> None:
        """Initialize the VeSync switch device."""
        super().__init__(switch)
        self.entity_description = description

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        self.device.turn_on()


class VeSyncSwitchHA(VeSyncBaseSwitch, SwitchEntity):
    """Representation of a VeSync switch."""

    device: VeSyncSwitch


class VeSyncOutletHA(VeSyncBaseSwitch, SwitchEntity):
    """Representation of a VeSync switch."""

    device: VeSyncOutlet

    def update(self) -> None:
        """Update outlet details and energy usage."""
        self.device.update()
        self.device.update_energy()


class VeSyncDisplayHA(VeSyncSwitchHA):
    """Representation of the display on a VeSync humidifier."""

    def __init__(
        self,
        switch: VeSyncSwitch,
        description: VeSyncSwitchEntityDescription,
    ) -> None:
        """Initialize the VeSync switch device."""
        super().__init__(switch, description)
        self._attr_name = f"{super().name} {description.name}"
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    @property
    def is_on(self) -> bool:
        """Return True if display is on."""
        return self.device.details["display"]

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the display on."""
        self.device.turn_on_display()

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the display off."""
        self.device.turn_off_display()


class VeSyncAutomaticStopHA(VeSyncSwitchHA):
    """Representation of the automatic stop toggle on a VeSync humidifier."""

    def __init__(
        self,
        switch: VeSyncSwitch,
        description: VeSyncSwitchEntityDescription,
    ) -> None:
        """Initialize the VeSync switch device."""
        super().__init__(switch, description)
        self._attr_name = f"{super().name} {description.name}"
        self._attr_unique_id = f"{super().unique_id}-{description.key}"

    @property
    def is_on(self) -> bool:
        """Return True if automatic stop is on."""
        return self.device.config["automatic_stop"]

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the automatic stop on."""
        self.device.automatic_stop_on()

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the automatic stop off."""
        self.device.automatic_stop_off()


class SwitchEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[VeSyncSwitchEntityDescription, type[VeSyncSwitchHA]]
):
    """Create an entity description for a device that is a switch."""

    object_class = VeSyncSwitchHA

    def create(self, device: VeSyncBaseDevice) -> VeSyncSwitchEntityDescription:
        """Create a VeSyncSwitchEntityDescription."""
        return VeSyncSwitchEntityDescription(
            key="", entity_category=EntityCategory.CONFIG
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device is an switch."""
        return DEVICE_HELPER.is_switch(device.device_type)


class OutletEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[VeSyncSwitchEntityDescription, type[VeSyncOutletHA]]
):
    """Create an entity description for a device that is an outlet."""

    object_class = VeSyncOutletHA

    def create(self, device: VeSyncBaseDevice) -> VeSyncSwitchEntityDescription:
        """Create a VeSyncSwitchEntityDescription."""
        return VeSyncOutletEntityDescription(
            key="", entity_category=EntityCategory.CONFIG
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device is an outlet."""
        return DEVICE_HELPER.is_outlet(device.device_type)


class DisplayEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[VeSyncSwitchEntityDescription, type[VeSyncDisplayHA]]
):
    """Create an entity description for a device that supports a display."""

    object_class = VeSyncDisplayHA

    def create(self, device: VeSyncBaseDevice) -> VeSyncSwitchEntityDescription:
        """Create a VeSyncSwitchEntityDescription."""
        return VeSyncSwitchEntityDescription(
            key="display",
            name="Display",
            entity_category=EntityCategory.CONFIG,
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports a display feature."""
        return hasattr(device, "set_display") and callable(device.set_display)


class AutomaticStopEntityDescriptionFactory(
    VeSyncEntityDescriptionFactory[
        VeSyncSwitchEntityDescription, type[VeSyncAutomaticStopHA]
    ]
):
    """Create an entity description for a device that supports a display."""

    object_class = VeSyncAutomaticStopHA

    def create(self, device: VeSyncBaseDevice) -> VeSyncSwitchEntityDescription:
        """Create a VeSyncSwitchEntityDescription."""
        return VeSyncSwitchEntityDescription(
            key="automatic-stop",
            name="Automatic Stop",
            entity_category=EntityCategory.CONFIG,
        )

    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Determine if this device supports a display feature."""
        return hasattr(device, "set_automatic_stop") and callable(
            device.set_automatic_stop
        )


_FACTORIES: list[VeSyncEntityDescriptionFactory] = [
    SwitchEntityDescriptionFactory(),
    OutletEntityDescriptionFactory(),
    DisplayEntityDescriptionFactory(),
    AutomaticStopEntityDescriptionFactory(),
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
        entities: list[SwitchEntity] = []
        for dev in devices:
            supported = False
            for factory in _FACTORIES:
                if factory.supports(dev):
                    supported = True
                    entities.append(factory.object_class(dev, factory.create(dev)))

            if not supported:
                # if no factory supported a property of the device
                _LOGGER.warning(
                    "%s - Unsupported device type - %s",
                    dev.device_name,
                    dev.device_type,
                )

        async_add_entities(entities, update_before_add=True)

    discover(get_domain_data(hass, config_entry, VS_SWITCHES))

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_SWITCHES), discover)
    )
