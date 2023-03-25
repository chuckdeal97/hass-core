"""Tests for VeSync air purifiers."""
import logging
from unittest.mock import MagicMock, Mock, patch

import pytest
from pyvesync.vesyncbasedevice import VeSyncBaseDevice
from pyvesync.vesyncfan import VeSyncAirBypass, VeSyncHumid200300S

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.vesync import DOMAIN, VS_SENSORS
from homeassistant.components.vesync.sensor import (
    AirQualityEntityDescriptionFactory,
    CurrentPowerEntityDescriptionFactory,
    EnergyMonthlyEntityDescriptionFactory,
    EnergyTodayEntityDescriptionFactory,
    EnergyWeeklyEntityDescriptionFactory,
    EnergyYearlyEntityDescriptionFactory,
    FilterLifeEntityDescriptionFactory,
    HumidityEntityDescriptionFactory,
    PM25EntityDescriptionFactory,
    VeSyncEnergySensorEntity,
    VeSyncSensorEntity,
    VeSyncSensorEntityDescription,
    VoltageEntityDescriptionFactory,
    async_setup_entry,
)
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import OUTLET_MODEL


async def test_async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    humidifier: VeSyncHumid200300S,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the discovery mechanism can handle supported devices."""
    caplog.set_level(logging.INFO)

    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_SENSORS] = [humidifier]
    with patch.object(config_entry, "async_on_unload") as mock_on_unload:
        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    callback.assert_called_once()
    assert len(callback.call_args.args[0]) == 1
    assert callback.call_args.args[0][0].device == humidifier
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
    hass.data[DOMAIN][config_entry.entry_id][VS_SENSORS] = []
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the discovery mechanism can handle unsupported devices."""
    mock_sensor = MagicMock(VeSyncBaseDevice)
    mock_sensor.device_type = "invalid_type"
    mock_sensor.device_name = "invalid_name"
    details = {}
    mock_sensor.details = details

    callback = Mock(AddEntitiesCallback)

    hass.data[DOMAIN] = {config_entry.entry_id: {}}
    hass.data[DOMAIN][config_entry.entry_id][VS_SENSORS] = [mock_sensor]
    with patch.object(config_entry, "async_on_unload") as mock_on_unload:
        await async_setup_entry(hass, config_entry, callback)
        await hass.async_block_till_done()

    callback.assert_called_once()
    assert callback.call_args.args == ([],)
    assert callback.call_args.kwargs == {"update_before_add": True}
    mock_on_unload.assert_called_once()
    assert (
        caplog.messages[1]
        == "invalid_name - No sensors found for device type - invalid_type"
    )


async def test_sensor_entity__init(base_device: VeSyncBaseDevice) -> None:
    """Test the sensor entity constructor."""
    mock_value_fn = Mock(return_value="value")
    description = VeSyncSensorEntityDescription(
        key="desc-key",
        name="Desc Name",
        value_fn=mock_value_fn,
    )
    entity = VeSyncSensorEntity(base_device, description)

    assert entity.device == base_device
    assert entity.device_class is None
    assert entity.entity_category is None
    assert entity.entity_description == description
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon is None
    assert entity.name == "device name Desc Name"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1-desc-key"


async def test_sensor_entity__native_value(base_device: VeSyncBaseDevice) -> None:
    """Test the number entity native_value impl."""
    mock_value_fn = Mock(return_value="value")
    description = VeSyncSensorEntityDescription(
        key="desc-key",
        name="Desc Name",
        value_fn=mock_value_fn,
    )
    entity = VeSyncSensorEntity(base_device, description)
    assert entity.native_value == "value"
    mock_value_fn.assert_called_once()


