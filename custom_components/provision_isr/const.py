"""Constants for the Provision ISR integration."""

from typing import Final

DOMAIN: Final = "provision_isr"

# Config flow
CONF_HOST: Final = "host"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_VERIFY_SSL: Final = "verify_ssl"

# Defaults
DEFAULT_PORT: Final = 80
DEFAULT_USERNAME: Final = "admin"
DEFAULT_VERIFY_SSL: Final = True

# Coordinators
EVENTS_COORDINATOR: Final = "events"
SECONDARY_COORDINATOR: Final = "secondary"

# Platforms
PLATFORMS: Final = ["camera", "binary_sensor", "sensor", "switch", "button"]

# Update intervals
SCAN_INTERVAL_EVENTS: Final = 120  # seconds
SCAN_INTERVAL_SECONDARY: Final = 3600  # seconds (1 hour)

# Services
SERVICE_REBOOT: Final = "reboot"
SERVICE_ISAPI_REQUEST: Final = "isapi_request"

# Attributes
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"