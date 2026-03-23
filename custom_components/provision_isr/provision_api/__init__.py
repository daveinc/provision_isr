"""Top‑level package for the Provision ISR API client library.

This module re‑exports the public API that the Home Assistant
integration expects:

* The main client class – ``ProvisionClient``.
* All data‑model classes (`ChannelList`, `DeviceInfo`, etc.).
* The full exception hierarchy – including the renamed
  ``ProvisionConnectionError``.
"""

# Re‑export the main client class (correct module name)
from .provision_client import ProvisionClient  # noqa: F401

# Re‑export the model types (used by camera, switch, binary_sensor, etc.)
from .models import (  # noqa: F401
    ChannelList,
    DeviceInfo,
    DiskInfo,
    StreamCaps,
    StreamInfo,
)

# Re‑export the exception hierarchy
from .exceptions import (  # noqa: F401
    ProvisionError,
    ProvisionConnectionError,
    AuthenticationError,
    InvalidRequestError,
    InvalidXMLFormatError,
    InvalidXMLContentError,
    PermissionDeniedError,
)

__all__ = [
    "ProvisionClient",
    "ChannelList",
    "DeviceInfo",
    "DiskInfo",
    "StreamCaps",
    "StreamInfo",
    "ProvisionError",
    "ProvisionConnectionError",
    "AuthenticationError",
    "InvalidRequestError",
    "InvalidXMLFormatError",
    "InvalidXMLContentError",
    "PermissionDeniedError",
]
