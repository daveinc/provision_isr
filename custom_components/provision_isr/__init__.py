"""The Provision ISR integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, DEFAULT_PORT, DEFAULT_USERNAME
from .provision_api import ProvisionClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "camera", "switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Provision ISR from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})
    
    # Get configuration from entry
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = entry.data[CONF_PASSWORD]
    
    # Create API client
    client = ProvisionClient(host, port, username, password)
    
    try:
        # Test connection and get device info
        await client.connect()
        device_info = await client.get_device_info()
        
        # Log device capabilities
        _log_device_capabilities(device_info)
        
    except Exception as err:
        await client.close()
        raise ConfigEntryNotReady(f"Failed to connect to device: {err}") from err
    
    # Store client and device info
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "device_info": device_info,
    }
    
    # Set up long polling for events
    await _setup_long_polling(hass, entry, client, device_info)
    
    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Clean up long polling
        if "long_polling" in hass.data[DOMAIN][entry.entry_id]:
            long_polling = hass.data[DOMAIN][entry.entry_id]["long_polling"]
            await long_polling.stop()
        
        # Close client
        client = hass.data[DOMAIN][entry.entry_id]["client"]
        await client.close()
        
        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


def _log_device_capabilities(device_info) -> None:
    """Log device capabilities for debugging."""
    caps = device_info.capabilities
    
    _LOGGER.info("Device: %s (%s)", device_info.model, device_info.mac_address)
    _LOGGER.info("Software: %s, Hardware: %s", 
                 device_info.software_version, device_info.hardware_version)
    
    # Log supported features
    supported_features = []
    
    if caps.support_motion_sens:
        supported_features.append("Motion Detection")
    if caps.support_pea:
        supported_features.append("Perimeter/Intrusion")
    if caps.support_avd:
        supported_features.append("Scene Change/Video Abnormality")
    if caps.support_osc:
        supported_features.append("Object Removal")
    if caps.support_vfd:
        supported_features.append("Face Detection")
    if caps.support_cpc:
        supported_features.append("People Counting")
    if caps.support_cdd:
        supported_features.append("Crowd Density")
    if caps.support_ipd:
        supported_features.append("People Intrusion")
    if caps.support_vehice:
        supported_features.append("License Plate")
    if caps.support_aoi_entry:
        supported_features.append("Region Entrance")
    if caps.support_aoi_leave:
        supported_features.append("Region Exiting")
    
    if supported_features:
        _LOGGER.info("Supported features: %s", ", ".join(supported_features))
    else:
        _LOGGER.warning("No advanced features supported")
    
    # Log hardware capabilities
    if caps.alarm_in_count > 0:
        _LOGGER.info("Alarm inputs: %d", caps.alarm_in_count)
    if caps.alarm_out_count > 0:
        _LOGGER.info("Alarm outputs: %d", caps.alarm_out_count)
    if caps.audio_in_count > 0:
        _LOGGER.info("Audio inputs: %d", caps.audio_in_count)
    if caps.audio_out_count > 0:
        _LOGGER.info("Audio outputs: %d", caps.audio_out_count)


async def _setup_long_polling(
    hass: HomeAssistant,
    entry: ConfigEntry,
    client: ProvisionClient,
    device_info
) -> None:
    """Set up long polling for event notifications."""
    try:
        # Import here to avoid circular dependency
        from .long_polling import ProvisionLongPolling
        
        # Only set up long polling if device supports it
        if device_info.capabilities.support_apilong_polling:
            long_polling = ProvisionLongPolling(client, device_info)
            await long_polling.start()
            
            # Store in hass data
            hass.data[DOMAIN][entry.entry_id]["long_polling"] = long_polling
            
            _LOGGER.info("Long polling started for %s", device_info.model)
        else:
            _LOGGER.warning("Device does not support API long polling - events may not work")
            
    except Exception as err:
        _LOGGER.error("Failed to set up long polling: %s", err)
        # Don't fail setup if long polling fails
