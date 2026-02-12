# provision_isr

# Provision ISR Integration for Home Assistant

Home Assistant integration for Provision ISR cameras and NVRs.

## Features

- ✅ **Camera Streams** - Main and sub streams via RTSP
- ✅ **Motion Detection** - Binary sensor for motion events
- ✅ **Motion Control** - Switch to enable/disable motion detection
- ✅ **Camera Snapshots** - Still image capture
- ✅ **Local Control** - No cloud required

## Installation

### Via HACS (Custom Repository)

1. Open HACS
2. Click the 3 dots → Custom repositories
3. Add: `https://github.com/daveinc/provision_isr`
4. Category: Integration
5. Install "Provision ISR"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/provision_isr` folder to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Provision ISR"
4. Enter:
   - **Host**: IP address of your camera (e.g., `192.168.1.100`)
   - **Username**: Camera username (default: `admin`)
   - **Password**: Camera password

## Supported Devices

- Provision ISR IP Cameras
- Provision ISR NVRs
- Compatible OEM cameras using Provision firmware

## Entities Created

For each camera:
- **Camera** - Main stream and sub stream
- **Binary Sensor** - Motion detection state
- **Switch** - Enable/disable motion detection

## Development

Based on reverse-engineered Provision ISR API from:
- [stream_provision.py](https://github.com/orinaor/Provision)
- [winClienteCamera2](https://github.com/kirkjoserey/winClienteCamera2)

## Credits

- Reverse engineering references: orinaor, kirkjoserey
- Architecture based on Hikvision Next integration structure

## License

MIT
