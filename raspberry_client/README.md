# PiCMS Raspberry Pi Client

This directory contains the client software that runs on Raspberry Pi devices to download and play videos from the PiCMS server.

## 🚀 **ONE-STEP INSTALLATION** (Recommended)

The easiest way to install PiCMS player on your Raspberry Pi:

```bash
curl -sL http://YOUR-SERVER:5000/static/client/install.sh | bash
```

That's it! The installer will:
- ✓ Install all dependencies automatically
- ✓ Download player software
- ✓ Register device with server
- ✓ Configure auto-start on boot
- ✓ Optimize for digital signage
- ✓ Start playing content immediately

**No manual configuration needed!**

---

## Files

- `player.py` - Main Python script that handles video sync and playback
- `config.json` - Configuration file (created automatically)
- `install_service.sh` - Installation script for systemd service
- `picms_player.service` - Systemd service file

## Installation

### 1. Prerequisites

Make sure your Raspberry Pi has:
- Raspberry Pi OS (Raspbian)
- Internet connectivity
- Python 3.7+

### 2. Quick Install

```bash
# Copy files to Raspberry Pi
scp player.py pi@raspberrypi.local:/home/pi/
scp config.json pi@raspberrypi.local:/home/pi/
scp install_service.sh pi@raspberrypi.local:/home/pi/

# SSH into Raspberry Pi
ssh pi@raspberrypi.local

# Run installation script
cd /home/pi
chmod +x install_service.sh
sudo ./install_service.sh
```

### 3. Manual Installation

If you prefer manual installation:

```bash
# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip mpv

# Install Python packages
pip3 install requests

# Make player executable
chmod +x /home/pi/player.py

# Edit configuration
nano /home/pi/config.json
# Set your server_url to point to your PiCMS server

# Copy service file
sudo cp picms_player.service /etc/systemd/system/

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable picms_player.service
sudo systemctl start picms_player.service
```

## Configuration

Edit `/home/pi/config.json`:

```json
{
  "server_url": "http://YOUR_SERVER_IP:5000",
  "device_id": null,
  "api_key": null,
  "device_name": "Pi Player 1",
  "serial": "RPI-001"
}
```

- `server_url` - URL of your PiCMS server
- `device_id` - Assigned automatically after registration
- `api_key` - Assigned automatically after registration
- `device_name` - Friendly name for your device
- `serial` - Unique serial number (auto-generated if not set)

## Service Management

```bash
# Start service
sudo systemctl start picms_player

# Stop service
sudo systemctl stop picms_player

# Restart service
sudo systemctl restart picms_player

# Check status
sudo systemctl status picms_player

# View logs
sudo journalctl -u picms_player -f

# View player log file
tail -f /home/pi/player.log
```

## How It Works

1. **Registration**: On first run, the player registers with the CMS server and receives an API key
2. **Sync**: Every 5 minutes, it checks for assigned videos
3. **Download**: Downloads any new videos to `/home/pi/videos/`
4. **Playback**: Plays videos in fullscreen loop using mpv
5. **Heartbeat**: Sends status updates every 60 seconds

## Troubleshooting

### Player won't start
```bash
# Check service status
sudo systemctl status picms_player

# Check logs
sudo journalctl -u picms_player -n 50
```

### Cannot connect to server
- Verify server URL in config.json
- Check network connectivity: `ping YOUR_SERVER_IP`
- Ensure firewall allows connections

### Videos not playing
- Verify mpv is installed: `mpv --version`
- Check video files exist: `ls -lh /home/pi/videos/`
- Test manual playback: `mpv /home/pi/videos/video.mp4`

### High CPU usage
- Check video resolution and codec
- Consider using hardware acceleration

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop picms_player
sudo systemctl disable picms_player

# Remove service file
sudo rm /etc/systemd/system/picms_player.service

# Reload systemd
sudo systemctl daemon-reload

# Remove player files
rm /home/pi/player.py
rm /home/pi/config.json
rm -rf /home/pi/videos/
```

## Requirements

- Python 3.7+
- requests library
- mpv media player
- Network connectivity
