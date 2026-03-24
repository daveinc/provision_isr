"""Provision ISR API Client."""
from __future__ import annotations

import copy
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
    ProvisionConnectionError,
    InvalidRequestError,
    InvalidXMLFormatError,
    InvalidXMLContentError,
    PermissionDeniedError,
    ProvisionError,
)
from .models import DeviceInfo, ChannelList, DiskInfo, StreamCaps, StreamInfo

_LOGGER = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Helper – build a full <config> XML from a motion‑config dictionary
# ----------------------------------------------------------------------
def _motion_cfg_to_xml(self, cfg: dict[str, Any], enabled: bool) -> str:
    """Return a <config> XML document built from a motion config dict."""
    cfg_copy = copy.deepcopy(cfg)

    # Toggle the <switch> value
    if "switch" in cfg_copy:
        if isinstance(cfg_copy["switch"], dict):
            cfg_copy["switch"]["#text"] = "true" if enabled else "false"
        else:
            cfg_copy["switch"] = {"#text": "true" if enabled else "false"}

    # Build the <config> root using the same version/namespace that the device sent
    root = {
        "config": {
            "@version": cfg_copy.get("@version", "1.7"),
            "@xmlns": cfg_copy.get("@xmlns", "http://www.ipc.com/ver10"),
            "motion": cfg_copy,
        }
    }

    body = xmltodict.unparse(root, full_document=False)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{body}'


