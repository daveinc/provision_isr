"""Camera platform for Provision ISR integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .provision_api import ProvisionClient
from .provision_api.models import DeviceInfo as ProvisionDeviceInfo, StreamInfo

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Provision ISR cameras from a config entry."""
    
    client: ProvisionClient = hass.data[DOMAIN][entry.entry_id]["client"]
    device_info: ProvisionDeviceInfo = hass.data[DOMAIN][entry.entry_id]["device_info"]
    
    cameras = []
    
    # Check if device is NVR with multiple channels
    if device_info.is_nvr():
        # Get channel list
        try:
            channel_list = await client.get_channel_list()
            
            for channel in channel_list.channels:
                if channel.is_online:
                    # Get stream capabilities for this channel
                    stream_caps = await client.get_stream_caps(int(channel.channel_id))
                    
                    # Create camera entity for main stream
                    main_stream = stream_caps.get_main_stream()
                    if main_stream:
                        cameras.append(
                            ProvisionCamera(
                                client=client,
                                device_info=device_info,
                                entry=entry,
                                channel_id=int(channel.channel_id),
                                stream_info=main_stream,
                                rtsp_port=stream_caps.rtsp_port,
                                is_main_stream=True,
                            )
                        )
                    
                    # Create camera entity for sub stream (if available)
                    sub_stream = stream_caps.get_sub_stream()
                    if sub_stream:
                        cameras.append(
                            ProvisionCamera(
                                client=client,
                                device_info=device_info,
                                entry=entry,
                                channel_id=int(channel.channel_id),
                                stream_info=sub_stream,
                                rtsp_port=stream_caps.rtsp_port,
                                is_main_stream=False,
                            )
                        )
        except Exception as err:
            _LOGGER.error("Failed to get channel list: %s", err)
    
    else:
        # Single camera (IPC)
        try:
            stream_caps = await client.get_stream_caps(1)
            
            # Create camera entity for main stream
            main_stream = stream_caps.get_main_stream()
            if main_stream:
                cameras.append(
                    ProvisionCamera(
                        client=client,
                        device_info=device_info,
                        entry=entry,
                        channel_id=1,
                        stream_info=main_stream,
                        rtsp_port=stream_caps.rtsp_port,
                        is_main_stream=True,
                    )
                )
            
            # Create camera entity for sub stream (if available)
            sub_stream = stream_caps.get_sub_stream()
            if sub_stream:
                cameras.append(
                    ProvisionCamera(
                        client=client,
                        device_info=device_info,
                        entry=entry,
                        channel_id=1,
                        stream_info=sub_stream,
                        rtsp_port=stream_caps.rtsp_port,
                        is_main_stream=False,
                    )
                )
        except Exception as err:
            _LOGGER.error("Failed to get stream capabilities: %s", err)
    
    if cameras:
        async_add_entities(cameras)
        _LOGGER.info("Added %d camera entit(ies)", len(cameras))


class ProvisionCamera(Camera):
    """Representation of a Provision ISR camera."""

    def __init__(
        self,
        client: ProvisionClient,
        device_info: ProvisionDeviceInfo,
        entry: ConfigEntry,
        channel_id: int,
        stream_info: StreamInfo,
        rtsp_port: int,
        is_main_stream: bool,
    ) -> None:
        """Initialize the camera."""
        super().__init__()
        
        self._client = client
        self._device_info = device_info
        self._entry = entry
        self._channel_id = channel_id
        self._stream_info = stream_info
        self._is_main_stream = is_main_stream
        
        # Build RTSP URL
        self._stream_source = stream_info.get_rtsp_url(
            host=entry.data[CONF_HOST],
            port=rtsp_port,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            is_nvr=device_info.is_nvr(),
            channel_id=channel_id,
        )
        
        # Generate unique ID
        stream_type = "main" if is_main_stream else "sub"
        self._attr_unique_id = f"{device_info.mac}_ch{channel_id}_{stream_type}"
        
        # Set name
        if device_info.is_nvr():
            base_name = f"{device_info.model} Channel {channel_id}"
        else:
            base_name = device_info.model
        
        self._attr_name = f"{base_name} ({stream_type.upper()})"
        
        # Camera features
        self._attr_supported_features = CameraEntityFeature.STREAM
        self._attr_brand = device_info.brand
        self._attr_model = device_info.model
        self._attr_frame_interval = 1 / stream_info.max_frame_rate

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if self._device_info.is_nvr():
            # For NVR, create a device per channel
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

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image from the camera."""
        try:
            return await self._client.get_snapshot(self._channel_id)
        except Exception as err:
            _LOGGER.error("Failed to get snapshot: %s", err)
            return None

    async def stream_source(self) -> str | None:
        """Return the RTSP stream source."""
        return self._stream_source

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "channel_id": self._channel_id,
            "stream_name": self._stream_info.stream_name,
            "resolution": self._stream_info.resolution,
            "frame_rate": self._stream_info.max_frame_rate,
            "encoding": self._stream_info.encode_type,
            "rtsp_url": self._stream_source,
        }
