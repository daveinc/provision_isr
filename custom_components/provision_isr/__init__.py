"""The Provision ISR integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME, Platform
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Provision ISR from a config entry."""
    
    # Check if IP auto-detection is enabled
    if entry.options.get(CONF_AUTO_DETECT_IP, False):
        await _auto_detect_ip_change(hass, entry)
    
    # Create API client
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
    except Exception as err:
        await client.close()
        _LOGGER.exception("Unexpected error during setup")
        raise ConfigEntryNotReady(f"Setup failed: {err}") from err
    
    # Store client and device info
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "device_info": device_info,
    }
    
    # Start long polling for motion events if supported
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
                
        except Exception as err:
            _LOGGER.warning("Failed to set up long polling: %s", err)
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Stop long polling if running
        if "long_polling" in hass.data[DOMAIN][entry.entry_id]:
            long_polling = hass.data[DOMAIN][entry.entry_id]["long_polling"]
            await long_polling.stop()
        
        # Close client connection
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        await client.close()
        
        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)
        
        _LOGGER.info("Unloaded Provision ISR integration")
    
    return unload_ok


async def _auto_detect_ip_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Auto-detect if device IP has changed and update config.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
    """
    if CONF_MAC_ADDRESS not in entry.data:
        _LOGGER.debug("No MAC address stored, skipping IP auto-detection")
        return
    
    stored_mac = entry.data[CONF_MAC_ADDRESS]
    current_host = entry.data[CONF_HOST]
    
    try:
        from .discovery import discover_devices
        
        _LOGGER.debug("Checking for IP changes (MAC: %s)...", stored_mac)
        
        # Discover devices
        devices = await discover_devices(hass)
        
        # Try to connect to each discovered device
        from .provision_api import ProvisionClient
        
        for device in devices:
            # Skip if same IP as current
            if device[CONF_HOST] == current_host:
                continue
            
            try:
                # Test connection
                client = ProvisionClient(
                    host=device[CONF_HOST],
                    port=device[CONF_PORT],
                    username=entry.data[CONF_USERNAME],
                    password=entry.data[CONF_PASSWORD],
                )
                
                device_info = await client.get_device_info()
                await client.close()
                
                # Check if MAC matches
                if device_info.mac == stored_mac:
                    _LOGGER.warning(
                        "Device IP changed from %s to %s (MAC: %s)",
                        current_host,
                        device[CONF_HOST],
                        stored_mac,
                    )
                    
                    # Update config entry
                    hass.config_entries.async_update_entry(
                        entry,
                        data={
                            **entry.data,
                            CONF_HOST: device[CONF_HOST],
                            CONF_PORT: device[CONF_PORT],
                        },
                    )
                    return
                    
            except Exception:
                continue
        
        _LOGGER.debug("No IP change detected")
        
    except Exception as err:
        _LOGGER.debug("IP auto-detection failed: %s", err)
