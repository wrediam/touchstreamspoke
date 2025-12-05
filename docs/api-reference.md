# TouchStream Spoke - API Reference

Complete reference for all network protocols and APIs used by TouchStream Spoke devices.

## Network Protocols

### UDP Broadcast Beacon

**Purpose:** Announce device presence on local network for automatic discovery.

**Protocol:** UDP Broadcast  
**Port:** 9999  
**Direction:** Spoke → Discovery App (one-way)  
**Interval:** Every 5 seconds  
**Broadcast Address:** `<broadcast>` (255.255.255.255 or subnet broadcast)

#### Payload Format

```json
{
  "device_name": "string",
  "device_id": "string"
}
```

#### Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `device_name` | string | Device hostname or user-assigned name | `"raspberrypi"` or `"Living Room Camera"` |
| `device_id` | string | Unique device identifier, or `"unadopted"` if not configured | `"550e8400-e29b-41d4-a716-446655440000"` |

#### Example Beacon (Unadopted)

```json
{
  "device_name": "raspberrypi",
  "device_id": "unadopted"
}
```

#### Example Beacon (Adopted)

```json
{
  "device_name": "Living Room Camera",
  "device_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Client Implementation

**Python:**
```python
import socket
import json

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', 9999))

while True:
    data, addr = sock.recvfrom(1024)
    beacon = json.loads(data.decode('utf-8'))
    print(f"Device: {beacon['device_name']} at {addr[0]}")
```

**JavaScript:**
```javascript
const dgram = require('dgram');
const server = dgram.createSocket('udp4');

server.on('message', (msg, rinfo) => {
  const beacon = JSON.parse(msg.toString());
  console.log(`Device: ${beacon.device_name} at ${rinfo.address}`);
});

server.bind(9999);
```

---

## HTTP API

**Base URL:** `http://<spoke-ip>:6077`  
**Protocol:** HTTP/1.1  
**Content-Type:** `application/json`  
**Authentication:** None (open endpoints)

### Endpoints

#### GET /info

Get device information and current status.

**Request:**
```http
GET /info HTTP/1.1
Host: 192.168.1.100:6077
```

**Response:** 200 OK
```json
{
  "device_id": "string",
  "device_name": "string",
  "ip": "string",
  "model": "string",
  "status": "string"
}
```

**Response Fields:**

| Field | Type | Description | Possible Values |
|-------|------|-------------|-----------------|
| `device_id` | string | Unique device identifier | UUID or `"unadopted"` |
| `device_name` | string | Device name | Any string |
| `ip` | string | Device's IP address on the network | IPv4 address |
| `model` | string | Device model identifier | `"raspberry-pi"` |
| `status` | string | Device operational status | `"ready"` |

**Example Request:**
```bash
curl http://192.168.1.100:6077/info
```

**Example Response:**
```json
{
  "device_id": "unadopted",
  "device_name": "raspberrypi",
  "ip": "192.168.1.100",
  "model": "raspberry-pi",
  "status": "ready"
}
```

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| 404 | Endpoint not found |
| 500 | Internal server error |

---

#### POST /adopt

Configure device with streaming parameters and adopt into management system.

**Request:**
```http
POST /adopt HTTP/1.1
Host: 192.168.1.100:6077
Content-Type: application/json

{
  "device_id": "string",
  "device_name": "string",
  "location": "string",
  "ingest_url": "string",
  "stream_key": "string",
  "video_bitrate": "string",
  "audio_bitrate": "string",
  "resolution": "string",
  "framerate": "string"
}
```

**Request Fields:**

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `device_id` | string | **Yes** | Unique identifier to assign | `"550e8400-e29b-41d4-a716-446655440000"` |
| `device_name` | string | **Yes** | Human-readable device name | `"Living Room Camera"` |
| `location` | string | No | Physical location description | `"Living Room"` |
| `ingest_url` | string | **Yes** | RTMP server URL (without stream key) | `"rtmp://ingest.example.com/live"` |
| `stream_key` | string | **Yes** | RTMP stream key/path | `"spoke_abc123"` |
| `video_bitrate` | string | No | H.264 encoding bitrate | `"4000k"` (default) |
| `audio_bitrate` | string | No | AAC encoding bitrate | `"128k"` (default) |
| `resolution` | string | No | Video resolution | `"1920x1080"` (default) |
| `framerate` | string | No | Video frame rate | `"30"` (default) |

