"""Data models for the Dietly integration."""

from __future__ import annotations

from typing import TypedDict


class DietlyMeal(TypedDict, total=False):
    """Normalized meal slot data."""

    slot: str
    name: str | None
    calories: float | None
    protein: float | None
    fat: float | None
    carbohydrates: float | None
    allergens: list[str]
    ingredients: list[str]


class DietlyNutrition(TypedDict, total=False):
    """Daily nutrition totals."""

    calories: float | None
    protein: float | None
    fat: float | None
    carbohydrates: float | None


class DietlyOrder(TypedDict, total=False):
    """Normalized active catering order data."""

    order_id: str
    company_id: str | None
    company_name: str | None
    diet_name: str | None
    status: str
    calorie_target: float | None
    date_from: str | None
    date_to: str | None
    next_delivery_date: str | None
    delivery_date: str | None
    is_today: bool
    delivery_address: str | None
    meals: list[DietlyMeal]
    nutrition: DietlyNutrition


class DietlyData(TypedDict):
    """Data stored in the update coordinator."""

    orders: dict[str, DietlyOrder]
