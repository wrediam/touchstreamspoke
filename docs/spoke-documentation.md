# TouchStream Spoke - Complete Documentation

## Overview

The TouchStream Spoke is a Raspberry Pi-based video capture and streaming device that provides:
- Real-time HDMI video capture via TC358743 CSI capture card
- Live preview on 3.5" touchscreen (480x320)
- Network discovery and remote configuration
- UDP/RTP streaming to configurable ingest servers (low latency)
- Kiosk-mode operation with minimal user interaction

## Architecture

### Hardware Stack
```
HDMI Source → TC358743 Capture Card → Raspberry Pi CSI-2 Port
                                            ↓
                                      /dev/video0
                                            ↓
                                    ┌───────┴────────┐
                                    │                │
                              GStreamer          FFmpeg
                              (Streaming)        (Streaming)
                                    │                │
                                    ↓                ↓
                              UDP Server        MHS35 Display
```

### Software Components

1. **GStreamer Streaming Pipeline** - Low-latency UDP/RTP output
1. **GStreamer Preview Pipeline** - Low-latency local display
2. **FFmpeg Streaming Engine** - High-quality UDP/RTP output
3. **HTTP Discovery Server** - Device adoption and configuration
4. **UDP Beacon** - Network presence announcement
5. **Kivy UI** - Touchscreen interface and status display

## Core Functionality

### 1. Video Capture

**Device:** `/dev/video0` (TC358743 HDMI-to-CSI)

**Capture Format:**
- Resolution: 1920x1080
- Frame Rate: 30 fps
- Pixel Format: UYVY422
- Colorimetry: BT.601

**Audio Capture:**
- Device: `hw:2,0` (ALSA, from TC358743)
- Embedded HDMI audio extraction
- Local playback with mute control
- Real-time stereo level metering

### 2. Preview System (GStreamer)

**Purpose:** Display live video on local touchscreen with minimal latency.

**Pipeline:**
```
v4l2src device=/dev/video0
  ↓
video/x-raw,format=UYVY,width=1920,height=1080,colorimetry=bt601,framerate=30/1
  ↓
videoscale (downscale for performance)
  ↓
video/x-raw,width=480,height=270
  ↓
videoconvert (UYVY → RGB, 4 threads)
  ↓
appsink (max-buffers=1, drop=true, sync=false)
  ↓
Kivy Texture (displayed on screen)
```

**Optimizations:**
- **Aggressive downscaling**: 480x270 = 1/16th the pixels of 1080p
- **Drop frames**: Only latest frame displayed, no buffering
- **Multi-threaded conversion**: 4 threads for color conversion
- **Async rendering**: No sync to clock, minimal latency

**Frame Rate:**
- Target: 30 fps
- Actual: Measured and displayed in UI
- Signal detection: FPS < 1 = "No Signal"

### 3. Streaming System (FFmpeg)

**Purpose:** Encode and stream high-quality video to UDP/RTP ingest server.

**FFmpeg Command:**
```bash
ffmpeg \
  -f v4l2 \
  -input_format uyvy422 \
  -framerate 30 \
  -video_size 1920x1080 \
  -i /dev/video0 \
  -f alsa \
  -i hw:2,0 \
  -c:v libx264 \
  -preset veryfast \
  -tune zerolatency \
  -b:v 4000k \
  -c:a aac \
  -b:a 128k \
  -f mpegts \
  udp://192.168.1.100:5000
```

**Encoding Parameters:**
- **Video Codec**: H.264 (libx264)
- **Preset**: veryfast (low CPU, good quality)
- **Tune**: zerolatency (minimal buffering)
- **Video Bitrate**: 4000 kbps (configurable)
- **Audio Codec**: AAC
- **Audio Bitrate**: 128 kbps (configurable)
- **Output Format**: MPEG-TS (UDP/RTP container)

**Stream Control:**
- Started/stopped via configuration updates
- Requires `ingest_url` to be set (e.g., `udp://192.168.1.100:5000`)
- Process managed as subprocess
- Automatic cleanup on stop

### 4. Network Discovery

The spoke implements a dual-protocol discovery system for automatic device detection.

#### UDP Broadcast Beacon

**Port:** 9999 (UDP)  
**Interval:** Every 5 seconds  
**Payload:**
```json
{
  "device_name": "raspberrypi",
  "device_id": "unadopted"
}
```

**Purpose:**
- Announces presence on local network
- Allows discovery app to find new devices
- Updates with current device_id after adoption

#### HTTP Discovery Server

**Port:** 6077 (TCP)  
**Endpoints:**

**GET /info**
```json
Response:
{
  "device_id": "unadopted",
  "device_name": "raspberrypi",
  "ip": "192.168.1.100",
  "model": "raspberry-pi",
  "status": "ready"
}
```

**POST /adopt**
```json
Request:
{
  "device_id": "unique-device-id",
  "device_name": "Living Room Camera",
  "location": "Living Room",
  "ingest_url": "udp://192.168.1.100:5000",
  "video_bitrate": "4000k",
  "audio_bitrate": "128k"
}

Response:
{
  "status": "ok",
  "saved": true
}
```