**Response:** 200 OK
```json
{
  "status": "string",
  "saved": boolean
}
```

**Success Response:**
```json
{
  "status": "ok",
  "saved": true
}
```

**Error Response:**
```json
{
  "status": "error",
  "error": "string"
}
```

**Example Request:**
```bash
curl -X POST http://192.168.1.100:6077/adopt \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "device_name": "Living Room Camera",
    "location": "Living Room",
    "ingest_url": "rtmp://ingest.example.com/live",
    "stream_key": "spoke_abc123",
    "video_bitrate": "4000k",
    "audio_bitrate": "128k"
  }'
```

**Example Response:**
```json
{
  "status": "ok",
  "saved": true
}
```

**Behavior:**
- Configuration is immediately saved to `~/stream-config.json`
- If `ingest_url` and `stream_key` are provided, FFmpeg streaming will start automatically
- Device will begin broadcasting new `device_id` in UDP beacons
- Configuration persists across reboots

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid JSON payload |
| 404 | Endpoint not found |
| 500 | Configuration save failed |

---

## UDP/RTP Streaming Protocol

### Connection

**Protocol:** UDP/RTP with MPEG-TS container  
**Port:** Configurable (typically 5000-5100)  
**Direction:** Spoke → Ingest Server (outbound)

### Stream URL Format

```
udp://<host>:<port>
```

Constructed from configuration:
- `ingest_url`: Complete UDP destination (e.g., `udp://192.168.1.100:5000`)

**Full URL Example:**
```
udp://192.168.1.100:5000
```

### Stream Specifications

#### Video

| Parameter | Value | Notes |
|-----------|-------|-------|
| Codec | H.264 (AVC) | libx264 encoder |
| Profile | Baseline/Main | Depends on encoder |
| Level | 4.0 | Typical for 1080p |
| Resolution | 1920x1080 | Configurable |
| Frame Rate | 30 fps | Configurable |
| Bitrate | 4000 kbps | Configurable (default) |
| Keyframe Interval | 2 seconds | 60 frames @ 30fps |
| Pixel Format | YUV420p | Standard |
| Preset | veryfast | Low latency, lower CPU |
| Tune | zerolatency | Minimal buffering |

#### Audio

| Parameter | Value | Notes |
|-----------|-------|-------|
| Codec | AAC | Advanced Audio Coding |
| Sample Rate | 48000 Hz | From HDMI source |
| Channels | 2 (Stereo) | From HDMI source |
| Bitrate | 128 kbps | Configurable (default) |
| Profile | LC (Low Complexity) | Standard |

#### Container

| Parameter | Value |
|-----------|-------|
| Format | MPEG-TS (Transport Stream) |
| Muxer | UDP/RTP |

### FFmpeg Command

The spoke uses the following FFmpeg command for streaming:

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

### Network Requirements

**Bandwidth:**
- Minimum: 4.2 Mbps upload (for 4000k video + 128k audio + UDP overhead)
- Recommended: 6+ Mbps upload (for stability)
- Lower overhead than RTMP (~8% bandwidth savings)

**Latency:**
- RTT to ingest server: <100ms recommended
- Higher latency may cause buffering issues

**Firewall:**
- Outbound UDP port (configured, typically 5000) must be allowed
- No inbound ports required

---

## Configuration File Format

