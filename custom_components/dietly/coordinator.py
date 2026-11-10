"""Coordinator for Dietly order and menu data."""

from __future__ import annotations

import logging

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import DietlyApi, DietlyAuthError, DietlyError
from .const import (
    CONF_COMPANY_ID,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SHOW_UPCOMING_MENU,
    DEFAULT_SHOW_UPCOMING_MENU,
    DOMAIN,
    REQUEST_TIMEOUT_SECONDS,
    UPDATE_INTERVAL,
)
from .models import DietlyData

_LOGGER = logging.getLogger(__name__)


class DietlyCoordinator(DataUpdateCoordinator[DietlyData]):
    """Fetch the next delivery for all active Dietly orders."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.api = DietlyApi(
            async_create_clientsession(
                hass,
                cookie_jar=aiohttp.CookieJar(),
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
            ),
            entry.data[CONF_EMAIL],
            entry.data[CONF_PASSWORD],
            entry.data.get(CONF_COMPANY_ID, ""),
            show_upcoming_menu=entry.options.get(
                CONF_SHOW_UPCOMING_MENU, DEFAULT_SHOW_UPCOMING_MENU
            ),
        )

    async def _async_update_data(self) -> DietlyData:
        try:
            return {
                "orders": await self.api.async_get_active_diets(dt_util.now().date())
            }
        except DietlyAuthError as err:
            raise ConfigEntryAuthFailed(
                "Dietly authentication expired; reauthentication is required"
            ) from err
        except DietlyError as err:
            raise UpdateFailed(str(err)) from err
