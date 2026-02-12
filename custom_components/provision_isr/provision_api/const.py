"""Constants for Provision ISR API."""

from typing import Final

# HTTP Methods
GET: Final = "GET"
POST: Final = "POST"
PUT: Final = "PUT"

# Connection types
CONNECTION_TYPE_DIRECT: Final = "Direct"
CONNECTION_TYPE_PROXIED: Final = "Proxied"

# Stream types
STREAM_TYPE: Final = {
    1: "Main Stream",
    2: "Sub-stream",
}

# Event types
EVENT_BASIC: Final = "basic"
EVENT_SMART: Final = "smart"
EVENT_IO: Final = "io"

# Events dictionary (Provision ISR specific)
EVENTS: Final = {
    "motiondetection": {
        "type": EVENT_BASIC,
        "label": "Motion",
        "device_class": "motion",
    },
    "tamperdetection": {
        "type": EVENT_BASIC,
        "label": "Video Tampering",
        "device_class": "tamper",
    },
    "videoloss": {
        "type": EVENT_BASIC,
        "label": "Video Loss",
        "device_class": "problem",
    },
    "fielddetection": {
        "type": EVENT_SMART,
        "label": "Intrusion",
        "device_class": "motion",
    },
    "linedetection": {
        "type": EVENT_SMART,
        "label": "Line Crossing",
        "device_class": "motion",
    },
    "io": {
        "type": EVENT_IO,
        "label": "Alarm Input",
        "device_class": "safety",
    },
}

# API Endpoints (will need adjustment based on actual Provision API)
ENDPOINT_DEVICE_INFO: Final = "System/deviceInfo"
ENDPOINT_CAPABILITIES: Final = "System/capabilities"
ENDPOINT_CHANNELS: Final = "System/Video/inputs/channels"
ENDPOINT_STREAMING: Final = "Streaming/channels"
ENDPOINT_MOTION: Final = "System/Video/inputs/channels/{}/motionDetection"