**Location:** `~/stream-config.json` (expands to user's home directory)  
**Format:** JSON  
**Permissions:** 644 (readable by all, writable by owner)

### Schema

```json
{
  "device_id": "string | null",
  "device_name": "string",
  "location": "string",
  "ingest_url": "string",
  "stream_key": "string",
  "video_bitrate": "string",
  "audio_bitrate": "string",
  "resolution": "string",
  "framerate": "string"
}
```

### Field Definitions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `device_id` | string \| null | `null` | Unique device identifier (null = unadopted) |
| `device_name` | string | hostname | Device display name |
| `location` | string | `""` | Physical location description |
| `ingest_url` | string | `""` | RTMP server base URL |
| `stream_key` | string | `""` | RTMP stream key |
| `video_bitrate` | string | `"4000k"` | H.264 bitrate (e.g., "2000k", "6000k") |
| `audio_bitrate` | string | `"128k"` | AAC bitrate (e.g., "96k", "192k") |
| `resolution` | string | `"1920x1080"` | Video resolution (WxH) |
| `framerate` | string | `"30"` | Video frame rate (fps) |
| `audio_muted` | boolean | `false` | Local audio playback muted |

### Example (Unadopted)

```json
{
  "device_id": null,
  "device_name": "raspberrypi",
  "location": "",
  "ingest_url": "",
  "video_bitrate": "4000k",
  "audio_bitrate": "128k",
  "resolution": "1920x1080",
  "framerate": "30"
}
```

### Example (Adopted and Configured)

```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "Living Room Camera",
  "location": "Living Room",
  "ingest_url": "udp://192.168.1.100:5000",
  "video_bitrate": "4000k",
  "audio_bitrate": "128k",
  "resolution": "1920x1080",
  "framerate": "30",
  "audio_muted": false
}
```

### Manual Editing

The configuration file can be manually edited:

```bash
nano ~/stream-config.json
```

**Note:** Changes take effect on next application restart or when reloaded by the beacon thread.

---

## Video4Linux2 (V4L2) Interface

The spoke accesses the capture card via Video4Linux2.

### Device Path

```
/dev/video0
```

### Capabilities

Query device capabilities:
```bash
v4l2-ctl -d /dev/video0 --all
```

### Supported Formats

| Parameter | Value |
|-----------|-------|
| Pixel Format | UYVY (4:2:2) |
| Resolution | 1920x1080 |
| Frame Rate | 30 fps |
| Colorimetry | BT.601 |
| Field | Progressive |

### Timings

Query current timings:
```bash
v4l2-ctl -d /dev/video0 --query-dv-timings
```

Set timings:
```bash
v4l2-ctl -d /dev/video0 --set-dv-bt-timings query
```

### EDID

EDID is loaded from `~/edid-1080p30.txt` on boot via systemd service.

---

## ALSA Audio Interface

### Device

```
hw:2,0
```

**Format:**
- `hw:X,Y` where X = card number, Y = device number
- Card 2 is typically the TC358743 audio capture

### Find Audio Devices

List all capture devices:
```bash
arecord -l
```

Example output:
```
card 2: tc358743 [tc358743], device 0: bcm2835-i2s-dir-hifi dir-hifi-0 []
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

### Test Audio Capture

```bash
arecord -D hw:2,0 -f S16_LE -r 48000 -c 2 test.wav
```

### Audio Monitoring Pipeline

The spoke includes a GStreamer pipeline for local audio monitoring:

```
alsasrc device=hw:2,0
  ! audioconvert
  ! level interval=50000000
  ! volume
  ! autoaudiosink
```

**Features:**
- Real-time stereo level metering (50ms intervals)
- Mute control via volume element
- Local playback through Pi's audio output

---

## GStreamer Pipeline

### Preview Pipeline

```
v4l2src device=/dev/video0
  ! video/x-raw,format=UYVY,width=1920,height=1080,colorimetry=bt601,framerate=30/1
  ! videoscale add-borders=false
  ! video/x-raw,width=480,height=270
  ! videoconvert n-threads=4
  ! video/x-raw,format=RGB
  ! appsink name=mysink emit-signals=true max-buffers=1 drop=true sync=false
```

### Pipeline Elements

| Element | Purpose | Configuration |
|---------|---------|---------------|
| `v4l2src` | Capture from V4L2 device | `device=/dev/video0` |
| `videoscale` | Downscale for performance | `add-borders=false` |
| `videoconvert` | Color space conversion | `n-threads=4` |
| `appsink` | Output to application | `max-buffers=1 drop=true sync=false` |

### Test Pipeline

```bash
gst-launch-1.0 v4l2src device=/dev/video0 \
  ! video/x-raw,format=UYVY,width=1920,height=1080,colorimetry=bt601,framerate=30/1 \
  ! videoconvert \
  ! autovideosink
```

---

## Port Reference

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 6077 | TCP (HTTP) | Inbound | Discovery API server |
| 9999 | UDP | Outbound | Beacon broadcast |
| 5000+ | UDP | Outbound | Video streaming (configurable) |

### Firewall Configuration

**On Spoke Device:**
```bash
# Allow inbound HTTP for discovery
sudo ufw allow 6077/tcp

# Allow outbound UDP (usually allowed by default)
sudo ufw allow out 5000/udp
```

**On Discovery App Server:**
```bash
# Allow inbound UDP beacons
sudo ufw allow 9999/udp

# Allow inbound UDP streams
sudo ufw allow 5000/udp
```

---

## Status Codes

### Device Status

| Status | Description |
|--------|-------------|
| `ready` | Device operational and ready for configuration |
| `streaming` | Currently streaming to ingest server |
| `error` | Device in error state |

### Adoption Status

| device_id Value | Status |
|-----------------|--------|
| `null` or `"unadopted"` | Not adopted, awaiting configuration |
| UUID string | Adopted and configured |

---

## Error Handling

### HTTP API Errors

All error responses follow this format:
```json
{
  "status": "error",
  "error": "Error description"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Connection refused (port 6077) | Discovery server not running | Check if touchstream-spoke.py is running |
| Timeout | Network connectivity issue | Verify network connection |
| Invalid JSON | Malformed request payload | Validate JSON syntax |
| Stream not starting | Missing ingest_url or stream_key | Provide complete configuration |
| No video signal | No HDMI input | Connect HDMI source |

---

## Rate Limits

**UDP Beacons:**
- 1 beacon per 5 seconds
- No burst limit

**HTTP API:**
- No rate limiting implemented
- Recommend max 10 requests/second per client

**RTMP Streaming:**
- Single concurrent stream per device
- Reconnection attempts: Unlimited (FFmpeg handles)

---

## Security Considerations

### Current Implementation

⚠️ **Warning:** The current implementation has NO security features:
- No authentication on HTTP endpoints
- No encryption on HTTP traffic
- No validation of configuration sources
- Config file readable by all users

### Recommended Enhancements

1. **API Authentication:**
   ```json
   {
     "api_key": "secret-key-here",
     "device_id": "..."
   }
   ```

2. **HTTPS:**
   - Use TLS for HTTP discovery API
   - Validate certificates

3. **RTMPS:**
   - Use encrypted RTMP (RTMPS)
   - Validate server certificates

4. **Network Isolation:**
   - Run on isolated VLAN
   - Firewall rules to restrict access

5. **Config Encryption:**
   - Encrypt stream_key in config file
   - Use system keyring for secrets

---

## Version Compatibility

### API Version

Current API version: **1.0**

No versioning implemented in endpoints. Future versions should use:
```
GET /v1/info
POST /v1/adopt
```

### Protocol Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| RTMP | 1.0 | Standard RTMP protocol |
| HTTP | 1.1 | Standard HTTP/1.1 |
| UDP | IPv4 | Broadcast on local subnet |
| GStreamer | 1.0+ | Requires GStreamer 1.x |
| FFmpeg | 4.0+ | Tested with FFmpeg 4.x and 5.x |

---

## Example Integrations

### Python Client

```python
import requests

class SpokeClient:
    def __init__(self, ip):
        self.ip = ip
        self.base_url = f'http://{ip}:6077'
    
    def get_info(self):
        return requests.get(f'{self.base_url}/info').json()
    
    def adopt(self, config):
        return requests.post(f'{self.base_url}/adopt', json=config).json()

# Usage
spoke = SpokeClient('192.168.1.100')
info = spoke.get_info()
print(info)
```

### JavaScript Client

```javascript
class SpokeClient {
  constructor(ip) {
    this.ip = ip;
    this.baseUrl = `http://${ip}:6077`;
  }
  
  async getInfo() {
    const response = await fetch(`${this.baseUrl}/info`);
    return response.json();
  }
  
  async adopt(config) {
    const response = await fetch(`${this.baseUrl}/adopt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    return response.json();
  }
}

// Usage
const spoke = new SpokeClient('192.168.1.100');
const info = await spoke.getInfo();
console.log(info);
```

### cURL Examples

```bash
# Get device info
curl http://192.168.1.100:6077/info

# Adopt device
curl -X POST http://192.168.1.100:6077/adopt \
  -H "Content-Type: application/json" \
  -d @config.json

# Listen for beacons
nc -ul 9999
```
