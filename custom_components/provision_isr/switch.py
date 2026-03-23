"""Switch platform for Provision ISR integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up Provision ISR switches from a config entry."""
    client: ProvisionClient = hass.data[DOMAIN][entry.entry_id]["client"]
    device_info: ProvisionDeviceInfo = hass.data[DOMAIN][entry.entry_id]["device_info"]

    switches = []

    # Check if device supports motion detection
    if device_info.support_motion_sens:
        if device_info.is_nvr():
            # Get channel list
            try:
                channel_list = await client.get_channel_list()
                for channel in channel_list.channels:
                    if channel.is_online:
                        switches.append(
                            ProvisionMotionSwitch(
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
            switches.append(
                ProvisionMotionSwitch(
                    client=client,
                    device_info=device_info,
                    entry=entry,
                    channel_id=1,
                )
            )

    if switches:
        async_add_entities(switches)
        _LOGGER.info("Added %d motion switch(es)", len(switches))


class ProvisionMotionSwitch(SwitchEntity):
    """Representation of a Provision ISR motion detection switch."""

    _attr_icon = "mdi:motion-sensor"

    def __init__(
        self,
        client: ProvisionClient,
        device_info: ProvisionDeviceInfo,
        entry: ConfigEntry,
        channel_id: int,
    ) -> None:
        """Initialize the motion switch."""
        self._client = client
        self._device_info = device_info
        self._entry = entry
        self._channel_id = channel_id

        # Generate unique ID
        self._attr_unique_id = f"{device_info.mac}_ch{channel_id}_motion_switch"

        # Set name
        if device_info.is_nvr():
            self._attr_name = f"{device_info.model} Channel {channel_id} Motion Detection"
        else:
            self._attr_name = f"{device_info.model} Motion Detection"

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
        # Get current motion detection state
        try:
            motion_config = await self._client.get_motion_config(self._channel_id)
            switch_value = motion_config.get("switch", "false")

            # Handle both boolean and string values
            self._attr_is_on = (
                (switch_value is True)
                or (isinstance(switch_value, str) and switch_value.lower() == "true")
            )

            _LOGGER.debug(
                "Motion detection for %s is %s",
                self._attr_unique_id,
                "enabled" if self._attr_is_on else "disabled",
            )
        except Exception as err:
            _LOGGER.error("Failed to get motion config: %s", err)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable motion detection."""
        try:
            changed = await self._client.set_motion_enabled(True, self._channel_id)
            if changed:
                self._attr_is_on = True
            else:
                _LOGGER.error("Camera rejected enable motion request")
        except Exception as err:
            _LOGGER.exception("Error enabling motion detection: %s", err)
        finally:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable motion detection."""
        try:
            changed = await self._client.set_motion_enabled(False, self._channel_id)
            if changed:
                self._attr_is_on = False
            else:
                _LOGGER.error("Camera rejected disable motion request")
        except Exception as err:
            _LOGGER.exception("Error disabling motion detection: %s", err)
        finally:
            self.async_write_ha_state()
