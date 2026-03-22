"""Provision ISR API Client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
import xmltodict

from .const import (
    DEFAULT_TIMEOUT,
    HTTP_OK,
    HTTP_UNAUTHORIZED,
    HTTP_BAD_REQUEST,
)
from .exceptions import (
    AuthenticationError,
    ConnectionError as ProvisionConnectionError,
    InvalidRequestError,
    InvalidXMLFormatError,
    InvalidXMLContentError,
    PermissionDeniedError,
    ProvisionError,
)
from .models import DeviceInfo, ChannelList, DiskInfo, StreamCaps

_LOGGER = logging.getLogger(__name__)


class ProvisionClient:
    """Client for Provision ISR API."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the Provision client.
        
        Args:
            host: IP address or hostname of the device
            port: HTTP port (default: 80)
            username: Username for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
        """
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        self._auth = httpx.BasicAuth(username, password)
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        """Test connection and authentication.
        
        Returns:
            True if connection successful
            
        Raises:
            AuthenticationError: If authentication fails
            ProvisionConnectionError: If connection fails
        """
        try:
            # Test connection by getting device info
            await self.get_device_info()
            _LOGGER.info("Successfully connected to %s:%s", self._host, self._port)
            return True
        except AuthenticationError:
            _LOGGER.error("Authentication failed for %s:%s", self._host, self._port)
            raise
        except Exception as err:
            _LOGGER.error("Connection failed to %s:%s: %s", self._host, self._port, err)
            raise ProvisionConnectionError(f"Failed to connect: {err}") from err

    async def get_device_info(self) -> DeviceInfo:
        """Get device information.
        
        Returns:
            DeviceInfo object with device details
        """
        response = await self._request("GetDeviceInfo")
        
        # Navigate to deviceInfo in the XML response
        config = response.get("config", {})
        device_data = config.get("deviceInfo", {})
        
        return DeviceInfo.from_dict(device_data)

    async def get_channel_list(self) -> ChannelList:
        """Get channel list (NVR only).
        
        Returns:
            ChannelList object with channel information
        """
        response = await self._request("GetChannelList")
        config = response.get("config", {})
        return ChannelList.from_dict(config)

    async def get_disk_info(self) -> DiskInfo:
        """Get disk information.
        
        Returns:
            DiskInfo object with disk details
        """
        response = await self._request("GetDiskInfo")
        config = response.get("config", {})
        return DiskInfo.from_dict(config)

    async def get_stream_caps(self, channel_id: int = 1) -> StreamCaps:
        """Get stream capabilities for a channel.
        
        Args:
            channel_id: Channel ID (default: 1)
            
        Returns:
            StreamCaps object with stream information
        """
        endpoint = f"GetStreamCaps/{channel_id}" if channel_id > 1 else "GetStreamCaps"
        response = await self._request(endpoint)
        config = response.get("config", {})
        return StreamCaps.from_dict(config)

    async def get_snapshot(self, channel_id: int = 1) -> bytes:
        """Get snapshot image for a channel.
        
        Args:
            channel_id: Channel ID (default: 1)
            
        Returns:
            JPEG image bytes
        """
        endpoint = f"GetSnapshot/{channel_id}" if channel_id > 1 else "GetSnapshot"
        url = f"{self._base_url}/{endpoint}"
        client = await self._get_client()
        
        try:
            response = await client.get(url)
            
            if response.status_code == HTTP_UNAUTHORIZED:
                raise AuthenticationError("Invalid username or password")
            
            if response.status_code != HTTP_OK:
                raise ProvisionConnectionError(f"Snapshot failed: HTTP {response.status_code}")
            
            return response.content
            
        except httpx.TimeoutException as err:
            raise ProvisionConnectionError(f"Snapshot timeout: {err}") from err
        except httpx.RequestError as err:
            raise ProvisionConnectionError(f"Snapshot failed: {err}") from err

    async def get_motion_config(self, channel_id: int = 1) -> dict[str, Any]:
        """Get motion detection configuration.
        
        Args:
            channel_id: Channel ID (default: 1)
            
        Returns:
            Motion configuration dict
        """
        endpoint = f"GetMotionConfig/{channel_id}" if channel_id > 1 else "GetMotionConfig"
        response = await self._request(endpoint)
        config = response.get("config", {})
        motion_config = config.get("motion", {})
        
        # Log the full config for debugging
        _LOGGER.debug("Motion config for channel %s: %s", channel_id, motion_config)
        
        return motion_config

    async def set_motion_enabled(self, enabled: bool, channel_id: int = 1) -> bool:
        """Enable or disable motion detection.
        
        Args:
            enabled: True to enable, False to disable
            channel_id: Channel ID (default: 1)
            
        Returns:
            True if successful
        """
        # First get current config
        motion_config = await self.get_motion_config(channel_id)
        
        # Log the current config
        _LOGGER.debug("Current motion config: %s", motion_config)
        
        # Extract values with defaults
        switch = str(enabled).lower()
        sensitivity = motion_config.get("sensitivity", {}).get("#text", "6")
        alarm_hold_time = motion_config.get("alarmHoldTime", {}).get("#text", "3")
        
        # Handle area list
        area_items = motion_config.get("area", {}).get("item", [])
        if not isinstance(area_items, list):
            area_items = [area_items]
        
        # Handle sensitivities list
        sensitivity_items = motion_config.get("sensitivities", {}).get("item", [])
        if not isinstance(sensitivity_items, list):
            sensitivity_items = [sensitivity_items]
        
        # Build complete XML request with ALL required fields
        xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<config version="1.7" xmlns="http://www.ipc.com/ver10">
    <motion>
        <switch type="boolean">{switch}</switch>
        <sensitivity type="int32" min="1" max="8">{sensitivity}</sensitivity>
        <alarmHoldTime type="uint32">{alarm_hold_time}</alarmHoldTime>
        <area type="list" count="9">
            <itemType type="string" minLen="16" maxLen="16"/>
            {self._build_xml_items(area_items)}
        </area>
        <sensitivities type="list" count="9">
            <itemType type="string" minLen="16" maxLen="16"/>
            {self._build_xml_items(sensitivity_items)}
        </sensitivities>
        <triggerAlarmOut type="list" count="0">
            <itemType type="boolean"/>
        </triggerAlarmOut>
        <mail type="list" count="0">
            <switch type="boolean">false</switch>
            <subject type="string" maxLen="63">
                <![CDATA[]]>
            </subject>
            <content type="string" maxLen="255">
                <![CDATA[]]>
            </content>
        </mail>
        <ftp type="list" count="0">
            <switch type="boolean">false</switch>
        </ftp>
        <sendPush>
            <pushSwitch type="boolean">false</pushSwitch>
            <recordSwitch type="boolean">false</recordSwitch>
            <recordStreamIndex type="uint8">0</recordStreamIndex>
            <sendPicSwitch type="boolean">false</sendPicSwitch>
            <recordTime type="uint32">0</recordTime>
            <pushContent type="string" maxLen="127">
                <![CDATA[]]>
            </pushContent>
        </sendPush>
        <audioSwitch type="boolean">false</audioSwitch>
    </motion>
</config>"""
        
        # Log the XML being sent
        _LOGGER.debug("Sending SetMotionConfig XML: %s", xml_data)
        
        endpoint = f"SetMotionConfig/{channel_id}" if channel_id > 1 else "SetMotionConfig"
        response = await self._request(endpoint, method="POST", data=xml_data)
        
        # Verify the change took effect
        new_config = await self.get_motion_config(channel_id)
        new_switch = new_config.get("switch", {}).get("#text", "false")
        
        if new_switch != switch:
            _LOGGER.error("Failed to update motion detection. Expected %s, got %s", 
                         switch, new_switch)
            return False
        
        _LOGGER.info("Successfully %s motion detection for channel %s", 
                    "enabled" if enabled else "disabled", channel_id)
        return True

    def _build_xml_items(self, items: list) -> str:
        """Build XML item elements from list.
        
        Args:
            items: List of item values
            
        Returns:
            XML string with item elements
        """
        xml_items = []
        for item in items:
            # Handle both dict format (from xmltodict) and string format
            if isinstance(item, dict):
                value = item.get("#text", "")
            else:
                value = str(item)
            xml_items.append(f'<item><![CDATA[{value}]]></item>')
        
        # Ensure we have exactly 9 items (as per the config)
        while len(xml_items) < 9:
            xml_items.append('<item><![CDATA[1111111111111111]]></item>')
        
        return '\n            '.join(xml_items)

    async def get_alarm_status(self) -> dict[str, Any]:
        """Get current alarm status.
        
        Returns:
            Alarm status dict with motion, sensor, and other alarms
        """
        response = await self._request("GetAlarmStatus")
        config = response.get("config", {})
        return config.get("alarmStatusInfo", {})

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            _LOGGER.debug("Client connection closed")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.
        
        Returns:
            Configured httpx.AsyncClient
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=self._auth,
                timeout=self._timeout,
                follow_redirects=True,
                headers={
                    "Content-Type": "application/xml; charset=UTF-8",
                    "Connection": "Keep-Alive",
                },
            )
        return self._client

    async def _request(
        self,
        endpoint: str,
        method: str = "POST",
        data: str | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to the device.
        
        Args:
            endpoint: API endpoint (e.g., "GetDeviceInfo")
            method: HTTP method (POST or GET)
            data: XML data for POST requests
            
        Returns:
            Parsed XML response as dictionary
            
        Raises:
            AuthenticationError: On 401 response
            ProvisionError: On API errors
            ProvisionConnectionError: On connection failures
        """
        url = f"{self._base_url}/{endpoint}"
        client = await self._get_client()

        try:
            _LOGGER.debug("Request: %s %s", method, url)
            
            if method == "POST":
                headers = {"Content-Type": "text/xml; charset=UTF-8"}
                response = await client.post(url, content=data, headers=headers)
            else:
                response = await client.get(url)

            _LOGGER.debug(
                "Response: %s (status: %s)",
                endpoint,
                response.status_code,
            )
            
            # Log response text for debugging
            _LOGGER.debug("Response text: %s", response.text[:500] if response.text else "Empty")

            # Handle HTTP status codes
            if response.status_code == HTTP_UNAUTHORIZED:
                raise AuthenticationError("Invalid username or password")

            if response.status_code == HTTP_BAD_REQUEST:
                # Parse error from response
                error_data = self._parse_xml(response.text)
                error_code = error_data.get("config", {}).get("@errorCode")
                self._raise_api_error(error_code)

            if response.status_code != HTTP_OK:
                raise ProvisionConnectionError(
                    f"HTTP {response.status_code}: {response.text}"
                )

            # Parse successful response
            return self._parse_xml(response.text)

        except httpx.TimeoutException as err:
            raise ProvisionConnectionError(f"Request timeout: {err}") from err
        except httpx.RequestError as err:
            raise ProvisionConnectionError(f"Request failed: {err}") from err

    def _parse_xml(self, xml_text: str) -> dict[str, Any]:
        """Parse XML response to dictionary.
        
        Args:
            xml_text: XML string
            
        Returns:
            Parsed XML as dictionary
        """
        try:
            # xmltodict preserves attributes with @ prefix
            return xmltodict.parse(xml_text)
        except Exception as err:
            _LOGGER.error("Failed to parse XML: %s", err)
            raise InvalidXMLFormatError(f"Invalid XML format: {err}") from err

    def _raise_api_error(self, error_code: str | None) -> None:
        """Raise appropriate exception based on error code.
        
        Args:
            error_code: Error code from API response
            
        Raises:
            Appropriate ProvisionError subclass
        """
        error_map = {
            "1": InvalidRequestError("Invalid request URL or parameters"),
            "2": InvalidXMLFormatError("Invalid XML format"),
            "3": InvalidXMLContentError("Invalid XML content or out-of-range parameters"),
            "4": PermissionDeniedError("Permission denied"),
            "5": ProvisionError("Network port number error"),
        }
        
        exception = error_map.get(error_code, ProvisionError(f"Unknown error code: {error_code}"))
        raise exception

    async def __aenter__(self) -> ProvisionClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()
