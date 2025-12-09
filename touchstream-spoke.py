#!/usr/bin/env python3
"""
TouchStream Spoke (GStreamer) — Optimized for Raspberry Pi 4 B (4GB)
 - True fullscreen kiosk mode
 - GStreamer appsink preview from /dev/video0 (UYVY -> RGB)
 - HUD overlay (tap to toggle)
 - Settings cog (top-left) to set ingest_url / device_name
 - UDP broadcast beacon + HTTP discovery server (GET /info, POST /adopt)
 - FFmpeg streamer (video+audio) via UDP/RTP (MPEG-TS) for low latency
 - Config persisted at ~/stream-config.json
 - OPTIMIZED: Scaled preview, reduced latency, UDP streaming

Copyright (c) 2025 Will Reeves and TouchStream Contributors
Licensed under the MIT License - see LICENSE file for details
"""
import os
import sys
from pathlib import Path

# Set environment for better GPU support BEFORE importing Kivy
os.environ['KIVY_GL_BACKEND'] = 'gl'

import json
import threading
import time
import socket
import subprocess
import platform
from http.server import BaseHTTPRequestHandler, HTTPServer

# Kivy + GObject/GStreamer (PyGObject)
import kivy
kivy.require('2.1.0')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.config import Config
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

# GStreamer
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    GST_OK = True
except Exception as e:
    print("GStreamer (python gi) not available:", e)
    GST_OK = False

# ---- Config and constants ----
CONFIG_PATH = str(Path.home() / 'stream-config.json')
DISCOVERY_PORT = 6077
DISCOVERY_UDP_PORT = 9999
VIDEO_DEVICE = '/dev/video0'
AUDIO_DEVICE = 'hw:2,0'  # adjust if different

# Preview resolution (scaled down AGGRESSIVELY for performance)
# 480x270 = 1/16th the pixels of 1080p, much faster
PREVIEW_WIDTH = 480
PREVIEW_HEIGHT = 270
PREVIEW_FPS = 30  # Preview at 30fps to save CPU

# Capture resolution (full quality for streaming)
CAPTURE_WIDTH = 1920
CAPTURE_HEIGHT = 1080
CAPTURE_FPS = 30  # Strict 30fps only

# Screen sleep settings
SCREEN_SLEEP_TIMEOUT = 3 * 60 * 60  # 3 hours in seconds

DEFAULT_CONFIG = {
    'device_id': None,
    'device_name': platform.node(),
    'location': '',  # Set via POST /adopt from hub
    'ingest_url': '',  # UDP URL: udp://host:port
    'video_bitrate': '4000k',
    'audio_bitrate': '128k',
    'resolution': f'{CAPTURE_WIDTH}x{CAPTURE_HEIGHT}',
    'framerate': str(CAPTURE_FPS),
    'audio_muted': False
}

