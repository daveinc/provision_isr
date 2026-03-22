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

from .const import DOMAIN, SENSOR_CAPABILITY_MAPPING, ALARM_INPUT_SENSOR, MULTI_SENSOR_CAPABILITIES
from .provision_api import ProvisionClient
from .provision_api.models import DeviceInfo as ProvisionDeviceInfo, DeviceCapabilities

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
    
    # Get capabilities
    capabilities = device_info.capabilities
    
    # Determine channels (NVR vs standalone camera)
    channels = await _get_channels(client, device_info)
    
    # Create sensors for each channel
    for channel_id in channels:
        # Create sensors based on capabilities
        sensors.extend(
            await _create_capability_sensors(
                client, device_info, entry, channel_id, capabilities
            )
        )
        
        # Create alarm input sensors (if any)
        if capabilities.alarm_in_count > 0:
            sensors.extend(
                _create_alarm_input_sensors(
                    client, device_info, entry, channel_id, capabilities
                )
            )
    
    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Added %d binary sensor(s) based on device capabilities", len(sensors))
    else:
        _LOGGER.warning("No binary sensors created - device may not support any sensors")


async def _get_channels(
    client: ProvisionClient, 
    device_info: ProvisionDeviceInfo
) -> list[int]:
    """Get list of channel IDs for the device."""
    channels = []
    
    try:
        if device_info.is_nvr():
            # Get channel list from NVR
            channel_list = await client.get_channel_list()
            for channel in channel_list.channels:
                if channel.is_online:
                    channels.append(int(channel.channel_id))
        else:
            # Single camera
            channels = [1]
            
    except Exception as err:
        _LOGGER.error("Failed to get channel list: %s", err)
        # Fallback to single channel
        channels = [1]
    
    _LOGGER.debug("Found channels: %s", channels)
    return channels


async def _create_capability_sensors(
    client: ProvisionClient,
    device_info: ProvisionDeviceInfo,
    entry: ConfigEntry,
    channel_id: int,
    capabilities: DeviceCapabilities
) -> list[ProvisionBinarySensor]:
    """Create sensors based on device capabilities."""
    sensors = []
    
    # Check each capability in the mapping
    for capability_name, sensor_config in SENSOR_CAPABILITY_MAPPING.items():
        # Check if device supports this capability
        if hasattr(capabilities, capability_name) and getattr(capabilities, capability_name):
            _LOGGER.debug("Device supports %s for channel %s", capability_name, channel_id)
            
            # Handle capabilities that create multiple sensors
            if capability_name in MULTI_SENSOR_CAPABILITIES and isinstance(sensor_config, list):
                for config_item in sensor_config:
                    sensors.append(
                        ProvisionBinarySensor(
                            client=client,
                            device_info=device_info,
                            entry=entry,
                            channel_id=channel_id,
                            sensor_config=config_item,
                        )
                    )
            else:
                # Single sensor per capability
                sensors.append(
                    ProvisionBinarySensor(
                        client=client,
                        device_info=device_info,
                        entry=entry,
                        channel_id=channel_id,
                        sensor_config=sensor_config,
                    )
                )
    
    return sensors


def _create_alarm_input_sensors(
    client: ProvisionClient,
    device_info: ProvisionDeviceInfo,
    entry: ConfigEntry,
    channel_id: int,
    capabilities: DeviceCapabilities
) -> list[ProvisionBinarySensor]:
    """Create alarm input sensors."""
    sensors = []
    
    # Create one sensor for each alarm input
    for input_index in range(capabilities.alarm_in_count):
        sensor_config = ALARM_INPUT_SENSOR.copy()
        sensor_config["input_index"] = input_index
        
        sensors.append(
            ProvisionBinarySensor(
                client=client,
                device_info=device_info,
                entry=entry,
                channel_id=channel_id,
                sensor_config=sensor_config,
            )
        )
    
    _LOGGER.debug("Created %d alarm input sensors for channel %s", 
                  len(sensors), channel_id)
    return sensors


