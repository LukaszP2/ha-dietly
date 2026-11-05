"""Async client for Dietly's private customer API."""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import date
from typing import Any

import aiohttp
from yarl import URL

from .const import API_BASE, LOGIN_URL

_LOGGER = logging.getLogger(__name__)


class DietlyError(Exception):
    """Base exception for Dietly API errors."""


class DietlyAuthError(DietlyError):
    """Credentials were rejected or the session expired."""


class DietlyHttpError(DietlyError):
    """An API endpoint returned an unsuccessful HTTP status."""

    def __init__(self, path: str, status: int) -> None:
        super().__init__(f"Dietly API returned HTTP {status} for {path}")
        self.path = path
        self.status = status


class DietlyApi:
    """Authenticated Dietly API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        company_id: str = "",
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        # Compatibility fallback for older config entries.
        self._legacy_company_id = company_id
        self._headers = {
            "Accept": "application/json",
            "x-launcher-type": "BROWSER_DIETLY",
        }
        self._xsrf_token: str | None = None
        self._logged_in = False
        self._account_id: str | None = None

    @property
    def account_id(self) -> str | None:
        """Return Dietly's stable profile identifier after login."""
        return self._account_id

    async def async_login(self) -> None:
        """Get the CSRF cookie, log in, and validate the session."""
        try:
            self._xsrf_token = await self._async_get_xsrf_token()
            if not self._xsrf_token:
                raise DietlyError("Dietly did not provide an XSRF-TOKEN cookie")

            login_headers = {
                **self._headers,
                "Origin": "https://dietly.pl",
                "Referer": "https://dietly.pl/",
                "X-XSRF-TOKEN": self._xsrf_token,
            }
            async with self._session.post(
                LOGIN_URL,
                data={
                    "username": self._email,
                    "password": self._password,
                    "remember-me": "true",
                },
                headers=login_headers,
            ) as response:
                _LOGGER.debug(
                    "Dietly login response: HTTP %s",
                    response.status,
                )
                if response.status in (401, 403):
                    raise DietlyAuthError(
                        f"Dietly rejected the login request (HTTP {response.status})"
                    )
                if response.status >= 400:
                    raise DietlyError(f"Dietly login returned HTTP {response.status}")
                await response.read()
            self._logged_in = True
            profile_data = await self._get("/profile")
            profile = (
                profile_data.get("profile") if isinstance(profile_data, dict) else None
            )
            profile_id = profile.get("profileId") if isinstance(profile, dict) else None
            if not isinstance(profile_id, (str, int)) or isinstance(profile_id, bool):
                raise DietlyError("Dietly profile did not include a stable account ID")
            self._account_id = str(profile_id)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise DietlyError("Could not connect to Dietly") from err

    async def _async_get_xsrf_token(self) -> str | None:
        """Visit safe pages that may initialize the CSRF cookie."""
        bootstrap_urls = (
            "https://dietly.pl/",
            "https://dietly.pl/api/profile",
            "https://dietly.pl/api/auth/login",
        )
        for url in bootstrap_urls:
            try:
                async with self._session.get(
                    url,
                    headers={
                        "Accept": "application/json, text/plain, */*",
                        "x-launcher-type": "BROWSER_DIETLY",
                        "Referer": "https://dietly.pl/",
                    },
                ) as response:
                    await response.read()
                    token_cookie = response.cookies.get("XSRF-TOKEN")
                    if token_cookie:
                        return token_cookie.value
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Dietly CSRF bootstrap GET failed for %s: %s", url, err)
                continue

            token_cookie = self._session.cookie_jar.filter_cookies(
                URL("https://dietly.pl/")
            ).get("XSRF-TOKEN")
            if token_cookie:
                return token_cookie.value
        return None

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        company_id: str | None = None,
    ) -> Any:
        if not self._logged_in:
            await self.async_login()
        try:
            async with self._session.get(
                f"{API_BASE}{path}",
                headers=self._headers_for(path, company_id),
                params=params,
            ) as response:
                _LOGGER.debug("Dietly API %s returned HTTP %s", path, response.status)
                if response.status in (401, 403):
                    self._logged_in = False
                    raise DietlyAuthError(
                        f"Dietly rejected {path} (HTTP {response.status})"
                    )
                if response.status >= 400:
                    raise DietlyHttpError(path, response.status)
                try:
                    return await response.json(content_type=None)
                except (json.JSONDecodeError, aiohttp.ContentTypeError) as err:
                    raise DietlyError(
                        f"Dietly API returned invalid JSON for {path}"
                    ) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise DietlyError("Could not connect to Dietly") from err

    def _headers_for(self, path: str, company_id: str | None = None) -> dict[str, str]:
        """Use the catering header only on catering-scoped endpoints."""
        headers = dict(self._headers)
        if self._xsrf_token:
            headers["X-XSRF-TOKEN"] = self._xsrf_token
        scoped_company_id = company_id or self._legacy_company_id
        if path.startswith("/company/") and scoped_company_id:
            headers["company-id"] = scoped_company_id
        return headers

    async def async_get_active_diets(self, today: date) -> dict[str, dict[str, Any]]:
        """Return the current delivery and order details for every active diet."""
        today_iso = today.isoformat()
        orders: list[dict[str, Any]] = []
        page = 0
        while True:
            orders_data = await self._get(
                "/profile/profile-order/all", params={"page": page}
            )
            orders.extend(
                item
                for item in _as_list(
                    orders_data, "results", "content", "orders", "profileOrders"
                )
                if isinstance(item, dict)
            )
            total_pages = (
                orders_data.get("totalPages", page + 1)
                if isinstance(orders_data, dict)
                else page + 1
            )
            try:
                if page + 1 >= int(total_pages):
                    break
            except (OverflowError, TypeError, ValueError):
                break
            page += 1

        if not orders:
            active_ids = await self._get("/profile/profile-order/active-ids")
            orders = [
                item
                if isinstance(item, dict)
                else {"orderId": item, "status": "ACTIVE"}
                for item in _as_list(
                    active_ids, "activeOrderIds", "orderIds", "results", "content"
                )
                if isinstance(item, (dict, str, int))
            ]

        active_orders = [
            order
            for order in orders
            if str(order.get("status", "ACTIVE")).upper() == "ACTIVE"
        ]
        diets: dict[str, dict[str, Any]] = {}
        for active in active_orders:
            nested_order = active.get("orderId")
            if not isinstance(nested_order, dict):
                nested_order = {}
            date_from = active.get("dateFrom") or nested_order.get("dateFrom")
            date_to = active.get("dateTo") or nested_order.get("dateTo")
            # Avoid querying catering details for history already known to be over.
            if _is_past(date_to, today):
                continue
            order_id = active.get("orderId", active.get("id"))
            if isinstance(order_id, dict):
                order_id = order_id.get("orderId", order_id.get("id"))
            if not isinstance(order_id, (str, int)):
                _LOGGER.warning("Skipping Dietly order without a usable order ID")
                continue
            order_id = str(order_id)
            if not re.fullmatch(r"[A-Za-z0-9_-]+", order_id):
                _LOGGER.warning("Skipping Dietly order with an invalid identifier")
                continue

            company_id = _company_id_for_order(active) or _company_id_for_order(
                nested_order
            )
            if not company_id and len(active_orders) == 1:
                company_id = self._legacy_company_id
            if not company_id:
                _LOGGER.warning(
                    "Dietly order %s has no catering identifier; menu details are unavailable",
                    order_id,
                )
                order = {}
            else:
                order_path = f"/company/customer/order/{order_id}"
                try:
                    order = await self._get(order_path, company_id=company_id)
                except DietlyHttpError as err:
                    if err.status not in (400, 404):
                        raise
                    _LOGGER.warning(
                        "Dietly order %s details are unavailable (HTTP %s)",
                        order_id,
                        err.status,
                    )
                    order = {}
            if not isinstance(order, dict):
                _LOGGER.warning("Skipping Dietly order with an invalid detail response")
                continue
            deliveries = _as_list(order, "deliveries")
            candidates = [
                item
                for item in deliveries
                if isinstance(item, dict) and str(item.get("date", "")) >= today_iso
            ]
            delivery = next(
                (item for item in candidates if str(item.get("date", "")) == today_iso),
                None,
            )
            if delivery is None and candidates:
                delivery = min(candidates, key=lambda item: str(item.get("date", "")))

            meals: list[dict[str, Any]] = []
            delivery_date = None
            if delivery:
                delivery_date = delivery.get("date")
                delivery_id = delivery.get("deliveryId", delivery.get("id"))
                if isinstance(delivery_id, (str, int)) and re.fullmatch(
                    r"[A-Za-z0-9_-]+", str(delivery_id)
                ):
                    menu_path = f"/company/general/menus/delivery/{delivery_id}/new"
                    try:
                        menu = await self._get(menu_path, company_id=company_id)
                    except DietlyHttpError as err:
                        if err.status not in (400, 404):
                            raise
                        _LOGGER.warning(
                            "Dietly menu for order %s is unavailable (HTTP %s)",
                            order_id,
                            err.status,
                        )
                    else:
                        meals = [
                            _normalize_meal(item)
                            for item in _as_list(
                                menu, "deliveryMenuMeal", "meals", "menu"
                            )
                            if isinstance(item, dict)
                        ]

            diet = order.get("diet") if isinstance(order.get("diet"), dict) else {}
            date_from = date_from or order.get("dateFrom")
            date_to = date_to or order.get("dateTo")
            # Dietly may leave old orders marked ACTIVE in profile-order/all.
            # A past end date is authoritative and should not create HA devices.
            if _is_past(date_to, today):
                continue
            delivery_address = _normalize_address(
                (delivery or {}).get("deliveryAddress")
                or (delivery or {}).get("address")
                or order.get("deliveryAddress")
                or order.get("address")
            )
            key = str(order_id)
            diets[key] = {
                "order_id": key,
                "company_id": company_id,
                "company_name": (
                    active.get("companyFullName")
                    or active.get("companyName")
                    or nested_order.get("companyFullName")
                    or nested_order.get("companyName")
                ),
                "diet_name": (
                    active.get("dietName")
                    or nested_order.get("dietName")
                    or diet.get("dietName")
                ),
                "status": active.get("status") or nested_order.get("status", "ACTIVE"),
                "calorie_target": _number(
                    active.get(
                        "dietCalories",
                        nested_order.get("dietCalories", diet.get("calories")),
                    )
                ),
                "date_from": date_from,
                "date_to": date_to,
                "delivery_date": delivery_date,
                "delivery_address": delivery_address,
                "meals": meals,
                "nutrition": _nutrition_totals(meals),
            }
        return diets


