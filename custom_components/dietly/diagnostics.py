"""Diagnostics for the Dietly integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import DietlyConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DietlyConfigEntry
) -> dict[str, Any]:
    """Return useful account/order status without credentials or addresses."""
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None or coordinator.data is None:
        return {
            "account": {
                "configured": bool(entry.data.get("email")),
            },
            "status": "not_loaded",
        }
    orders = coordinator.data.get("orders", {})
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
