"""Constants for the Dietly integration."""

from datetime import timedelta

DOMAIN = "dietly"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_COMPANY_ID = "company_id"
CONF_ACCOUNT_ID = "account_id"
CONF_ENTITY_NAMESPACE = "entity_namespace"
CONF_SHOW_UPCOMING_MENU = "show_upcoming_menu"
CONF_MEAL_COUNT = "meal_count"
DEFAULT_MEAL_COUNT = 5
DEFAULT_SHOW_UPCOMING_MENU = False
UPDATE_INTERVAL = timedelta(hours=2)
REQUEST_TIMEOUT_SECONDS = 30
PLATFORMS = ["sensor"]
API_BASE = "https://dietly.pl/api"
LOGIN_URL = "https://dietly.pl/api/auth/login"
