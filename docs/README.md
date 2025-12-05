# TouchStream Documentation

Complete documentation for the TouchStream Spoke video capture and streaming system.

## 📚 Documentation Index

### [Index](./index.md)
Overview and quick navigation to all documentation sections.

### [Installation Guide](./INSTALL.md)
**Quick installation instructions and troubleshooting**
- One-command installation
- Step-by-step installation
- Remote SSH installation
- Troubleshooting common issues
- Update and uninstallation procedures

**Read this if you're:**
- Installing TouchStream for the first time
- Need quick installation commands
- Troubleshooting installation problems
- Updating or removing the software

### [Setup Guide](./setup-guide.md)
**Detailed breakdown of the setup process**
- Step-by-step explanation of `setup.sh`
- Hardware requirements
- Boot configuration details
- Post-setup verification
- Troubleshooting common issues

**Read this if you're:**
- Setting up a new spoke device
- Understanding what the setup script does
- Troubleshooting installation problems
- Modifying the setup process

### [Spoke Documentation](./spoke-documentation.md)
**Complete reference for spoke functionality**
- Architecture overview
- Video capture and preview system
- Streaming engine details
- Network discovery protocols
- Configuration management
- User interface guide
- Performance characteristics
- Error handling

**Read this if you're:**
- Understanding how the spoke works
- Debugging spoke behavior
- Optimizing performance
- Customizing spoke functionality
- Monitoring device health

### [Integration Guide](./integration-guide.md)
**How to integrate spokes with your discovery app**
- Discovery implementation (UDP + HTTP)
- Device adoption workflow
- Restreaming server setup
- Complete code examples (Python, Node.js)
- Testing procedures
- Best practices

**Read this if you're:**
- Building a discovery/management app
- Implementing device adoption
- Setting up restreaming infrastructure
- Integrating with existing platforms
- Managing multiple spoke devices

### [API Reference](./api-reference.md)
**Technical specification for all protocols and APIs**
- UDP beacon protocol
- HTTP API endpoints
- RTMP streaming specifications
- Configuration file format
- V4L2 and ALSA interfaces
- GStreamer pipeline details
- Port reference
- Error codes
- Example integrations

**Read this if you're:**
- Implementing API clients
- Debugging network communication
- Understanding protocol details
- Building custom integrations
- Writing automated tests

## 🚀 Quick Start

### For New Users

1. **Start here:** [Index](./index.md) - Get oriented
2. **Setup device:** [Setup Guide](./setup-guide.md) - Install and configure
3. **Understand operation:** [Spoke Documentation](./spoke-documentation.md) - Learn how it works

### For Developers

1. **Integration:** [Integration Guide](./integration-guide.md) - Build discovery app
2. **API Details:** [API Reference](./api-reference.md) - Protocol specifications
3. **Customization:** [Spoke Documentation](./spoke-documentation.md) - Modify behavior

## 📖 Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── index.md                     # Overview and navigation
├── setup-guide.md              # Setup process explained
├── spoke-documentation.md      # Spoke functionality reference
├── integration-guide.md        # Discovery app integration
└── api-reference.md            # Protocol and API specs
```

## 🎯 Common Tasks

### Setting Up a New Spoke Device

1. Flash Raspberry Pi OS to SD card
2. Configure WiFi/Ethernet
3. Clone the repository:
   - `setup.sh`
   - `touchstream-spoke.py`
4. Run: `sudo bash setup.sh`
5. Wait for automatic reboot
6. Device ready for discovery

**Detailed instructions:** [Setup Guide](./setup-guide.md)

### Discovering and Adopting a Spoke

1. Listen for UDP beacons on port 9999
2. Query device info via `GET /info`
3. Present device to user for naming
4. Send configuration via `POST /adopt`
5. Monitor stream reception

**Detailed instructions:** [Integration Guide](./integration-guide.md)

### Troubleshooting a Spoke

1. Check if app is running: `ps aux | grep touchstream`
2. Verify video signal: `v4l2-ctl -d /dev/video0 --query-dv-timings`
3. Test discovery: `curl http://<ip>:6077/info`
4. Check streaming: `ps aux | grep ffmpeg`
5. Review logs: `journalctl -u tc358743-edid.service`

