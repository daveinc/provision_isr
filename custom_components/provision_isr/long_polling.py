"""Long polling event listener for Provision ISR."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

import httpx
import xmltodict

_LOGGER = logging.getLogger(__name__)

# Subscription renewal interval (seconds)
RENEW_INTERVAL = 300  # 5 minutes


class ProvisionLongPolling:
    """Long polling event listener for Provision ISR cameras."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        long_polling_port: int = 8080,
    ) -> None:
        """Initialize long polling client.
        
        Args:
            host: Camera IP address
            port: Camera HTTP port
            username: Username for auth
            password: Password for auth
            long_polling_port: Long polling port (default: 8080)
        """
        self._host = host
        self._port = port
        self._long_polling_port = long_polling_port
        self._auth = httpx.BasicAuth(username, password)
        self._base_url = f"http://{host}:{port}"
        self._polling_url = f"http://{host}:{long_polling_port}"
        
        self._client: httpx.AsyncClient | None = None
        self._subscription_id: str | None = None
        self._callbacks: list[Callable] = []
        self._poll_task: asyncio.Task | None = None
        self._renew_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> bool:
        """Start long polling subscription.
        
        Returns:
            True if subscription successful
        """
        try:
            # Create HTTP client
            self._client = httpx.AsyncClient(
                auth=self._auth,
                timeout=60.0,  # Long timeout for polling
            )
            
            # Subscribe to events
            if not await self._subscribe():
                return False
            
            # Start polling and renewal tasks
            self._running = True
            self._poll_task = asyncio.create_task(self._poll_events())
            self._renew_task = asyncio.create_task(self._renew_subscription())
            
            _LOGGER.info("Long polling started on %s:%s", self._host, self._long_polling_port)
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to start long polling: %s", err)
            return False

    async def stop(self) -> None:
        """Stop long polling and unsubscribe."""
        self._running = False
        
        # Cancel tasks
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        if self._renew_task:
            self._renew_task.cancel()
            try:
                await self._renew_task
            except asyncio.CancelledError:
                pass
        
        # Unsubscribe
        if self._subscription_id:
            try:
                await self._unsubscribe()
            except Exception as err:
                _LOGGER.debug("Error unsubscribing: %s", err)
        
        # Close client
        if self._client:
            await self._client.aclose()
            self._client = None
        
        _LOGGER.info("Long polling stopped")

    def register_callback(self, callback: Callable) -> None:
        """Register callback for events.
        
        Args:
            callback: Async function to call with event data
        """
        self._callbacks.append(callback)

    async def _subscribe(self) -> bool:
        """Subscribe to motion events.
        
        Returns:
            True if subscription successful
        """
        # Build subscription XML
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<config version="1.0" xmlns="http://www.ipc.com/ver10">
    <types>
        <smartType>
            <enum>MOTION</enum>
        </smartType>
        <subscribeOption>
            <enum>ALARM</enum>
        </subscribeOption>
        <subscribeTypes>
            <enum>BASE_SUBSCRIBE</enum>
            <enum>REALTIME_SUBSCRIBE</enum>
        </subscribeTypes>
    </types>
    <channelID>1</channelID>
    <initTermTime>0</initTermTime>
    <subscribeFlag>REALTIME_SUBSCRIBE</subscribeFlag>
    <subscribeList type="list" count="1">
        <item>
            <smartType>MOTION</smartType>
            <subscribeRelation>ALARM</subscribeRelation>
        </item>
    </subscribeList>
