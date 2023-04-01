"""Tests for VeSync common utilities."""
from unittest.mock import MagicMock

import pytest
from pyvesync.vesyncbasedevice import VeSyncBaseDevice

from homeassistant.components.vesync.common import (
    DOMAIN,
    VeSyncBaseEntity,
    VeSyncDevice,
    get_domain_data,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo


async def test_get_domain_data(
    hass: HomeAssistant,
    config_entry,
) -> None:
    """Test helper get_feature."""
    assert not hasattr(hass.data, DOMAIN)
    assert get_domain_data(hass, config_entry, "domain") is None

    hass.data[DOMAIN] = {}
    assert get_domain_data(hass, config_entry, "domain") is None

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    with pytest.raises(KeyError) as ex_info:
        get_domain_data(hass, config_entry, "domain")
    assert ex_info.value.args[0] == "domain"

    hass.data[DOMAIN] = {config_entry.entry_id: {"domain": []}}
    assert get_domain_data(hass, config_entry, "domain") == []

    mock_device = MagicMock()
    hass.data[DOMAIN] = {config_entry.entry_id: {"domain": [mock_device]}}
    assert get_domain_data(hass, config_entry, "domain") == [mock_device]


async def test_base_entity__init(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity constructor."""
    entity = VeSyncBaseEntity(base_device)

    assert entity.device == base_device
    assert entity.device_class is None
    assert entity.entity_category is None
    assert entity.icon is None
    assert entity.name == "device name"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1"


async def test_base_entity__base_unique_id(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity base_unique_id impl."""
    entity = VeSyncBaseEntity(base_device)

    assert entity.base_unique_id == "cid1"
    base_device.sub_device_no = None
    assert entity.base_unique_id == "cid"


async def test_base_entity__base_name(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity base_name impl."""
    entity = VeSyncBaseEntity(base_device)

    assert entity.base_name == "device name"


async def test_base_entity__available(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity available impl."""
    entity = VeSyncBaseEntity(base_device)

    assert entity.available is True
    base_device.connection_status = "not online"
    assert entity.available is False


async def test_base_entity__device_info(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity device_info impl."""
    entity = VeSyncBaseEntity(base_device)

    device_info: DeviceInfo = entity.device_info
    assert device_info
    assert device_info["identifiers"] == {(DOMAIN, "cid1")}
    assert device_info["name"] == "device name"
    assert device_info["model"] == "device type"
    assert device_info["default_manufacturer"] == "VeSync"
    assert device_info["sw_version"] == 0


async def test_base_entity__update(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity update impl."""
    entity = VeSyncDevice(base_device)

    entity.update()

    assert base_device.update.call_count == 1


async def test_base_device__details(base_device: VeSyncBaseDevice) -> None:
    """Test the base device details impl."""
    device = VeSyncDevice(base_device)

    assert device.details == base_device.details


async def test_base_device__is_on(base_device: VeSyncBaseDevice) -> None:
    """Test the base device is_on impl."""
    device = VeSyncDevice(base_device)

    assert device.is_on is True
    base_device.device_status = "not on"
    assert device.is_on is False


async def test_base_device__turn_off(base_device: VeSyncBaseDevice) -> None:
    """Test the base device turn_on impl."""
    device = VeSyncDevice(base_device)

    device.turn_off()

    assert base_device.turn_off.call_count == 1
