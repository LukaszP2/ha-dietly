"""Home Assistant integration for Dietly."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import PLATFORMS
from .coordinator import DietlyCoordinator

type DietlyConfigEntry = ConfigEntry[DietlyCoordinator]
CONFIG_SCHEMA = cv.config_entry_only_config_schema("dietly")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from config entries only."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: DietlyConfigEntry) -> bool:
    """Set up a Dietly account."""
    coordinator = DietlyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DietlyConfigEntry) -> bool:
    """Unload a Dietly account."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
