# TouchStream Spoke

A Raspberry Pi-based HDMI video capture and streaming device with automatic network discovery and remote configuration.

## Overview

TouchStream Spoke transforms a Raspberry Pi into a professional video capture and streaming device that:
- Captures 1080p30 HDMI video via TC358743 capture card
- Displays live preview on 3.5" touchscreen
- Announces presence via UDP beacon for automatic discovery
- Accepts remote configuration via HTTP API
- Streams via UDP/RTP to discovery server (low latency, local network)
- Operates in kiosk mode with minimal user interaction

## Features

### Video Capture
- **Resolution:** 1920x1080 @ 30fps
- **Input:** HDMI via TC358743 CSI-2 capture card
- **Audio:** Embedded HDMI audio extraction
- **Format:** UYVY422 with BT.601 colorimetry

### Display & UI
- **Screen:** MHS35 3.5" touchscreen (480x320)
- **Preview:** Real-time scaled video (480x270)
- **Interface:** Touch-activated info overlay
- **Status:** Visual indicators for adoption and streaming state

### Network Discovery
- **UDP Beacon:** Broadcasts presence every 5 seconds on port 9999
- **HTTP API:** Device info and configuration on port 6077
- **Auto-adoption:** Accepts configuration from discovery app

### Streaming
- **Protocol:** UDP/RTP with MPEG-TS
- **Video Codec:** H.264 (libx264, veryfast preset)
- **Audio Codec:** AAC
- **Bitrate:** Configurable (default 4000k video, 128k audio)
- **Latency:** ~200-500ms to UDP server (much lower than RTMP)

## Quick Start

### Prerequisites

- Raspberry Pi 4 or 5 (4GB+ RAM recommended)
- TC358743 HDMI-to-CSI capture card (Auvidea B101/B102 or compatible)
- MHS35 3.5" SPI touchscreen
- MicroSD card (16GB+)
- Raspberry Pi OS (Bookworm or later)

### Installation

1. **Flash Raspberry Pi OS** to SD card and boot

2. **Configure network** (WiFi or Ethernet)

3. **Copy files** to `/home/pbc/`:
   ```bash
   scp setup.sh touchstream-spoke.py pbc@raspberrypi.local:/home/pbc/
   ```

4. **Run setup script:**
   ```bash
   ssh pbc@raspberrypi.local
   cd /home/pbc
   sudo bash setup.sh
   ```

5. **Wait for automatic reboot** (triggered by screen driver installation)

6. **Device is ready** - will display "Pending Adoption" on screen

### Post-Installation

After reboot, the device will:
- Show live video preview on touchscreen
- Broadcast UDP beacons announcing its presence
- Listen for configuration via HTTP API on port 6077
- Wait for adoption by discovery app

## Usage

### For End Users

1. **Connect HDMI source** to the capture card
2. **Power on** the Raspberry Pi
3. **Wait for preview** to appear on screen
4. **Tap screen** to view device info (IP address, status)
5. Device will be **automatically discovered** by your discovery app

### For Developers

See the [Integration Guide](./docs/integration-guide.md) for detailed instructions on:
- Implementing UDP beacon discovery
- Querying device information
- Adopting and configuring devices
- Setting up restreaming infrastructure

## Architecture

```
┌──────────────┐         ┌──────────────────┐         ┌─────────────────┐
│ HDMI Source  │────────▶│  Spoke Device    │────────▶│ Discovery App   │
│              │  Video  │  (Raspberry Pi)  │  UDP    │ (Restreaming)   │
└──────────────┘         └──────────────────┘         └─────────┤────────┐┘
                                  │                             │
                                  │                             ▼
                                  │                    ┌────────────────┐
                                  │                    │ YouTube/FB/etc │
                                  │                    └────────────────┘
                                  │
                         UDP Beacon + HTTP Config
```

## Documentation

Comprehensive documentation is available in the [`docs/`](./docs/) directory:

