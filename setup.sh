#!/bin/bash
# TouchStream Spoke Setup Script
# Copyright (c) 2025 Will Reeves and TouchStream Contributors
# Licensed under the MIT License - see LICENSE file for details

# set the version number
VERSION="1.2"

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
echo "Version: $VERSION"

# Check for existing installation
if [ -f "$SCRIPT_DIR/touchstream-spoke.py" ]; then
    echo ""
    echo "Existing installation detected."
    echo ""
    echo "What would you like to do?"
    echo "1) Reinstall (Run full setup again)"
    echo "2) Update Code (git pull and restart service)"
    echo "3) Exit"
    echo ""
    read -p "Enter choice [1-3]: " CHOICE

    case $CHOICE in
        1)
            echo "Proceeding with full reinstallation..."
            ;;
        2)
            echo "Updating code..."
            # Pull latest changes
            git pull
            
            # Kill existing instances
            echo "Stopping running instances..."
            pkill -f touchstream-spoke.py || true
            
            # Restart application
            echo ""
            echo "Update complete. Restarting application..."
            echo "Note: If the application does not appear, you may need to reboot manually."
            
            # Restart as the actual user on the display
            su - $ACTUAL_USER -c "export DISPLAY=:0 && nohup python3 $SCRIPT_DIR/touchstream-spoke.py > /dev/null 2>&1 &"
            
            exit 0
            ;;
        3)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo "Invalid choice. Exiting."
            exit 1
            ;;
    esac
fi

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

# 2. Setup 1080p30 EDID for capture card (with CEA extension for audio support)
echo "Setting up TC358743 EDID service..."
cat <<EOF > $USER_HOME/edid-1080p30.txt
00 FF FF FF FF FF FF 00 52 62 88 88 00 88 88 88
FF 1C 01 03 80 50 2D 78 0A 0D C9 A0 57 47 98 27
12 48 4C 21 08 00 01 01 01 01 01 01 01 01 01 01
01 01 01 01 01 01 8C 1B 80 A0 70 38 1F 40 30 20
35 00 00 00 00 00 00 1E 00 00 00 FC 00 54 6F 75
63 68 53 74 72 65 61 6D 0A 20 00 00 00 FD 00 0F
1E 11 44 0F 00 0A 20 20 20 20 20 20 00 00 00 FF
00 54 53 50 4F 4B 45 30 30 31 0A 20 20 20 01 B9
02 03 1D F1 4A 90 04 03 01 14 12 05 1F 10 13 23
09 07 07 83 01 00 00 65 03 0C 00 10 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 8F
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
ExecStart=/bin/sleep 1
ExecStart=-/usr/bin/v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=UYVY
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

# 4. Setup nightly reboot at 1am local time
echo "Setting up nightly reboot cron job..."
(crontab -l 2>/dev/null | grep -v "reboot.*nightly"; echo "0 1 * * * /sbin/reboot # TouchStream nightly reboot") | sudo crontab -

# 5. Note: config.txt and cmdline.txt updates happen AFTER screen driver installation
# This is handled by the automatic completion service to prevent the screen driver from overwriting our changes
echo "Boot configuration will be updated after screen driver installation..."

# 6. Create automatic post-reboot completion script and service
echo "Creating automatic post-reboot completion service..."

# Create the completion script
cat > $SCRIPT_DIR/complete-setup.sh << 'EOFSCRIPT'
#!/bin/bash
# Complete TouchStream setup after screen driver installation
set -e

echo "Completing TouchStream setup after screen driver installation..."

# Update CMA to 512MB in cmdline.txt (if not already set)
echo "Updating CMA in /boot/firmware/cmdline.txt..."
CMDLINE_FILE="/boot/firmware/cmdline.txt"
if ! grep -q "cma=512M" "$CMDLINE_FILE"; then
    sed -i '1s/$/ cma=512M/' "$CMDLINE_FILE"
    echo "✓ Added cma=512M to cmdline.txt"
else
    echo "✓ cma=512M already present in cmdline.txt"
fi

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

echo ""
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
