# Provision ISR Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/daveinc/provision_isr.svg)](https://github.com/daveinc/provision_isr/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Home Assistant integration for Provision ISR NVRs and IP cameras.

> **⚠️ Status:** Currently in development. Waiting on official API documentation from Provision ISR.

## Features (Planned)

- 🎥 **NVR Support** - Connect to Provision ISR NVRs
- 📹 **Multiple Cameras** - Auto-discover all cameras connected to NVR
- 🎬 **RTSP Streams** - Main and sub streams
- 🚨 **Motion Detection** - Real-time motion event sensors
- 🔔 **Event Alerts** - Alarm inputs, tampering, line crossing
- 📸 **Snapshots** - Still image capture
- 🎛️ **Motion Control** - Enable/disable motion detection per camera
- 🏠 **Local Control** - No cloud required, works entirely on your LAN

## Planned Architecture

This integration is being built from the ground up using the same proven architecture as [Hikvision Next](https://github.com/maciej-or/hikvision_next), adapted for Provision ISR's API.

### Why This Integration?

- **NVR-First Design** - Built specifically for NVR deployments (not just standalone cameras)
- **Event-Driven** - Real-time event streams, not polling
- **Professional Features** - AI events, alarm I/O, advanced motion detection
- **Clean Code** - Modern HA integration patterns, fully async

## Installation

### HACS (Recommended - when ready)

1. Open HACS
2. Click the 3 dots (top right) → **Custom repositories**
3. Add repository: `https://github.com/daveinc/provision_isr`
4. Category: **Integration**
5. Click **Install**
6. Restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/daveinc/provision_isr/releases)
2. Extract `custom_components/provision_isr` to your HA `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Provision ISR"**
3. Enter your NVR details:
   - **Host**: NVR IP address (e.g., `192.168.1.100`)
   - **Port**: HTTP port (default: `80`)
   - **Username**: NVR admin username
   - **Password**: NVR password
4. Click **Submit**

The integration will auto-discover all cameras connected to your NVR.

## Supported Devices

### Tested
- *List will be populated once testing begins*

### Should Work
- Provision ISR NVRs (all models)
- Provision ISR IP Cameras
- OEM cameras using Provision firmware

**Have a device to test?** Open an [issue](https://github.com/daveinc/provision_isr/issues) with your model info!

## Entities Created

### Per NVR
- **Binary Sensor** - NVR online status
- **Sensor** - Firmware version, model info

### Per Camera
- **Camera** - Live stream (main + sub stream)
- **Binary Sensor** - Motion detection
- **Binary Sensor** - Tampering detection (if supported)
- **Binary Sensor** - Video loss
- **Switch** - Motion detection enable/disable
- **Switch** - Alarm output control (if available)

## Troubleshooting

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.provision_isr: debug
```

Restart HA, reproduce the issue, then check **Settings → System → Logs**.

### Common Issues

**"Could not connect to NVR"**
- Verify IP address and port
- Check firewall rules
- Ensure NVR web interface is accessible from HA server

**"Authentication failed"**
- Double-check username/password
- Try creating a new admin user on the NVR
- Ensure account has full permissions

**"No cameras found"**
- Verify cameras are online in NVR interface
- Check that cameras are using Provision firmware (not third-party)
- Enable debug logging and check for API errors

## Development Status

### ✅ Completed
- Repository structure
- Documentation framework
- Integration scaffold

### 🔄 In Progress
- Awaiting official Provision ISR API documentation
- API client development
- Event stream implementation

### 📋 To Do
- Config flow
- Entity creation
- Event handling
- Testing with real hardware

## Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Submit a PR with clear description


## License

MIT License - see [LICENSE](LICENSE) file for details

---

**⭐ If this integration helps you, consider starring the repo!**
