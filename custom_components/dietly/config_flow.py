"""Config flow for Dietly."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import DietlyApi, DietlyAuthError, DietlyError
from .const import (
    CONF_ACCOUNT_ID,
    CONF_EMAIL,
    CONF_ENTITY_NAMESPACE,
    DOMAIN,
    REQUEST_TIMEOUT_SECONDS,
)
from .identity import entity_namespace

_LOGGER = logging.getLogger(__name__)


async def _validate(hass: HomeAssistant, values: dict[str, Any]) -> str:
    session = async_create_clientsession(
        hass,
        auto_cleanup=False,
        cookie_jar=aiohttp.CookieJar(),
        timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
    )
    try:
        api = DietlyApi(session, values[CONF_EMAIL], values[CONF_PASSWORD])
        await api.async_login()
        if api.account_id is None:
            raise DietlyError("Dietly profile did not include a stable account ID")
        return api.account_id
    finally:
        session.detach()


class DietlyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up a Dietly customer account."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                account_id = await _validate(self.hass, user_input)
            except DietlyAuthError as err:
                _LOGGER.warning("Dietly setup failed: %s", err)
                errors["invalid_auth"] = "invalid_auth"
            except (DietlyError, aiohttp.ClientError, OSError, TimeoutError):
                _LOGGER.exception("Dietly setup failed while connecting to the service")
                errors["cannot_connect"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while connecting to Dietly")
                errors["unknown"] = "unknown"
            else:
                if any(
                    existing_entry.data.get(CONF_EMAIL, "").casefold()
                    == user_input[CONF_EMAIL].casefold()
                    for existing_entry in self._async_current_entries()
                ):
                    return self.async_abort(reason="already_configured")
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Dietly",
                    data={
                        CONF_EMAIL: user_input[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_ACCOUNT_ID: account_id,
                        CONF_ENTITY_NAMESPACE: entity_namespace(account_id, ""),
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow the password for the configured account to be updated."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                account_id = await _validate(
                    self.hass,
                    {
                        CONF_EMAIL: entry.data[CONF_EMAIL],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )
            except DietlyAuthError as err:
                _LOGGER.warning("Dietly reconfiguration failed: %s", err)
                errors["invalid_auth"] = "invalid_auth"
            except (DietlyError, aiohttp.ClientError, OSError, TimeoutError):
                _LOGGER.exception("Dietly reconfiguration failed while connecting")
                errors["cannot_connect"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while reconfiguring Dietly")
                errors["unknown"] = "unknown"
            else:
                existing = next(
                    (
                        configured
                        for configured in self._async_current_entries()
                        if configured.entry_id != entry.entry_id
                        and configured.unique_id == account_id
                    ),
                    None,
                )
                if existing is not None:
                    errors["account_already_configured"] = "account_already_configured"
                elif (
                    entry.data.get(CONF_ACCOUNT_ID) is not None
                    and entry.data[CONF_ACCOUNT_ID] != account_id
                ):
                    errors["wrong_account"] = "wrong_account"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=account_id,
                        data_updates={
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_ACCOUNT_ID: account_id,
                            CONF_ENTITY_NAMESPACE: entry.data.get(
                                CONF_ENTITY_NAMESPACE,
                                entity_namespace(entry.unique_id, entry.entry_id),
                            ),
                        },
                        reason="reconfigure_successful",
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start native reauthentication after Dietly rejects the session."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and save a replacement password on the same entry."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            values = {
                CONF_EMAIL: entry.data[CONF_EMAIL],
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            try:
                account_id = await _validate(self.hass, values)
            except DietlyAuthError as err:
                _LOGGER.warning("Dietly reauthentication failed: %s", err)
                errors["invalid_auth"] = "invalid_auth"
            except (DietlyError, aiohttp.ClientError, OSError, TimeoutError):
                _LOGGER.exception("Dietly reauthentication failed while connecting")
                errors["cannot_connect"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while reauthenticating Dietly")
                errors["unknown"] = "unknown"
            else:
                existing = next(
                    (
                        configured
                        for configured in self._async_current_entries()
                        if configured.entry_id != entry.entry_id
                        and configured.unique_id == account_id
                    ),
                    None,
                )
                if existing is not None:
                    errors["account_already_configured"] = "account_already_configured"
                elif (
                    entry.data.get(CONF_ACCOUNT_ID) is not None
                    and entry.data[CONF_ACCOUNT_ID] != account_id
                ):
                    errors["wrong_account"] = "wrong_account"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        unique_id=account_id,
                        data_updates={
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            CONF_ACCOUNT_ID: account_id,
                            CONF_ENTITY_NAMESPACE: entry.data.get(
                                CONF_ENTITY_NAMESPACE,
                                entity_namespace(entry.unique_id, entry.entry_id),
                            ),
                        },
                    )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )
