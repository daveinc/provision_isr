"""Provision ISR API Client."""
from __future__ import annotations

import copy
import logging
import asyncio
from typing import Any, Dict

import httpx
import xmltodict

# --- import the command definitions ------------------------------------------------
from .xml_commands import commands

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


class ProvisionClient:
    """Client for Provision ISR camera."""

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
        try:
            await self.get_device_info()
            _LOGGER.info("Connected to %s:%s", self._host, self._port)
            return True
        except AuthenticationError:
            _LOGGER.error("Auth failed for %s:%s", self._host, self._port)
            raise
        except Exception as err:
            _LOGGER.error("Connection error: %s", err)
            raise ProvisionConnectionError(f"Connect failed: {err}") from err

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            _LOGGER.debug("Client closed")

    async def _get_client(self) -> httpx.AsyncClient:
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
        return DeviceInfo.from_dict(
            (await self._request("GetDeviceInfo")).get("config", {}
                                  ).get("deviceInfo", {})
        )

    async def get_channel_list(self) -> ChannelList:
        return ChannelList.from_dict(
            (await self._request("GetChannelList")).get("config", {})
        )

    async def get_disk_info(self) -> DiskInfo:
        return DiskInfo.from_dict(
            (await self._request("GetDiskInfo")).get("config", {})
        )

    async def get_stream_caps(self, channel_id: int = 1) -> StreamCaps:
        ep = f"GetStreamCaps/{channel_id}" if channel_id > 1 else "GetStreamCaps"
        return StreamCaps.from_dict(
            (await self._request(ep)).get("config", {})
        )

    async def get_snapshot(self, channel_id: int = 1) -> bytes:
        ep = f"GetSnapshot/{channel_id}" if channel_id > 1 else "GetSnapshot"
        client = await self._get_client()
        try:
            r = await client.get(f"{self._base_url}/{ep}")
            if r.status_code == HTTP_UNAUTHORIZED:
                raise AuthenticationError("Bad credentials")
            r.raise_for_status()
            return r.content
        except httpx.HTTPError as ex:
            raise ProvisionConnectionError(f"Snapshot error: {ex}") from ex

    # ------------------------------------------------------------------
    # Generic command executor (uses xml_commands.commands)
    # ------------------------------------------------------------------
    async def _execute(self, cmd_name: str, toggle: bool = False, channel_id: int = 1) -> bool:
        """Execute a command defined in xml_commands.commands."""
        if cmd_name not in commands:
            raise ValueError(f"Unknown command: {cmd_name}")

        spec = commands[cmd_name]
        endpoint = spec["endpoint"].lstrip("/").format(channel_id=channel_id)

        # start with a deep copy of the dict that the device sent
        payload = copy.deepcopy(spec["dict_repr"])

        # Apply any POST‑specific overrides first (if present)
        if spec["method"] == "POST" and "post_fields" in spec:
            for path, v in spec["post_fields"].items():
                parts = path.split(".")
                d = payload
                for p in parts[:-1]:
                    d = d.setdefault(p, {})
                d[parts[-1]] = {"#text": str(v).lower()}

        # Flip the toggle fields
        for path in spec.get("toggle_fields", []):
            parts = path.split(".")
            d = payload
            for p in parts[:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = {"#text": "true" if toggle else "false"}

        # Convert dict back to XML
        xml_body = xmltodict.unparse(payload, full_document=False)
        xml_payload = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}'

        # Send request
        if spec["method"] == "GET":
            resp = await self._request(endpoint)
        else:
            resp = await self._request(endpoint, method="POST", data=xml_payload)

        # If we toggled, confirm that the switch changed
        if toggle and spec["method"] == "POST":
            new_cfg = dict(resp.get("config", {}).get("motion", {}))
            new_switch = new_cfg.get("switch", {}).get("#text", "false")
            return new_switch == ("true" if toggle else "false")

        return True

    # ------------------------------------------------------------------
    # High‑level convenience wrappers
    # ------------------------------------------------------------------
    async def _get_motion_config(self, channel_id: int = 1) -> Dict[str, Any]:
        """Return the raw motion config dict for a channel."""
        ep = f"GetMotionConfig/{channel_id}" if channel_id > 1 else "GetMotionConfig"
        return (await self._request(ep)).get("config", {}).get("motion", {})

    async def set_motion_enabled(self, enabled: bool, channel_id: int = 1) -> bool:
        """Enable or disable motion detection via read-modify-write."""
        get_ep = f"GetMotionConfig/{channel_id}" if channel_id > 1 else "GetMotionConfig"
        raw = await self._request(get_ep)
        payload = copy.deepcopy(raw)

        # Modify the switch field inside the live config
        try:
            payload["config"]["motion"]["switch"] = {"#text": "true" if enabled else "false"}
        except KeyError:
            _LOGGER.error("Unexpected GetMotionConfig response structure")
            return False

        xml_body = xmltodict.unparse(payload, full_document=False)
        xml_payload = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_body}'

        post_ep = f"SetMotionConfig/{channel_id}" if channel_id > 1 else "SetMotionConfig"
        await self._request(post_ep, method="POST", data=xml_payload)
        return True

    async def toggle_audio(self, enable: bool, channel_id: int = 1) -> bool:
        return await self._execute("ToggleAudio", toggle=enable, channel_id=channel_id)

    # ------------------------------------------------------------------
    # ALARM helpers
    # ------------------------------------------------------------------
    async def get_alarm_status(self) -> Dict[str, Any]:
        return (await self._request("GetAlarmStatus")).get("config", {}).get("alarmStatusInfo", {})

    # ------------------------------------------------------------------
    # Generic request routine
    # ------------------------------------------------------------------
    async def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: str | None = None,
    ) -> Dict[str, Any]:
        url = f"{self._base_url}/{endpoint}"
        client = await self._get_client()

        try:
            if method.upper() == "POST":
                hdrs = {"Content-Type": "text/xml; charset=UTF-8"}
                r = await client.post(url, content=data, headers=hdrs)
            else:
                r = await client.get(url)

            r.raise_for_status()
            return xmltodict.parse(r.text)

        except httpx.HTTPError as ex:
            raise ProvisionConnectionError(f"HTTP error: {ex}") from ex

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "ProvisionClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()
