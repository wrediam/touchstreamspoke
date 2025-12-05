# TouchStream Spoke - Quick Installation Guide

## One-Command Installation

For a fresh Raspberry Pi with Raspberry Pi OS installed:

```bash
cd ~ && git clone https://github.com/wrediam/touchstreamspoke.git && cd touchstreamspoke && sudo bash setup.sh
```


---

## Step-by-Step Installation

### 1. Prepare Your Raspberry Pi

- Flash Raspberry Pi OS (Bookworm or later) to SD card
- Boot and complete initial setup
- Connect to network (Ethernet or WiFi)
- Enable SSH if needed: `sudo raspi-config` → Interface Options → SSH

### 2. Install Git (if not already installed)

```bash
sudo apt-get update
sudo apt-get install -y git
```

### 3. Clone the Repository

```bash
cd /home/pbc
git clone https://github.com/YOUR_USERNAME/touchstreamspoke.git
cd touchstreamspoke
```

### 4. Run Setup Script

```bash
sudo bash setup.sh
```

The setup script will:
- ✅ Expand filesystem to fill SD card
- ✅ Install all dependencies
- ✅ Configure TC358743 capture card
- ✅ Set up TouchStream application
- ✅ Configure display scaling (smallest)
- ✅ Update boot configuration
- ✅ Install MHS35 screen driver
- 🔄 **Automatically reboot**

### 5. After Reboot

The TouchStream application will start automatically and display:
- Live HDMI preview on the 3.5" screen
- Device information overlay (tap to toggle)
- Settings button (top-left corner)

---

## Remote Installation via SSH

If you want to set up the device remotely:

```bash
# From your computer
ssh <user>@<raspberry-pi-ip>

# On the Raspberry Pi
cd ~
git clone https://github.com/wrediam/touchstreamspoke.git
cd touchstreamspoke
sudo bash setup.sh
```

The system will reboot automatically when complete.

---

## Troubleshooting Installation

### Git Clone Fails

```bash
# If you get SSL/certificate errors
git config --global http.sslVerify false
git clone https://github.com/wrediam/touchstreamspoke.git
```

### Permission Denied

```bash
# Make sure you're in your home directory
cd ~
# Or run with sudo if needed
sudo git clone https://github.com/wrediam/touchstreamspoke.git
sudo chown -R $USER:$USER touchstreamspoke
```

### Setup Script Fails

```bash
# Check the error message and try running individual sections
# View the setup script to see what failed
cat setup.sh
```

### Screen Doesn't Work After Reboot

```bash
# The MHS35 driver should install automatically
# If it doesn't, manually run:
cd ~/touchstreamspoke/LCD-show
sudo ./MHS35-show
```

---

## Updating an Existing Installation

```bash
cd ~/touchstreamspoke
git pull origin main
sudo systemctl restart touchstream  # If running as service
# Or simply reboot
sudo reboot
```

---

## Uninstallation

To remove TouchStream Spoke:

```bash
# Stop autostart
rm ~/.config/autostart/touchstream.desktop

# Remove systemd services
sudo systemctl disable tc358743-edid.service
sudo rm /etc/systemd/system/tc358743-edid.service

# Remove files
rm -rf ~/touchstreamspoke
rm ~/edid-1080p30.txt

# Revert screen driver (optional)
cd ~/LCD-show
sudo ./LCD-hdmi
```

---

## Next Steps

After installation:

1. **Configure Device:** Use the settings button or HTTP API to set device name and location
2. **Set Up Discovery App:** Follow the [Integration Guide](./docs/integration-guide.md)
3. **Adopt Device:** Send configuration via POST /adopt endpoint
4. **Start Streaming:** Device will stream to configured UDP destination

See the [Documentation](./docs/) for complete details.