def _as_list(data: Any, *keys: str) -> list[Any]:
    """Extract a list from common API response wrappers."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict) and isinstance(value.get("content"), list):
                return value["content"]
        for wrapper in ("data", "result"):
            nested = data.get(wrapper)
            if isinstance(nested, (dict, list)):
                found = _as_list(nested, *keys)
                if found:
                    return found
    return []


def _company_id_for_order(order: dict[str, Any]) -> str | None:
    """Read the catering slug attached to a profile-order record."""
    value = order.get("companyName")
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]+", value.strip()):
        return value.strip()
    companies = order.get("companies")
    if isinstance(companies, list):
        for company in companies:
            if isinstance(company, dict):
                name = company.get("companyName") or company.get("slug")
                if isinstance(name, str) and re.fullmatch(
                    r"[A-Za-z0-9_-]+", name.strip()
                ):
                    return name.strip()
    return None


def _number(value: Any) -> float | None:
    """Convert an API numeric field without interpreting missing as zero."""
    try:
        if value is None or isinstance(value, bool):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (OverflowError, TypeError, ValueError):
        return None


def _is_past(value: Any, today: date) -> bool:
    """Return whether an order's end date is before today."""
    if not isinstance(value, str) or not value:
        return False
    try:
        return date.fromisoformat(value[:10]) < today
    except ValueError:
        return False


