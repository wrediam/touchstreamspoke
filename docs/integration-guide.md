# Discovery App Integration Guide

This guide explains how to integrate TouchStream Spoke devices into your discovery/management application for multi-platform restreaming.

## System Overview

```
┌──────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Spoke Device    │         │  Discovery App   │         │  YouTube        │
│  (Raspberry Pi)  │─UDP────▶│  (Restreaming    │─RTMP───▶│  Facebook       │
│                  │         │   Hub)           │         │  Twitch, etc.   │
└──────────────────┘         └──────────────────┘         └─────────────────┘
         │                            │
         │◀────HTTP Config────────────│
         │                            │
         └─────UDP Beacon────────────▶│
              (Discovery)
```

**Flow:**
1. Spoke broadcasts UDP beacon announcing presence
2. Discovery app detects spoke and queries device info
3. User names the device and assigns location
4. Discovery app sends UDP ingest URL to spoke
5. Spoke streams to discovery app via UDP (low latency)
6. Discovery app restreams to multiple platforms via RTMP (YouTube, Facebook, etc.)

## Discovery Implementation

### 1. UDP Beacon Listener

Implement a UDP listener to detect new spoke devices on the network.

**Protocol:**
- **Port:** 9999 (UDP)
- **Broadcast Interval:** Every 5 seconds
- **Payload Format:** JSON

**Example Implementation (Python):**

```python
import socket
import json
import threading

class SpokeDiscovery:
    def __init__(self, on_device_found):
        self.on_device_found = on_device_found
        self.known_devices = {}
        self.running = False
        
    def start(self):
        """Start listening for UDP beacons"""
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        
    def _listen(self):
        """Listen for UDP broadcasts"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 9999))
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                ip_address = addr[0]
                
                # Parse beacon payload
                beacon = json.loads(data.decode('utf-8'))
                device_name = beacon.get('device_name')
                device_id = beacon.get('device_id')
                
                # Create device identifier
                device_key = f"{ip_address}:{device_name}"
                
                # Check if this is a new device
                if device_key not in self.known_devices:
                    self.known_devices[device_key] = {
                        'ip': ip_address,
                        'device_name': device_name,
                        'device_id': device_id,
                        'last_seen': time.time()
                    }
                    
                    # Notify callback of new device
                    self.on_device_found(ip_address, device_name, device_id)
                else:
                    # Update last seen time
                    self.known_devices[device_key]['last_seen'] = time.time()
                    
            except Exception as e:
                print(f"Beacon parsing error: {e}")
                
    def stop(self):
        """Stop listening"""
        self.running = False

# Usage
def handle_new_device(ip, name, device_id):
    print(f"Found device: {name} at {ip} (ID: {device_id})")
    if device_id == 'unadopted':
        # This is a new device that needs adoption
        initiate_adoption_flow(ip, name)

discovery = SpokeDiscovery(on_device_found=handle_new_device)
discovery.start()
```

**Example Implementation (Node.js):**

```javascript
const dgram = require('dgram');
const server = dgram.createSocket('udp4');

const knownDevices = new Map();

server.on('message', (msg, rinfo) => {
  try {
    const beacon = JSON.parse(msg.toString());
    const ip = rinfo.address;
    const deviceKey = `${ip}:${beacon.device_name}`;
    
    if (!knownDevices.has(deviceKey)) {
      knownDevices.set(deviceKey, {
        ip: ip,
        deviceName: beacon.device_name,
        deviceId: beacon.device_id,
        lastSeen: Date.now()
      });
      
      console.log(`Found device: ${beacon.device_name} at ${ip}`);
      
      if (beacon.device_id === 'unadopted') {
        // Initiate adoption flow
        initiateAdoption(ip, beacon.device_name);
      }
    } else {
      // Update last seen
      knownDevices.get(deviceKey).lastSeen = Date.now();
    }
  } catch (err) {
    console.error('Beacon parse error:', err);
  }
});

server.bind(9999);
```

### 2. Device Information Query

Once a device is discovered, query its full information via HTTP.

**Endpoint:** `GET http://<spoke-ip>:6077/info`

**Example Request:**

```python
import requests

def get_device_info(ip_address):
    """Query device information"""
    try:
        response = requests.get(f'http://{ip_address}:6077/info', timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Failed to query device at {ip_address}: {e}")
    return None

# Example usage
info = get_device_info('192.168.1.100')
print(info)
# {
#   "device_id": "unadopted",
#   "device_name": "raspberrypi",
#   "ip": "192.168.1.100",
#   "model": "raspberry-pi",
#   "status": "ready"
# }
```

### 3. Device Adoption Flow