**Detailed instructions:** [Setup Guide - Troubleshooting](./setup-guide.md#troubleshooting)

### Customizing Stream Quality

Edit configuration via `POST /adopt`:
```json
{
  "video_bitrate": "6000k",
  "audio_bitrate": "192k"
}
```

**Detailed instructions:** [API Reference - POST /adopt](./api-reference.md#post-adopt)

## 🔧 Technical Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Spoke Device                         │
│  ┌──────────────┐    ┌──────────────┐                  │
│  │ HDMI Source  │───▶│  TC358743    │                  │
│  │              │    │  Capture Card │                  │
│  └──────────────┘    └──────┬───────┘                  │
│                              │                           │
│                              ▼                           │
│                       /dev/video0                        │
│                              │                           │
│                    ┌─────────┴─────────┐                │
│                    │                   │                │
│              ┌─────▼─────┐      ┌─────▼─────┐          │
│              │ GStreamer │      │  FFmpeg   │          │
│              │ (Preview) │      │(Streaming)│          │
│              └─────┬─────┘      └─────┬─────┘          │
│                    │                   │                │
│                    ▼                   ▼                │
│              MHS35 Display      RTMP Server             │
│                                                          │
│  ┌────────────────────────────────────────────┐        │
│  │  Discovery Services                        │        │
│  │  • UDP Beacon (port 9999)                  │        │
│  │  • HTTP API (port 6077)                    │        │
│  └────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Discovery App   │
                    │ (Restreaming)   │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
              YouTube           Facebook
```

### Key Components

- **TC358743**: HDMI to CSI-2 capture card
- **GStreamer**: Low-latency preview pipeline
- **FFmpeg**: High-quality RTMP streaming
- **Kivy**: Touchscreen UI framework
- **Discovery**: UDP beacon + HTTP API

### Network Protocols

- **UDP Port 9999**: Broadcast beacon (outbound)
- **TCP Port 6077**: HTTP API (inbound)
- **TCP Port 1935**: RTMP streaming (outbound)

## 📝 Configuration Files

| File | Purpose | Documentation |
|------|---------|---------------|
| `~/stream-config.json` | Runtime configuration | [API Reference](./api-reference.md#configuration-file-format) |
| `/boot/firmware/config.txt` | Boot configuration | [Setup Guide](./setup-guide.md#config-txt-modifications) |
| `/boot/firmware/cmdline.txt` | Kernel parameters | [Setup Guide](./setup-guide.md#cmdline-txt-modifications) |
| `/etc/systemd/system/tc358743-edid.service` | EDID loader | [Setup Guide](./setup-guide.md#tc358743-edid-configuration) |

## 🔍 Finding Information

### By Topic

| Topic | Document | Section |
|-------|----------|---------|
| Installation | Setup Guide | All |
| Video capture | Spoke Documentation | Video Capture |
| Streaming | Spoke Documentation | Streaming System |
| Discovery protocol | API Reference | UDP Broadcast Beacon |
| HTTP endpoints | API Reference | HTTP API |
| Device adoption | Integration Guide | Device Adoption Flow |
| Restreaming | Integration Guide | Restreaming Server Setup |
| Configuration | API Reference | Configuration File Format |
| Troubleshooting | Setup Guide | Troubleshooting |
| Performance | Spoke Documentation | Performance Characteristics |

### By User Role

**System Administrator:**
- [Setup Guide](./setup-guide.md) - Installation and configuration
- [Spoke Documentation](./spoke-documentation.md#monitoring-and-debugging) - Monitoring

**Application Developer:**
- [Integration Guide](./integration-guide.md) - Building discovery app
- [API Reference](./api-reference.md) - Protocol specifications

**DevOps Engineer:**
- [Setup Guide](./setup-guide.md#post-setup-verification) - Verification
- [Spoke Documentation](./spoke-documentation.md#performance-characteristics) - Performance
- [Integration Guide](./integration-guide.md#restreaming-server-setup) - Infrastructure

**End User:**
- [Index](./index.md) - Overview
- [Spoke Documentation](./spoke-documentation.md#user-interface-kivy) - UI guide

## 🛠️ Development

### Modifying the Spoke

1. Read: [Spoke Documentation](./spoke-documentation.md)
2. Edit: `touchstream-spoke.py`
3. Test locally before deploying
4. Update documentation if behavior changes

### Extending the API

1. Read: [API Reference](./api-reference.md)
2. Add endpoints to `DiscoveryHandler` class
3. Update API documentation
4. Maintain backward compatibility

### Contributing

When contributing documentation:
- Keep language clear and concise
- Include code examples
- Add troubleshooting sections
- Update this index if adding new docs

## 📞 Support

### Documentation Issues

If you find errors or omissions in the documentation:
1. Note the specific document and section
2. Describe the issue or missing information
3. Submit feedback to the project maintainer

### Technical Issues

For technical problems:
1. Check [Setup Guide - Troubleshooting](./setup-guide.md#troubleshooting)
2. Review [Spoke Documentation - Error Handling](./spoke-documentation.md#error-handling)
3. Consult [Integration Guide - Troubleshooting](./integration-guide.md#troubleshooting)

## 📄 License

Documentation is provided as-is for the TouchStream project.

## 🔄 Version History

### Version 1.0 (Current)
- Initial documentation release
- Complete coverage of setup, spoke, integration, and API
- Code examples in Python and JavaScript
- Comprehensive troubleshooting guides

---

**Last Updated:** December 2025  
**Documentation Version:** 1.0  
**Spoke Version:** 1.0
