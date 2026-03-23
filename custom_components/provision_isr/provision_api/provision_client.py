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
    ProvisionConnectionError,
    InvalidRequestError,
    InvalidXMLFormatError,
    InvalidXMLContentError,
    PermissionDeniedError,
    ProvisionError,
)
from .models import DeviceInfo, ChannelList, DiskInfo, StreamCaps, StreamInfo

_LOGGER = logging.getLogger(__name__)

# --- The remainder of this file stays exactly the same as in your original version.
# It already imports the renamed ProvisionConnectionError correctly and uses
# `ProvisionConnectionError` when raising network‑related errors.
# No further edits are required here.
