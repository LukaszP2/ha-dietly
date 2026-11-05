"""Sensors for each active Dietly order under one account entry."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any, ClassVar

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import (
    ChildDeviceInfo,
    DeviceEntryType,
    DeviceInfo,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import DietlyConfigEntry
from .const import CONF_ENTITY_NAMESPACE, DOMAIN
from .coordinator import DietlyCoordinator
from .identity import entity_namespace


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DietlyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors per active order and discover new active orders on refresh."""
    coordinator = entry.runtime_data
    known_orders: set[str] = set()
    parent_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{_account_key(entry)}_account")},
        name="Dane z Dietly Club",
        manufacturer="Dietly",
        entry_type=DeviceEntryType.SERVICE,
    )
    _remove_stale_entities(
        hass, entry, coordinator.data.get("orders", {}), parent_device.id
    )
    async_add_entities([DietlyAccountSensor(entry, coordinator)])

    @callback
    def add_order_sensors() -> None:
        orders = coordinator.data.get("orders", {})
        new_entities: list[SensorEntity] = []
        for order_id, order in orders.items():
            if order_id in known_orders:
                continue
            known_orders.add(order_id)
            new_entities.extend(
                _order_entities(entry, coordinator, order_id, order, parent_device.id)
            )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(add_order_sensors))
    add_order_sensors()


def _remove_stale_entities(
    hass: HomeAssistant,
    entry: DietlyConfigEntry,
    orders: dict[str, dict[str, Any]],
    parent_device_id: str,
) -> None:
    """Remove registry entries left behind by ended orders or old versions."""
    registry = er.async_get(hass)
    expected = {f"{_account_key(entry)}_active_diets"}
    order_keys = (
        "order_status",
        "calorie_target",
        "order_start",
        "order_end",
        "days_remaining",
        "next_delivery",
        "delivery_address",
        "calories",
        "protein",
        "fat",
        "carbohydrates",
    )
    for order_id, order in orders.items():
        expected.update(f"{_account_key(entry)}_{order_id}_{key}" for key in order_keys)
        expected.update(
            f"{_account_key(entry)}_{order_id}_meal_{index + 1}"
            for index in range(max(5, len(order.get("meals", []))))
        )
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain == "sensor" and entity.unique_id not in expected:
            registry.async_remove(entity.entity_id)

    expected_children = {
        f"{_account_key(entry)}_{order.get('order_id')}" for order in orders.values()
    }
    devices = dr.async_get(hass)
    account_prefix = f"{_account_key(entry)}_"
    expected_main = {
        (DOMAIN, f"{_account_key(entry)}_account"),
        *((DOMAIN, child_id) for child_id in expected_children),
    }
    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        dietly_identifiers = {
            identifier
            for identifier in device.identifiers
            if identifier[0] == DOMAIN and identifier[1].startswith(account_prefix)
        }
        if dietly_identifiers and not dietly_identifiers.intersection(expected_main):
            devices.async_remove_device(device.id)

    for child in dr.async_child_entries_for_config_entry(devices, entry.entry_id):
        if child.parent_device_id != parent_device_id:
            continue
        dietly_identifiers = {
            identifier for identifier in child.identifiers if identifier[0] == DOMAIN
        }
        if dietly_identifiers and not any(
            identifier == (DOMAIN, child_id)
            for child_id in expected_children
            for identifier in dietly_identifiers
        ):
            devices.async_remove_device(child.id)


def _order_entities(
    entry: DietlyConfigEntry,
    coordinator: DietlyCoordinator,
    order_id: str,
    order: dict[str, Any],
    parent_device_id: str,
) -> list[SensorEntity]:
    """Create one order device with order dates, menu totals and meal slots."""
    entities: list[SensorEntity] = [
        DietlyOrderSensor(entry, coordinator, order_id, key, parent_device_id)
        for key in (
            "order_status",
            "calorie_target",
            "order_start",
            "order_end",
            "days_remaining",
            "next_delivery",
            "delivery_address",
            "calories",
            "protein",
            "fat",
            "carbohydrates",
        )
    ]
    meal_count = max(5, len(order.get("meals", [])))
    entities.extend(
        DietlyMealSensor(entry, coordinator, order_id, index, parent_device_id)
        for index in range(meal_count)
    )
    return entities


