"""Long polling for Provision ISR events."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.core import callback

from .provision_api import ProvisionClient
from .provision_api.models import DeviceInfo

_LOGGER = logging.getLogger(__name__)


class ProvisionLongPolling:
    """Handles long polling for Provision ISR events."""

    def __init__(self, client: ProvisionClient, device_info: DeviceInfo) -> None:
        """Initialize the long polling handler."""
        self._client = client
        self._device_info = device_info
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._is_running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start long polling."""
        if self._is_running:
            return
            
        self._is_running = True
        self._task = asyncio.create_task(self._poll_events())
        _LOGGER.info("Long polling started for %s", self._device_info.model)

    async def stop(self) -> None:
        """Stop long polling."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        _LOGGER.info("Long polling stopped for %s", self._device_info.model)

    @callback
    def register_callback(self, callback_func: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback for event notifications."""
        self._callbacks.append(callback_func)
        _LOGGER.debug("Registered callback, total callbacks: %d", len(self._callbacks))

    @callback
    def unregister_callback(self, callback_func: Callable[[dict[str, Any]], None]) -> None:
        """Unregister a callback."""
        if callback_func in self._callbacks:
            self._callbacks.remove(callback_func)
        _LOGGER.debug("Unregistered callback, total callbacks: %d", len(self._callbacks))

    async def _poll_events(self) -> None:
        """Long polling loop for events."""
        subscription_id = None
        
        try:
            # Subscribe to events
            subscription_id = await self._subscribe_to_events()
            if not subscription_id:
                _LOGGER.error("Failed to subscribe to events")
                return
                
            _LOGGER.info("Subscribed to events with ID: %s", subscription_id)
            
            # Main polling loop
            while self._is_running:
                try:
                    # Get events with timeout
                    events = await self._get_events(subscription_id)
                    
                    if events:
                        _LOGGER.debug("Received %d event(s)", len(events))
                        await self._process_events(events)
                    
                    # Small delay to prevent tight loop
                    await asyncio.sleep(0.1)
                    
                except asyncio.TimeoutError:
                    # Timeout is normal, just continue polling
                    continue
                except Exception as err:
                    _LOGGER.error("Error in polling loop: %s", err)
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except Exception as err:
            _LOGGER.error("Long polling failed: %s", err)
        finally:
            # Clean up subscription
            if subscription_id:
                await self._unsubscribe_from_events(subscription_id)
            self._is_running = False

    async def _subscribe_to_events(self) -> str | None:
        """Subscribe to device events."""
        try:
            # Build subscription XML based on device capabilities
            xml_payload = self._build_subscription_xml()
            
            response = await self._client._request(
                "SetSubscribe", 
                method="POST", 
                data=xml_payload
            )
            
            # Extract subscription ID from response
            config = response.get("config", {})
            server_address = config.get("serverAddress", {}).get("#text", "")
            
            if server_address:
                # Extract ID from server address like "http://192.168.0.43:8080/IPC/event/subsription_5"
                parts = server_address.split("_")
                if len(parts) > 1:
                    return parts[-1]
            
            return None
            
        except Exception as err:
            _LOGGER.error("Failed to subscribe to events: %s", err)
            return None

    def _build_subscription_xml(self) -> str:
        """Build subscription XML based on device capabilities."""
        # Start with basic motion detection
        smart_types = ["MOTION"]
        subscribe_relation = "ALARM_FEATURE"
        
        # Add additional event types based on capabilities
        caps = self._device_info.capabilities
        
        if caps.support_pea:
            smart_types.append("PEA")  # Perimeter/Intrusion
        if caps.support_avd:
            smart_types.append("AVD")  # Scene change/Video abnormality
        if caps.support_osc:
            smart_types.append("OSC")  # Object removal
        if caps.support_vfd:
            smart_types.append("VFD")  # Face detection
        if caps.support_cpc:
            smart_types.append("CPC")  # People counting
        if caps.support_cdd:
            smart_types.append("CDD")  # Crowd density
        if caps.support_ipd:
            smart_types.append("IPD")  # People intrusion
        if caps.support_vehice:
            smart_types.append("VEHICLE")  # License plate
        if caps.support_aoi_entry:
            smart_types.append("AOIENTRY")  # Region entrance
        if caps.support_aoi_leave:
            smart_types.append("AOILEAVE")  # Region exiting
        
        # Build XML with all supported event types
        smart_type_items = "\n".join(
            f'<item><smartType type="openAlramObj">{st}</smartType>'
            f'<subscribeRelation type="subscribeRelation">{subscribe_relation}</subscribeRelation></item>'
            for st in smart_types
        )
        
        xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<config version="1.0" xmlns="http://www.ipc.com/ver10">
    <channelID type="uint32">1</channelID>
    <initTermTime type="uint32">0</initTermTime>
    <subscribeFlag type="subscribeTypes">BASE_SUBSCRIBE</subscribeFlag>
    <subscribeList type="list" count="{len(smart_types)}">
        {smart_type_items}
    </subscribeList>
</config>"""
        
        _LOGGER.debug("Subscription XML: %s", xml_data)
        return xml_data

    async def _get_events(self, subscription_id: str) -> list[dict[str, Any]]:
        """Get events from device."""
        try:
            # Use GetPullMessages or similar endpoint
            response = await self._client._request(
                "GetPullMessages", 
                method="POST",
                data=f"""<?xml version="1.0" encoding="UTF-8"?>
<config version="1.0" xmlns="http://www.ipc.com/ver10">
    <serverAddress type="string">http://{self._client._host}:8080/IPC/event/subsription_{subscription_id}</serverAddress>
    <timeout type="uint32">5</timeout>
    <messageLimit type="uint32">10</messageLimit>
</config>"""
            )
            
            # Extract events from response
            config = response.get("config", {})
            events = config.get("alarmInfoList", {}).get("item", [])
            
            if not isinstance(events, list):
                events = [events]
                
            return events
            
        except Exception as err:
            _LOGGER.debug("No events received (timeout or error): %s", err)
            return []

    async def _process_events(self, events: list[dict[str, Any]]) -> None:
        """Process received events and notify callbacks."""
        for event in events:
            try:
                # Extract alarm status from event
                alarm_status = event.get("alarmStatusInfo", {})
                
                # Add device info to event data
                event_data = {
                    "alarmStatusInfo": alarm_status,
                    "deviceInfo": {
                        "mac": self._device_info.mac_address,
                        "model": self._device_info.model,
                    },
                    "timestamp": event.get("dataTime", {}).get("#text", "")
                }
                
                # Notify all registered callbacks
                for callback_func in self._callbacks:
                    try:
                        callback_func(event_data)
                    except Exception as err:
                        _LOGGER.error("Callback error: %s", err)
                        
                _LOGGER.debug("Processed event: %s", event_data)
                
            except Exception as err:
                _LOGGER.error("Error processing event: %s - %s", event, err)

    async def _unsubscribe_from_events(self, subscription_id: str) -> None:
        """Unsubscribe from events."""
        try:
            await self._client._request(
                "SetUnSubscribe", 
                method="POST",
                data=f"""<?xml version="1.0" encoding="UTF-8"?>
<config version="1.0" xmlns="http://www.ipc.com/ver10">
    <serverAddress type="string">http://{self._client._host}:8080/IPC/event/subsription_{subscription_id}</serverAddress>
</config>"""
            )
            _LOGGER.info("Unsubscribed from events")
        except Exception as err:
            _LOGGER.error("Failed to unsubscribe: %s", err)
