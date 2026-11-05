"""Diagnostics for the Dietly integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import DietlyConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DietlyConfigEntry
) -> dict[str, Any]:
    """Return useful account/order status without credentials or addresses."""
    coordinator = entry.runtime_data
    orders = coordinator.data.get("orders", {}) if coordinator.data else {}
    return {
        "account": {
            "configured": bool(entry.data.get("email")),
        },
        "refresh": {
            "last_update_success": coordinator.last_update_success,
            "last_update": coordinator.last_update.isoformat()
            if coordinator.last_update
            else None,
            "active_diet_count": len(orders),
        },
        "diets": [
            {
                "order_id": order.get("order_id"),
                "company": order.get("company_name"),
                "diet": order.get("diet_name"),
                "status": order.get("status"),
                "date_from": order.get("date_from"),
                "date_to": order.get("date_to"),
                "delivery_date": order.get("delivery_date"),
                "meal_count": len(order.get("meals", [])),
            }
            for order in orders.values()
        ],
    }
