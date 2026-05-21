"""DataUpdateCoordinator for Provision ISR integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .provision_api import ProvisionClient
from .provision_api.exceptions import AuthenticationError, ProvisionConnectionError
from .provision_api.models import ChannelList, DeviceInfo, DiskInfo

_LOGGER = logging.getLogger(__name__)

# How often to poll device health (channel list, disk, etc.)
POLL_INTERVAL_SECONDS = 30


class ProvisionDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that manages shared Provision ISR device state.

    Polls device info, channel list, and disk status.
    Motion events arrive via ProvisionLongPolling and are merged here.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: ProvisionClient,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_info.mac}",
            update_interval=__import__("datetime").timedelta(seconds=POLL_INTERVAL_SECONDS),
        )
        self.client = client
        self.device_info = device_info
        # Motion state per channel: {channel_id: bool}
        self.motion_state: dict[int, bool] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest device state."""
        try:
            data: dict[str, Any] = {"device_info": self.device_info}

            if self.device_info.is_nvr():
                channel_list: ChannelList = await self.client.get_channel_list()
                data["channel_list"] = channel_list

            if self.device_info.support_sd_card:
                try:
                    disk: DiskInfo = await self.client.get_disk_info()
                    data["disk_info"] = disk
                except Exception as err:
                    _LOGGER.debug("Could not fetch disk info: %s", err)

            return data

        except AuthenticationError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except ProvisionConnectionError as err:
            raise UpdateFailed(f"Connection error: {err}") from err

    def update_motion(self, channel_id: int, is_on: bool) -> None:
        """Called by long polling when a motion event arrives."""
        if self.motion_state.get(channel_id) != is_on:
            self.motion_state[channel_id] = is_on
            # Notify all listeners (entity callbacks fire automatically)
            self.async_set_updated_data(self.data or {})
