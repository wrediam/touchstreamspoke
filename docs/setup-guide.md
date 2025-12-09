# Setup Guide - Detailed Breakdown

This document provides a comprehensive explanation of what the `setup.sh` script does during installation.

## Overview

The setup script configures a Raspberry Pi 4/5 to function as a TouchStream Spoke device with:
- TC358743 HDMI-to-CSI capture card support
- MHS35 3.5" touchscreen display
- Automatic video preview on boot
- Network-based configuration capability

## Setup Process (Step-by-Step)

### 1. Dependency Installation

```bash
sudo apt-get update
sudo apt-get install -y python3-kivy python3-gi python3-gst-1.0 gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-libav v4l-utils ffmpeg
```

**What it does:**
- **python3-kivy**: GUI framework for the touchscreen interface
- **python3-gi & python3-gst-1.0**: GStreamer Python bindings for video processing
- **gstreamer1.0-***: Complete GStreamer multimedia framework with all codec support
- **v4l-utils**: Video4Linux utilities for camera control
- **ffmpeg**: Video encoding/decoding library

### 2. TC358743 EDID Configuration

**Purpose:** Configure the HDMI capture card to accept 1080p30 input signals.

**EDID File Creation:**
Creates `~/edid-1080p30.txt` with binary EDID data that advertises:
- Resolution: 1920x1080 @ 30Hz
- Timing: CVT standard
- Audio: Supported (CEA extension block with 2-channel LPCM)

**Systemd Service:**
Creates `/etc/systemd/system/tc358743-edid.service` that runs on boot:

```bash
v4l2-ctl -d /dev/v4l-subdev0 --set-edid=file=~/edid-1080p30.txt
sleep 2
v4l2-ctl -d /dev/video0 --set-dv-bt-timings query
```

**What it does:**
1. Loads EDID into the TC358743 chip
2. Waits for signal detection
3. Queries and sets the detected video timings

### 3. TouchStream Application Setup

**Application Permissions:**
```bash
chmod +x ~/touchstreamspoke/touchstream-spoke.py
```

**Autostart Configuration:**
Creates `~/.config/autostart/touchstream.desktop`:
- Launches `touchstream-spoke.py` on user login
- Runs in graphical environment (X11/Wayland)
- No user interaction required

### 4. Boot Configuration Updates

#### Config.txt Modifications

**File:** `/boot/firmware/config.txt`

**Changes:**
1. `avoid_warnings=1` - Suppresses boot warning overlays
2. `camera_auto_detect=0` - Disables automatic camera detection (prevents conflicts)
3. `dtoverlay=tc358743,4lane=1,link-frequency=297000000` - Enables 4-lane CSI capture at 1080p30
4. `dtoverlay=tc358743-audio` - Enables audio capture from HDMI

#### Cmdline.txt Modifications

**File:** `/boot/firmware/cmdline.txt`

**Changes:**
Adds `cma=512M` to the kernel command line.

**What it does:**
- **CMA (Contiguous Memory Allocator)**: Reserves 512MB of RAM for GPU/video operations
- **Why 512MB?**: Required for smooth 1080p video processing and buffering
- **Placement**: Must be on the first line, space-separated from other parameters

**Example cmdline.txt:**
```
console=serial0,115200 console=tty1 root=PARTUUID=... rootfstype=ext4 ... cma=512M
```

### 5. Nightly Reboot Schedule

A cron job is configured to reboot the device at 1:00 AM local time daily:

```bash
0 1 * * * /sbin/reboot # TouchStream nightly reboot
```

**Purpose:**
- Ensures system stability over long periods
- Clears any accumulated memory issues
- Applies pending system updates

### 6. Screen Driver Installation

**Driver:** MHS35 (3.5" SPI touchscreen)

**Process:**
1. Clones `https://github.com/goodtft/LCD-show.git`
2. Runs `./MHS35-show` which:
   - Installs framebuffer drivers
   - Configures SPI interface
   - Sets display resolution (480x320)
   - Configures touchscreen calibration
   - **Automatically reboots the system**

**Post-Reboot State:**
- Display active and calibrated
- Touch input functional
- TouchStream app auto-starts
- Capture card ready for input
- Audio monitoring active with local playback
- Screen sleep enabled (3 hours timeout)

## Hardware Requirements

- **Raspberry Pi 4 or 5** (4GB+ RAM recommended)
- **TC358743 HDMI-to-CSI capture card** (Auvidea B101/B102 or compatible)
- **MHS35 3.5" touchscreen** (480x320 SPI display)
- **MicroSD card** (16GB+ recommended)
- **Power supply** (5V 3A minimum)

## Network Requirements

- **Ethernet or WiFi** configured before running setup
- **Internet access** required during setup for package downloads
- **Static IP recommended** for reliable discovery

## Updating an Existing Installation

The `setup.sh` script detects if TouchStream is already installed and offers two options:

1.  **Reinstall:** Runs the full setup process again. Useful if the system configuration is broken or dependencies need to be repaired.
2.  **Update:** Pulls the latest code from git, stops the existing process, and prompts to reboot or start the application manually. This preserves system configurations.

To use this feature, simply run the setup script again:
```bash
sudo bash setup.sh
```

## Post-Setup Verification

After reboot, verify:

1. **Display working:**
   ```bash
   DISPLAY=:0 xrandr
   # Should show 480x320 resolution
   ```

2. **Capture card detected:**
   ```bash
   v4l2-ctl --list-devices
   # Should show /dev/video0
   ```

3. **Video signal:**
   ```bash
   v4l2-ctl -d /dev/video0 --query-dv-timings
   # Should show 1920x1080p30 if HDMI source connected
   ```

4. **TouchStream running:**
   ```bash
   ps aux | grep touchstream-spoke.py
   # Should show python process
   ```

## Troubleshooting

### No video signal
- Check HDMI cable connection
- Verify source outputs 1080p30
- Restart EDID service: `sudo systemctl restart tc358743-edid.service`

### Display not working
- Re-run: `cd ~/LCD-show && sudo ./MHS35-show`
- Check SPI enabled: `lsmod | grep spi`

### App not auto-starting
- Check desktop file: `cat ~/.config/autostart/touchstream.desktop`
- Verify permissions: `ls -l ~/touchstream-spoke.py`
- Check logs: `journalctl --user -u touchstream`

## Manual Configuration

If you need to modify settings after setup:

**Change CMA allocation:**
```bash
sudo nano /boot/firmware/cmdline.txt
# Modify cma=512M to desired value
sudo reboot
```

**Change capture resolution:**
```bash
sudo nano /boot/firmware/config.txt
# Modify link-frequency parameter
# 297000000 = 1080p30
# 594000000 = 1080p60 (if supported)
```

**Disable autostart:**
```bash
rm ~/.config/autostart/touchstream.desktop
```
