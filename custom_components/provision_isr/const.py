"""Constants for Provision ISR integration."""

# Domain
DOMAIN = "provision_isr"

# Config
CONF_MAC_ADDRESS = "mac_address"
CONF_AUTO_DETECT_IP = "auto_detect_ip"

# Defaults
DEFAULT_PORT = 80
DEFAULT_TIMEOUT = 30  # seconds

# Discovery
COMMON_PORTS = [80, 90, 51986]  # Common Provision ISR ports
DISCOVERY_TIMEOUT = 10  # seconds

# HTTP Status Codes
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401

# API Endpoints
ENDPOINT_GET_DEVICE_INFO = "GetDeviceInfo"
ENDPOINT_GET_CHANNEL_LIST = "GetChannelList"
ENDPOINT_GET_DISK_INFO = "GetDiskInfo"
ENDPOINT_GET_ALARM_IN_LIST = "GetAlarmInList"
ENDPOINT_GET_ALARM_OUT_LIST = "GetAlarmOutList"
ENDPOINT_GET_DATE_TIME = "GetDateAndTime"

# Device Types (from GetDeviceInfo deviceType field)
# TODO: Map these values based on API testing
DEVICE_TYPE_IPC = 1  # IP Camera
DEVICE_TYPE_NVR = 2  # NVR (placeholder)
DEVICE_TYPE_DVR = 3  # DVR (placeholder)

# Platforms
PLATFORMS = ["camera", "binary_sensor", "switch"]