When a new unadopted device is found, present it to the user for configuration.

**UI Flow:**
1. Show discovered device with IP and default name
2. Prompt user to enter custom name
3. Optionally prompt for location
4. Generate unique device_id
5. Configure RTMP ingest URL pointing to your restreaming server
6. Send configuration to spoke via POST /adopt

**Example Adoption Implementation:**

```python
import uuid
import requests

def adopt_device(spoke_ip, user_provided_name, location, rtmp_ingest_url):
    """
    Adopt a spoke device and configure it for streaming
    
    Args:
        spoke_ip: IP address of the spoke device
        user_provided_name: Name provided by user (e.g., "Living Room Camera")
        location: Physical location (e.g., "Living Room")
        rtmp_ingest_url: Your restreaming server's RTMP ingest URL
    """
    # Generate unique device ID
    device_id = str(uuid.uuid4())
    
    # Generate unique UDP port for this device (or use fixed port per device)
    udp_port = 5000  # You can assign different ports per device if needed
    
    # Prepare configuration payload
    config = {
        'device_id': device_id,
        'device_name': user_provided_name,
        'location': location,
        'ingest_url': f'{rtmp_ingest_url}:{udp_port}',  # e.g., udp://192.168.1.100:5000
        'video_bitrate': '4000k',  # Optional: customize
        'audio_bitrate': '128k'     # Optional: customize
    }
    
    try:
        # Send configuration to spoke
        response = requests.post(
            f'http://{spoke_ip}:6077/adopt',
            json=config,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'ok':
                print(f"Successfully adopted device: {user_provided_name}")
                
                # Store device in your database
                save_device_to_database({
                    'device_id': device_id,
                    'device_name': user_provided_name,
                    'location': location,
                    'ip_address': spoke_ip,
                    'udp_port': udp_port,
                    'status': 'adopted'
                })
                
                return True
    except Exception as e:
        print(f"Adoption failed: {e}")
    
    return False

# Example usage
success = adopt_device(
    spoke_ip='192.168.1.100',
    user_provided_name='Living Room Camera',
    location='Living Room',
    rtmp_ingest_url='udp://192.168.1.50'  # Your discovery app's IP
)
```

**Example UI Flow (Pseudocode):**

```javascript
// When new device discovered
function onDeviceDiscovered(ip, defaultName, deviceId) {
  if (deviceId === 'unadopted') {
    showAdoptionDialog({
      ip: ip,
      defaultName: defaultName,
      onSubmit: async (userInputs) => {
        const config = {
          device_id: generateUUID(),
          device_name: userInputs.name,
          location: userInputs.location,
          ingest_url: 'udp://192.168.1.50:5000',  // Your discovery app's IP and port
          video_bitrate: '4000k',
          audio_bitrate: '128k'
        };
        
        const success = await adoptDevice(ip, config);
        if (success) {
          showSuccess(`Device "${userInputs.name}" adopted successfully!`);
          // Start monitoring device
          monitorDevice(config.device_id, ip);
        }
      }
    });
  }
}
```

## Restreaming Server Setup

Your discovery app needs a UDP receiver to receive streams from spokes, then restream to platforms via RTMP.

### Option 1: FFmpeg UDP Receiver + Restreamer (Recommended)

Receive UDP stream from spoke and restream to multiple RTMP destinations:

```python
import subprocess
import threading

class UDPRestreamer:
    def __init__(self, udp_port, device_id):
        self.udp_port = udp_port
        self.device_id = device_id
        self.proc = None
        
    def start(self, destinations):
        """
        Start receiving UDP and restreaming to RTMP destinations
        
        Args:
            destinations: List of dicts with 'platform' and 'rtmp_url'
        """
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-i', f'udp://0.0.0.0:{self.udp_port}',  # Receive UDP
            '-c', 'copy'  # No re-encoding (fast, low CPU)
        ]
        
        # Add each destination
        for dest in destinations:
            cmd.extend(['-f', 'flv', dest['rtmp_url']])
        
        # Start process
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Restreaming device {self.device_id} from UDP:{self.udp_port}")
        
    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=5)
            self.proc = None

# Example usage
restreamer = UDPRestreamer(udp_port=5000, device_id='device-123')
restreamer.start([
    {'platform': 'YouTube', 'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/YOUR_KEY'},
    {'platform': 'Facebook', 'rtmp_url': 'rtmp://live-api-s.facebook.com:80/rtmp/YOUR_KEY'}
])
```

### Option 2: GStreamer UDP Receiver

For lower latency and more control:

```python
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

def create_udp_receiver(udp_port, rtmp_destinations):
    """
    Create GStreamer pipeline to receive UDP and restream to RTMP
    """
    # Build pipeline string
    pipeline_str = f"udpsrc port={udp_port} ! tsdemux ! "
    
    # Add tee for multiple outputs
    pipeline_str += "tee name=t "
    
    # Add RTMP outputs
    for i, dest in enumerate(rtmp_destinations):
        pipeline_str += f"t. ! queue ! flvmux ! rtmpsink location={dest['rtmp_url']} "
    
    pipeline = Gst.parse_launch(pipeline_str)
    pipeline.set_state(Gst.State.PLAYING)
    
    return pipeline

# Example
pipeline = create_udp_receiver(5000, [
    {'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/YOUR_KEY'},
    {'rtmp_url': 'rtmp://live-api-s.facebook.com:80/rtmp/YOUR_KEY'}
])
```

### Option 3: Simple UDP Monitor + FFmpeg

Monitor for incoming UDP streams and spawn FFmpeg for each:

```python
import subprocess
import socket

def monitor_udp_stream(udp_port, device_id, destinations):
    """
    Monitor UDP port and start restreaming when data arrives
    """
    
    for dest in destinations:
        cmd.extend(['-f', 'flv', dest['rtmp_url']])
    
    # Start restreaming process
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    
    return proc

# Example usage
destinations = [
    {'platform': 'YouTube', 'rtmp_url': 'rtmp://a.rtmp.youtube.com/live2/your-key'},
    {'platform': 'Facebook', 'rtmp_url': 'rtmp://live-api-s.facebook.com:80/rtmp/your-key'},
    {'platform': 'Twitch', 'rtmp_url': 'rtmp://live.twitch.tv/app/your-key'}
]

restream_proc = start_restreaming('spoke_abc123', destinations)
```

## Complete Integration Example

Here's a complete example of a discovery app that handles the full lifecycle:

```python
import socket
import json
import threading
import requests
import uuid
import time
from typing import Dict, Callable

class TouchStreamDiscoveryApp:
    def __init__(self, rtmp_ingest_url: str):
        """
        Initialize discovery app
        
        Args:
            rtmp_ingest_url: Your RTMP server URL (e.g., 'rtmp://your-server.com/live')
        """
        self.rtmp_ingest_url = rtmp_ingest_url
        self.devices = {}  # device_id -> device_info
        self.running = False
        
    def start(self):
        """Start discovery service"""
        self.running = True
        
        # Start UDP beacon listener
        self.beacon_thread = threading.Thread(target=self._listen_beacons, daemon=True)
        self.beacon_thread.start()
        
        print("Discovery app started")
        
    def _listen_beacons(self):
        """Listen for UDP beacons from spokes"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 9999))
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                beacon = json.loads(data.decode('utf-8'))
                ip = addr[0]
                
                self._handle_beacon(ip, beacon)
            except Exception as e:
                print(f"Beacon error: {e}")
                
    def _handle_beacon(self, ip: str, beacon: dict):
        """Process received beacon"""
        device_id = beacon.get('device_id')
        device_name = beacon.get('device_name')
        
        if device_id == 'unadopted':
            # New device found
            print(f"\n🆕 New device discovered: {device_name} at {ip}")
            
            # Query full device info
            info = self._query_device_info(ip)
            if info:
                # Prompt user for adoption (in real app, this would be a UI)
                self._prompt_adoption(ip, info)
        else:
            # Known device, update status
            if device_id in self.devices:
                self.devices[device_id]['last_seen'] = time.time()
                self.devices[device_id]['ip'] = ip  # Update IP if changed
                
    def _query_device_info(self, ip: str) -> dict:
        """Query device information via HTTP"""
        try:
            response = requests.get(f'http://{ip}:6077/info', timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Failed to query device: {e}")
        return None
        
    def _prompt_adoption(self, ip: str, info: dict):
        """
        Prompt user to adopt device
        In a real app, this would show a UI dialog
        """
        print(f"\n📋 Device Information:")
        print(f"   IP: {ip}")
        print(f"   Default Name: {info['device_name']}")
        print(f"   Model: {info['model']}")
        print(f"   Status: {info['status']}")
        
        # Simulate user input (in real app, get from UI)
        user_name = input("\n✏️  Enter device name (or press Enter to skip): ").strip()
        if not user_name:
            print("Skipped adoption")
            return
            
        location = input("📍 Enter location (optional): ").strip()
        
        # Adopt device
        success = self.adopt_device(ip, user_name, location)
        if success:
            print(f"✅ Device '{user_name}' adopted successfully!")
        else:
            print("❌ Adoption failed")
            
    def adopt_device(self, ip: str, name: str, location: str = '') -> bool:
        """Adopt and configure a spoke device"""
        device_id = str(uuid.uuid4())
        stream_key = f"spoke_{device_id[:8]}"
        
        config = {
            'device_id': device_id,
            'device_name': name,
            'location': location,
            'ingest_url': self.rtmp_ingest_url,
            'stream_key': stream_key,
            'video_bitrate': '4000k',
            'audio_bitrate': '128k'
        }
        
        try:
            response = requests.post(
                f'http://{ip}:6077/adopt',
                json=config,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'ok':
                    # Store device
                    self.devices[device_id] = {
                        'device_id': device_id,
                        'device_name': name,
                        'location': location,
                        'ip': ip,
                        'stream_key': stream_key,
                        'adopted_at': time.time(),
                        'last_seen': time.time()
                    }
                    return True
        except Exception as e:
            print(f"Adoption error: {e}")
            
        return False
        
    def list_devices(self):
        """List all adopted devices"""
        print("\n📱 Adopted Devices:")
        for device_id, device in self.devices.items():
            age = time.time() - device['last_seen']
            status = "🟢 Online" if age < 10 else "🔴 Offline"
            print(f"   {status} {device['device_name']} ({device['location']}) - {device['ip']}")
            
    def stop(self):
        """Stop discovery service"""
        self.running = False
        print("Discovery app stopped")

# Usage
if __name__ == '__main__':
    app = TouchStreamDiscoveryApp(rtmp_ingest_url='rtmp://your-server.com/live')
    app.start()
    
    try:
        while True:
            time.sleep(10)
            app.list_devices()
    except KeyboardInterrupt:
        app.stop()
```