# ---- Config helpers ----
def ensure_config():
    # Expand the path to handle ~ properly
    config_path = os.path.expanduser(CONFIG_PATH)
    d = os.path.dirname(config_path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    if not os.path.exists(config_path):
        # Write default config directly to avoid recursion
        try:
            with open(config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG.copy(), f, indent=2)
        except Exception as e:
            print("Failed to create default config:", e)

def load_config():
    ensure_config()
    config_path = os.path.expanduser(CONFIG_PATH)
    try:
        with open(config_path, 'r') as f:
            cfg = json.load(f)
    except Exception:
        cfg = DEFAULT_CONFIG.copy()
    for k, v in DEFAULT_CONFIG.items():
        if k not in cfg:
            cfg[k] = v
    return cfg

def save_config(cfg):
    config_path = os.path.expanduser(CONFIG_PATH)
    try:
        with open(config_path, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print("Failed to save config:", e)

# ---- Discovery HTTP Server ----
class DiscoveryHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

    def do_GET(self):
        if self.path == '/info':
            cfg = load_config()
            data = {
                'device_id': cfg.get('device_id') or 'unadopted',
                'device_name': cfg.get('device_name'),
                'ip': self._get_device_ip(),
                'model': 'raspberry-pi',
                'status': 'ready'
            }
            self._send_json(data)
            return
        self.send_response(404)
        self.end_headers()
    
    def _get_device_ip(self):
        """Get the device's own IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unknown"

    def do_POST(self):
        if self.path == '/adopt':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body)
                cfg = load_config()
                cfg.update(payload)
                save_config(cfg)
                resp = {'status': 'ok', 'saved': True}
            except Exception as e:
                resp = {'status': 'error', 'error': str(e)}
            self._send_json(resp)
            return

        if self.path == '/shutdown':
            self._send_json({'status': 'shutdown_initiated'})
            threading.Thread(target=lambda: (time.sleep(1), os.system('sudo shutdown -h now'))).start()
            return
            
        if self.path == '/reboot':
            self._send_json({'status': 'reboot_initiated'})
            threading.Thread(target=lambda: (time.sleep(1), os.system('sudo reboot'))).start()
            return

        if self.path == '/update':
            self._send_json({'status': 'updating'})
            
            def do_update():
                time.sleep(1)
                try:
                    # git pull
                    print("Running git pull...")
                    result = subprocess.run(['git', 'pull'], check=False, capture_output=True, text=True)
                    print(f"Git output: {result.stdout}")
                    if result.returncode != 0:
                        print(f"Git error: {result.stderr}")
                    
                    # Restart process
                    print("Restarting application...")
                    os.execv(sys.executable, ['python3'] + sys.argv)
                except Exception as e:
                    print(f"Update failed: {e}")

            threading.Thread(target=do_update).start()
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def start_discovery_server():
    try:
        server = HTTPServer(('0.0.0.0', DISCOVERY_PORT), DiscoveryHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Discovery HTTP server running on port {DISCOVERY_PORT}")
    except Exception as e:
        print("Failed to start discovery HTTP server:", e)

# ---- UDP Beacon ----
def udp_beacon_thread():
    cfg = load_config()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        try:
            cfg = load_config()  # Reload to get updates
            payload = json.dumps({
                'device_name': cfg.get('device_name'),
                'device_id': cfg.get('device_id') or 'unadopted'
            })
            sock.sendto(payload.encode('utf-8'), ('<broadcast>', DISCOVERY_UDP_PORT))
        except Exception:
            pass
        time.sleep(5)

# ---- FFmpeg streamer controller ----
class FfmpegStreamer:
    def __init__(self, on_start_callback=None):
        self.proc = None
        self.on_start_callback = on_start_callback

    def start(self, cfg):
        if not cfg.get('ingest_url'):
            print("Missing ingest_url")
            return False
        url = cfg['ingest_url']
        resolution = cfg.get('resolution', f'{CAPTURE_WIDTH}x{CAPTURE_HEIGHT}')
        fr = cfg.get('framerate', str(CAPTURE_FPS))
        vbit = cfg.get('video_bitrate', '4000k')
        ab = cfg.get('audio_bitrate', '128k')

        cmd = [
            'ffmpeg',
            '-f', 'v4l2',
            '-input_format', 'uyvy422',
            '-framerate', fr,
            '-video_size', resolution,
            '-i', VIDEO_DEVICE,
            '-f', 'alsa',
            '-i', AUDIO_DEVICE,
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-tune', 'zerolatency',
            '-b:v', vbit,
            '-c:a', 'aac',
            '-b:a', ab,
            '-f', 'mpegts',
            url
        ]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("FFmpeg started")
            # Notify callback (used to wake screen)
            if self.on_start_callback:
                self.on_start_callback()
            return True
        except Exception as e:
            print("Failed to start ffmpeg:", e)
            return False

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
            print("FFmpeg stopped")

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None

# ---- GStreamer preview pipeline (appsink) - OPTIMIZED ----
class GstPreview:
    def __init__(self, on_frame_callback):
        self.on_frame = on_frame_callback
        self.pipeline = None
        self.appsink = None
        self.running = False
        if not GST_OK:
            raise RuntimeError("GStreamer not available")

    def build_pipeline(self):
        # STRICT 30fps pipeline with proper colorimetry
        # Force device to 30fps, bt601 colorimetry required by TC358743
        pipeline_str = (
            f"v4l2src device={VIDEO_DEVICE} ! "
            f"video/x-raw,format=UYVY,width={CAPTURE_WIDTH},height={CAPTURE_HEIGHT},framerate={CAPTURE_FPS}/1,colorimetry=bt601 ! "
            "videoscale add-borders=false ! "
            f"video/x-raw,width={PREVIEW_WIDTH},height={PREVIEW_HEIGHT} ! "
            "videoconvert n-threads=4 ! video/x-raw,format=RGB ! "
            "appsink name=mysink emit-signals=true max-buffers=1 drop=true sync=false"
        )
        print(f"Building pipeline: {pipeline_str}")
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.appsink = self.pipeline.get_by_name('mysink')
        self.appsink.connect('new-sample', self._on_new_sample)

    def _on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        if sample:
            buf = sample.get_buffer()
            data = buf.extract_dup(0, buf.get_size())
            self.on_frame(data, PREVIEW_WIDTH, PREVIEW_HEIGHT)
        return Gst.FlowReturn.OK

    def start(self):
        if not self.pipeline:
            self.build_pipeline()
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Failed to start pipeline!")
            return False
        self.running = True
        print(f"GStreamer preview started ({PREVIEW_WIDTH}x{PREVIEW_HEIGHT} @ {CAPTURE_FPS}fps)")
        return True

    def stop(self):
        self.running = False
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            self.appsink = None
            print("GStreamer preview stopped")


# ---- Audio Monitor (captures HDMI audio for level metering only) ----
class AudioMonitor:
    def __init__(self, on_level_callback):
        self.on_level = on_level_callback
        self.pipeline = None
        self.running = False
        if not GST_OK:
            raise RuntimeError("GStreamer not available")

    def build_pipeline(self):
        # Capture from ALSA, analyze levels, discard audio (no speaker on Pi)
        # level element provides RMS/peak levels for metering
        pipeline_str = (
            f"alsasrc device={AUDIO_DEVICE} ! "
            "audioconvert ! "
            "level name=level interval=50000000 ! "  # 50ms intervals
            "fakesink"  # Discard audio - no speaker on Pi
        )
        print(f"Building audio pipeline: {pipeline_str}")
        self.pipeline = Gst.parse_launch(pipeline_str)
        
        # Connect to bus for level messages
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::element', self._on_level_message)

    def _on_level_message(self, bus, message):
        struct = message.get_structure()
        if struct and struct.get_name() == 'level':
            # Extract RMS levels for left and right channels
            # GStreamer returns levels as GValueArray, need to handle properly
            try:
                rms = struct.get_value('rms')
                if rms:
                    # Handle both list and single value cases
                    if hasattr(rms, '__len__') and len(rms) >= 2:
                        left_db = float(rms[0])
                        right_db = float(rms[1])
                    elif hasattr(rms, '__len__') and len(rms) >= 1:
                        left_db = right_db = float(rms[0])  # Mono
                    else:
                        left_db = right_db = float(rms)
                    
                    # Convert from dB to linear (0-1 range)
                    # RMS is in dB, typically -60 to 0
                    # Clamp and normalize: -60dB = 0, 0dB = 1
                    left = max(0, min(1, (left_db + 60) / 60))
                    right = max(0, min(1, (right_db + 60) / 60))
                    self.on_level(left, right)
            except Exception as e:
                print(f"Audio level parse error: {e}")

    def start(self):
        if not self.pipeline:
            self.build_pipeline()
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Failed to start audio pipeline!")
            return False
        self.running = True
        print("Audio monitor started")
        return True

    def stop(self):
        self.running = False
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            print("Audio monitor stopped")


# ---- Stereo Level Meter Widget ----
class StereoMeter(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.left_level = 0
        self.right_level = 0
        self.bar_width = 4  # 4px wide each bar
        self.bar_gap = 1    # 1px gap between bars
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self._update_canvas()

    def _update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            # No background - just the bars flush against edge
            # Calculate bar dimensions - full height, no padding
            bar_height = self.height
            left_x = self.x
            right_x = self.x + self.bar_width + self.bar_gap
            bar_y = self.y
            
            # Left channel (green gradient based on level)
            left_h = bar_height * self.left_level
            if self.left_level > 0.8:
                Color(1, 0.3, 0.3, 1)  # Red for high
            elif self.left_level > 0.5:
                Color(1, 0.8, 0.2, 1)  # Yellow for medium
            else:
                Color(0.3, 0.9, 0.3, 1)  # Green for normal
            Rectangle(pos=(left_x, bar_y), size=(self.bar_width, left_h))
            
            # Right channel
            right_h = bar_height * self.right_level
            if self.right_level > 0.8:
                Color(1, 0.3, 0.3, 1)
            elif self.right_level > 0.5:
                Color(1, 0.8, 0.2, 1)
            else:
                Color(0.3, 0.9, 0.3, 1)
            Rectangle(pos=(right_x, bar_y), size=(self.bar_width, right_h))

    def set_levels(self, left, right):
        self.left_level = left
        self.right_level = right
        self._update_canvas()


# ---- Kivy UI ----
class PreviewRoot(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cfg = load_config()

        # Pre-create texture at known size to avoid recreation overhead
        self.tex = Texture.create(size=(PREVIEW_WIDTH, PREVIEW_HEIGHT), colorfmt='rgb')
        self.tex.flip_vertical()
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0
        self.frames_since_last_check = 0
        self.has_signal = False
        self.info_visible = False
        
        # Screen sleep state
        self.last_activity_time = time.time()
        self.screen_asleep = False

        # Image widget for video frames - add first so it's behind everything
        from kivy.uix.image import Image
        self.img_widget = Image(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self.img_widget.texture = self.tex
        self.add_widget(self.img_widget)

        # No signal overlay (centered, shown when no frames)
        self.no_signal_label = Label(
            text='No Signal',
            font_size='24sp',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            color=(1, 1, 1, 0.8),
            opacity=1
        )
        self.add_widget(self.no_signal_label)

        # ---- TOP BAR (25px, with edge padding) ----
        # Status label (left-aligned with 5% padding)
        self.status_label = Label(
            text='Pending Adoption',
            font_size='14sp',
            size_hint=(0.45, 0.08),
            pos_hint={'x': 0.05, 'y': 0.92},
            halign='left',
            valign='middle',
            color=(1, 1, 1, 1)
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        self.add_widget(self.status_label)

        # FPS label (right-aligned with 5% padding)
        self.fps_label = Label(
            text='...waiting',
            font_size='14sp',
            size_hint=(0.45, 0.08),
            pos_hint={'x': 0.50, 'y': 0.92},
            halign='right',
            valign='middle',
            color=(1, 1, 1, 1)
        )
        self.fps_label.bind(size=self.fps_label.setter('text_size'))
        self.add_widget(self.fps_label)

        # ---- LEFT SIDE: Stereo Audio Meter (flush left, full video height) ----
        self.audio_meter = StereoMeter(
            size_hint=(None, 0.84),  # Match video area height (between top/bottom bars)
            width=9,  # 4+1+4 = 9px wide total
            pos_hint={'x': 0, 'y': 0.08}  # Flush left, above bottom bar
        )
        self.add_widget(self.audio_meter)

        # ---- BOTTOM BAR (25px, with edge padding) ----
        # CPU temp label (bottom left)
        self.cpu_temp_label = Label(
            text='--°C',
            font_size='12sp',
            size_hint=(0.15, 0.08),
            pos_hint={'x': 0.02, 'y': 0.0},
            halign='left',
            valign='middle',
            color=(1, 1, 1, 0.6)
        )
        self.cpu_temp_label.bind(size=self.cpu_temp_label.setter('text_size'))
        self.add_widget(self.cpu_temp_label)
        
        # Tap hint (center - expanded now that mute is removed)
        self.tap_hint = Label(
            text='Tap for info',
            font_size='14sp',
            size_hint=(0.66, 0.08),
            pos_hint={'x': 0.17, 'y': 0.0},
            halign='center',
            valign='middle',
            color=(1, 1, 1, 0.6)
        )
        self.tap_hint.bind(size=self.tap_hint.setter('text_size'))
        self.add_widget(self.tap_hint)
        
        # CPU usage label (bottom right)
        self.cpu_usage_label = Label(
            text='--%',
            font_size='12sp',
            size_hint=(0.15, 0.08),
            pos_hint={'x': 0.83, 'y': 0.0},
            halign='right',
            valign='middle',
            color=(1, 1, 1, 0.6)
        )
        self.cpu_usage_label.bind(size=self.cpu_usage_label.setter('text_size'))
        self.add_widget(self.cpu_usage_label)

        # ---- INFO OVERLAY (hidden by default, simpler implementation) ----
        # Use a Label with markup for the overlay instead of canvas drawing
        self.info_overlay = Label(
            text='',
            font_size='14sp',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            halign='center',
            valign='middle',
            color=(1, 1, 1, 1),
            opacity=0
        )
        self.info_overlay.bind(size=self.info_overlay.setter('text_size'))
        self.add_widget(self.info_overlay)
        
        # Track overlay state
        self.info_visible = False

        # Initialize streamer, preview, and audio monitor
        self.ff = FfmpegStreamer(on_start_callback=self._on_stream_start)
        self.gst = None
        self.audio = None
        self._pending_frame = None
        self._frame_lock = threading.Lock()
        self._pending_audio_levels = None
        self._audio_lock = threading.Lock()

        if GST_OK:
            try:
                self.gst = GstPreview(self.on_gst_frame)
                if not self.gst.start():
                    self.no_signal_label.text = "Preview Failed"
            except Exception as e:
                print("Failed to start GstPreview:", e)
                self.no_signal_label.text = f"Error: {e}"
            
            # Start audio monitor (level metering only, no playback)
            try:
                self.audio = AudioMonitor(self.on_audio_level)
                self.audio.start()
            except Exception as e:
                print("Failed to start AudioMonitor:", e)

        # Touch handling
        Window.bind(on_touch_down=self._on_touch)

        # Schedule texture updates to match source framerate (30fps)
        Clock.schedule_interval(self.update_display, 1.0 / 30.0)

        # Heartbeat for status updates (1 second)
        Clock.schedule_interval(self.heartbeat, 1.0)


    def on_gst_frame(self, data, w, h):
        """Called from GStreamer thread - just store the frame"""
        with self._frame_lock:
            self._pending_frame = data
        self.frame_count += 1
        self.frames_since_last_check += 1

    def on_audio_level(self, left, right):
        """Called from GStreamer thread - store audio levels"""
        with self._audio_lock:
            self._pending_audio_levels = (left, right)

    def update_display(self, dt):
        """Called on main thread - update texture if we have a new frame"""
        frame = None
        with self._frame_lock:
            if self._pending_frame is not None:
                frame = self._pending_frame
                self._pending_frame = None

        if frame is not None:
            try:
                self.tex.blit_buffer(frame, colorfmt='rgb', bufferfmt='ubyte')
                self.img_widget.texture = self.tex
                self.img_widget.canvas.ask_update()
                
                # Hide no signal label when we have frames
                if self.no_signal_label.opacity > 0:
                    self.no_signal_label.opacity = 0
                    self.has_signal = True
            except Exception as e:
                print(f"Texture update failed: {e}")
        
        # Update audio meter
        levels = None
        with self._audio_lock:
            if self._pending_audio_levels is not None:
                levels = self._pending_audio_levels
                self._pending_audio_levels = None
        
        if levels is not None:
            self.audio_meter.set_levels(levels[0], levels[1])

    def _on_touch(self, window, touch):
        """Toggle info overlay on tap"""
        # Record activity for screen sleep
        self._record_activity()
        
        # Wake screen if asleep (don't process tap further)
        if self.screen_asleep:
            self._wake_screen()
            return True
        
        if self.info_visible:
            # Hide overlay
            self.info_overlay.opacity = 0
            self.info_visible = False
        else:
            # Show overlay with current info
            self._update_info_text()
            self.info_overlay.opacity = 1
            self.info_visible = True
        return True

    def _update_info_text(self):
        """Update the info overlay text"""
        cfg = load_config()
        
        # Get IP address
        ip = self._get_ip_address()
        
        # Adoption status
        device_id = cfg.get('device_id')
        if device_id:
            adoption_status = f"Adopted (ID: {device_id})"
        else:
            adoption_status = "Not Adopted"
        
        # Location
        location = cfg.get('location') or 'Not Set'
        
        self.info_overlay.text = (
            f"IP Address: {ip}\n\n"
            f"Status: {adoption_status}\n\n"
            f"Location: {location}"
        )

    def _get_ip_address(self):
        """Get the device's IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unknown"

    def _get_status_text(self):
        """Determine current status based on state"""
        cfg = load_config()
        
        # Check if adopted
        if not cfg.get('device_id'):
            return "Pending Adoption"
        
        # Check if streaming
        if self.ff.is_running():
            return "Streaming"
        
        return "Standby"
    
    def _get_cpu_temp(self):
        """Get CPU temperature in Celsius (low overhead)"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = int(f.read().strip()) / 1000.0
                return f"{temp:.0f}°C"
        except Exception:
            return "--°C"
    
    def _get_cpu_usage(self):
        """Get CPU usage percentage (cached, low overhead)"""
        try:
            # Read /proc/stat for CPU times (very fast)
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                fields = line.split()
                # fields: cpu user nice system idle iowait irq softirq
                idle = int(fields[4])
                total = sum(int(x) for x in fields[1:8])
                
                # Calculate delta since last check
                if hasattr(self, '_last_cpu_idle'):
                    idle_delta = idle - self._last_cpu_idle
                    total_delta = total - self._last_cpu_total
                    if total_delta > 0:
                        usage = 100.0 * (1.0 - idle_delta / total_delta)
                        self._last_cpu_idle = idle
                        self._last_cpu_total = total
                        return f"{usage:.0f}%"
                
                # First run, just store values
                self._last_cpu_idle = idle
                self._last_cpu_total = total
                return "--%"
        except Exception:
            return "--%"

    def heartbeat(self, dt):
        """Update status and FPS displays"""
        # Calculate FPS
        now = time.time()
        elapsed = now - self.last_fps_time
        if elapsed >= 1.0:
            self.fps = self.frames_since_last_check / elapsed
            self.frames_since_last_check = 0
            self.last_fps_time = now
            
            # Check for signal loss
            if self.fps < 1 and self.has_signal:
                self.no_signal_label.opacity = 1
                self.has_signal = False

        # Update status label
        self.status_label.text = self._get_status_text()
        
        # Update FPS label
        if self.ff.is_running():
            self.fps_label.text = f"{self.fps:.0f} FPS"
        else:
            self.fps_label.text = "...waiting"
        
        # Update CPU metrics (bottom corners)
        self.cpu_temp_label.text = self._get_cpu_temp()
        self.cpu_usage_label.text = self._get_cpu_usage()
        
        # Check screen sleep timeout
        self._check_screen_sleep()

    def _record_activity(self):
        """Record user/network activity to reset sleep timer"""
        self.last_activity_time = time.time()

    def _on_stream_start(self):
        """Called when streaming starts - wake screen and record activity"""
        self._record_activity()
        if self.screen_asleep:
            self._wake_screen()

    def _check_screen_sleep(self):
        """Check if screen should sleep due to inactivity"""
        if self.screen_asleep:
            return
        
        # Don't sleep if streaming
        if self.ff.is_running():
            self._record_activity()
            return
        
        # Check timeout
        idle_time = time.time() - self.last_activity_time
        if idle_time >= SCREEN_SLEEP_TIMEOUT:
            self._sleep_screen()

    def _sleep_screen(self):
        """Turn off the display to save power"""
        if self.screen_asleep:
            return
        
        self.screen_asleep = True
        print("Screen sleeping due to inactivity")
        
        # Turn off display using xset (works on Pi with X11)
        try:
            subprocess.run(['xset', 'dpms', 'force', 'off'], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Failed to sleep screen: {e}")

    def _wake_screen(self):
        """Turn on the display"""
        if not self.screen_asleep:
            return
        
        self.screen_asleep = False
        self.last_activity_time = time.time()
        print("Screen waking up")
        
        # Turn on display using xset
        try:
            subprocess.run(['xset', 'dpms', 'force', 'on'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Failed to wake screen: {e}")


class TouchStreamApp(App):
    def build(self):
        # Kiosk config
        Window.borderless = True
        Window.fullscreen = 'auto'
        Window.show_cursor = False
        Window.clearcolor = (0, 0, 0, 1)

        # Run GLib main loop in thread for GStreamer
        from gi.repository import GLib
        main_loop = GLib.MainLoop()
        threading.Thread(target=main_loop.run, daemon=True).start()

        return PreviewRoot()

    def on_stop(self):
        # Clean shutdown
        if hasattr(self.root, 'gst') and self.root.gst:
            self.root.gst.stop()
        if hasattr(self.root, 'ff') and self.root.ff:
            self.root.ff.stop()
        if hasattr(self.root, 'audio') and self.root.audio:
            self.root.audio.stop()


# ---- main ----
def main():
    ensure_config()
    start_discovery_server()
    threading.Thread(target=udp_beacon_thread, daemon=True).start()

    # Initialize GStreamer
    if GST_OK:
        Gst.init(None)

    TouchStreamApp().run()


if __name__ == '__main__':
    main()