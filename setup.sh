#!/bin/bash
# TouchStream Spoke Setup Script
# Copyright (c) 2025 Will Reeves and TouchStream Contributors
# Licensed under the MIT License - see LICENSE file for details

set -e

echo "Starting TouchStream Setup..."

# 0. Expand filesystem to fill SD card
echo "Expanding filesystem to fill disk..."
sudo raspi-config --expand-rootfs
echo "Filesystem will expand on next reboot"

# 1. Install Dependencies
echo "Installing dependencies..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3-kivy python3-gi python3-gst-1.0 gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-libav v4l-utils ffmpeg

# 2. Setup 1080p30 EDID for capture card
echo "Setting up TC358743 EDID service..."
cat <<EOF > /home/pbc/edid-1080p30.txt
00 FF FF FF FF FF FF 00 10 AC 00 00 00 00 00 00
01 20 01 03 80 00 00 78 0A EE 91 A3 54 4C 99 26
0F 50 54 00 00 00 01 01 01 01 01 01 01 01 01 01
01 01 01 01 01 01 1A 36 80 A0 70 38 1F 40 30 20
35 00 00 00 00 00 00 1E 00 00 00 FC 00 31 30 38
30 70 33 30 0A 20 20 20 20 20 00 00 00 FD 00 17
4B 0F 51 0F 00 0A 20 20 20 20 20 20 00 00 00 FF
00 30 30 30 30 30 30 30 30 0A 20 20 20 20 00 4E
EOF
chown pbc:pbc /home/pbc/edid-1080p30.txt

echo "Creating systemd service for EDID..."
sudo tee /etc/systemd/system/tc358743-edid.service > /dev/null <<EOF
[Unit]
Description=Set TC358743 EDID and timings
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/v4l2-ctl -d /dev/v4l-subdev0 --set-edid=file=/home/pbc/edid-1080p30.txt
ExecStart=/bin/sleep 2
ExecStart=-/usr/bin/v4l2-ctl -d /dev/video0 --set-dv-bt-timings query
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable tc358743-edid.service

# 3. Setup TouchStream application
echo "Setting up TouchStream application..."
chmod +x /home/pbc/touchstream-spoke.py

echo "Creating autostart .desktop file..."
mkdir -p /home/pbc/.config/autostart
cat <<EOF > /home/pbc/.config/autostart/touchstream.desktop
[Desktop Entry]
Type=Application
Name=TouchStream
Exec=/usr/bin/python3 /home/pbc/touchstream-spoke.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=TouchStream Video Preview
EOF
chown -R pbc:pbc /home/pbc/.config/autostart

# Set display scaling to smallest (for better screen real estate)
echo "Setting display scaling to smallest..."
mkdir -p /home/pbc/.config/lxsession/LXDE-pi
cat <<EOF > /home/pbc/.config/lxsession/LXDE-pi/desktop.conf
[GTK]
sGtk/FontName=Sans 8
iGtk/ToolbarStyle=3
iGtk/ToolbarIconSize=1
iGtk/ButtonImages=0
iGtk/MenuImages=0
sGtk/CursorThemeName=PiXflat
iXft/Antialias=1
sXft/HintStyle=hintfull
iNet/EnableEventSounds=0
iNet/EnableInputFeedbackSounds=0
sGtk/ColorScheme=
EOF
chown -R pbc:pbc /home/pbc/.config/lxsession

# Also set DPI scaling for smaller UI elements
mkdir -p /home/pbc/.config/autostart
cat <<EOF > /home/pbc/.config/autostart/display-scaling.desktop
[Desktop Entry]
Type=Application
Name=Display Scaling
Exec=xrandr --dpi 96
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
Comment=Set display DPI for smaller UI
EOF
chown -R pbc:pbc /home/pbc/.config/autostart

# 4. Update config.txt
echo "Updating /boot/firmware/config.txt..."
CONFIG_FILE="/boot/firmware/config.txt"

# Function to safely update config
update_config() {
    key="$1"
    value="$2"
    if grep -q "^$key" "$CONFIG_FILE"; then
        sudo sed -i "s|^$key.*|$key=$value|" "$CONFIG_FILE"
    else
        echo "$key=$value" | sudo tee -a "$CONFIG_FILE" > /dev/null
    fi
}

update_config "avoid_warnings" "1"
update_config "camera_auto_detect" "0"

# Add capture card overlays if missing
if ! grep -q "dtoverlay=tc358743,4lane=1" "$CONFIG_FILE"; then
    echo "dtoverlay=tc358743,4lane=1,link-frequency=297000000" | sudo tee -a "$CONFIG_FILE" > /dev/null
fi
if ! grep -q "dtoverlay=tc358743-audio" "$CONFIG_FILE"; then
    echo "dtoverlay=tc358743-audio" | sudo tee -a "$CONFIG_FILE" > /dev/null
fi

# Update CMA to 512MB in cmdline.txt
echo "Updating CMA in /boot/firmware/cmdline.txt..."
CMDLINE_FILE="/boot/firmware/cmdline.txt"
if ! grep -q "cma=512M" "$CMDLINE_FILE"; then
    # Add cma=512M to the end of the first line
    sudo sed -i '1s/$/ cma=512M/' "$CMDLINE_FILE"
    echo "Added cma=512M to cmdline.txt"
else
    echo "cma=512M already present in cmdline.txt"
fi

# 5. Install Screen Driver (Last step - reboots)
echo "Installing MHS35 screen driver..."
cd /home/pbc
if [ -d "LCD-show" ]; then
    echo "Removing invalid LCD-show directory..."
    sudo rm -rf LCD-show
fi

echo "Cloning LCD-show repository..."
git clone https://github.com/goodtft/LCD-show.git
chmod -R 755 LCD-show
cd LCD-show

echo "Running MHS35-show (System will reboot!)..."
sudo ./MHS35-show
