"""Common utilities for VeSync Component."""
import abc
from itertools import chain
import logging
from typing import Any, Generic, TypeVar

from pyvesync.vesyncbasedevice import VeSyncBaseDevice
from pyvesync.vesyncfan import air_features, humid_features
from pyvesync.vesyncoutlet import outlet_config as outlet_features
from pyvesync.vesyncswitch import feature_dict as switch_features

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity, ToggleEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_domain_data(hass: HomeAssistant, config_entry: ConfigEntry, key: str) -> Any:
    """Get value of this domain's data."""
    if DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]:
        return hass.data[DOMAIN][config_entry.entry_id][key]
    return None


class VeSyncDeviceHelper:
    """Collection of VeSync device helpers."""

    air_models: set | None = None
    dim_switch_models: set | None = None
    humidifier_models: set | None = None
    outlet_models: set | None = None
    switch_models: set | None = None

    def get_feature(
        self, device: VeSyncBaseDevice, dictionary: str, attribute: str
    ) -> Any:
        """Return the value of the feature."""
        return getattr(device, dictionary, {}).get(attribute, None)

    def has_feature(
        self, device: VeSyncBaseDevice, dictionary: str, attribute: str
    ) -> bool:
        """Return true if the feature is available."""
        return self.get_feature(device, dictionary, attribute) is not None

    def is_air_purifier(self, device_type: str) -> bool:
        """Return true if the device type is an air_purifier."""
        if self.air_models is None:
            # cache the model list after the first use
            self.air_models = set(
                chain(*[features["models"] for features in air_features.values()]),
            ).union(set(air_features.keys()))
            _LOGGER.debug(
                "Initialized air_models cache with %d models",
                len(self.air_models),
            )

        return device_type in self.air_models

    def is_dimmable_switch(self, device_type: str) -> bool:
        """Return true if the device type is a switch."""
        if self.dim_switch_models is None:
            # cache the model list after the first use
            switches = self._process_switches()
            self.dim_switch_models = set(switches["dimmable"])
            _LOGGER.debug(
                "Initialized dim_switch_models cache with %d models",
                len(self.dim_switch_models),
            )

        return device_type in self.dim_switch_models

    def is_humidifier(self, device_type: str) -> bool:
        """Return true if the device type is a humidifier."""
        if self.humidifier_models is None:
            # cache the model list after the first use
            self.humidifier_models = set(
                chain(*[features["models"] for features in humid_features.values()]),
            ).union(set(humid_features.keys()))
            _LOGGER.debug(
                "Initialized humidifier_models cache with %d models",
                len(self.humidifier_models),
            )

        return device_type in self.humidifier_models

    def is_outlet(self, device_type: str) -> bool:
        """Return true if the device type is an outlet."""
        if self.outlet_models is None:
            # cache the model list after the first use
            self.outlet_models = set(outlet_features.keys())
            _LOGGER.debug(
                "Initialized outlet_models cache with %d models",
                len(self.outlet_models),
            )

        return device_type in self.outlet_models

    def is_switch(self, device_type: str) -> bool:
        """Return true if the device type is a switch."""
        if self.switch_models is None:
            # cache the model list after the first use
            switches = self._process_switches()
            self.switch_models = set(switches["non-dimmable"])
            _LOGGER.debug(
                "Initialized switch_models cache with %d models",
                len(self.switch_models),
            )

        return device_type in self.switch_models

    def reset_cache(self) -> None:
        """Reset the helper caches."""
        self.air_models = None
        self.dim_switch_models = None
        self.humidifier_models = None
        self.outlet_models = None
        self.switch_models = None

    def _process_switches(self) -> dict[str, list[str]]:
        """Process the vesync feature dict for switches."""
        switches: dict[str, list[str]] = {"dimmable": [], "non-dimmable": []}
        for key, value in switch_features.items():
            if "dimmable" in value["features"]:
                switches["dimmable"].append(key)
            else:
                switches["non-dimmable"].append(key)
        return switches


DEVICE_HELPER = VeSyncDeviceHelper()


class VeSyncBaseEntity(Entity):
    """Base class for VeSync Entity Representations."""

    device: VeSyncBaseDevice

    def __init__(self, device: VeSyncBaseDevice) -> None:
        """Initialize the VeSync device."""
        self.device = device
        self._attr_unique_id = self.base_unique_id
        self._attr_name = self.base_name

    @property
    def base_unique_id(self):
        """Return the ID of this device."""
        # The unique_id property may be overridden in subclasses, such as in
        # sensors. Maintaining base_unique_id allows us to group related
        # entities under a single device.
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{str(self.device.sub_device_no)}"
        return self.device.cid

    @property
    def base_name(self) -> str:
        """Return the name of the device."""
        # Same story here as `base_unique_id` above
        return self.device.device_name

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self.device.connection_status == "online"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.base_unique_id)},
            name=self.base_name,
            model=self.device.device_type,
            default_manufacturer="VeSync",
            sw_version=self.device.current_firm_version,
        )

    def update(self) -> None:
        """Update vesync device."""
        self.device.update()


class VeSyncDevice(VeSyncBaseEntity, ToggleEntity):
    """Base class for VeSync Device Representations."""

    @property
    def details(self):
        """Provide access to the device details dictionary."""
        return self.device.details

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self.device.device_status == "on"

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self.device.turn_off()


T = TypeVar("T")
U = TypeVar("U")


class VeSyncEntityDescriptionFactory(Generic[T, U], metaclass=abc.ABCMeta):
    """Describe a factory interface for creating EntityDescription objects."""

    object_class: U

    @classmethod
    def __subclasshook__(cls, subclass):
        """Impl of meta data."""
        return (
            hasattr(subclass, "create")
            and callable(subclass.create)
            and hasattr(subclass, "supports")
            and callable(subclass.supports)
        )

    @abc.abstractmethod
    def create(self, device: VeSyncBaseDevice) -> T:
        """Interface method for create."""

    @abc.abstractmethod
    def supports(self, device: VeSyncBaseDevice) -> bool:
        """Interface method for supports."""
