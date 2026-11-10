"""Unit tests for Dietly sensors and device info."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock

from custom_components.dietly.sensor import (
    DietlyMealSensor,
    DietlyOrderSensor,
    _device_info,
    _order_slug,
    _parse_date,
    _slug,
)


class TestSensors(unittest.TestCase):
    """Test sensor behavior and formatting."""

    def test_slug_generation(self) -> None:
        """Test Polish text normalization to slug."""
        self.assertEqual(_slug("Super Dieta — Białkowa"), "super_dieta_bialkowa")
        self.assertEqual(_slug("Śniadanie & Przekąska"), "sniadanie_przekaska")

    def test_order_slug(self) -> None:
        """Test order slug creation."""
        order = {
            "company_name": "Pomelo",
            "diet_name": "Sport",
            "date_from": "2026-11-01",
        }
        self.assertEqual(_order_slug(order), "pomelo_sport_2026_11_01")

    def test_parse_date(self) -> None:
        """Test ISO date parsing."""
        self.assertEqual(_parse_date("2026-11-06"), date(2026, 11, 6))
        self.assertEqual(_parse_date("2026-11-06T12:00:00Z"), date(2026, 11, 6))
        self.assertIsNone(_parse_date(None))
        self.assertIsNone(_parse_date("invalid-date"))

    def test_device_info_fallback(self) -> None:
        """Verify device info generates correct identifiers and naming."""
        entry = MagicMock()
        entry.data = {}
        entry.unique_id = "test_acc"
        entry.entry_id = "entry_1"
        order = {
            "order_id": "999",
            "company_name": "Pomelo",
            "diet_name": "Fit",
            "date_from": "2026-11-01",
        }
        dev = _device_info(entry, order, "parent_1")
        self.assertIsNotNone(dev)
        # Verify identifiers contain domain and order id
        idents = dev.get("identifiers") if isinstance(dev, dict) else getattr(dev, "identifiers", set())
        has_identifier = any(
            ident[0] == "dietly" and "999" in ident[1] for ident in idents
        )
        self.assertTrue(has_identifier)

    def test_meal_sensor_attributes(self) -> None:
        """Test meal sensor properties and truncation."""
        entry = MagicMock()
        entry.data = {}
        entry.unique_id = "test_acc"
        entry.entry_id = "entry_1"
        coordinator = MagicMock()
        coordinator.last_update_success = True
        coordinator.data = {
            "orders": {
                "10": {
                    "meals": [
                        {
                            "name": "Owsianka z borówkami",
                            "slot": "Śniadanie",
                            "calories": 420.0,
                            "protein": 15.0,
                            "fat": 10.0,
                            "carbohydrates": 65.0,
                            "allergens": ["Laktoza"],
                            "ingredients": ["Płatki owsiane", "Mleko"],
                        }
                    ]
                }
            }
        }
        sensor = DietlyMealSensor(entry, coordinator, "10", 0, "parent_1")
        self.assertEqual(sensor.native_value, "Owsianka z borówkami")
        self.assertEqual(sensor.name, "Śniadanie")
        self.assertTrue(sensor.has_entity_name)
        attrs = sensor.extra_state_attributes
        self.assertEqual(attrs["calories"], 420.0)
        self.assertEqual(attrs["allergens"], ["Laktoza"])

    def test_order_sensor_days_remaining_no_negative(self) -> None:
        """Verify that days_remaining does not return negative values."""
        entry = MagicMock()
        entry.data = {}
        entry.unique_id = "test_acc"
        entry.entry_id = "entry_1"
        coordinator = MagicMock()
        coordinator.last_update_success = True
        coordinator.data = {
            "orders": {
                "10": {
                    "date_to": "2020-01-01",
                }
            }
        }
        sensor = DietlyOrderSensor(entry, coordinator, "10", "days_remaining", "parent_1")
        self.assertEqual(sensor.native_value, 0)

    def test_order_sensor_entity_category(self) -> None:
        """Verify that metadata sensors are marked as DIAGNOSTIC."""
        entry = MagicMock()
        entry.data = {}
        entry.unique_id = "test_acc"
        entry.entry_id = "entry_1"
        coordinator = MagicMock()
        coordinator.data = {"orders": {"10": {}}}

        status_sensor = DietlyOrderSensor(entry, coordinator, "10", "order_status", "parent_1")
        self.assertEqual(status_sensor.entity_category, "diagnostic")

        addr_sensor = DietlyOrderSensor(entry, coordinator, "10", "delivery_address", "parent_1")
        self.assertEqual(addr_sensor.entity_category, "diagnostic")

        calories_sensor = DietlyOrderSensor(entry, coordinator, "10", "calories", "parent_1")
        self.assertIsNone(calories_sensor.entity_category)


if __name__ == "__main__":
    unittest.main()
