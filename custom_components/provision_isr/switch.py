"""Switch platform for Provision ISR integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ProvisionDataUpdateCoordinator
from .provision_api import ProvisionClient
from .provision_api.models import DeviceInfo as ProvisionDeviceInfo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Provision ISR switches from a config entry."""
    coordinator: ProvisionDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    client: ProvisionClient = hass.data[DOMAIN][entry.entry_id]["client"]
    device_info: ProvisionDeviceInfo = hass.data[DOMAIN][entry.entry_id]["device_info"]

    switches: list[ProvisionMotionSwitch] = []

    if device_info.support_motion_sens:
        if device_info.is_nvr():
            channel_list = coordinator.data.get("channel_list") if coordinator.data else None
            if channel_list:
                for channel in channel_list.channels:
                    if channel.is_online:
                        switches.append(
                            ProvisionMotionSwitch(
                                coordinator=coordinator,
                                client=client,
                                device_info=device_info,
                                entry=entry,
                                channel_id=int(channel.channel_id),
                            )
                        )
        else:
            switches.append(
                ProvisionMotionSwitch(
                    coordinator=coordinator,
                    client=client,
                    device_info=device_info,
                    entry=entry,
                    channel_id=1,
                )
            )

    if switches:
        async_add_entities(switches)
        _LOGGER.info("Added %d motion switch(es)", len(switches))


class ProvisionMotionSwitch(CoordinatorEntity[ProvisionDataUpdateCoordinator], SwitchEntity):
    """Motion detection enable/disable switch."""

    _attr_icon = "mdi:motion-sensor"

    def __init__(
        self,
        coordinator: ProvisionDataUpdateCoordinator,
        client: ProvisionClient,
        device_info: ProvisionDeviceInfo,
        entry: ConfigEntry,
        channel_id: int,
    ) -> None:
        super().__init__(coordinator)
        self._client = client
        self._provision_device_info = device_info
        self._entry = entry
        self._channel_id = channel_id
        self._attr_unique_id = f"{device_info.mac}_ch{channel_id}_motion_switch"
        if device_info.is_nvr():
            self._attr_name = f"{device_info.model} Channel {channel_id} Motion Detection"
        else:
            self._attr_name = f"{device_info.model} Motion Detection"

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

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        try:
            motion_config = await self._client._get_motion_config(self._channel_id)
            switch_value = motion_config.get("switch", {}).get("#text", "false")
            self._attr_is_on = switch_value.lower() == "true"
        except Exception as err:
            _LOGGER.warning("Could not read initial motion state for %s: %s", self._attr_unique_id, err)
            self._attr_is_on = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable motion detection."""
        try:
            changed = await self._client.set_motion_enabled(True, self._channel_id)
            if changed:
                self._attr_is_on = True
            else:
                _LOGGER.error("Failed to enable motion detection")
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
                _LOGGER.error("Failed to disable motion detection")
        except Exception as err:
            _LOGGER.exception("Error disabling motion detection: %s", err)
        finally:
            self.async_write_ha_state()