class ProvisionBinarySensor(BinarySensorEntity):
    """Representation of a Provision ISR binary sensor."""

    def __init__(
        self,
        client: ProvisionClient,
        device_info: ProvisionDeviceInfo,
        entry: ConfigEntry,
        channel_id: int,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        self._client = client
        self._device_info = device_info
        self._entry = entry
        self._channel_id = channel_id
        self._sensor_config = sensor_config
        
        # Extract sensor type and name
        self._sensor_type = sensor_config.get("sensor_type", "unknown")
        self._input_index = sensor_config.get("input_index")
        
        # Generate unique ID
        if self._input_index is not None:
            self._attr_unique_id = f"{device_info.mac_address}_ch{channel_id}_{self._sensor_type}_{self._input_index}"
        else:
            self._attr_unique_id = f"{device_info.mac_address}_ch{channel_id}_{self._sensor_type}"
        
        # Set name
        base_name = sensor_config.get("name", "Unknown Sensor")
        if device_info.is_nvr():
            channel_text = f"Channel {channel_id} "
        else:
            channel_text = ""
            
        if self._input_index is not None:
            self._attr_name = f"{device_info.model} {channel_text}{base_name} {self._input_index + 1}"
        else:
            self._attr_name = f"{device_info.model} {channel_text}{base_name}"
        
        # Set device class and icon
        self._attr_device_class = sensor_config.get("device_class")
        self._attr_icon = sensor_config.get("icon")
        
        # Initial state
        self._attr_is_on = False
        
        _LOGGER.debug("Created sensor: %s (type: %s, channel: %s)", 
                     self._attr_name, self._sensor_type, channel_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self._device_info.is_nvr():
            # For NVR, link to channel device
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self._device_info.mac_address}_ch{self._channel_id}")},
                name=f"{self._device_info.model} Channel {self._channel_id}",
                manufacturer=self._device_info.brand,
                model=self._device_info.model,
                sw_version=self._device_info.software_version,
                via_device=(DOMAIN, self._device_info.mac_address),
            )
        else:
            # For IPC, use main device
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_info.mac_address)},
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
            _LOGGER.warning("Long polling not available for %s", self._attr_name)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity is removed from hass."""
        # No cleanup needed for long polling (handled in __init__.py)
        pass

    async def _handle_event_callback(self, alarm_data: dict[str, Any]) -> None:
        """Handle alarm notification from alarm server.
        
        Args:
            alarm_data: Alarm status data from camera
        """
        try:
            new_state = self._extract_alarm_state(alarm_data)
            
            if new_state is not None and new_state != self._attr_is_on:
                self._attr_is_on = new_state
                self.async_write_ha_state()
                
                if new_state:
                    _LOGGER.debug("%s triggered for %s", 
                                 self._sensor_config.get("name", "Sensor"),
                                 self._attr_unique_id)
                else:
                    _LOGGER.debug("%s cleared for %s",
                                 self._sensor_config.get("name", "Sensor"),
                                 self._attr_unique_id)
                                 
        except Exception as err:
            _LOGGER.error("Error processing alarm data for %s: %s", 
                         self._attr_unique_id, err)

    def _extract_alarm_state(self, alarm_data: dict[str, Any]) -> bool | None:
        """Extract alarm state for this specific sensor type."""
        # Get the alarm status info
        alarm_status = alarm_data.get("alarmStatusInfo", alarm_data)
        
        # Handle different sensor types
        if self._sensor_type == "motion":
            return self._extract_motion_state(alarm_status)
        elif self._sensor_type == "sensor_input" and self._input_index is not None:
            return self._extract_sensor_input_state(alarm_status)
        elif self._sensor_type == "perimeter_alarm":
            return self._extract_perimeter_state(alarm_status)
        elif self._sensor_type == "scene_change":
            return self._extract_scene_change_state(alarm_status)
        elif self._sensor_type == "clarity_abnormal":
            return self._extract_clarity_state(alarm_status)
        elif self._sensor_type == "color_abnormal":
            return self._extract_color_state(alarm_status)
        elif self._sensor_type == "object_removal":
            return self._extract_object_removal_state(alarm_status)
        # Add more sensor type handlers as needed
        
        _LOGGER.warning("No handler for sensor type: %s", self._sensor_type)
        return None

    def _extract_motion_state(self, alarm_status: dict[str, Any]) -> bool:
        """Extract motion alarm state."""
        motion_alarms = alarm_status.get("motionAlarm", [])
        
        if not isinstance(motion_alarms, list):
            motion_alarms = [motion_alarms]
        
        for alarm in motion_alarms:
            if isinstance(alarm, dict):
                alarm_id = alarm.get("@id", "1")
                alarm_state = alarm.get("#text", "false")
            else:
                alarm_id = "1"
                alarm_state = str(alarm)
            
            if int(alarm_id) == self._channel_id:
                return alarm_state.lower() == "true"
        
        return False

    def _extract_sensor_input_state(self, alarm_status: dict[str, Any]) -> bool:
        """Extract sensor input alarm state."""
        sensor_inputs = alarm_status.get("sensorAlarmIn", {})
        items = sensor_inputs.get("item", [])
        
        if not isinstance(items, list):
            items = [items]
        
        if self._input_index < len(items):
            item = items[self._input_index]
            if isinstance(item, dict):
                return item.get("#text", "false") == "true"
            else:
                return str(item).lower() == "true"
        
        return False

    def _extract_perimeter_state(self, alarm_status: dict[str, Any]) -> bool:
        """Extract perimeter alarm state."""
        perimeter_alarms = alarm_status.get("perimeterAlarm", [])
        
        if not isinstance(perimeter_alarms, list):
            perimeter_alarms = [perimeter_alarms]
        
        for alarm in perimeter_alarms:
            if isinstance(alarm, dict):
                alarm_id = alarm.get("@id", "1")
                alarm_state = alarm.get("#text", "false")
            else:
                alarm_id = "1"
                alarm_state = str(alarm)
            
            if int(alarm_id) == self._channel_id:
                return alarm_state.lower() == "true"
        
        return False

    def _extract_scene_change_state(self, alarm_status: dict[str, Any]) -> bool:
        """Extract scene change alarm state."""
        scene_changes = alarm_status.get("sceneChange", [])
        
        if not isinstance(scene_changes, list):
            scene_changes = [scene_changes]
        
        for alarm in scene_changes:
            if isinstance(alarm, dict):
                alarm_id = alarm.get("@id", "1")
                alarm_state = alarm.get("#text", "false")
            else:
                alarm_id = "1"
                alarm_state = str(alarm)
            
            if int(alarm_id) == self._channel_id:
                return alarm_state.lower() == "true"
        
        return False

    def _extract_clarity_state(self, alarm_status: dict[str, Any]) -> bool:
        """Extract video clarity abnormal state."""
        clarity_alarms = alarm_status.get("clarityAbnormal", [])
        
        if not isinstance(clarity_alarms, list):
            clarity_alarms = [clarity_alarms]
        
        for alarm in clarity_alarms:
            if isinstance(alarm, dict):
                alarm_id = alarm.get("@id", "1")
                alarm_state = alarm.get("#text", "false")
            else:
                alarm_id = "1"
                alarm_state = str(alarm)
            
            if int(alarm_id) == self._channel_id:
                return alarm_state.lower() == "true"
        
        return False

    def _extract_color_state(self, alarm_status: dict[str, Any]) -> bool:
        """Extract video color abnormal state."""
        color_alarms = alarm_status.get("colorAbnormal", [])
        
        if not isinstance(color_alarms, list):
            color_alarms = [color_alarms]
        
        for alarm in color_alarms:
            if isinstance(alarm, dict):
                alarm_id = alarm.get("@id", "1")
                alarm_state = alarm.get("#text", "false")
            else:
                alarm_id = "1"
                alarm_state = str(alarm)
            
            if int(alarm_id) == self._channel_id:
                return alarm_state.lower() == "true"
        
        return False

    def _extract_object_removal_state(self, alarm_status: dict[str, Any]) -> bool:
        """Extract object removal alarm state."""
        osc_alarms = alarm_status.get("oscAlarm", [])
        
        if not isinstance(osc_alarms, list):
            osc_alarms = [osc_alarms]
        
        for alarm in osc_alarms:
            if isinstance(alarm, dict):
                alarm_id = alarm.get("@id", "1")
                alarm_state = alarm.get("#text", "false")
            else:
                alarm_id = "1"
                alarm_state = str(alarm)
            
            if int(alarm_id) == self._channel_id:
                return alarm_state.lower() == "true"
        
        return False
