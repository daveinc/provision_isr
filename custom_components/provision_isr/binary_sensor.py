"""Binary sensor platform for Provision ISR integration."""
from __future__ import annotations

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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProvisionDataUpdateCoordinator
from .provision_api.models import DeviceInfo as ProvisionDeviceInfo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Provision ISR binary sensors from a config entry."""
    coordinator: ProvisionDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info: ProvisionDeviceInfo = hass.data[DOMAIN][entry.entry_id]["device_info"]
    long_polling = hass.data[DOMAIN][entry.entry_id].get("long_polling")

    sensors: list[ProvisionMotionSensor] = []

    if device_info.support_motion_sens:
        if device_info.is_nvr():
            channel_list = coordinator.data.get("channel_list") if coordinator.data else None
            if channel_list:
                for channel in channel_list.channels:
                    if channel.is_online:
                        sensors.append(
                            ProvisionMotionSensor(
                                coordinator=coordinator,
                                device_info=device_info,
                                entry=entry,
                                channel_id=int(channel.channel_id),
                            )
                        )
        else:
            sensors.append(
                ProvisionMotionSensor(
                    coordinator=coordinator,
                    device_info=device_info,
                    entry=entry,
                    channel_id=1,
                )
            )

    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Added %d motion sensor(s)", len(sensors))

        # Wire long polling callbacks now that entities exist
        if long_polling:
            for sensor in sensors:
                long_polling.register_callback(sensor.handle_event_callback)


class ProvisionMotionSensor(CoordinatorEntity[ProvisionDataUpdateCoordinator], BinarySensorEntity):
    """Motion sensor backed by the shared coordinator."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(
        self,
        coordinator: ProvisionDataUpdateCoordinator,
        device_info: ProvisionDeviceInfo,
        entry: ConfigEntry,
        channel_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._provision_device_info = device_info
        self._entry = entry
        self._channel_id = channel_id
        self._attr_unique_id = f"{device_info.mac}_ch{channel_id}_motion"
        if device_info.is_nvr():
            self._attr_name = f"{device_info.model} Channel {channel_id} Motion"
        else:
            self._attr_name = f"{device_info.model} Motion"

    @property
    def is_on(self) -> bool:
        """Return True when motion is detected."""
        return self.coordinator.motion_state.get(self._channel_id, False)

    @property
    def device_info(self) -> DeviceInfo:
        if self._provision_device_info.is_nvr():
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self._provision_device_info.mac}_ch{self._channel_id}")},
                name=f"{self._provision_device_info.model} Channel {self._channel_id}",
                manufacturer=self._provision_device_info.brand,
                model=self._provision_device_info.model,
                sw_version=self._provision_device_info.software_version,
                via_device=(DOMAIN, self._provision_device_info.mac),
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self._provision_device_info.mac)},
            name=self._provision_device_info.model,
            manufacturer=self._provision_device_info.brand,
            model=self._provision_device_info.model,
            sw_version=self._provision_device_info.software_version,
            hw_version=self._provision_device_info.hardware_version,
            serial_number=self._provision_device_info.serial_number,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """React to coordinator updates (motion_state changed)."""
        self.async_write_ha_state()

    async def handle_event_callback(self, alarm_data: dict[str, Any]) -> None:
        """Called by ProvisionLongPolling when a motion event arrives."""
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

            if int(alarm_id) == self._channel_id:
                new_state = alarm_state.lower() == "true"
                self.coordinator.update_motion(self._channel_id, new_state)
                _LOGGER.debug(
                    "Motion %s for channel %d",
                    "detected" if new_state else "cleared",
                    self._channel_id,
                )
                break
