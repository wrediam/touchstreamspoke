#!/bin/bash
# TouchStream Spoke Setup Script
# Copyright (c) 2025 Will Reeves and TouchStream Contributors
# Licensed under the MIT License - see LICENSE file for details

set -e

# Detect home directory and script location
# If running as sudo, get the actual user's home directory
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
    USER_HOME=$(eval echo ~$SUDO_USER)
else
    ACTUAL_USER="$(whoami)"
    USER_HOME="$HOME"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting TouchStream Setup..."
echo "Actual user: $ACTUAL_USER"
echo "Home directory: $USER_HOME"
echo "Script directory: $SCRIPT_DIR"

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
cat <<EOF > $USER_HOME/edid-1080p30.txt
00 FF FF FF FF FF FF 00 10 AC 00 00 00 00 00 00
01 20 01 03 80 00 00 78 0A EE 91 A3 54 4C 99 26
0F 50 54 00 00 00 01 01 01 01 01 01 01 01 01 01
01 01 01 01 01 01 1A 36 80 A0 70 38 1F 40 30 20
35 00 00 00 00 00 00 1E 00 00 00 FC 00 31 30 38
30 70 33 30 0A 20 20 20 20 20 00 00 00 FD 00 17
4B 0F 51 0F 00 0A 20 20 20 20 20 20 00 00 00 FF
00 30 30 30 30 30 30 30 30 0A 20 20 20 20 00 4E
EOF
chown $ACTUAL_USER:$ACTUAL_USER $USER_HOME/edid-1080p30.txt

echo "Creating systemd service for EDID..."
sudo tee /etc/systemd/system/tc358743-edid.service > /dev/null <<EOF
[Unit]
Description=Set TC358743 EDID and timings
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/bin/v4l2-ctl -d /dev/v4l-subdev0 --set-edid=file=$USER_HOME/edid-1080p30.txt
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
chmod +x $SCRIPT_DIR/touchstream-spoke.py

echo "Creating autostart .desktop file..."
mkdir -p $USER_HOME/.config/autostart
cat <<EOF > $USER_HOME/.config/autostart/touchstream.desktop
[Desktop Entry]
Type=Application
Name=TouchStream
Exec=/usr/bin/python3 $SCRIPT_DIR/touchstream-spoke.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=TouchStream Video Preview
EOF
chown -R $ACTUAL_USER:$ACTUAL_USER $USER_HOME/.config/autostart

# Set display scaling to smallest (for better screen real estate)
echo "Setting display scaling to smallest..."
mkdir -p $USER_HOME/.config/lxsession/LXDE-pi
cat <<EOF > $USER_HOME/.config/lxsession/LXDE-pi/desktop.conf
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
chown -R $ACTUAL_USER:$ACTUAL_USER $USER_HOME/.config/lxsession

# Also set DPI scaling for smaller UI elements
mkdir -p $USER_HOME/.config/autostart
cat <<EOF > $USER_HOME/.config/autostart/display-scaling.desktop
[Desktop Entry]
Type=Application
Name=Display Scaling
Exec=xrandr --dpi 96
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
Comment=Set display DPI for smaller UI
EOF
chown -R $ACTUAL_USER:$ACTUAL_USER $USER_HOME/.config/autostart

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

# 5. Create automatic post-reboot completion script and service
echo "Creating automatic post-reboot completion service..."

# Create the completion script
cat > $SCRIPT_DIR/complete-setup.sh << 'EOFSCRIPT'
#!/bin/bash
# Complete TouchStream setup after screen driver installation
set -e

echo "Completing TouchStream setup after screen driver installation..."

# Add TC358743 configuration to config.txt
echo "Adding TC358743 HDMI capture card configuration..."
bash -c 'cat >> /boot/firmware/config.txt << EOF

# TC358743 HDMI Capture Card Configuration
avoid_warnings=1
camera_auto_detect=0
dtoverlay=tc358743,4lane=1,link-frequency=297000000
dtoverlay=tc358743-audio
EOF'

echo "✓ TC358743 configuration added"

# Disable this service so it only runs once
systemctl disable touchstream-complete-setup.service

echo "Setup complete! Rebooting to load capture card drivers..."
sleep 3
reboot
EOFSCRIPT

chmod +x $SCRIPT_DIR/complete-setup.sh
chown $ACTUAL_USER:$ACTUAL_USER $SCRIPT_DIR/complete-setup.sh

# Create systemd service to run completion script on next boot
sudo tee /etc/systemd/system/touchstream-complete-setup.service > /dev/null <<EOF
[Unit]
Description=TouchStream Setup Completion (runs once after screen driver)
After=multi-user.target
ConditionPathExists=$SCRIPT_DIR/complete-setup.sh

[Service]
Type=oneshot
ExecStart=/bin/bash $SCRIPT_DIR/complete-setup.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable touchstream-complete-setup.service

echo ""
echo "=========================================="
echo "Automatic Two-Stage Installation"
echo "=========================================="
echo "Stage 1 (current): Installing screen driver - system will reboot"
echo "Stage 2 (automatic): After reboot, setup will complete automatically and reboot again"
echo "Stage 3 (final): TouchStream will be ready!"
echo "=========================================="
echo ""
sleep 5

# 6. Install Screen Driver (Last step - reboots)
echo "Installing MHS35 screen driver..."
cd $USER_HOME
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