def _device_info(
    entry: DietlyConfigEntry, order: dict[str, Any], parent_device_id: str
) -> ChildDeviceInfo:
    """Identify one active catering order as a service device."""
    provider = order.get("company_name") or "Dietly"
    diet = order.get("diet_name") or "Dieta"
    start = order.get("date_from")
    suffix = f" ({start})" if start else ""
    account_id = _account_key(entry)
    return ChildDeviceInfo(
        identifiers={(DOMAIN, f"{account_id}_{order.get('order_id')}")},
        name=f"{provider} — {diet}{suffix}",
        parent_device_id=parent_device_id,
    )


def _account_device_info(entry: DietlyConfigEntry) -> DeviceInfo:
    """Represent the Dietly Club account as the parent service device."""
    account_id = _account_key(entry)
    return DeviceInfo(
        identifiers={(DOMAIN, f"{account_id}_account")},
        name="Dane z Dietly Club",
        manufacturer="Dietly",
        entry_type=DeviceEntryType.SERVICE,
    )


class DietlyAccountSensor(CoordinatorEntity[DietlyCoordinator], SensorEntity):
    """Show the number of active diets on the account device."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_diets"
    _attr_icon = "mdi:account-multiple"

    def __init__(
        self, entry: DietlyConfigEntry, coordinator: DietlyCoordinator
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{_account_key(entry)}_active_diets"
        self._attr_device_info = _account_device_info(entry)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("orders", {}))

    @property
    def suggested_object_id(self) -> str:
        """Use a short, readable entity ID for the account summary."""
        return "dietly_aktywne_diety"


class DietlyOrderSensor(CoordinatorEntity[DietlyCoordinator], SensorEntity):
    """Expose order metadata or daily menu totals for one Dietly order."""

    _attr_has_entity_name = True

    _LABELS: ClassVar[dict[str, str]] = {
        "order_status": "order_status",
        "calorie_target": "calorie_target",
        "order_start": "order_start",
        "order_end": "order_end",
        "days_remaining": "days_remaining",
        "next_delivery": "next_delivery",
        "delivery_address": "delivery_address",
        "calories": "calories",
        "protein": "protein",
        "fat": "fat",
        "carbohydrates": "carbohydrates",
    }

    def __init__(
        self,
        entry: DietlyConfigEntry,
        coordinator: DietlyCoordinator,
        order_id: str,
        key: str,
        parent_device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._order_id = order_id
        self._key = key
        self._attr_translation_key = self._LABELS[key]
        self._attr_unique_id = f"{_account_key(entry)}_{order_id}_{key}"
        self._attr_device_info = _device_info(
            entry,
            coordinator.data.get("orders", {}).get(order_id, {}),
            parent_device_id,
        )
        if key in {"order_start", "order_end", "next_delivery"}:
            self._attr_device_class = SensorDeviceClass.DATE
        elif key == "days_remaining":
            self._attr_native_unit_of_measurement = "d"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif key in {"calories", "calorie_target"}:
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_CALORIE
        elif key in {"protein", "fat", "carbohydrates"}:
            self._attr_native_unit_of_measurement = UnitOfMass.GRAMS
        elif key == "delivery_address":
            self._attr_icon = "mdi:map-marker"

    @property
    def suggested_object_id(self) -> str:
        """Group readable entity IDs by diet and data type."""
        order = self._order
        diet_slug = _order_slug(order)
        key_slug = {
            "order_status": "zamowienie_status",
            "calorie_target": "dieta_kalorie_docelowe",
            "order_start": "dieta_data_rozpoczecia",
            "order_end": "dieta_data_zakonczenia",
            "days_remaining": "dieta_dni_do_konca",
            "next_delivery": "dostawa_data",
            "delivery_address": "dostawa_adres",
            "calories": "menu_kalorie",
            "protein": "menu_bialko",
            "fat": "menu_tluszcz",
            "carbohydrates": "menu_weglowodany",
        }[self._key]
        return f"dietly_{diet_slug}_{key_slug}"

    @property
    def _order(self) -> dict[str, Any]:
        return self.coordinator.data.get("orders", {}).get(self._order_id, {})

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self._order)

    @property
    def native_value(self) -> Any:
        order = self._order
        if not order:
            return None
        if self._key == "order_status":
            return order.get("status")
        if self._key == "calorie_target":
            return order.get("calorie_target")
        if self._key == "order_start":
            return _parse_date(order.get("date_from"))
        if self._key == "order_end":
            return _parse_date(order.get("date_to"))
        if self._key == "next_delivery":
            return _parse_date(order.get("delivery_date"))
        if self._key == "delivery_address":
            return order.get("delivery_address") or "Brak adresu w danych Dietly"
        if self._key == "days_remaining":
            end_date = _parse_date(order.get("date_to"))
            return (end_date - dt_util.now().date()).days if end_date else None
        return order.get("nutrition", {}).get(self._key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        order = self._order
        return {
            "order_id": self._order_id,
            "company": order.get("company_name"),
            "diet": order.get("diet_name"),
            "order_end": order.get("date_to"),
            "delivery_date": order.get("delivery_date"),
            "delivery_address": order.get("delivery_address"),
        }


class DietlyMealSensor(CoordinatorEntity[DietlyCoordinator], SensorEntity):
    """Expose a menu meal and its nutrition as attributes."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:food"

    def __init__(
        self,
        entry: DietlyConfigEntry,
        coordinator: DietlyCoordinator,
        order_id: str,
        index: int,
        parent_device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._order_id = order_id
        self._index = index
        self._attr_unique_id = f"{_account_key(entry)}_{order_id}_meal_{index + 1}"
        self._attr_device_info = _device_info(
            entry,
            coordinator.data.get("orders", {}).get(order_id, {}),
            parent_device_id,
        )

    @property
    def _order(self) -> dict[str, Any]:
        return self.coordinator.data.get("orders", {}).get(self._order_id, {})

    @property
    def _meal(self) -> dict[str, Any]:
        meals = self._order.get("meals", [])
        return meals[self._index] if self._index < len(meals) else {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self._order)

    @property
    def native_value(self) -> str | None:
        meal = self._meal
        return (meal.get("name") or meal.get("slot")) if meal else None

    @property
    def name(self) -> str | None:
        """Name the entity after the meal slot; state carries the dish name."""
        meal = self._meal
        if not meal:
            return f"Posiłek {self._index + 1}"
        slot = meal.get("slot") or f"Posiłek {self._index + 1}"
        return str(slot)

    @property
    def suggested_object_id(self) -> str:
        """Build a readable and grouped entity ID for the meal slot."""
        slot = self._meal.get("slot") or f"posilek_{self._index + 1}"
        return f"dietly_{_order_slug(self._order)}_posilek_{_slug(slot)}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        order = self._order
        meal = self._meal
        return {
            "order_id": self._order_id,
            "company": order.get("company_name"),
            "diet": order.get("diet_name"),
            "meal_slot": meal.get("slot"),
            "calories": meal.get("calories"),
            "protein_g": meal.get("protein"),
            "fat_g": meal.get("fat"),
            "carbohydrates_g": meal.get("carbohydrates"),
            "allergens": meal.get("allergens", []),
            "ingredients": meal.get("ingredients", []),
            "delivery_date": order.get("delivery_date"),
            "delivery_address": order.get("delivery_address"),
            "order_end": order.get("date_to"),
        }


def _parse_date(value: Any) -> date | None:
    """Parse an ISO date from the Dietly response."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _account_key(entry: DietlyConfigEntry) -> str:
    """Return a stable, non-PII account suffix for registry identifiers."""
    return entry.data.get(CONF_ENTITY_NAMESPACE) or entity_namespace(
        entry.unique_id, entry.entry_id
    )


def _order_slug(order: dict[str, Any]) -> str:
    """Create a readable per-order ID component without internal numeric IDs."""
    pieces = (
        order.get("company_name") or "dietly",
        order.get("diet_name") or "dieta",
        order.get("date_from") or "",
    )
    return _slug("_".join(str(piece) for piece in pieces if piece))


def _slug(value: str) -> str:
    """Normalize Polish labels to Home Assistant object ID characters."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode().lower()
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", ascii_value)).strip("_")
