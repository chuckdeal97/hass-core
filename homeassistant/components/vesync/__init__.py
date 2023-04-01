"""VeSync integration."""
import logging

from pyvesync import VeSync

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    SERVICE_UPDATE_DEVS,
    VS_DISCOVERY,
    VS_FANS,
    VS_LIGHTS,
    VS_MANAGER,
    VS_SENSORS,
    VS_SWITCHES,
)

PLATFORMS = {
    Platform.FAN: VS_FANS,
    Platform.LIGHT: VS_LIGHTS,
    Platform.SENSOR: VS_SENSORS,
    Platform.SWITCH: VS_SWITCHES,
}

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Vesync as config entry."""
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    time_zone = str(hass.config.time_zone)

    manager = VeSync(username, password, time_zone)

    login = await hass.async_add_executor_job(manager.login)

    if not login:
        _LOGGER.error("Unable to login to the VeSync server")
        return False

    device_dict = await _async_process_devices(hass, manager)

    forward_setup = hass.config_entries.async_forward_entry_setup

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_MANAGER] = manager

    for platform, domain in PLATFORMS.items():
        hass.data[DOMAIN][config_entry.entry_id][domain] = []
        if device_dict[domain]:
            hass.data[DOMAIN][config_entry.entry_id][domain].extend(device_dict[domain])
            hass.async_create_task(
                forward_setup(config_entry, platform),
                name=f"config entry forward setup {config_entry.title} {config_entry.domain} {config_entry.entry_id} {platform}",
            )

    async def async_new_device_discovery(service: ServiceCall) -> None:
        """Discover if new devices should be added."""
        await _async_new_device_discovery(hass, config_entry, forward_setup, service)

    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_DEVS, async_new_device_discovery
    )

    return True


async def _async_new_device_discovery(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    forward_setup,
    service: ServiceCall,
) -> None:
    """Discover if new devices should be added."""
    manager = hass.data[DOMAIN][config_entry.entry_id][VS_MANAGER]
    dev_dict = await _async_process_devices(hass, manager)

    def _add_new_devices(platform: str, domain: str) -> None:
        """Add new devices to hass."""
        old_devices = hass.data[DOMAIN][config_entry.entry_id][domain]
        if new_devices := list(set(dev_dict.get(domain, [])).difference(old_devices)):
            if old_devices:
                # must do assignment here to prevent changing the list before using as conditional
                old_devices.extend(new_devices)
                async_dispatcher_send(hass, VS_DISCOVERY.format(domain), new_devices)
            else:
                # must do assignment here because forward_setup method uses the list
                old_devices.extend(new_devices)
                hass.async_create_task(forward_setup(config_entry, platform))

    for platform, domain in PLATFORMS.items():
        _add_new_devices(platform, domain)


async def _async_process_devices(
    hass: HomeAssistant, manager: VeSync
) -> dict[str, list]:
    """Assign devices to proper component."""
    devices: dict[str, list] = {}
    for domain in PLATFORMS.values():
        devices[domain] = []

    await hass.async_add_executor_job(manager.update)

    if manager.fans:
        devices[VS_FANS].extend(manager.fans)
        # Expose fan sensors separately
        devices[VS_SENSORS].extend(manager.fans)
        _LOGGER.info("%d VeSync fans found", len(manager.fans))

    if manager.bulbs:
        devices[VS_LIGHTS].extend(manager.bulbs)
        _LOGGER.info("%d VeSync lights found", len(manager.bulbs))

    if manager.outlets:
        devices[VS_SWITCHES].extend(manager.outlets)
        # Expose outlets' voltage, power & energy usage as separate sensors
        devices[VS_SENSORS].extend(manager.outlets)
        _LOGGER.info("%d VeSync outlets found", len(manager.outlets))

    if manager.switches:
        for switch in manager.switches:
            if not switch.is_dimmable():
                devices[VS_SWITCHES].append(switch)
            else:
                devices[VS_LIGHTS].append(switch)
        _LOGGER.info("%d VeSync switches found", len(manager.switches))

    return devices


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, list(PLATFORMS.keys())
    )
    if unload_ok and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
