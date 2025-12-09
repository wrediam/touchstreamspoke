# TouchStream Documentation

Welcome to the TouchStream documentation. This system consists of two main components:

1. **TouchStream Spoke** - Raspberry Pi-based video capture and streaming device
2. **Discovery App** - Central management platform for device discovery and multi-platform streaming

## Documentation Structure

- [Setup Guide](./setup-guide.md) - Detailed walkthrough of the setup.sh script
- [Spoke Documentation](./spoke-documentation.md) - Complete spoke functionality reference
- [Integration Guide](./integration-guide.md) - Integrating with discovery apps and remote management
- [API Reference](./api-reference.md) - Network protocol and API endpoints

## Quick Start

### For Spoke Devices
1. Flash Raspberry Pi OS to SD card
2. Clone the repository to your home directory
3. Run `sudo bash setup.sh`
4. Device will reboot and be ready for discovery

### For Discovery App Integration
1. Implement mDNS/Bonjour discovery for `_touchstream._tcp` service
2. Send device configuration via HTTP POST to `http://<spoke-ip>:8080/configure`
3. Monitor stream health via status endpoint

## System Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Spoke Device   │────────▶│  Discovery App   │────────▶│  YouTube/FB/etc │
│  (Raspberry Pi) │  RTMP   │  (Restreaming)   │  RTMP   │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                            │
        │                            │
        └────────────────────────────┘
              HTTP Configuration
```

## Support

For issues or questions, refer to the specific documentation sections linked above.