def _normalize_address(value: Any) -> str | None:
    """Format common Dietly delivery-address objects for a sensor state."""
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, dict):
        return None
    fields = (
        "street",
        "streetName",
        "buildingNumber",
        "houseNumber",
        "apartmentNumber",
        "flatNumber",
        "postalCode",
        "zipCode",
        "city",
    )
    parts = [
        str(value[key]).strip()
        for key in fields
        if isinstance(value.get(key), (str, int)) and str(value[key]).strip()
    ]
    return ", ".join(dict.fromkeys(parts)) or None


def _normalize_meal(meal: dict[str, Any]) -> dict[str, Any]:
    menu_meal = meal.get("menuMeal")
    if not isinstance(menu_meal, dict):
        menu_meal = {}
    nutrition = meal.get("nutrition") or menu_meal.get("nutrition") or {}
    if not isinstance(nutrition, dict):
        nutrition = {}
    meal_name = meal.get("menuMealName") or meal.get("dishName") or meal.get("name")
    slot = meal.get("mealName") or meal.get("name") or "Posiłek"
    return {
        "slot": slot if isinstance(slot, str) else "Posiłek",
        "name": meal_name if isinstance(meal_name, str) else None,
        "calories": _number(
            nutrition.get("calories", nutrition.get("energy", nutrition.get("kcal")))
        ),
        "protein": _number(nutrition.get("protein", nutrition.get("proteins"))),
        "fat": _number(nutrition.get("fat", nutrition.get("fats"))),
        "carbohydrates": _number(
            nutrition.get(
                "carbohydrates", nutrition.get("carbs", nutrition.get("carbohydrate"))
            )
        ),
        "allergens": _as_text_list(
            meal.get("allergensWithExcluded") or meal.get("allergens")
        ),
        "ingredients": _as_text_list(meal.get("ingredients")),
    }


def _as_text_list(value: Any) -> list[str]:
    """Convert optional text/list/object fields to JSON-safe strings."""
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in values:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(item.get("name") or item.get("allergenName") or "").strip()
        else:
            text = ""
        if text:
            result.append(text)
    return result


def _nutrition_totals(meals: list[dict[str, Any]]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in ("calories", "protein", "fat", "carbohydrates"):
        values = [meal.get(key) for meal in meals]
        result[key] = (
            sum(value for value in values if value is not None)
            if values and all(value is not None for value in values)
            else None
        )
    return result
