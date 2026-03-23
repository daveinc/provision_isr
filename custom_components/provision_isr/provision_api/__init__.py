"""Top‑level package for the Provision ISR API client library."""

# Re‑export the main client class
from .client import ProvisionClient  # noqa: F401

# Re‑export the model types (so other modules can use them without a submodule import)
from .models import (
    ChannelList,
    DeviceInfo,
    DiskInfo,
    StreamCaps,
    StreamInfo,
)  # noqa: F401

# Re‑export the exception hierarchy
from .exceptions import *  # noqa: F401,F403

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