- **[Documentation Index](./docs/README.md)** - Start here
- **[Setup Guide](./docs/setup-guide.md)** - Detailed installation walkthrough
- **[Spoke Documentation](./docs/spoke-documentation.md)** - Complete functionality reference
- **[Integration Guide](./docs/integration-guide.md)** - Build discovery apps
- **[API Reference](./docs/api-reference.md)** - Protocol specifications

## Configuration

### Via HTTP API

Send configuration to the device:

```bash
curl -X POST http://<spoke-ip>:6077/adopt \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "unique-id-123",
    "device_name": "Living Room Camera",
    "location": "Living Room",
    "ingest_url": "udp://192.168.1.100:5000",
    "video_bitrate": "4000k",
    "audio_bitrate": "128k"
  }'
```

### Manual Configuration

Edit `/home/pbc/stream-config.json`:

```json
{
  "device_id": "unique-id-123",
  "device_name": "Living Room Camera",
  "location": "Living Room",
  "ingest_url": "udp://192.168.1.100:5000",
  "video_bitrate": "4000k",
  "audio_bitrate": "128k",
  "resolution": "1920x1080",
  "framerate": "30"
}
```

## API Endpoints

### GET /info

Get device information:

```bash
curl http://<spoke-ip>:6077/info
```

Response:
```json
{
  "device_id": "unadopted",
  "device_name": "raspberrypi",
  "ip": "192.168.1.100",
  "model": "raspberry-pi",
  "status": "ready"
}
```

### POST /adopt

Configure and adopt device (see Configuration section above).

## Network Ports

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 6077 | TCP (HTTP) | Inbound | Discovery API |
| 9999 | UDP | Outbound | Beacon broadcast |
| 5000+ | UDP | Outbound | Video streaming (configurable) |

## Hardware Setup

### Connections

1. **HDMI Input** → TC358743 capture card
2. **Capture Card** → Raspberry Pi CSI-2 port
3. **MHS35 Screen** → Raspberry Pi GPIO pins
4. **Ethernet/WiFi** → Network connection
5. **Power** → 5V 3A USB-C power supply

### Recommended Hardware

- **Raspberry Pi:** Pi 4 Model B (4GB or 8GB)
- **Capture Card:** Auvidea B101 or B102
- **Screen:** MHS35 3.5" 480x320 SPI touchscreen
- **SD Card:** SanDisk Extreme 32GB or larger
- **Power:** Official Raspberry Pi 15W USB-C power supply

## Performance

### Resource Usage

**Idle (Preview Only):**
- CPU: ~25-35%
- RAM: ~200MB
- GPU: 512MB (CMA allocation)

**Streaming (Preview + UDP):**
- CPU: ~55-75% (lower than RTMP)
- RAM: ~300MB
- Network: ~4.1 Mbps upload (less overhead)

### Latency

- **Preview:** ~100-200ms (capture to display)
- **Streaming:** ~200-500ms (capture to UDP server, much lower than RTMP)
- **Discovery:** <100ms (HTTP response)

## Troubleshooting

### No Video Signal

```bash
# Check if capture card is detected
v4l2-ctl --list-devices

# Query video timings
v4l2-ctl -d /dev/video0 --query-dv-timings

# Restart EDID service
sudo systemctl restart tc358743-edid.service
```

### App Not Running

```bash
# Check if app is running
ps aux | grep touchstream-spoke.py

# Check autostart configuration
cat ~/.config/autostart/touchstream.desktop

# Run manually for debugging
python3 /home/pbc/touchstream-spoke.py
```

### Discovery Not Working

```bash
# Test HTTP endpoint
curl http://localhost:6077/info

# Check if port is listening
sudo netstat -tulpn | grep 6077

# Test UDP beacon reception
nc -ul 9999
```

### Streaming Issues

```bash
# Check FFmpeg process
ps aux | grep ffmpeg

# Verify configuration
cat /home/pbc/stream-config.json

# Test RTMP server connectivity
ffmpeg -re -f lavfi -i testsrc -f mpegts udp://your-server:5000
```