</config>"""
        
        try:
            response = await self._client.post(
                f"{self._polling_url}/SetSubscribe",
                content=xml_data,
                headers={"Content-Type": "application/xml; charset=UTF-8"},
            )
            
            if response.status_code == 404:
                _LOGGER.warning(
                    "Camera does not support SetSubscribe endpoint. "
                    "Long polling not available on this camera model."
                )
                return False
            
            if response.status_code != 200:
                _LOGGER.error("Subscription failed: HTTP %s", response.status_code)
                return False
            
            # Parse response
            data = xmltodict.parse(response.text)
            config = data.get("config", {})
            
            # Extract subscription ID
            server_address = config.get("serverAddress", {})
            if isinstance(server_address, dict) and "#text" in server_address:
                self._subscription_id = server_address["#text"]
            else:
                self._subscription_id = str(server_address)
            
            _LOGGER.info("Subscribed with ID: %s", self._subscription_id)
            return True
            
        except Exception as err:
            _LOGGER.error("Subscription error: %s", err)
            return False

    async def _unsubscribe(self) -> None:
        """Unsubscribe from events."""
        if not self._subscription_id:
            return
        
        xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<config version="1.0" xmlns="http://www.ipc.com/ver10">
    <serverAddress><![CDATA[{self._subscription_id}]]></serverAddress>
</config>"""
        
        try:
            await self._client.post(
                f"{self._polling_url}/SetUnSubscribe",
                content=xml_data,
                headers={"Content-Type": "application/xml; charset=UTF-8"},
            )
            _LOGGER.debug("Unsubscribed from events")
        except Exception as err:
            _LOGGER.debug("Error unsubscribing: %s", err)

    async def _renew_subscription(self) -> None:
        """Periodically renew subscription."""
        while self._running:
            try:
                await asyncio.sleep(RENEW_INTERVAL)
                
                if not self._subscription_id:
                    continue
                
                xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<config version="1.0" xmlns="http://www.ipc.com/ver10">
    <serverAddress><![CDATA[{self._subscription_id}]]></serverAddress>
    <renewTime>600</renewTime>
</config>"""
                
                response = await self._client.post(
                    f"{self._polling_url}/SetRenew",
                    content=xml_data,
                    headers={"Content-Type": "application/xml; charset=UTF-8"},
                )
                
                if response.status_code == 200:
                    _LOGGER.debug("Subscription renewed")
                else:
                    _LOGGER.warning("Failed to renew subscription: HTTP %s", response.status_code)
                    
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Error renewing subscription: %s", err)

    async def _poll_events(self) -> None:
        """Poll for events continuously."""
        while self._running:
            try:
                if not self._subscription_id:
                    await asyncio.sleep(1)
                    continue
                
                # Build pull message request
                xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<config version="1.0" xmlns="http://www.ipc.com/ver10">
    <serverAddress><![CDATA[{self._subscription_id}]]></serverAddress>
    <timeout>30</timeout>
    <messageLimit>10</messageLimit>
</config>"""
                
                # Long poll for events (blocks until event or timeout)
                response = await self._client.post(
                    f"{self._polling_url}/GetPullMessages",
                    content=xml_data,
                    headers={"Content-Type": "application/xml; charset=UTF-8"},
                )
                
                if response.status_code != 200:
                    _LOGGER.debug("Poll returned HTTP %s", response.status_code)
                    await asyncio.sleep(5)
                    continue
                
                # Parse events
                data = xmltodict.parse(response.text)
                config = data.get("config", {})
                alarm_list = config.get("alarmInfoList", {})
                
                items = alarm_list.get("item", [])
                if not isinstance(items, list):
                    items = [items] if items else []
                
                # Process each event
                for item in items:
                    alarm_status = item.get("alarmStatusInfo", {})
                    if alarm_status:
                        # Trigger callbacks
                        for callback in self._callbacks:
                            try:
                                asyncio.create_task(callback(alarm_status))
                            except Exception as err:
                                _LOGGER.error("Error in callback: %s", err)
                
                if items:
                    _LOGGER.debug("Received %d event(s)", len(items))
                    
            except asyncio.CancelledError:
                break
            except httpx.ReadTimeout:
                # Normal timeout, continue polling
                continue
            except Exception as err:
                _LOGGER.error("Error polling events: %s", err)
                await asyncio.sleep(5)
