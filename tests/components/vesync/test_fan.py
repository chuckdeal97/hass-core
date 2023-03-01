"""Tests for the fan module."""
import pytest
import requests_mock
from syrupy import SnapshotAssertion

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    DOMAIN as FAN_DOMAIN,
    FanEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.components.humidifier import MODE_AUTO, MODE_SLEEP
from homeassistant.const import ATTR_FRIENDLY_NAME, ATTR_SUPPORTED_FEATURES, STATE_ON

from .common import ALL_DEVICE_NAMES, mock_devices_response

from tests.common import MockConfigEntry


@pytest.mark.parametrize("device_name", ALL_DEVICE_NAMES)
async def test_fan_state(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    requests_mock: requests_mock.Mocker,
    device_name: str,
) -> None:
    """Test the resulting setup state is as expected for the platform."""

    # Configure the API devices call for device_name
    mock_devices_response(requests_mock, device_name)

    # setup platform - only including the named device
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Check device registry
    devices = dr.async_entries_for_config_entry(device_registry, config_entry.entry_id)
    assert devices == snapshot(name="devices")

    # Check entity registry
    entities = [
        entity
        for entity in er.async_entries_for_config_entry(
            entity_registry, config_entry.entry_id
        )
        if entity.domain == FAN_DOMAIN
    ]
    assert entities == snapshot(name="entities")

    # Check states
    for entity in entities:
        assert hass.states.get(entity.entity_id) == snapshot(name=entity.entity_id)


async def test_attributes_air_purifier(hass, setup_platform):
    """Test the air purifier attributes are correct."""
    state = hass.states.get("fan.air_purifier_400s")
    assert state.state == STATE_ON
    assert state.attributes.get(ATTR_PERCENTAGE) == 25
    assert state.attributes.get(ATTR_PERCENTAGE_STEP) == 25
    assert state.attributes.get(ATTR_PRESET_MODE) is None
    assert state.attributes.get(ATTR_PRESET_MODES) == [
        MODE_AUTO,
        MODE_SLEEP,
    ]
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Air Purifier 400s"
    assert state.attributes.get(ATTR_SUPPORTED_FEATURES) == FanEntityFeature.SET_SPEED