See the [Setup Guide](./docs/setup-guide.md#troubleshooting) for more detailed troubleshooting.

## Development

### Project Structure

```
touchstreamspoke/
├── README.md                    # This file
├── setup.sh                     # Installation script
├── touchstream-spoke.py         # Main application
└── docs/                        # Documentation
    ├── README.md               # Documentation index
    ├── index.md                # Overview
    ├── setup-guide.md          # Setup details
    ├── spoke-documentation.md  # Functionality reference
    ├── integration-guide.md    # Integration guide
    └── api-reference.md        # API specifications
```

### Dependencies

**System packages:**
- python3-kivy
- python3-gi
- python3-gst-1.0
- gstreamer1.0-* (plugins)
- v4l-utils
- ffmpeg

**Python modules:**
- kivy
- gi (PyGObject)

### Customization

See [Spoke Documentation - Customization](./docs/spoke-documentation.md#customization) for details on:
- Changing preview resolution
- Modifying capture settings
- Adjusting discovery ports
- Configuring audio devices

## Integration Examples

### Python Discovery Client

```python
import socket
import json

# Listen for beacons
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', 9999))

while True:
    data, addr = sock.recvfrom(1024)
    beacon = json.loads(data.decode('utf-8'))
    print(f"Found: {beacon['device_name']} at {addr[0]}")
```

### Node.js Discovery Client

```javascript
const dgram = require('dgram');
const server = dgram.createSocket('udp4');

server.on('message', (msg, rinfo) => {
  const beacon = JSON.parse(msg.toString());
  console.log(`Found: ${beacon.device_name} at ${rinfo.address}`);
});

server.bind(9999);
```

See the [Integration Guide](./docs/integration-guide.md) for complete examples.

## Use Cases

### Multi-Camera Live Streaming
Deploy multiple spokes to capture different camera angles, all streaming to a central restreaming server that combines feeds for YouTube/Facebook Live.

### Church/Event Broadcasting
Capture HDMI output from video switcher and stream to multiple platforms simultaneously via discovery app.

### Remote Monitoring
Deploy spokes at remote locations with automatic discovery and centralized management.

### Video Production
Use as wireless HDMI transmitter alternative - capture HDMI locally and stream to production system over network.

## Security Considerations

⚠️ **Current implementation has no authentication or encryption.**

Recommended for use on:
- Trusted local networks
- Isolated VLANs
- Behind firewalls

For production deployments, consider:
- Adding API key authentication
- Using HTTPS for discovery API
- Implementing RTMPS for streaming
- Encrypting configuration files

See [API Reference - Security](./docs/api-reference.md#security-considerations) for details.

## Known Limitations

- Fixed 1080p30 resolution (hardcoded)
- Single stream destination
- No local recording
- No authentication on API endpoints
- No audio monitoring on device
- No stream health metrics reporting

See [Spoke Documentation - Known Limitations](./docs/spoke-documentation.md#known-limitations) for full list.

## Future Enhancements

- [ ] Multi-destination streaming
- [ ] Local recording to SD card
- [ ] Stream health monitoring
- [ ] Auto-restart on stream failure
- [ ] Web-based configuration UI
- [ ] Support for multiple resolutions
- [ ] Audio level metering
- [ ] Network bandwidth adaptation
- [ ] API authentication
- [ ] HTTPS/RTMPS support

## Contributing

Contributions welcome! Please:
1. Read the documentation first
2. Test changes thoroughly
3. Update documentation as needed
4. Follow existing code style

## License

[Specify your license here]

## Support

For issues and questions:
1. Check the [Documentation](./docs/)
2. Review [Troubleshooting](./docs/setup-guide.md#troubleshooting)
3. Search existing issues
4. Create a new issue with details

## Acknowledgments

- **GStreamer** - Multimedia framework
- **FFmpeg** - Video encoding
- **Kivy** - UI framework
- **TC358743** - HDMI capture chip
- **Raspberry Pi Foundation** - Hardware platform

## Version

**Current Version:** 1.0  
**Last Updated:** December 2025  
**Raspberry Pi OS:** Bookworm (Debian 12)  
**Python:** 3.11+

---

**Made with ❤️ for the streaming community**
