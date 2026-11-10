"""Unit tests for Dietly config flow."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from custom_components.dietly.api import DietlyAuthError, DietlyError
from custom_components.dietly.config_flow import (
    DietlyConfigFlow,
    DietlyOptionsFlowHandler,
    _validate,
)
from custom_components.dietly.const import CONF_MEAL_COUNT, CONF_SHOW_UPCOMING_MENU


class TestConfigFlow(unittest.IsolatedAsyncioTestCase):
    """Test config flow steps and error mapping."""

    async def test_user_step_invalid_auth(self) -> None:
        """Verify that authentication failure maps error key to 'base'."""
        flow = DietlyConfigFlow()
        flow.hass = None

        with patch(
            "custom_components.dietly.config_flow._validate",
            side_effect=DietlyAuthError("Invalid credentials"),
        ):
            res = await flow.async_step_user({"email": "test@example.com", "password": "wrong"})
            self.assertEqual(res["type"], "form")
            self.assertEqual(res["step_id"], "user")
            # Must be mapped under "base", NOT "invalid_auth"
            self.assertEqual(res["errors"], {"base": "invalid_auth"})

    async def test_user_step_cannot_connect(self) -> None:
        """Verify that connection failure maps error key to 'base'."""
        flow = DietlyConfigFlow()
        flow.hass = None

        with patch(
            "custom_components.dietly.config_flow._validate",
            side_effect=DietlyError("Connection timeout"),
        ):
            res = await flow.async_step_user({"email": "test@example.com", "password": "pass"})
            self.assertEqual(res["type"], "form")
            self.assertEqual(res["errors"], {"base": "cannot_connect"})

    async def test_options_flow(self) -> None:
        """Verify options flow displays form and creates entry."""
        entry = MagicMock()
        entry.options = {CONF_SHOW_UPCOMING_MENU: True, CONF_MEAL_COUNT: 4}
        handler = DietlyConfigFlow.async_get_options_flow(entry)
        self.assertIsInstance(handler, DietlyOptionsFlowHandler)

        # Show form
        form = await handler.async_step_init()
        self.assertEqual(form["type"], "form")
        self.assertEqual(form["step_id"], "init")

        # Save options
        created = await handler.async_step_init({CONF_SHOW_UPCOMING_MENU: False, CONF_MEAL_COUNT: 3})
        self.assertEqual(created["type"], "create_entry")
        self.assertEqual(created["data"], {CONF_SHOW_UPCOMING_MENU: False, CONF_MEAL_COUNT: 3})

    async def test_validate_success(self) -> None:
        """Verify _validate logs in, returns account_id and safely closes the session."""
        hass = MagicMock()
        mock_session = MagicMock()
        mock_session.close = unittest.mock.AsyncMock()
        with (
            patch(
                "custom_components.dietly.config_flow.async_create_clientsession",
                return_value=mock_session,
            ),
            patch("custom_components.dietly.config_flow.DietlyApi") as mock_api_cls,
        ):
            mock_api = mock_api_cls.return_value
            mock_api.account_id = "12345"
            mock_api.async_login = unittest.mock.AsyncMock()

            account_id = await _validate(hass, {"email": "user@example.com", "password": "pwd"})
            self.assertEqual(account_id, "12345")
            mock_session.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