{
  "status": "ok",
  "saved": true
}
```

**GET /shutdown**
Initiates a system shutdown.
```json
Response:
{
  "status": "shutdown_initiated"
}
```

**GET /reboot**
Initiates a system reboot.
```json
Response:
{
  "status": "reboot_initiated"
}
```

**GET /update**
Initiates a code update (git pull) and service restart.
```json
Response:
{
  "status": "updating"
}
```

### 5. Configuration Management

**Config File:** `~/stream-config.json`

**Default Configuration:**
```json
{
  "device_id": null,
  "device_name": "raspberrypi",
  "location": "",
  "ingest_url": "",
  "video_bitrate": "4000k",
  "audio_bitrate": "128k",
  "resolution": "1920x1080",
  "framerate": "30",
  "audio_muted": false
}
```

**Configuration Fields:**

- **device_id**: Unique identifier assigned by discovery app (null = unadopted)
- **device_name**: Human-readable name for the device
- **location**: Physical location description
- **ingest_url**: UDP destination URL (e.g., "udp://192.168.1.100:5000")
- **video_bitrate**: H.264 encoding bitrate (e.g., "4000k")
- **audio_bitrate**: AAC encoding bitrate (e.g., "128k")
- **resolution**: Capture resolution (currently fixed at 1920x1080)
- **framerate**: Capture frame rate (currently fixed at 30)

**Persistence:**
- JSON format for easy editing
- Reloaded on every beacon broadcast
- Updated via HTTP POST /adopt
- Survives reboots

#### Maintenance
- **Reinstall/Update**: Run `setup.sh` again to access the maintenance menu (Reinstall, Update, Exit).
- **Remote Update**: Use the `/update` endpoint to trigger an update remotely.

### 6. User Interface (Kivy)

**Display:** 480x320 touchscreen (MHS35)  
**Mode:** Fullscreen kiosk (no cursor, no borders)

**UI Elements:**

#### Top Bar (92-100% height)
- **Status Label** (left): Shows adoption/streaming status
  - "Pending Adoption" - Not configured
  - "Standby" - Adopted but not streaming
  - "Streaming" - Actively streaming
- **FPS Label** (right): Shows preview frame rate or "...waiting"

#### Center Area
- **Video Preview**: Live scaled video feed (480x270)
- **No Signal Overlay**: Shown when FPS < 1

#### Left Side
- **Stereo Audio Meter**: Vertical bars showing L/R audio levels
  - Green: Normal levels (< -30dB)
  - Yellow: Medium levels (-30dB to -12dB)
  - Red: High levels (> -12dB)

#### Bottom Bar (0-8% height)
- **CPU Temp** (left): Current CPU temperature
- **Mute Button**: 🔊/🔇 toggle for local audio playback
- **Tap Hint** (center): "Tap for info" instruction
- **CPU Usage** (right): Current CPU percentage

#### Info Overlay (Tap to toggle)
Shows when screen is tapped:
- IP Address
- Adoption Status (with device_id if adopted)
- Location

**Touch Interaction:**
- Single tap anywhere toggles info overlay
- Tap mute button to toggle local audio playback
- First tap wakes screen if asleep

### 7. Device States

```
┌─────────────────┐
│   Unadopted     │ device_id = null
│                 │ Status: "Pending Adoption"
└────────┬────────┘
         │ POST /adopt
         ↓
┌─────────────────┐
│    Adopted      │ device_id set
│   (Standby)     │ Status: "Standby"
└────────┬────────┘
         │ ingest_url + stream_key configured
         ↓
┌─────────────────┐
│   Streaming     │ FFmpeg running
│                 │ Status: "Streaming"
└─────────────────┘
```

### 8. Screen Sleep

The display automatically sleeps after 3 hours of inactivity to save power.

**Sleep Triggers:**
- No touch input for 3 hours
- No active streaming

**Wake Triggers:**
- Any touch on the screen
- Streaming starts (via /adopt endpoint)

**Implementation:**
- Uses `xset dpms force off/on` for display control
- Configurable timeout: `SCREEN_SLEEP_TIMEOUT` constant

### 9. Nightly Reboot

The device automatically reboots at 1:00 AM local time daily for system health.

**Purpose:**
- Clear memory leaks
- Apply pending updates
- Ensure long-term stability

**Implementation:**
- Cron job: `0 1 * * * /sbin/reboot`

## Performance Characteristics

### Resource Usage (Raspberry Pi 4, 4GB)

**Idle (Preview Only):**
- CPU: ~25-35% (single core)
- RAM: ~200MB
- GPU Memory: 512MB (CMA allocation)

**Streaming (Preview + UDP):**
- CPU: ~55-75% (distributed across cores, lower than RTMP)
- RAM: ~300MB
- Network: ~4.1 Mbps upload (at 4000k bitrate, less overhead)

### Latency

- **Preview Latency**: ~100-200ms (capture to display)
- **Streaming Latency**: ~200-500ms (capture to UDP server, much lower than RTMP)
- **Discovery Response**: <100ms (HTTP endpoint)

## File Locations

```
~/
├── touchstreamspoke/
│   └── touchstream-spoke.py      # Main application
├── stream-config.json            # Configuration file
├── edid-1080p30.txt              # EDID data for capture card
└── .config/autostart/
    └── touchstream.desktop       # Autostart configuration