## Testing the Integration

### 1. Test Discovery

```bash
# Listen for UDP beacons
nc -ul 9999

# You should see JSON beacons every 5 seconds:
# {"device_name": "raspberrypi", "device_id": "unadopted"}
```

### 2. Test Device Query

```bash
curl http://<spoke-ip>:6077/info
```

### 3. Test Adoption

```bash
curl -X POST http://<spoke-ip>:6077/adopt \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-device-123",
    "device_name": "Test Camera",
    "location": "Test Location",
    "ingest_url": "rtmp://your-server.com/live",
    "stream_key": "test_key_123",
    "video_bitrate": "4000k",
    "audio_bitrate": "128k"
  }'
```

### 4. Verify Streaming

```bash
# Check if spoke is streaming to your server
ffprobe rtmp://your-server.com/live/test_key_123
```

## Best Practices

1. **Device ID Generation**: Use UUIDs for globally unique device IDs
2. **Stream Key Security**: Generate cryptographically secure stream keys
3. **Network Isolation**: Run discovery on isolated VLAN for security
4. **Health Monitoring**: Track last_seen timestamps to detect offline devices
5. **Error Handling**: Implement retry logic for network failures
6. **Database Persistence**: Store device configurations in database
7. **User Notifications**: Alert users when devices go offline
8. **Stream Validation**: Verify stream health before restreaming to platforms

## Troubleshooting

### Device Not Discovered
- Check firewall allows UDP port 9999
- Verify spoke and discovery app on same network
- Check spoke is running: `ps aux | grep touchstream`

### Adoption Fails
- Verify HTTP port 6077 is accessible
- Check spoke logs for errors
- Ensure JSON payload is valid

### Stream Not Received
- Verify RTMP server is running
- Check network connectivity between spoke and server
- Verify stream key matches configuration
- Check FFmpeg process on spoke: `ps aux | grep ffmpeg`

### Stream Quality Issues
- Adjust video_bitrate based on network capacity
- Monitor network bandwidth usage
- Check CPU usage on spoke device
- Verify RTMP server has sufficient resources

## Remote Management

The spoke device exposes HTTP GET endpoints for remote management. These can be integrated into your discovery app's device management UI.

### Available Actions

| Action       | Endpoint        | Description                                         |
| ------------ | --------------- | --------------------------------------------------- |
| **Reboot**   | `GET /reboot`   | Reboots the Raspberry Pi                            |
| **Shutdown** | `GET /shutdown` | Shuts down the Raspberry Pi                         |
| **Update**   | `GET /update`   | Pulls latest code from git and restarts the service |

### Implementation Example

```python
def reboot_device(ip):
    """Reboot a remote spoke device"""
    try:
        response = requests.get(f'http://{ip}:6077/reboot', timeout=5)
        if response.status_code == 200:
            print(f"Reboot initiated for {ip}")
            return True
    except Exception as e:
        print(f"Failed to reboot {ip}: {e}")
    return False
```
