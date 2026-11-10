"""Unit tests for Dietly diagnostics."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from custom_components.dietly.diagnostics import async_get_config_entry_diagnostics


class TestDiagnostics(unittest.IsolatedAsyncioTestCase):
    """Test diagnostics export."""

    async def test_diagnostics_when_not_loaded(self) -> None:
        """Verify diagnostics handles entry without runtime_data gracefully."""
        entry = MagicMock()
        entry.runtime_data = None
        entry.data = {"email": "user@example.com"}

        diag = await async_get_config_entry_diagnostics(MagicMock(), entry)
        self.assertEqual(diag["account"]["configured"], True)
        self.assertEqual(diag["status"], "not_loaded")

    async def test_diagnostics_when_loaded(self) -> None:
        """Verify diagnostics exports order details safely without PII."""
        entry = MagicMock()
        coordinator = MagicMock()
        coordinator.last_update_success = True
        coordinator.last_update = None
        coordinator.data = {
            "orders": {
                "123": {
                    "order_id": "123",
                    "company_name": "Pomelo",
                    "diet_name": "Sport",
                    "status": "ACTIVE",
                    "date_from": "2026-11-01",
                    "date_to": "2026-11-30",
                    "delivery_date": "2026-11-06",
                    "meals": [{"name": "Śniadanie"}],
                }
            }
        }
        entry.runtime_data = coordinator
        entry.data = {"email": "user@example.com"}

        diag = await async_get_config_entry_diagnostics(MagicMock(), entry)
        self.assertEqual(diag["account"]["configured"], True)
        self.assertEqual(diag["refresh"]["active_diet_count"], 1)
        self.assertEqual(len(diag["diets"]), 1)
        self.assertEqual(diag["diets"][0]["company"], "Pomelo")
        # Ensure credentials/addresses are not present in root
        self.assertNotIn("password", diag)
        self.assertNotIn("delivery_address", diag["diets"][0])


if __name__ == "__main__":
    unittest.main()
