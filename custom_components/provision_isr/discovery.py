"""Device discovery for Provision ISR."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import COMMON_PORTS, DISCOVERY_TIMEOUT

_LOGGER = logging.getLogger(__name__)


async def discover_devices(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Discover Provision ISR devices on the network.
    
    Args:
        hass: Home Assistant instance
        
    Returns:
        List of discovered devices with host, port, and device info
    """
    discovered = []
    
    # Try UPnP discovery first
    _LOGGER.debug("Starting UPnP discovery...")
    upnp_devices = await discover_upnp(hass)
    discovered.extend(upnp_devices)
    
    # Try port scanning for common Provision ports
    _LOGGER.debug("Starting port scan...")
    scanned_devices = await scan_network(hass)
    
    # Merge results, avoiding duplicates
    existing_hosts = {d[CONF_HOST] for d in discovered}
    for device in scanned_devices:
        if device[CONF_HOST] not in existing_hosts:
            discovered.append(device)
    
    _LOGGER.info("Discovery complete. Found %d device(s)", len(discovered))
    return discovered


async def discover_upnp(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Discover devices via UPnP.
    
    Args:
        hass: Home Assistant instance
        
    Returns:
        List of discovered devices
    """
    devices = []
    
    try:
        # UPnP SSDP discovery
        from homeassistant.components import ssdp
        
        entries = await ssdp.async_get_discovery_info_by_st(
            hass, "upnp:rootdevice"
        )
        
        for entry in entries:
            # Check if it's a Provision device
            manufacturer = entry.upnp.get(ssdp.ATTR_UPNP_MANUFACTURER, "").lower()
            model = entry.upnp.get(ssdp.ATTR_UPNP_MODEL_NAME, "").lower()
            
            if "provision" in manufacturer or "provision" in model:
                # Extract host and port from presentation URL
                presentation_url = entry.upnp.get(ssdp.ATTR_UPNP_PRESENTATION_URL)
                if presentation_url:
                    # Parse URL to get host:port
                    from urllib.parse import urlparse
                    parsed = urlparse(presentation_url)
                    
                    devices.append({
                        CONF_HOST: parsed.hostname,
                        CONF_PORT: parsed.port or 80,
                        "model": entry.upnp.get(ssdp.ATTR_UPNP_MODEL_NAME, "Unknown"),
                        "name": f"{entry.upnp.get(ssdp.ATTR_UPNP_MODEL_NAME, 'Provision')} ({parsed.hostname})",
                    })
        
        _LOGGER.debug("UPnP found %d Provision device(s)", len(devices))
        
    except ImportError:
        _LOGGER.debug("SSDP component not available, skipping UPnP discovery")
    except Exception as err:
        _LOGGER.debug("UPnP discovery failed: %s", err)
    
    return devices


async def scan_network(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Scan local network for Provision devices.
    
    Args:
        hass: Home Assistant instance
        
    Returns:
        List of discovered devices
    """
    devices = []
    
    # Get local network range
    import ipaddress
    
    try:
        # Get Home Assistant's network configuration
        from homeassistant.components import network
        
        adapters = await network.async_get_adapters(hass)
        local_ips = []
        
        for adapter in adapters:
            for ip_info in adapter["ipv4"]:
                if ip_info.get("address"):
                    local_ips.append(ip_info["address"])
        
        # Scan first local IP's subnet (limit scope)
        if local_ips:
            network_ip = ipaddress.ip_network(f"{local_ips[0]}/24", strict=False)
            tasks = []
            
            # Limit to first 50 IPs to avoid slowdown
            for ip in list(network_ip.hosts())[:50]:
                tasks.append(_probe_host(str(ip)))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and result.get("found"):
                    devices.append(result)
        
        _LOGGER.debug("Network scan found %d device(s)", len(devices))
        
    except ImportError:
        _LOGGER.debug("Network component not available, skipping network scan")
    except Exception as err:
        _LOGGER.debug("Network scan failed: %s", err)
    
    return devices


async def _probe_host(host: str) -> dict[str, Any]:
    """Probe a host for Provision device on common ports.
    
    Args:
        host: IP address to probe
        
    Returns:
        Device info if found, empty dict otherwise
    """
    import httpx
    
    for port in COMMON_PORTS:
        try:
            # Quick connection test
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"http://{host}:{port}/GetDeviceInfo")
                
                # Check if response looks like Provision XML
                if response.status_code in (200, 401) and "provision" in response.text.lower():
                    return {
                        "found": True,
                        CONF_HOST: host,
                        CONF_PORT: port,
                        "model": "Provision ISR Device",
                        "name": f"Provision ISR ({host}:{port})",
                    }
        except:
            continue
    
    return {"found": False}