async def test_sensor__update(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity update impl."""
    mock_value_fn = Mock(return_value="value")
    description = VeSyncSensorEntityDescription(
        key="desc-key",
        name="Desc Name",
        value_fn=mock_value_fn,
    )
    entity = VeSyncSensorEntity(base_device, description)

    mock_update_energy = Mock()
    base_device.update_energy = mock_update_energy
    entity.update()

    assert base_device.update.call_count == 1
    assert base_device.update_energy.call_count == 0


async def test_energy_sensor_entity__init(base_device: VeSyncBaseDevice) -> None:
    """Test the sensor entity constructor."""
    mock_value_fn = Mock(return_value="value")
    description = VeSyncSensorEntityDescription(
        key="desc-key",
        name="Desc Name",
        value_fn=mock_value_fn,
    )
    entity = VeSyncEnergySensorEntity(base_device, description)

    assert entity.device == base_device
    assert entity.device_class is None
    assert entity.entity_category is None
    assert entity.entity_description == description
    assert entity.entity_picture is None
    assert entity.has_entity_name is False
    assert entity.icon is None
    assert entity.name == "device name Desc Name"
    assert entity.supported_features is None
    assert entity.unique_id == "cid1-desc-key"


async def test_energy_sensor_entity__native_value(
    base_device: VeSyncBaseDevice,
) -> None:
    """Test the number entity native_value impl."""
    mock_value_fn = Mock(return_value="value")
    description = VeSyncSensorEntityDescription(
        key="desc-key",
        name="Desc Name",
        value_fn=mock_value_fn,
    )
    entity = VeSyncEnergySensorEntity(base_device, description)
    assert entity.native_value == "value"
    mock_value_fn.assert_called_once()


async def test_energy_sensor__update(base_device: VeSyncBaseDevice) -> None:
    """Test the base entity update impl."""
    mock_value_fn = Mock(return_value="value")
    description = VeSyncSensorEntityDescription(
        key="desc-key",
        name="Desc Name",
        value_fn=mock_value_fn,
    )
    entity = VeSyncEnergySensorEntity(base_device, description)

    mock_update_energy = Mock()
    base_device.update_energy = mock_update_energy
    entity.update()

    assert base_device.update.call_count == 1
    assert base_device.update_energy.call_count == 1


async def test_air_quality_factory__create() -> None:
    """Test the Air Quality Factory creates impl."""
    factory = AirQualityEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    details_dict = {"air_quality": 5}
    device.details = MagicMock()
    device.details.get.side_effect = details_dict.get
    device.details.__getitem__.side_effect = details_dict.__getitem__

    description = factory.create(device)
    assert description
    assert description.device_class is None
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "air-quality"
    assert description.name == "Air Quality"
    assert callable(description.value_fn)
    assert description.value_fn(device) == 5
    assert device.details.mock_calls[0].args == ("air_quality",)


async def test_air_quality_factory__supports() -> None:
    """Test the Air Quality Factory supports impl."""
    factory = AirQualityEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    device.details = {}
    assert factory.supports(device) is False
    device.details = {"air_quality": 50}
    assert factory.supports(device) is True


async def test_current_power_factory__create() -> None:
    """Test the Current Power Factory creates impl."""
    factory = CurrentPowerEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    details_dict = {"power": 2}
    device.details = MagicMock()
    device.details.get.side_effect = details_dict.get
    device.details.__getitem__.side_effect = details_dict.__getitem__

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.POWER
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "power"
    assert description.name == "Current Power"
    assert description.native_unit_of_measurement == UnitOfPower.WATT
    assert description.state_class == SensorStateClass.MEASUREMENT
    assert callable(description.value_fn)
    assert description.value_fn(device) == 2
    assert device.details.mock_calls[0].args == ("power",)


async def test_current_power_factory__supports(outlet_features) -> None:
    """Test the Current Power Factory supports impl."""
    factory = CurrentPowerEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    with patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_features:
        mock_features.keys.side_effect = outlet_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = OUTLET_MODEL
        assert factory.supports(device) is True


async def test_energy_monthly_factory__create() -> None:
    """Test the Monthly Energy Use Factory creates impl."""
    factory = EnergyMonthlyEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    device.monthly_energy_total = 100

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.ENERGY
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "energy-monthly"
    assert description.name == "Energy Use Monthly"
    assert description.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert description.state_class == SensorStateClass.TOTAL_INCREASING
    assert callable(description.value_fn)
    assert description.value_fn(device) == 100


async def test_energy_monthly_factory__supports(outlet_features) -> None:
    """Test the Monthly Energy Use Factory supports impl."""
    factory = EnergyMonthlyEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    with patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_features:
        mock_features.keys.side_effect = outlet_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = OUTLET_MODEL
        assert factory.supports(device) is True


async def test_energy_factory__create() -> None:
    """Test the Energy Use Factory creates impl."""
    factory = EnergyTodayEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    device.energy_today = 8

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.ENERGY
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "energy"
    assert description.name == "Energy Use Today"
    assert description.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert description.state_class == SensorStateClass.TOTAL_INCREASING
    assert callable(description.value_fn)
    assert description.value_fn(device) == 8


async def test_energy_factory__supports(outlet_features) -> None:
    """Test the Energy Use Factory supports impl."""
    factory = EnergyTodayEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    with patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_features:
        mock_features.keys.side_effect = outlet_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = OUTLET_MODEL
        assert factory.supports(device) is True


async def test_energy_weekly_factory__create() -> None:
    """Test the Weekly Energy Use Factory creates impl."""
    factory = EnergyWeeklyEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    device.weekly_energy_total = 50

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.ENERGY
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "energy-weekly"
    assert description.name == "Energy Use Weekly"
    assert description.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert description.state_class == SensorStateClass.TOTAL_INCREASING
    assert callable(description.value_fn)
    assert description.value_fn(device) == 50


async def test_energy_weekly_factory__supports(outlet_features) -> None:
    """Test the Weekly Energy Use Factory supports impl."""
    factory = EnergyWeeklyEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    with patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_features:
        mock_features.keys.side_effect = outlet_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = OUTLET_MODEL
        assert factory.supports(device) is True


async def test_energy_yearly_factory__create() -> None:
    """Test the Yearly Energy Use Factory creates impl."""
    factory = EnergyYearlyEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    device.yearly_energy_total = 500

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.ENERGY
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "energy-yearly"
    assert description.name == "Energy Use Yearly"
    assert description.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert description.state_class == SensorStateClass.TOTAL_INCREASING
    assert callable(description.value_fn)
    assert description.value_fn(device) == 500


async def test_energy_yearly_factory__supports(outlet_features) -> None:
    """Test the Yearly Energy Use Factory supports impl."""
    factory = EnergyYearlyEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    with patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_features:
        mock_features.keys.side_effect = outlet_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = OUTLET_MODEL
        assert factory.supports(device) is True


async def test_filter_life_factory__create() -> None:
    """Test the Filter Life Factory creates impl."""
    factory = FilterLifeEntityDescriptionFactory()

    device = MagicMock(VeSyncAirBypass)
    device.filter_life = 1

    description = factory.create(device)
    assert description
    assert description.device_class is None
    assert description.entity_category == EntityCategory.DIAGNOSTIC
    assert description.icon is None
    assert description.key == "filter-life"
    assert description.name == "Filter Life"
    assert description.native_unit_of_measurement == PERCENTAGE
    assert description.state_class == SensorStateClass.MEASUREMENT
    assert callable(description.value_fn)
    assert description.value_fn(device) == 1


async def test_filter_life_factory__supports() -> None:
    """Test the Filter Life Factory supports impl."""
    factory = FilterLifeEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    assert factory.supports(device) is False
    device.filter_life = 50
    assert factory.supports(device) is True


async def test_humidity_factory__create() -> None:
    """Test the Humidity Factory creates impl."""
    factory = HumidityEntityDescriptionFactory()

    device = MagicMock(VeSyncAirBypass)
    details_dict = {"humidity": 60}
    device.details = MagicMock()
    device.details.get.side_effect = details_dict.get
    device.details.__getitem__.side_effect = details_dict.__getitem__

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.HUMIDITY
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "humidity"
    assert description.name == "Humidity"
    assert description.native_unit_of_measurement == PERCENTAGE
    assert description.state_class == SensorStateClass.MEASUREMENT
    assert callable(description.value_fn)
    assert description.value_fn(device) == 60
    assert device.details.mock_calls[0].args == ("humidity",)


async def test_humidity_factory__supports() -> None:
    """Test the Humidity Factory supports impl."""
    factory = HumidityEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    device.details = {}
    assert factory.supports(device) is False
    device.details = {"humidity": 50}
    assert factory.supports(device) is True


async def test_pm25_factory__create() -> None:
    """Test the Air Quality Value (PM2.5)  Factory creates impl."""
    factory = PM25EntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    details_dict = {"air_quality_value": 10}
    device.details = MagicMock()
    device.details.get.side_effect = details_dict.get
    device.details.__getitem__.side_effect = details_dict.__getitem__

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.PM25
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "pm25"
    assert description.name == "PM2.5"
    assert (
        description.native_unit_of_measurement
        == CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    )
    assert description.state_class == SensorStateClass.MEASUREMENT
    assert callable(description.value_fn)
    assert description.value_fn(device) == 10
    assert device.details.mock_calls[0].args == ("air_quality_value",)


async def test_pm25_factory__supports() -> None:
    """Test the Air Quality Value (PM2.5) Factory supports impl."""
    factory = PM25EntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    device.details = {}
    assert factory.supports(device) is False
    device.details = {"air_quality_value": 50}
    assert factory.supports(device) is True


async def test_voltage_factory__create() -> None:
    """Test the Voltage Factory creates impl."""
    factory = VoltageEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    details_dict = {"voltage": 13}
    device.details = MagicMock()
    device.details.get.side_effect = details_dict.get
    device.details.__getitem__.side_effect = details_dict.__getitem__

    description = factory.create(device)
    assert description
    assert description.device_class == SensorDeviceClass.VOLTAGE
    assert description.entity_category is None
    assert description.icon is None
    assert description.key == "voltage"
    assert description.name == "Current Voltage"
    assert description.native_unit_of_measurement == UnitOfElectricPotential.VOLT
    assert description.state_class == SensorStateClass.MEASUREMENT
    assert callable(description.value_fn)
    assert description.value_fn(device) == 13
    assert device.details.mock_calls[0].args == ("voltage",)


async def test_voltage_factory__supports(outlet_features) -> None:
    """Test the Voltage Factory supports impl."""
    factory = VoltageEntityDescriptionFactory()

    device = MagicMock(VeSyncBaseDevice)
    with patch(
        "homeassistant.components.vesync.common.outlet_features"
    ) as mock_features:
        mock_features.keys.side_effect = outlet_features.keys

        device.device_type = "ANYTHING"
        assert factory.supports(device) is False
        device.device_type = OUTLET_MODEL
        assert factory.supports(device) is True