class ProvisionClient:
    """Client for Provision ISR device."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        self._auth = httpx.BasicAuth(username, password)
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    async def connect(self) -> bool:
        """Test connection and authentication."""
        try:
            await self.get_device_info()
            _LOGGER.info("Successfully connected to %s:%s", self._host, self._port)
            return True
        except AuthenticationError:
            _LOGGER.error("Authentication failed for %s:%s", self._host, self._port)
            raise
        except Exception as err:
            _LOGGER.error("Connection failed to %s:%s: %s", self._host, self._port, err)
            raise ProvisionConnectionError(f"Failed to connect: {err}") from err

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            _LOGGER.debug("Client connection closed")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
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

    # ------------------------------------------------------------------
    # Device‑info helpers
    # ------------------------------------------------------------------
    async def get_device_info(self) -> DeviceInfo:
        response = await self._request("GetDeviceInfo")
        config = response.get("config", {})
        device_data = config.get("deviceInfo", {})
        return DeviceInfo.from_dict(device_data)

    async def get_channel_list(self) -> ChannelList:
        response = await self._request("GetChannelList")
        return ChannelList.from_dict(response.get("config", {}))

    async def get_disk_info(self) -> DiskInfo:
        response = await self._request("GetDiskInfo")
        return DiskInfo.from_dict(response.get("config", {}))

    async def get_stream_caps(self, channel_id: int = 1) -> StreamCaps:
        endpoint = f"GetStreamCaps/{channel_id}" if channel_id > 1 else "GetStreamCaps"
        response = await self._request(endpoint)
        return StreamCaps.from_dict(response.get("config", {}))

    async def get_snapshot(self, channel_id: int = 1) -> bytes:
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

    # ------------------------------------------------------------------
    # Helper for motion‑config retrieval with error guard
    # ------------------------------------------------------------------
    async def _get_motion_config(self, channel_id: int = 1) -> dict[str, Any] | None:
        try:
            return await self.get_motion_config(channel_id)
        except Exception as err:
            _LOGGER.warning(
                "Failed to get motion config (channel %s): %s", channel_id, err
            )
            return None

    async def get_motion_config(self, channel_id: int = 1) -> dict[str, Any]:
        """Return the motion configuration dict (just the <motion> node)."""
        endpoint = f"GetMotionConfig/{channel_id}" if channel_id > 1 else "GetMotionConfig"
        response = await self._request(endpoint)  # GET by default
        return response.get("config", {}).get("motion", {})

    async def set_motion_enabled(self, enabled: bool, channel_id: int = 1) -> bool:
        """Enable or disable motion detection.
        Returns True when the switch is successfully toggled.
        """
        # Grab current configuration
        motion_cfg = await self._get_motion_config(channel_id)
        if not motion_cfg:
            return False

        # Build XML payload using the helper
        xml_payload = _motion_cfg_to_xml(self, motion_cfg, enabled)

        _LOGGER.debug("Sending SetMotionConfig XML: %s", xml_payload)

        endpoint = f"SetMotionConfig/{channel_id}" if channel_id > 1 else "SetMotionConfig"
        await self._request(endpoint, method="POST", data=xml_payload)

        # Verify new state
        new_cfg = await self._get_motion_config(channel_id)
        if not new_cfg:
            return False
        new_switch = new_cfg.get("switch", {}).get("#text", "false")
        return new_switch == ("true" if enabled else "false")

    async def get_alarm_status(self) -> dict[str, Any]:
        """Get current alarm status."""
        response = await self._request("GetAlarmStatus")
        return response.get("config", {}).get("alarmStatusInfo", {})

    # ------------------------------------------------------------------
    # Generic request/response handling
    # ------------------------------------------------------------------
    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: str | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the device."""
        url = f"{self._base_url}/{endpoint}"
        client = await self._get_client()

        try:
            _LOGGER.debug("Request: %s %s", method, url)

            if method == "POST":
                headers = {"Content-Type": "text/xml; charset=UTF-8"}
                response = await client.post(url, content=data, headers=headers)
            else:  # GET
                response = await client.get(url)

            _LOGGER.debug(
                "Response: %s (status: %s)",
                endpoint,
                response.status_code,
            )
            _LOGGER.debug(
                "Response text: %s",
                response.text[:500] if response.text else "Empty",
            )

            # Handle HTTP status codes
            if response.status_code == HTTP_UNAUTHORIZED:
                raise AuthenticationError("Invalid username or password")

            if response.status_code == HTTP_BAD_REQUEST:
                # Parse error from the response
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
        """Parse XML text to a dictionary."""
        try:
            return xmltodict.parse(xml_text)
        except Exception as err:
            _LOGGER.error("Failed to parse XML: %s", err)
            raise InvalidXMLFormatError(f"Invalid XML format: {err}") from err

    def _raise_api_error(self, error_code: str | None) -> None:
        """Raise the appropriate exception based on the device error code."""
        error_map = {
            "1": InvalidRequestError("Invalid request URL or parameters"),
            "2": InvalidXMLFormatError("Invalid XML format"),
            "3": InvalidXMLContentError("Invalid XML content or out-of-range parameters"),
            "4": PermissionDeniedError("Permission denied"),
            "5": ProvisionError("Network port number error"),
        }

        exception = error_map.get(error_code, ProvisionError(f"Unknown error code: {error_code}"))
        raise exception

    # ------------------------------------------------------------------
    # Async time‑validate routine (optional)
    # ------------------------------------------------------------------
    async def async_time_validate(self, channel_id: int = 1, timeout_ms: int = 500) -> bool:
        """Re‑read GetMotionConfig after a short pause to confirm state.

        Returns True if the switch value matches the one returned by the last
        call to `set_motion_enabled`.
        """
        try:
            cfg_before = await self.get_motion_config(channel_id)
            if not cfg_before:
                _LOGGER.warning("async_time_validate: no config for channel %s", channel_id)
                return False
            # Wait a moment for the device to apply the change
            await asyncio.sleep(timeout_ms / 1000)
            cfg_after = await self.get_motion_config(channel_id)
            return (
                cfg_after.get("switch", {}).get("#text", "false")
                == cfg_before.get("switch", {}).get("#text", "false")
            )
        except Exception as err:
            _LOGGER.error("async_time_validate error: %s", err)
            return False

    # ------------------------------------------------------------------
    # Async context manager support
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "ProvisionClient":
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
