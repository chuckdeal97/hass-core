"""Tests for VeSync numbers."""
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from pyvesync.vesyncbulb import VeSyncBulb

from homeassistant.components.light import ColorMode, LightEntityFeature
from homeassistant.components.vesync import DOMAIN, VS_LIGHTS
from homeassistant.components.vesync.light import (
    VeSyncDimmableLightHA,
    VeSyncTunableWhiteLightHA,
    _ha_brightness_to_vesync,
    _vesync_brightness_to_ha,
    async_setup_entry,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def test_async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    bulb: VeSyncBulb,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the discovery mechanism can handle supported devices."""
    caplog.set_level(logging.INFO)

    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_LIGHTS] = [bulb]
    with patch.object(config_entry, "async_on_unload") as mock_on_unload, patch(
        "homeassistant.components.vesync.light.DEV_TYPE_TO_HA"
    ) as mock_mapping:
        mock_mapping.get = Mock(return_value="bulb-dimmable")

        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    mock_mapping.get.assert_called_with(bulb.device_type)
    callback.assert_called_once()
    assert len(callback.call_args.args[0]) == 1
    assert callback.call_args.args[0][0].device == bulb
    assert callback.call_args.kwargs == {"update_before_add": True}
    mock_on_unload.assert_called_once()
    assert len(caplog.records) == 0


async def test_async_setup_entry__empty(
    hass: HomeAssistant, config_entry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the discovery mechanism can handle no devices."""
    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_LIGHTS] = []
    with patch.object(config_entry, "async_on_unload") as mock_on_unload:
        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    callback.assert_called_once()
    assert callback.call_args.args == ([],)
    assert callback.call_args.kwargs == {"update_before_add": True}
    mock_on_unload.assert_called_once()
    assert len(caplog.records) == 0


async def test_async_setup_entry__invalid(
    hass: HomeAssistant, config_entry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the discovery mechanism can handle unsupported devices."""
    caplog.set_level(logging.INFO)

    mock_bulb = MagicMock(VeSyncBulb)
    mock_bulb.device_type = "invalid_type"
    mock_bulb.device_name = "invalid_name"
    details = {}
    mock_bulb.details = details
    config_dict = {}
    mock_bulb.config_dict = config_dict

    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_LIGHTS] = [mock_bulb]
    with patch.object(config_entry, "async_on_unload") as mock_on_unload:
        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    callback.assert_called_once()
    assert callback.call_args.args == ([],)
    assert callback.call_args.kwargs == {"update_before_add": True}
    mock_on_unload.assert_called_once()
    assert caplog.messages[0] == "invalid_name - Unknown device type - invalid_type"


async def test_vesync_brightness_to_ha() -> None:
    """Test the private _vesync_brightness_to_ha impl ."""
    assert _vesync_brightness_to_ha("100") == 255
    assert _vesync_brightness_to_ha(100) == 255
    assert _vesync_brightness_to_ha(10) == 26
    assert _vesync_brightness_to_ha(0.1) == 3


async def test_vesync_brightness_to_ha__invalid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the private _vesync_brightness_to_ha impl with invalid data."""
    assert _vesync_brightness_to_ha("bright") == 0
    assert (
        caplog.messages[0]
        == "VeSync - received unexpected 'brightness' value from pyvesync api: bright"
    )


async def test_ha_brightness_to_vesync(bulb: VeSyncBulb) -> None:
    """Test the private _ha_brightness_to_vesync impl."""
    assert _ha_brightness_to_vesync("100") == 39
    assert _ha_brightness_to_vesync(100) == 39
    assert _ha_brightness_to_vesync(255) == 100
    assert _ha_brightness_to_vesync(256) == 100
    assert _ha_brightness_to_vesync(1) == 1
    assert _ha_brightness_to_vesync(0.1) == 1


async def test_dimmable_entity__init(bulb: VeSyncBulb) -> None:
    """Test the dimmable light entity constructor."""
    entity = VeSyncDimmableLightHA(bulb)

    assert entity.device == bulb
    assert entity.device_class is None
    assert entity.entity_category is None
    assert hasattr(entity, "entity_description") is False
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon is None
    assert entity.max_mireds == 500
    assert entity.min_mireds == 153
    assert entity.name == "device name"
    assert entity.supported_features == LightEntityFeature(0)
    assert entity.unique_id == "cid1"
    assert entity.unit_of_measurement is None


async def test_dimmable_entity__brightness(bulb: VeSyncBulb) -> None:
    """Test the dimmable light entity brightness impl."""
    entity = VeSyncDimmableLightHA(bulb)
    assert entity.brightness == 255


async def test_dimmable_entity__color_mode(bulb: VeSyncBulb) -> None:
    """Test the dimmable light entity color_mode impl."""
    entity = VeSyncDimmableLightHA(bulb)
    assert entity.color_mode == ColorMode.BRIGHTNESS


async def test_dimmable_entity__supported_color_modes(bulb: VeSyncBulb) -> None:
    """Test the dimmable light entity supported_color_modes impl."""
    entity = VeSyncDimmableLightHA(bulb)
    assert entity.supported_color_modes == {ColorMode.BRIGHTNESS}


async def test_dimmable_entity__turn_on(bulb: VeSyncBulb) -> None:
    """Test the dimmable light entity turn_on impl."""
    entity = VeSyncDimmableLightHA(bulb)
    assert entity.color_mode == ColorMode.BRIGHTNESS
    entity.turn_on()
    bulb.turn_on.assert_called_once()
    bulb.set_brightness.assert_not_called()
    bulb.set_color_temp.assert_not_called()


async def test_dimmable_entity__turn_on_brightness(bulb: VeSyncBulb) -> None:
    """Test the dimmable light entity turn_on impl."""
    entity = VeSyncDimmableLightHA(bulb)
    assert entity.color_mode == ColorMode.BRIGHTNESS
    entity.turn_on(brightness=50)
    bulb.turn_on.assert_not_called()
    bulb.set_brightness.assert_called_once_with(20)
    bulb.set_color_temp.assert_not_called()


async def test_tunable_entity__turn_on_temperature(bulb: VeSyncBulb) -> None:
    """Test the tunable light entity turn_on impl."""
    entity = VeSyncTunableWhiteLightHA(bulb)
    assert entity.color_mode == ColorMode.COLOR_TEMP
    entity.turn_on(color_temp=50)
    bulb.turn_on.assert_not_called()
    bulb.set_brightness.assert_not_called()
    bulb.set_color_temp.assert_called_once_with(100)
