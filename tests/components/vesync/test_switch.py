"""Tests for VeSync air purifiers."""
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from pyvesync.vesyncfan import VeSyncAirBypass, VeSyncHumid200300S
from pyvesync.vesyncoutlet import VeSyncOutlet
from pyvesync.vesyncswitch import VeSyncSwitch

from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.vesync import DOMAIN, VS_SWITCHES
from homeassistant.components.vesync.common import VeSyncDevice
from homeassistant.components.vesync.switch import (
    AutomaticStopEntityDescriptionFactory,
    ChildLockEntityDescriptionFactory,
    DisplayEntityDescriptionFactory,
    OutletEntityDescriptionFactory,
    SwitchEntityDescriptionFactory,
    VeSyncAutomaticStopHA,
    VeSyncChildLockHA,
    VeSyncDisplayHA,
    VeSyncOutletEntityDescription,
    VeSyncOutletHA,
    VeSyncSwitchEntityDescription,
    VeSyncSwitchHA,
    async_setup_entry,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import OUTLET_MODEL, SWITCH_MODEL


async def test_async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    outlet_features,
    switch_features,
    switch: VeSyncSwitch,
    outlet: VeSyncOutlet,
    humidifier: VeSyncHumid200300S,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the discovery mechanism can handle supported devices."""
    caplog.set_level(logging.INFO)

    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_SWITCHES] = [switch, outlet, humidifier]
    with patch.object(config_entry, "async_on_unload") as mock_on_unload, patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_outlet_features, patch(
        "homeassistant.components.vesync.common.switch_features"
    ) as mock_switch_features:
        mock_outlet_features.keys.side_effect = outlet_features.keys
        mock_switch_features.items.side_effect = switch_features.items

        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    callback.assert_called_once()
    assert len(callback.call_args.args[0]) == 4
    assert callback.call_args.args[0][0].device == switch
    assert callback.call_args.args[0][1].device == outlet
    assert callback.call_args.args[0][2].device == humidifier
    assert callback.call_args.args[0][3].device == humidifier
    assert callback.call_args.kwargs == {"update_before_add": True}
    mock_on_unload.assert_called_once()
    assert len(caplog.records) == 0


async def test_async_setup_entry__empty(
    hass: HomeAssistant,
    config_entry,
    outlet_features,
    switch_features,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the discovery mechanism can handle no devices."""
    caplog.set_level(logging.INFO)

    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_SWITCHES] = []
    with patch.object(config_entry, "async_on_unload") as mock_on_unload, patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_outlet_features, patch(
        "homeassistant.components.vesync.common.switch_features"
    ) as mock_switch_features:
        mock_outlet_features.keys.side_effect = outlet_features.keys
        mock_switch_features.items.side_effect = switch_features.items

        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    callback.assert_called_once()
    assert callback.call_args.args == ([],)
    assert callback.call_args.kwargs == {"update_before_add": True}
    mock_on_unload.assert_called_once()
    assert len(caplog.records) == 0


