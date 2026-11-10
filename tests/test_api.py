"""Unit tests for Dietly API client and parsing utilities."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.dietly.api import (
    DietlyApi,
    _company_id_for_order,
    _is_past,
    _normalize_address,
    _normalize_meal,
    _number,
    _nutrition_totals,
)


class TestDietlyParsing(unittest.TestCase):
    """Test response normalization and parsing functions."""

    def test_company_id_extraction(self) -> None:
        """Test extraction of company identifiers from various order formats."""
        # Standard ASCII company name
        self.assertEqual(
            _company_id_for_order({"companyName": "Pomelo"}),
            "Pomelo",
        )
        # Numeric companyId
        self.assertEqual(
            _company_id_for_order({"companyId": 456, "companyName": "Pomelo Catering"}),
            "456",
        )
        # Slug field
        self.assertEqual(
            _company_id_for_order({"slug": "fit-apetit", "companyName": "Fit Apetit"}),
            "fit-apetit",
        )
        # Nested companies list
        self.assertEqual(
            _company_id_for_order(
                {"companies": [{"companyId": 789, "companyName": "Kuchnia Vikinga"}]}
            ),
            "789",
        )
        # Empty order
        self.assertIsNone(_company_id_for_order({}))

    def test_normalize_address(self) -> None:
        """Test address normalization and deduplication."""
        addr = {
            "street": "Marszałkowska",
            "buildingNumber": "10",
            "apartmentNumber": "5",
            "postalCode": "00-001",
            "city": "Warszawa",
        }
        self.assertEqual(
            _normalize_address(addr),
            "Marszałkowska, 10, 5, 00-001, Warszawa",
        )
        self.assertIsNone(_normalize_address(None))
        self.assertIsNone(_normalize_address({}))

    def test_normalize_meal_truncation(self) -> None:
        """Test that long dish names and meal slots are safely truncated to 255 chars."""
        long_dish_name = "Super smaczne danie " * 20
        self.assertGreater(len(long_dish_name), 255)
        raw_meal = {
            "mealName": "Śniadanie",
            "menuMealName": long_dish_name,
            "nutrition": {
                "calories": "450",
                "protein": "25.5",
                "fat": "15.2",
                "carbohydrates": "50.1",
            },
            "allergens": ["Gluten", "Laktoza"],
            "ingredients": ["Jaja", "Masło"],
        }
        normalized = _normalize_meal(raw_meal)
        self.assertEqual(len(normalized["name"]), 255)
        self.assertEqual(normalized["slot"], "Śniadanie")
        self.assertEqual(normalized["calories"], 450.0)
        self.assertEqual(normalized["protein"], 25.5)
        self.assertEqual(normalized["fat"], 15.2)
        self.assertEqual(normalized["carbohydrates"], 50.1)
        self.assertEqual(normalized["allergens"], ["Gluten", "Laktoza"])

    def test_nutrition_totals(self) -> None:
        """Test summing and rounding of daily nutrition values."""
        meals = [
            {"calories": 400.4, "protein": 20.12, "fat": 10.05, "carbohydrates": 40.0},
            {"calories": 600.2, "protein": 30.15, "fat": 15.12, "carbohydrates": 60.0},
        ]
        totals = _nutrition_totals(meals)
        self.assertEqual(totals["calories"], 1001)  # rounded to int
        self.assertEqual(totals["protein"], 50.3)   # rounded to 1 decimal place
        self.assertEqual(totals["fat"], 25.2)
        self.assertEqual(totals["carbohydrates"], 100.0)

    def test_nutrition_totals_partial(self) -> None:
        """Test that missing meal nutrition does not erase known totals."""
        meals = [
            {"calories": 400.0, "protein": 20.0, "fat": 10.0, "carbohydrates": 40.0},
            {"calories": None, "protein": 10.0, "fat": 5.0, "carbohydrates": 20.0},
        ]
        totals = _nutrition_totals(meals)
        self.assertEqual(totals["calories"], 400)
        self.assertEqual(totals["protein"], 30.0)
        self.assertEqual(totals["fat"], 15.0)
        self.assertEqual(totals["carbohydrates"], 60.0)

    def test_number_helper(self) -> None:
        """Test numeric conversion helper."""
        self.assertEqual(_number("123.45"), 123.45)
        self.assertEqual(_number(100), 100.0)
        self.assertIsNone(_number(None))
        self.assertIsNone(_number(True))
        self.assertIsNone(_number(False))
        self.assertIsNone(_number("invalid"))

    def test_is_past(self) -> None:
        """Test past date check."""
        today = date(2026, 11, 6)
        self.assertTrue(_is_past("2026-11-05", today))
        self.assertFalse(_is_past("2026-11-06", today))
        self.assertFalse(_is_past("2026-11-07", today))
        self.assertFalse(_is_past("", today))
        self.assertFalse(_is_past(None, today))


class TestDietlyApiSession(unittest.IsolatedAsyncioTestCase):
    """Test Dietly API client session handling and auto-relogin."""

    async def test_auto_relogin_on_401(self) -> None:
        """Verify that an expired session (401) triggers async_login and retries once."""
        session = MagicMock()
        api = DietlyApi(session, "user@example.com", "secret")
        api._logged_in = True

        call_count = 0

        class MockGetContext:
            async def __aenter__(self):
                nonlocal call_count
                call_count += 1
                mock_resp = MagicMock()
                if call_count == 1:
                    mock_resp.status = 401
                else:
                    mock_resp.status = 200
                    mock_resp.json = AsyncMock(return_value={"results": []})
                return mock_resp

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        session.get = MagicMock(side_effect=lambda *args, **kwargs: MockGetContext())

        with patch.object(api, "async_login", new_callable=AsyncMock) as mock_login:
            res = await api._get("/test/endpoint")
            self.assertEqual(res, {"results": []})
            mock_login.assert_awaited_once()
            self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()
