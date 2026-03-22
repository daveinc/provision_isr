"""Data models for Provision ISR."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass
class DeviceCapabilities:
    """Device capability flags from GetDeviceInfo."""
    
    # Motion and basic alarms
    support_motion_sens: bool = False
    support_pea: bool = False  # Perimeter/Intrusion detection
    support_osc: bool = False  # Object removal
    support_avd: bool = False  # Scene change/Video abnormality
    
    # Advanced analytics
    support_vfd: bool = False  # Face detection
    support_vfd_match: bool = False  # Face comparison
    support_vfd_detect: bool = False  # Face detection (alternative)
    support_cpc: bool = False  # People counting
    support_cdd: bool = False  # Crowd density
    support_ipd: bool = False  # People intrusion
    support_vehice: bool = False  # License plate (note typo in API)
    support_aoi_entry: bool = False  # Region entrance
    support_aoi_leave: bool = False  # Region exiting
    support_pass_line_count: bool = False  # Line crossing counting
    support_traffic: bool = False  # Traffic counting
    
    # Hardware features
    support_sd_card: bool = False
    support_ptz: bool = False
    support_rs485_ptz: bool = False
    support_infrared_lamp: bool = False
    support_wiper: bool = False
    
    # Audio features
    audio_in_count: int = 0
    audio_out_count: int = 0
    support_audio_alarm_out: bool = False
    
    # Alarm I/O
    alarm_in_count: int = 0
    alarm_out_count: int = 0
    support_white_light_alarm_out: bool = False
    
    # Network and protocols
    support_p2p_service: bool = False
    support_pppoe: bool = False
    support_https: bool = False
    support_rtmp: bool = False
    support_ftp: bool = False
    support_snmp: bool = False
    support_apilong_polling: bool = False
    
    # Other features
    support_roi: bool = False  # Region of Interest
    support_private_zone: bool = False
    support_watermark: bool = False
    support_anonymous_login: bool = False
    support_http_post: bool = False
    
    # Channel count
    chl_max_count: int = 1
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeviceCapabilities:
        """Create capabilities from device info XML data."""
        caps = cls()
        
        # Extract deviceInfo section
        device_info = data.get("deviceInfo", {})
        if isinstance(device_info, dict):
            # Motion and alarm capabilities
            caps.support_motion_sens = device_info.get("supportMotionSens", {}).get("#text", "false") == "true"
            caps.support_pea = device_info.get("supportPea", {}).get("#text", "false") == "true"
            caps.support_osc = device_info.get("supportOsc", {}).get("#text", "false") == "true"
            caps.support_avd = device_info.get("supportAvd", {}).get("#text", "false") == "true"
            
            # Advanced analytics
            caps.support_vfd = device_info.get("supportVfd", {}).get("#text", "false") == "true"
            caps.support_vfd_match = device_info.get("supportVfdMatch", {}).get("#text", "false") == "true"
            caps.support_vfd_detect = device_info.get("supportVfdDetect", {}).get("#text", "false") == "true"
            caps.support_cpc = device_info.get("supportCpc", {}).get("#text", "false") == "true"
            caps.support_cdd = device_info.get("supportCdd", {}).get("#text", "false") == "true"
            caps.support_ipd = device_info.get("supportIpd", {}).get("#text", "false") == "true"
            caps.support_vehice = device_info.get("supportVehice", {}).get("#text", "false") == "true"  # Note typo
            caps.support_aoi_entry = device_info.get("supportAoiEntry", {}).get("#text", "false") == "true"
            caps.support_aoi_leave = device_info.get("supportAoiLeave", {}).get("#text", "false") == "true"
            caps.support_pass_line_count = device_info.get("supportPassLineCount", {}).get("#text", "false") == "true"
            caps.support_traffic = device_info.get("supportTraffic", {}).get("#text", "false") == "true"
            
            # Hardware features
            caps.support_sd_card = device_info.get("supportSDCard", {}).get("#text", "false") == "true"
            caps.support_ptz = device_info.get("integratedPtz", {}).get("#text", "false") == "true"
            caps.support_rs485_ptz = device_info.get("supportRS485Ptz", {}).get("#text", "false") == "true"
            caps.support_infrared_lamp = device_info.get("supportInfraredLamp", {}).get("#text", "false") == "true"
            caps.support_wiper = device_info.get("supportWiper", {}).get("#text", "false") == "true"
            
            # Audio features
            caps.audio_in_count = int(device_info.get("audioInCount", {}).get("#text", "0"))
            caps.audio_out_count = int(device_info.get("audioOutCount", {}).get("#text", "0"))
            caps.support_audio_alarm_out = device_info.get("supportAudioAlarmOut", {}).get("#text", "false") == "true"
            
            # Alarm I/O
            caps.alarm_in_count = int(device_info.get("alarmInCount", {}).get("#text", "0"))
            caps.alarm_out_count = int(device_info.get("alarmOutCount", {}).get("#text", "0"))
            caps.support_white_light_alarm_out = device_info.get("supportWhiteLightAlarmOut", {}).get("#text", "false") == "true"
            
            # Network and protocols
            caps.support_p2p_service = device_info.get("supportP2PService", {}).get("#text", "false") == "true"
            caps.support_pppoe = device_info.get("supportPPPoE", {}).get("#text", "false") == "true"
            caps.support_https = device_info.get("supportHttps", {}).get("#text", "false") == "true"
            caps.support_rtmp = device_info.get("supportRtmp", {}).get("#text", "false") == "true"
            caps.support_ftp = device_info.get("supportFtp", {}).get("#text", "false") == "true"
            caps.support_snmp = device_info.get("supportSnmp", {}).get("#text", "false") == "true"
            caps.support_apilong_polling = device_info.get("supportAPILongPolling", {}).get("#text", "false") == "true"
            
            # Other features
            caps.support_roi = device_info.get("supportROI", {}).get("#text", "false") == "true"
            caps.support_private_zone = device_info.get("supportPrivateZone", {}).get("#text", "false") == "true"
            caps.support_watermark = device_info.get("supportWatermark", {}).get("#text", "false") == "true"
            caps.support_anonymous_login = device_info.get("supportAnonymousLogin", {}).get("#text", "false") == "true"
            caps.support_http_post = device_info.get("SupportHttpPost", {}).get("#text", "false") == "true"
            
            # Channel count
            caps.chl_max_count = int(device_info.get("chlMaxCount", {}).get("#text", "1"))
        
        return caps

@dataclass
class DeviceInfo:
    """Device information."""
    device_name: str
    device_number: str
    serial_number: str
    model: str
    brand: str
    ip_address: str
    mac_address: str
    software_version: str
    hardware_version: str
    capabilities: DeviceCapabilities
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeviceInfo:
        """Create DeviceInfo from XML response."""
        # Extract deviceInfo section
        device_data = data.get("deviceInfo", {})
        
        # Parse capabilities first
        capabilities = DeviceCapabilities.from_dict(data)
        
        return cls(
            device_name=device_data.get("deviceName", {}).get("#text", ""),
            device_number=device_data.get("deviceNumber", {}).get("#text", ""),
            serial_number=device_data.get("sn", {}).get("#text", ""),
            model=device_data.get("model", {}).get("#text", ""),
            brand=device_data.get("brand", {}).get("#text", ""),
            ip_address=device_data.get("ipAddress", {}).get("#text", ""),
            mac_address=device_data.get("mac", {}).get("#text", ""),
            software_version=device_data.get("softwareVersion", {}).get("#text", ""),
            hardware_version=device_data.get("hardwareVersion", {}).get("#text", ""),
            capabilities=capabilities,
        )
    
    def is_nvr(self) -> bool:
        """Check if device is an NVR (multiple channels)."""
        return self.capabilities.chl_max_count > 1
    
    @property
    def support_motion_sens(self) -> bool:
        """Convenience property for motion sensor support."""
        return self.capabilities.support_motion_sens

# Keep your existing Channel, ChannelList, DiskInfo, StreamCaps models below...
# [Your existing Channel, ChannelList, DiskInfo, StreamCaps classes here]

@dataclass
class Channel:
    """Channel information."""
    channel_id: str
    name: str
    is_online: bool
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Channel:
        return cls(
            channel_id=data.get("@id", ""),
            name=data.get("name", {}).get("#text", ""),
            is_online=data.get("online", {}).get("#text", "false") == "true",
        )

@dataclass
class ChannelList:
    """Channel list for NVR."""
    channels: List[Channel]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChannelList:
        channels_data = data.get("channelList", {}).get("item", [])
        if not isinstance(channels_data, list):
            channels_data = [channels_data]
        
        channels = [Channel.from_dict(channel) for channel in channels_data]
        return cls(channels=channels)

@dataclass
class DiskInfo:
    """Disk information."""
    total_size: int
    free_size: int
    used_size: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DiskInfo:
        return cls(
            total_size=int(data.get("totalSize", {}).get("#text", "0")),
            free_size=int(data.get("freeSize", {}).get("#text", "0")),
            used_size=int(data.get("usedSize", {}).get("#text", "0")),
        )

@dataclass
class StreamCaps:
    """Stream capabilities."""
    main_stream: Dict[str, Any]
    sub_stream: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StreamCaps:
        return cls(
            main_stream=data.get("mainStream", {}),
            sub_stream=data.get("subStream", {}),
        )
