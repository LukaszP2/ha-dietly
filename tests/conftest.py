"""Test configuration and Home Assistant stubs for unit testing without full HA installation."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock


def _setup_ha_stubs():
    if "voluptuous" not in sys.modules:
        vol = types.ModuleType("voluptuous")
        vol.Schema = MagicMock(side_effect=lambda x: x)
        vol.Required = MagicMock(side_effect=lambda x: x)
        vol.Optional = MagicMock(side_effect=lambda *args, **kwargs: args[0] if args else kwargs)
        vol.All = MagicMock(side_effect=lambda *args: args)
        vol.Coerce = MagicMock(side_effect=lambda x: x)
        vol.Range = MagicMock(side_effect=lambda **kwargs: kwargs)
        sys.modules["voluptuous"] = vol

    if "homeassistant" in sys.modules:
        return

    ha = types.ModuleType("homeassistant")
    sys.modules["homeassistant"] = ha

    # homeassistant.config_entries
    ce = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry(MagicMock):
        __class_getitem__ = classmethod(lambda cls, item: cls)

    class ConfigFlow:
        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls._domain = domain

        def async_show_form(
            self, step_id, data_schema=None, errors=None, description_placeholders=None
        ):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_abort(self, reason):
            return {"type": "abort", "reason": reason}

    class OptionsFlow:
        def async_show_form(
            self, step_id, data_schema=None, errors=None, description_placeholders=None
        ):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors or {},
            }

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

    ce.ConfigEntry = ConfigEntry
    ce.ConfigFlow = ConfigFlow
    ce.OptionsFlow = OptionsFlow
    ce.ConfigFlowResult = dict
    sys.modules["homeassistant.config_entries"] = ce
    ha.config_entries = ce

    # homeassistant.core
    core = types.ModuleType("homeassistant.core")

    class HomeAssistant(MagicMock):
        pass

    def callback(fn):
        return fn

    core.HomeAssistant = HomeAssistant
    core.callback = callback
    sys.modules["homeassistant.core"] = core
    ha.core = core

    # homeassistant.data_entry_flow
    deflow = types.ModuleType("homeassistant.data_entry_flow")
    deflow.FlowResult = dict
    sys.modules["homeassistant.data_entry_flow"] = deflow
    ha.data_entry_flow = deflow

    # homeassistant.helpers
    helpers = types.ModuleType("homeassistant.helpers")
    cv = types.ModuleType("homeassistant.helpers.config_validation")
    cv.config_entry_only_config_schema = lambda domain: lambda x: x
    sys.modules["homeassistant.helpers.config_validation"] = cv
    helpers.config_validation = cv

    typing_mod = types.ModuleType("homeassistant.helpers.typing")
    typing_mod.ConfigType = dict
    sys.modules["homeassistant.helpers.typing"] = typing_mod
    helpers.typing = typing_mod

    dr = types.ModuleType("homeassistant.helpers.device_registry")

    class DeviceEntryType:
        SERVICE = "service"

    class DeviceInfo(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

    dr.DeviceEntryType = DeviceEntryType
    dr.DeviceInfo = DeviceInfo
    dr.async_get = MagicMock()
    dr.async_entries_for_config_entry = MagicMock(return_value=[])
    sys.modules["homeassistant.helpers.device_registry"] = dr
    helpers.device_registry = dr

    er = types.ModuleType("homeassistant.helpers.entity_registry")
    er.async_get = MagicMock()
    er.async_entries_for_config_entry = MagicMock(return_value=[])
    sys.modules["homeassistant.helpers.entity_registry"] = er
    helpers.entity_registry = er

    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_create_clientsession = MagicMock()
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client
    helpers.aiohttp_client = aiohttp_client

    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = MagicMock
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform
    helpers.entity_platform = entity_platform

    coord = types.ModuleType("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator(MagicMock):
        __class_getitem__ = classmethod(lambda cls, item: cls)

        def __init__(self, hass, logger, name, update_interval=None):
            super().__init__()
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = {}

    class UpdateFailed(Exception):
        pass

    class CoordinatorEntity:
        __class_getitem__ = classmethod(lambda cls, item: cls)

        def __init__(self, coordinator):
            self.coordinator = coordinator

    coord.DataUpdateCoordinator = DataUpdateCoordinator
    coord.UpdateFailed = UpdateFailed
    coord.CoordinatorEntity = CoordinatorEntity
    sys.modules["homeassistant.helpers.update_coordinator"] = coord
    helpers.update_coordinator = coord

    sys.modules["homeassistant.helpers"] = helpers
    ha.helpers = helpers

    # homeassistant.components.sensor
    comps = types.ModuleType("homeassistant.components")
    sensor = types.ModuleType("homeassistant.components.sensor")

    class SensorEntity:
        _attr_has_entity_name = False
        _attr_entity_category = None

        @property
        def has_entity_name(self) -> bool:
            return getattr(self, "_attr_has_entity_name", False)

        @property
        def entity_category(self):
            return getattr(self, "_attr_entity_category", None)

    class SensorDeviceClass:
        DATE = "date"

    class SensorStateClass:
        MEASUREMENT = "measurement"

    sensor.SensorEntity = SensorEntity
    sensor.SensorDeviceClass = SensorDeviceClass
    sensor.SensorStateClass = SensorStateClass
    sys.modules["homeassistant.components.sensor"] = sensor
    comps.sensor = sensor
    sys.modules["homeassistant.components"] = comps
    ha.components = comps

    # homeassistant.const
    const = types.ModuleType("homeassistant.const")
    const.CONF_EMAIL = "email"
    const.CONF_PASSWORD = "password"

    class UnitOfEnergy:
        KILO_CALORIE = "kcal"

    class UnitOfMass:
        GRAMS = "g"

    class UnitOfTime:
        DAYS = "d"

    class EntityCategory:
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    const.UnitOfEnergy = UnitOfEnergy
    const.UnitOfMass = UnitOfMass
    const.UnitOfTime = UnitOfTime
    const.EntityCategory = EntityCategory
    sys.modules["homeassistant.const"] = const
    ha.const = const

    # homeassistant.exceptions
    exc = types.ModuleType("homeassistant.exceptions")

    class ConfigEntryAuthFailed(Exception):
        pass

    exc.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    sys.modules["homeassistant.exceptions"] = exc
    ha.exceptions = exc

    # homeassistant.util.dt
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")
    import datetime

    dt.now = datetime.datetime.now
    sys.modules["homeassistant.util.dt"] = dt
    util.dt = dt
    sys.modules["homeassistant.util"] = util
    ha.util = util


_setup_ha_stubs()