/boot/firmware/
├── config.txt                    # Boot config (overlays)
└── cmdline.txt                   # Kernel parameters (CMA)

/etc/systemd/system/
└── tc358743-edid.service         # EDID loader service
```

## Startup Sequence

1. **Boot** - Raspberry Pi OS loads
2. **Kernel** - CMA=512M allocated, device tree overlays loaded
3. **tc358743-edid.service** - EDID loaded, timings configured
4. **User Login** - Auto-login to graphical session
5. **Autostart** - touchstream-spoke.py launches
6. **GStreamer Init** - Preview pipeline starts
7. **Discovery Services** - HTTP server and UDP beacon start
8. **UI Ready** - Display shows "Pending Adoption"

## Error Handling

### No Video Signal
- UI shows "No Signal" overlay
- FPS drops to 0
- Streaming continues (black frames)
- Auto-recovers when signal returns

### Network Loss
- Discovery beacon continues broadcasting
- HTTP server remains available
- Streaming fails (FFmpeg exits)
- Config persists for reconnection

### FFmpeg Crash
- Detected via process polling
- Status returns to "Standby"
- Can be restarted via new /adopt POST

### GStreamer Pipeline Failure
- Shows error message on display
- HTTP discovery still functional
- Requires restart to recover

## Security Considerations

**Current Implementation:**
- No authentication on HTTP endpoints
- Assumes trusted local network
- Config file world-readable
- No encryption on UDP stream

**Recommendations for Production:**
- Add API key authentication
- Use HTTPS for discovery
- Encrypt config file
- Use SRT (Secure Reliable Transport) for streaming
- Implement firewall rules

## Monitoring and Debugging

### Check Device Status
```bash
# Is the app running?
ps aux | grep touchstream-spoke.py

# Check discovery server
curl http://localhost:6077/info

# Check video device
v4l2-ctl -d /dev/video0 --query-dv-timings

# Check streaming process
ps aux | grep ffmpeg
```

### View Logs
```bash
# System logs
journalctl -u tc358743-edid.service

# Application output (if run manually)
python3 ~/touchstreamspoke/touchstream-spoke.py

# FFmpeg output (modify spoke to enable)
# Remove stdout=DEVNULL, stderr=DEVNULL from Popen
```

### Test Preview Pipeline
```bash
# Manual GStreamer test
gst-launch-1.0 v4l2src device=/dev/video0 ! \
  video/x-raw,format=UYVY,width=1920,height=1080,colorimetry=bt601 ! \
  videoconvert ! autovideosink
```

### Test Streaming
```bash
# Manual FFmpeg test
ffmpeg -f v4l2 -input_format uyvy422 -framerate 30 \
  -video_size 1920x1080 -i /dev/video0 \
  -f alsa -i hw:2,0 \
  -c:v libx264 -preset veryfast -b:v 4000k \
  -c:a aac -b:a 128k \
  -f mpegts udp://your-server:5000
```

## Customization

### Change Preview Resolution
Edit `touchstream-spoke.py`:
```python
PREVIEW_WIDTH = 640   # Default: 480
PREVIEW_HEIGHT = 360  # Default: 270
```

### Change Capture Settings
Edit `touchstream-spoke.py`:
```python
CAPTURE_WIDTH = 1280   # Default: 1920
CAPTURE_HEIGHT = 720   # Default: 1080
CAPTURE_FPS = 60       # Default: 30
```

### Change Discovery Ports
Edit `touchstream-spoke.py`:
```python
DISCOVERY_PORT = 8080      # Default: 6077
DISCOVERY_UDP_PORT = 8888  # Default: 9999
```

### Change Audio Device
Edit `touchstream-spoke.py`:
```python
AUDIO_DEVICE = 'hw:1,0'  # Default: 'hw:2,0'
```

Find your audio device:
```bash
arecord -l
```

## Known Limitations

1. **Fixed Resolution**: Currently hardcoded to 1080p30
2. **No Authentication**: Discovery endpoints are open
3. **Single Stream**: Can only stream to one destination
4. **No Recording**: No local storage of video
5. **No Stream Health Metrics**: No bitrate/quality reporting
6. **No Auto-Recovery**: FFmpeg crashes require manual restart via /adopt

## Future Enhancements

- Multi-destination streaming
- Local recording capability
- Stream health monitoring
- Auto-restart on stream failure
- Web-based configuration UI
- Support for multiple resolutions
- Network bandwidth adaptation