async def test_async_setup_entry__invalid(
    hass: HomeAssistant,
    config_entry,
    outlet_features,
    switch_features,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the discovery mechanism can handle unsupported devices."""
    caplog.set_level(logging.INFO)

    mock_switch = MagicMock(VeSyncSwitch)
    mock_switch.device_type = "invalid_type"
    mock_switch.device_name = "invalid_name"
    mock_switch.set_display = None
    mock_switch.set_automatic_stop = None

    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_SWITCHES] = [mock_switch]
    with patch.object(config_entry, "async_on_unload") as mock_on_unload, patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_outlet_features, patch(
        "homeassistant.components.vesync.common.switch_features"
    ) as mock_switch_features:
        mock_outlet_features.keys.side_effect = outlet_features.keys
        mock_switch_features.items.side_effect = switch_features.items

        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    callback.assert_called_once()
    assert callback.call_args.args == ([],)
    assert callback.call_args.kwargs == {"update_before_add": True}
    mock_on_unload.assert_called_once()
    assert caplog.messages[0] == "invalid_name - Unsupported device type - invalid_type"


async def test_switch_entity__init(switch: VeSyncSwitch) -> None:
    """Test the switch entity constructor."""
    description = VeSyncSwitchEntityDescription(
        key="",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncSwitchHA(switch, description)

    assert entity.device == switch
    assert entity.device_class == SwitchDeviceClass.SWITCH
    assert entity.entity_category is None
    assert entity.entity_description == description
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon == "mdi:light-switch"
    assert entity.name == "device name"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1"


async def test_switch_entity__extra_state_attributes(
    switch: VeSyncSwitch,
) -> None:
    """Test the switch extra_state_attributes impl."""
    description = VeSyncSwitchEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncSwitchHA(switch, description)

    assert entity.extra_state_attributes is None


async def test_switch_entity__is_on(switch: VeSyncSwitch) -> None:
    """Test the switch is_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncSwitchHA(switch, description)

    switch.device_status = "on"
    assert entity.is_on is True
    switch.device_status = "not on"
    assert entity.is_on is False


async def test_switch_entity__turn_off(switch: VeSyncSwitch) -> None:
    """Test the switch turn_off impl."""
    description = VeSyncSwitchEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncSwitchHA(switch, description)

    entity.turn_off()
    assert switch.turn_off.call_count == 1


async def test_switch_entity__turn_on(switch: VeSyncSwitch) -> None:
    """Test the switch turn_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncSwitchHA(switch, description)

    entity.turn_on()
    assert switch.turn_on.call_count == 1


async def test_outlet_entity__init(outlet: VeSyncOutlet) -> None:
    """Test the outlet entity constructor."""
    description = VeSyncOutletEntityDescription(
        key="",
        icon="mdi-power-socket",
        device_class=SwitchDeviceClass.OUTLET,
    )
    entity = VeSyncOutletHA(outlet, description)

    assert entity.device == outlet
    assert entity.device_class == SwitchDeviceClass.OUTLET
    assert entity.entity_category is None
    assert entity.entity_description == description
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon == "mdi-power-socket"
    assert entity.name == "device name"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1"


async def test_outlet_entity__extra_state_attributes(outlet: VeSyncOutlet) -> None:
    """Test the outlet entity extra_attributes impl."""
    description = VeSyncOutletEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi-power-socket",
        device_class=SwitchDeviceClass.OUTLET,
    )
    entity = VeSyncOutletHA(outlet, description)

    assert entity.extra_state_attributes == {
        "voltage": 1,
        "weekly_energy_total": 2,
        "monthly_energy_total": 3,
        "yearly_energy_total": 4,
    }


async def test_outlet_entity__is_on(outlet: VeSyncOutlet) -> None:
    """Test the outlet entity is_on impl."""
    description = VeSyncOutletEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi-power-socket",
        device_class=SwitchDeviceClass.OUTLET,
    )
    entity = VeSyncOutletHA(outlet, description)

    outlet.device_status = "on"
    assert entity.is_on is True
    outlet.device_status = "not on"
    assert entity.is_on is False


async def test_outlet_entity__turn_off(outlet: VeSyncOutlet) -> None:
    """Test the outlet entity turn_off impl."""
    description = VeSyncOutletEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi-power-socket",
        device_class=SwitchDeviceClass.OUTLET,
    )
    entity = VeSyncOutletHA(outlet, description)

    entity.turn_off()
    assert outlet.turn_off.call_count == 1


async def test_outlet_entity__turn_on(outlet: VeSyncOutlet) -> None:
    """Test the outlet entity turn_on impl."""
    description = VeSyncOutletEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi-power-socket",
        device_class=SwitchDeviceClass.OUTLET,
    )
    entity = VeSyncOutletHA(outlet, description)

    entity.turn_on()
    assert outlet.turn_on.call_count == 1


async def test_outlet_entity__update(outlet: VeSyncOutlet) -> None:
    """Test the outlet entity update impl."""
    description = VeSyncOutletEntityDescription(
        key="desc-key",
        name="Desc Name",
        icon="mdi-power-socket",
        device_class=SwitchDeviceClass.OUTLET,
    )
    entity = VeSyncOutletHA(outlet, description)

    entity.update()
    assert outlet.update.call_count == 1
    assert outlet.update_energy.call_count == 1


async def test_automatic_stop_entity__init(humidifier: VeSyncHumid200300S) -> None:
    """Test the automatic_stop entity constructor."""
    description = VeSyncSwitchEntityDescription(
        key="automatic-stop",
        name="Automatic Stop",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncAutomaticStopHA(humidifier, description)

    assert entity.device == humidifier
    assert entity.device_class == SwitchDeviceClass.SWITCH
    assert entity.entity_category is None
    assert entity.entity_description == description
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon == "mdi:light-switch"
    assert entity.name == "device name Automatic Stop"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1-automatic-stop"


async def test_automatic_stop_entity__is_on(humidifier: VeSyncHumid200300S) -> None:
    """Test the automatic_stop entity is_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="automatic-stop",
        name="Automatic Stop",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncAutomaticStopHA(humidifier, description)

    humidifier.config["automatic_stop"] = False
    assert entity.is_on is False
    humidifier.config["automatic_stop"] = True
    assert entity.is_on is True


async def test_automatic_stop_entity__turn_off(humidifier: VeSyncHumid200300S) -> None:
    """Test the automatic_stop entity turn_off impl."""
    description = VeSyncSwitchEntityDescription(
        key="automatic-stop",
        name="Automatic Stop",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncAutomaticStopHA(humidifier, description)

    entity.turn_off()
    assert humidifier.turn_off.call_count == 0
    assert humidifier.automatic_stop_off.call_count == 1


async def test_automatic_stop_entity__turn_on(humidifier: VeSyncHumid200300S) -> None:
    """Test the automatic_stop entity turn_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="automatic-stop",
        name="Automatic Stop",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncAutomaticStopHA(humidifier, description)

    entity.turn_on()
    assert humidifier.turn_on.call_count == 0
    assert humidifier.automatic_stop_on.call_count == 1


async def test_child_lock_entity__init(fan: VeSyncAirBypass) -> None:
    """Test the child_lock entity constructor."""
    description = VeSyncSwitchEntityDescription(
        key="child-lock",
        name="Child Lock",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncChildLockHA(fan, description)

    assert entity.device == fan
    assert entity.device_class == SwitchDeviceClass.SWITCH
    assert entity.entity_category is None
    assert entity.entity_description == description
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon == "mdi:light-switch"
    assert entity.name == "device name Child Lock"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1-child-lock"


async def test_child_lock_entity__is_on(fan: VeSyncAirBypass) -> None:
    """Test the child_lock entity is_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="child-lock",
        name="Child Lock",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncChildLockHA(fan, description)

    fan.details["child_lock"] = False
    assert entity.is_on is False
    fan.details["child_lock"] = True
    assert entity.is_on is True


async def test_child_lock_entity__turn_off(fan: VeSyncAirBypass) -> None:
    """Test the child_lock entity turn_off impl."""
    description = VeSyncSwitchEntityDescription(
        key="child-lock",
        name="Child Lock",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncChildLockHA(fan, description)

    entity.turn_off()
    assert fan.turn_off.call_count == 0
    assert fan.child_lock_off.call_count == 1


async def test_child_lock_entity__turn_on(fan: VeSyncAirBypass) -> None:
    """Test the child_lock entity turn_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="child-lock",
        name="Child Lock",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncChildLockHA(fan, description)

    entity.turn_on()
    assert fan.turn_on.call_count == 0
    assert fan.child_lock_on.call_count == 1


async def test_display_entity__init(humidifier: VeSyncHumid200300S) -> None:
    """Test the display entity constructor."""
    description = VeSyncSwitchEntityDescription(
        key="display",
        name="Display",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncDisplayHA(humidifier, description)

    assert entity.device == humidifier
    assert entity.device_class == SwitchDeviceClass.SWITCH
    assert entity.entity_category is None
    assert entity.entity_description == description
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon == "mdi:light-switch"
    assert entity.name == "device name Display"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1-display"


async def test_display_entity__is_on(humidifier: VeSyncHumid200300S) -> None:
    """Test the display entity is_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="display",
        name="Display",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncDisplayHA(humidifier, description)

    humidifier.details["display"] = False
    assert entity.is_on is False
    humidifier.details["display"] = True
    assert entity.is_on is True


async def test_display_entity__turn_off(humidifier: VeSyncHumid200300S) -> None:
    """Test the display entity turn_off impl."""
    description = VeSyncSwitchEntityDescription(
        key="display",
        name="Display",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncDisplayHA(humidifier, description)

    entity.turn_off()
    assert humidifier.turn_off.call_count == 0
    assert humidifier.turn_off_display.call_count == 1


async def test_display_entity__turn_on(humidifier: VeSyncHumid200300S) -> None:
    """Test the display entity turn_on impl."""
    description = VeSyncSwitchEntityDescription(
        key="display",
        name="Display",
        icon="mdi:light-switch",
        device_class=SwitchDeviceClass.SWITCH,
    )
    entity = VeSyncDisplayHA(humidifier, description)

    entity.turn_on()
    assert humidifier.turn_on.call_count == 0
    assert humidifier.turn_on_display.call_count == 1


async def test_automatic_stop_factory__create() -> None:
    """Test the Automatic Stop Factory creates impl."""
    factory = AutomaticStopEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)

    description = factory.create(device)
    assert description
    assert description.device_class == SwitchDeviceClass.SWITCH
    assert description.entity_category == EntityCategory.CONFIG
    assert description.icon == "mdi:light-switch"
    assert description.key == "automatic-stop"
    assert description.name == "Automatic Stop"


async def test_automatic_stop_factory__supports() -> None:
    """Test the Automatic Stop Factory supports impl."""
    factory = AutomaticStopEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)
    device.set_automatic_stop = None
    assert factory.supports(device) is False
    device.set_automatic_stop = Mock()
    assert factory.supports(device) is True


async def test_child_lock_factory__create() -> None:
    """Test the Child Lock Factory creates impl."""
    factory = ChildLockEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)

    description = factory.create(device)
    assert description
    assert description.device_class == SwitchDeviceClass.SWITCH
    assert description.entity_category == EntityCategory.CONFIG
    assert description.icon == "mdi:light-switch"
    assert description.key == "child-lock"
    assert description.name == "Child Lock"


async def test_child_lock_factory__supports() -> None:
    """Test the Child Lock Factory supports impl."""
    factory = ChildLockEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)
    device.set_child_lock = None
    assert factory.supports(device) is False
    device.set_child_lock = Mock()
    assert factory.supports(device) is True


