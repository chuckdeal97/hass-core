"""Support for number settings on VeSync devices."""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory

from .common import VeSyncBaseEntity
from .const import DEV_TYPE_TO_HA, DOMAIN, VS_DISCOVERY, VS_DISPATCHERS, VS_NUMBERS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up numbers."""

    async def async_discover(devices):
        """Add new devices to platform."""
        _async_setup_entities(devices, async_add_entities)

    disp = async_dispatcher_connect(
        hass, VS_DISCOVERY.format(VS_NUMBERS), async_discover
    )
    hass.data[DOMAIN][VS_DISPATCHERS].append(disp)

    _async_setup_entities(hass.data[DOMAIN][VS_NUMBERS], async_add_entities)


@callback
def _async_setup_entities(devices, async_add_entities):
    """Check if device is online and add entity."""
    entities = []
    for dev in devices:
        if DEV_TYPE_TO_HA.get(dev.device_type) == "humidifier":
            entities.append(VeSyncHumidifierMistLevelHA(dev))
        else:
            _LOGGER.debug(
                "%s - Unknown device type - %s", dev.device_name, dev.device_type
            )
            continue

    async_add_entities(entities, update_before_add=True)


class VeSyncHumidifierNumberEntity(VeSyncBaseEntity, NumberEntity):
    """Representation of a number for configuring a VeSync humidifier."""

    def __init__(self, humidifier):
        """Initialize the VeSync humidifier device."""
        super().__init__(humidifier)
        self.smarthumidifier = humidifier

    @property
    def entity_category(self):
        """Return the diagnostic entity category."""
        return EntityCategory.CONFIG


class VeSyncHumidifierMistLevelHA(VeSyncHumidifierNumberEntity):
    """Representation of the mist level of a VeSync humidifier."""

    _attr_max_value = 9
    _attr_min_value = 1
    _attr_step = 1

    @property
    def unique_id(self):
        """Return the ID of this device."""
        return f"{super().unique_id}-mist-level"

    @property
    def name(self):
        """Return the name of the device."""
        return f"{super().name} mist level"

    @property
    def value(self):
        """Return the mist level."""
        return self.device.details["mist_virtual_level"]

    def set_value(self, value):
        """Set the mist level."""
        self.device.set_mist_level(int(value))
