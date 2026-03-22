"""Binary sensor platform for Provision ISR integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .provision_api import ProvisionClient
from .provision_api.models import DeviceInfo as ProvisionDeviceInfo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Provision ISR binary sensors from a config entry."""
    
    client: ProvisionClient = hass.data[DOMAIN][entry.entry_id]["client"]
    device_info: ProvisionDeviceInfo = hass.data[DOMAIN][entry.entry_id]["device_info"]
    
    sensors = []
    
    # Check if device supports motion detection
    if device_info.support_motion_sens:
        if device_info.is_nvr():
            # Get channel list
            try:
                channel_list = await client.get_channel_list()
                
                for channel in channel_list.channels:
                    if channel.is_online:
                        sensors.append(
                            ProvisionMotionSensor(
                                client=client,
                                device_info=device_info,
                                entry=entry,
                                channel_id=int(channel.channel_id),
                            )
                        )
            except Exception as err:
                _LOGGER.error("Failed to get channel list: %s", err)
        else:
            # Single camera
            sensors.append(
                ProvisionMotionSensor(
                    client=client,
                    device_info=device_info,
                    entry=entry,
                    channel_id=1,
                )
            )
    
    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Added %d motion sensor(s)", len(sensors))


class ProvisionMotionSensor(BinarySensorEntity):
    """Representation of a Provision ISR motion sensor."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(
        self,
        client: ProvisionClient,
        device_info: ProvisionDeviceInfo,
        entry: ConfigEntry,
        channel_id: int,
    ) -> None:
        """Initialize the motion sensor."""
        self._client = client
        self._device_info = device_info
        self._entry = entry
        self._channel_id = channel_id
        self._attr_is_on = False
        
        # Generate unique ID
        self._attr_unique_id = f"{device_info.mac}_ch{channel_id}_motion"
        
        # Set name
        if device_info.is_nvr():
            self._attr_name = f"{device_info.model} Channel {channel_id} Motion"
        else:
            self._attr_name = f"{device_info.model} Motion"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self._device_info.is_nvr():
            # For NVR, link to channel device
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self._device_info.mac}_ch{self._channel_id}")},
                name=f"{self._device_info.model} Channel {self._channel_id}",
                manufacturer=self._device_info.brand,
                model=self._device_info.model,
                sw_version=self._device_info.software_version,
                via_device=(DOMAIN, self._device_info.mac),
            )
        else:
            # For IPC, use main device
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_info.mac)},
                name=self._device_info.model,
                manufacturer=self._device_info.brand,
                model=self._device_info.model,
                sw_version=self._device_info.software_version,
                hw_version=self._device_info.hardware_version,
                serial_number=self._device_info.serial_number,
            )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        # Register for long polling callbacks if available
        if "long_polling" in self.hass.data[DOMAIN][self._entry.entry_id]:
            long_polling = self.hass.data[DOMAIN][self._entry.entry_id]["long_polling"]
            long_polling.register_callback(self._handle_event_callback)
            _LOGGER.debug("Registered long polling callback for %s", self._attr_unique_id)
        else:
            _LOGGER.warning("Long polling not available, motion detection may not work")

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity is removed from hass."""
        # No cleanup needed for long polling (handled in __init__.py)
        pass

    async def _handle_event_callback(self, alarm_data: dict[str, Any]) -> None:
        """Handle alarm notification from alarm server.
        
        Args:
            alarm_data: Alarm status data from camera
        """
        # Extract motion alarm for this channel
        motion_alarms = alarm_data.get("motionAlarm", [])
        
        if not isinstance(motion_alarms, list):
            motion_alarms = [motion_alarms]
        
        for alarm in motion_alarms:
            if isinstance(alarm, dict):
                alarm_id = alarm.get("@id", "1")
                alarm_state = alarm.get("#text", "false")
            else:
                alarm_id = "1"
                alarm_state = str(alarm)
            
            # Check if this alarm is for our channel
            if int(alarm_id) == self._channel_id:
                new_state = alarm_state.lower() == "true"
                if new_state != self._attr_is_on:
                    self._attr_is_on = new_state
                    self.async_write_ha_state()
                    _LOGGER.debug(
                        "Motion %s for %s",
                        "detected" if new_state else "cleared",
                        self._attr_unique_id,
                    )
                break