async def test_display_factory__create() -> None:
    """Test the Display Factory creates impl."""
    factory = DisplayEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)

    description = factory.create(device)
    assert description
    assert description.device_class == SwitchDeviceClass.SWITCH
    assert description.entity_category == EntityCategory.CONFIG
    assert description.icon == "mdi:light-switch"
    assert description.key == "display"
    assert description.name == "Display"


async def test_display_factory__supports() -> None:
    """Test the Display Factory supports impl."""
    factory = DisplayEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)
    device.set_display = None
    assert factory.supports(device) is False
    device.set_display = Mock()
    assert factory.supports(device) is True


async def test_outlet_factory__create() -> None:
    """Test the Outlet Factory creates impl."""
    factory = OutletEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)

    description = factory.create(device)
    assert description
    assert description.device_class == SwitchDeviceClass.OUTLET
    assert description.entity_category == EntityCategory.CONFIG
    assert description.icon == "mdi-power-socket"
    assert description.key == ""
    assert description.name is None


async def test_outlet_factory__supports(outlet_features) -> None:
    """Test the Outlet Factory supports impl."""
    factory = OutletEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)
    with patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_outlet_features:
        mock_outlet_features.keys.side_effect = outlet_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = OUTLET_MODEL
        assert factory.supports(device) is True


async def test_switch_factory__create() -> None:
    """Test the Switch Factory creates impl."""
    factory = SwitchEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)

    description = factory.create(device)
    assert description
    assert description.device_class == SwitchDeviceClass.SWITCH
    assert description.entity_category == EntityCategory.CONFIG
    assert description.icon == "mdi:light-switch"
    assert description.key == ""
    assert description.name is None


async def test_switch_factory__supports(switch_features) -> None:
    """Test the Switch Factory supports impl."""
    factory = SwitchEntityDescriptionFactory()

    device = MagicMock(VeSyncDevice)
    with patch(
        "homeassistant.components.vesync.common.switch_features"
    ) as mock_features:
        mock_features.items.side_effect = switch_features.items
        mock_features.values.side_effect = switch_features.values
        mock_features.keys.side_effect = switch_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = SWITCH_MODEL
        assert factory.supports(device) is True
