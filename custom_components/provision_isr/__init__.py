"""The Provision ISR integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_AUTO_DETECT_IP, CONF_MAC_ADDRESS, DOMAIN
from .provision_api import ProvisionClient
from .provision_api.exceptions import AuthenticationError, ConnectionError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CAMERA,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up Provision ISR from a config entry."""
    # Check if IP auto‑detection is enabled
    if entry.options.get(CONF_AUTO_DETECT_IP, False):
        await _auto_detect_ip_change(hass, entry)

    # Create the client
    client = ProvisionClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    # Test connection
    try:
        await client.connect()
        device_info = await client.get_device_info()

        _LOGGER.info(
            "Connected to %s %s at %s:%s",
            device_info.brand,
            device_info.model,
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
        )

    except AuthenticationError as err:
        await client.close()
        raise ConfigEntryNotReady(f"Authentication failed: {err}") from err
    except ConnectionError as err:
        await client.close()
        raise ConfigEntryNotReady(f"Connection failed: {err}") from err
    except Exception as err:  # pragma: no cover
        await client.close()
        _LOGGER.exception("Unexpected error during setup")
        raise ConfigEntryNotReady(f"Setup failed: {err}") from err

    # Store client & device info
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "device_info": device_info,
    }

    # Start long polling if supported
    if device_info.support_api_long_polling and device_info.support_motion_sens:
        from .long_polling import ProvisionLongPolling

        try:
            long_polling = ProvisionLongPolling(
                host=entry.data[CONF_HOST],
                port=entry.data[CONF_PORT],
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD],
            )

            if await long_polling.start():
                hass.data[DOMAIN][entry.entry_id]["long_polling"] = long_polling
                _LOGGER.info("Long polling started for motion events")
            else:
                _LOGGER.warning("Failed to start long polling")

        except Exception as err:  # pragma: no cover
            _LOGGER.warning("Failed to set up long polling: %s", err)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        # Stop long polling if running
        long_polling = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).pop(
            "long_polling", None
        )
        if long_polling:
            await long_polling.stop()

        # Close client
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        await client.close()

        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id, None)

        _LOGGER.info("Unloaded Provision ISR integration")

    return unload_ok


async def _auto_detect_ip_change(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Auto‑detect if the device IP has changed and update the config entry.

    Returns True if the device IP changed and the entry was updated; False otherwise.
    """
    if CONF_MAC_ADDRESS not in entry.data:
        _LOGGER.debug("No MAC address stored, skipping IP auto‑detection")
        return False

    stored_mac = entry.data[CONF_MAC_ADDRESS]
    current_host = entry.data[CONF_HOST]

    try:
        from .discovery import discover_devices

        _LOGGER.debug("Checking for IP changes (MAC: %s)…", stored_mac)

        devices = await discover_devices(hass)

        for device in devices:
            if device[CONF_HOST] == current_host:
                continue

            client = ProvisionClient(
                host=device[CONF_HOST],
                port=device[CONF_PORT],
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD],
            )
            try:
                await client.connect()
                device_info = await client.get_device_info()
            except Exception:
                continue
            finally:
                await client.close()

            if device_info.mac == stored_mac:
                _LOGGER.warning(
                    "Device IP changed from %s to %s (MAC: %s)",
                    current_host,
                    device[CONF_HOST],
                    stored_mac,
                )

                await hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_HOST: device[CONF_HOST],
                        CONF_PORT: device[CONF_PORT],
                    },
                )
                return True

        _LOGGER.debug("No IP change detected")
        return False

    except Exception as err:  # pragma: no cover
        _LOGGER.debug("IP auto‑detection failed: %s", err)
        return False
