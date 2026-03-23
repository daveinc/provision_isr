"""Constants for Provision ISR integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

DOMAIN = "provision_isr"
DEFAULT_TIMEOUT = 10
DEFAULT_PORT = 90
DEFAULT_USERNAME = "admin"  # Add this line

# Discovery
COMMON_PORTS = [80, 90, 51986]  # Common Provision ISR ports
DISCOVERY_TIMEOUT = 10  # seconds

# HTTP Status Codes
HTTP_OK = 200
HTTP_UNAUTHORIZED = 401
HTTP_BAD_REQUEST = 400

# Configuration
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Mapping between API capability flags and sensor types
SENSOR_CAPABILITY_MAPPING = {
    # Motion detection
    "support_motion_sens": {
        "sensor_type": "motion",
        "name": "Motion",
        "device_class": BinarySensorDeviceClass.MOTION,
        "icon": None,
    },
    # Perimeter/Intrusion detection (PEA - Perimeter Alarm)
    "support_pea": {
        "sensor_type": "perimeter_alarm", 
        "name": "Perimeter Alarm",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:alert",
    },
    # Scene change/Video abnormality (AVD - Audio Video Detection)
    "support_avd": [
        {
            "sensor_type": "scene_change",
            "name": "Scene Change", 
            "device_class": BinarySensorDeviceClass.PROBLEM,
            "icon": "mdi:image-filter-center-focus",
        },
        {
            "sensor_type": "clarity_abnormal",
            "name": "Video Clarity Abnormal",
            "device_class": BinarySensorDeviceClass.PROBLEM, 
            "icon": "mdi:video-off",
        },
        {
            "sensor_type": "color_abnormal",
            "name": "Video Color Abnormal",
            "device_class": BinarySensorDeviceClass.PROBLEM,
            "icon": "mdi:palette", 
        }
    ],
    # Object removal detection (OSC - Object Scene Change)
    "support_osc": {
        "sensor_type": "object_removal",
        "name": "Object Removal",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:package-variant-remove",
    },
    # Face detection (VFD - Video Face Detection)
    "support_vfd": {
        "sensor_type": "face_detection",
        "name": "Face Detection",
        "device_class": BinarySensorDeviceClass.OCCUPANCY,
        "icon": "mdi:face-recognition",
    },
    # People counting (CPC - Counting People Camera)
    "support_cpc": {
        "sensor_type": "people_counting",
        "name": "People Counting Alert",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:account-alert",
    },
    # Crowd density (CDD - Crowd Density Detection)
    "support_cdd": {
        "sensor_type": "crowd_density", 
        "name": "Crowd Density Alert",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:account-multiple",
    },
    # People intrusion (IPD - Intrusion People Detection)
    "support_ipd": {
        "sensor_type": "people_intrusion",
        "name": "People Intrusion",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:shield-alert",
    },
    # License plate detection (note typo in API: supportVehice)
    "support_vehice": {
        "sensor_type": "license_plate",
        "name": "License Plate Detection", 
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:car",
    },
    # Region entrance (AOI - Area Of Interest)
    "support_aoi_entry": {
        "sensor_type": "region_entrance",
        "name": "Region Entrance",
        "device_class": BinarySensorDeviceClass.PRESENCE,
        "icon": "mdi:entrance",
    },
    # Region exiting (AOI - Area Of Interest) 
    "support_aoi_leave": {
        "sensor_type": "region_exiting",
        "name": "Region Exiting",
        "device_class": BinarySensorDeviceClass.PRESENCE,
        "icon": "mdi:exit-run",
    },
    # Line crossing counting
    "support_pass_line_count": {
        "sensor_type": "line_crossing",
        "name": "Line Crossing",
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:vector-line",
    },
    # Traffic counting
    "support_traffic": {
        "sensor_type": "traffic",
        "name": "Traffic Alert", 
        "device_class": BinarySensorDeviceClass.PROBLEM,
        "icon": "mdi:traffic-light",
    },
}

# Sensor types that require special handling (multiple sensors per capability)
MULTI_SENSOR_CAPABILITIES = {
    "support_avd",  # Creates 3 different sensors
}

# Alarm input sensors (based on alarm_in_count)
ALARM_INPUT_SENSOR = {
    "sensor_type": "sensor_input",
    "name": "Sensor Input",
    "device_class": BinarySensorDeviceClass.OPENING, 
    "icon": "mdi:door-contact",
}

# Long polling constants
LONG_POLLING_TIMEOUT = 30
EVENT_SUBSCRIPTION_PATH = "/IPC/event/subsription"
