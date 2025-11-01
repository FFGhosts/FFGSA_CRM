# 🍓 Raspberry Pi Quick Start Guide

## One-Step Installation

Get your Raspberry Pi playing videos in **under 5 minutes**!

---

## Prerequisites

Before starting, ensure you have:

- ✓ Raspberry Pi (3B+ or newer recommended)
- ✓ Raspberry Pi OS installed (Bullseye or newer)
- ✓ Network connection (WiFi or Ethernet)
- ✓ Display connected via HDMI
- ✓ Access to your PiCMS server

---

## Installation Steps

### Step 1: Power On Your Raspberry Pi

1. Connect your Raspberry Pi to power
2. Connect HDMI display
3. Connect to your network (WiFi or Ethernet)
4. Boot into Raspberry Pi OS desktop

### Step 2: Open Terminal

Click the terminal icon in the menu bar or press `Ctrl+Alt+T`

### Step 3: Run the Installer

Copy and paste this command into the terminal:

```bash
curl -sL http://YOUR-SERVER-IP:5000/static/client/install.sh | bash
```

**Replace `YOUR-SERVER-IP` with your actual PiCMS server address!**

Examples:
```bash
# Local network
curl -sL http://192.168.1.100:5000/static/client/install.sh | bash

# Domain name
curl -sL http://picrm.example.com:5000/static/client/install.sh | bash
```

### Step 4: Answer the Prompts

The installer will ask you:

1. **Server URL**: Enter your PiCMS server address (e.g., `http://192.168.1.100:5000`)
2. **Device Name**: Press Enter to use hostname, or enter custom name (e.g., "Living Room Display")
3. **Device Serial**: Press Enter to auto-detect, or enter custom serial

### Step 5: Wait for Installation

The installer will automatically:
- Install all required software
- Download the player
- Register with your server
- Configure auto-start
- Optimize display settings
- Start playing content

**Installation takes 2-5 minutes depending on your internet speed.**

### Step 6: Verify Installation

After installation completes, you'll see:
```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              Installation Complete! ✓                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

Your device is now registered and will start playing assigned content within 5 minutes!

---

## Next Steps

### Assign Content to Your Device

1. Open web browser and go to your PiCMS server
2. Navigate to **Devices** page
3. Find your newly registered device
4. Click **Assign Videos** or **Assign Playlist**
5. Select content and save

### Configure Display Settings

1. Go to **Devices** page
2. Click the **⚙️ Configure** button next to your device
3. Adjust settings:
   - **Screen Rotation**: 0°, 90°, 180°, 270°
   - **Brightness**: 0-100%
   - **Resolution**: Match your display
   - **Audio Volume**: 0-100%

### Monitor Your Device

- **Real-time Status**: Go to **Dashboard** → **Real-time Dashboard**
- **Device History**: Click **History** button on Devices page
- **Screenshots**: Request screenshots via Configure page

---

## Troubleshooting

### Installation Fails

**Problem**: Cannot connect to server

**Solution**:
```bash
# Test server connectivity
ping YOUR-SERVER-IP

# Check if server is running
curl http://YOUR-SERVER-IP:5000/api/health
```

**Problem**: Permission denied

**Solution**:
```bash
# Run as pi user
whoami  # Should show "pi"

# If needed, switch to pi user
su - pi
```

### Device Not Playing Videos

**Problem**: Service not running

**Solution**:
```bash
# Check service status
sudo systemctl status picms-player

# Start service if stopped
sudo systemctl start picms-player

# View logs
tail -f /home/pi/picms/logs/player.log
```

**Problem**: No content assigned

**Solution**:
- Go to web interface
- Assign videos or playlists to device
- Wait up to 5 minutes for sync

### Display Issues

**Problem**: Screen is blank

**Solution**:
```bash
# Check if mpv is running
ps aux | grep mpv

# Test display manually
mpv /home/pi/picms/videos/*.mp4
```

**Problem**: Wrong rotation

**Solution**:
- Use web interface to configure rotation
- Or edit `/boot/config.txt`:
```bash
sudo nano /boot/config.txt
# Add: display_rotate=1  (for 90°)
# Add: display_rotate=2  (for 180°)
# Add: display_rotate=3  (for 270°)
```

---

## Useful Commands

### Service Management

```bash
# Check status
sudo systemctl status picms-player

# Restart service
sudo systemctl restart picms-player

# Stop service
sudo systemctl stop picms-player

# View logs (real-time)
sudo journalctl -u picms-player -f
```

### File Locations

```bash
# View configuration
cat /home/pi/picms/config.json

# View logs
tail -f /home/pi/picms/logs/player.log

# List downloaded videos
ls -lh /home/pi/picms/videos/

# Check disk space
df -h
```

### Network Diagnostics

```bash
# Check IP address
hostname -I

# Test server connection
ping YOUR-SERVER-IP

# Test API endpoint
curl http://YOUR-SERVER-IP:5000/api/health
```

---

## Advanced Configuration

### Static IP Address (Recommended)

Edit DHCP client configuration:
```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:
```
interface eth0
static ip_address=192.168.1.50/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

Reboot:
```bash
sudo reboot
```

### Disable WiFi Power Management

Prevent WiFi disconnections:
```bash
sudo nano /etc/rc.local
```

Add before `exit 0`:
```bash
/sbin/iwconfig wlan0 power off
```

### Increase GPU Memory (for better video performance)

```bash
sudo nano /boot/config.txt
```

Add:
```
gpu_mem=256
```

For Raspberry Pi 4:
```
gpu_mem=512
```

Reboot:
```bash
sudo reboot
```

### Auto-Login to Desktop

```bash
sudo raspi-config
```

Navigate to:
1. System Options
2. Boot / Auto Login
3. Desktop Autologin

---

## Uninstallation

If you need to remove the player:

```bash
# Stop and disable service
sudo systemctl stop picms-player
sudo systemctl disable picms-player

# Remove service file
sudo rm /etc/systemd/system/picms-player.service
sudo systemctl daemon-reload

# Remove installation directory
sudo rm -rf /home/pi/picms

# Remove autostart files
rm /home/pi/.config/autostart/unclutter.desktop
```

---

## Security Best Practices

1. **Change Default Password**:
```bash
passwd
# Enter new password
```

2. **Update System Regularly**:
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

3. **Enable Firewall** (optional):
```bash
sudo apt-get install ufw
sudo ufw allow ssh
sudo ufw enable
```

4. **Use SSH Keys** instead of passwords for remote access

---

## Performance Tips

### For Multiple Raspberry Pis

1. **Use device groups** for bulk management
2. **Set up static IP addresses** for each device
3. **Use wired Ethernet** when possible for reliability
4. **Label devices physically** with name/serial number
5. **Create naming convention**: `location-room-number` (e.g., `lobby-main-01`)

### Video Optimization

1. **Use H.264 codec** for best compatibility
2. **Keep resolution at or below** your display resolution
3. **Bitrate**: 2-5 Mbps for HD content
4. **Test videos** on one device before mass deployment

---

## Getting Help

### Check Logs First

```bash
# Player logs
tail -100 /home/pi/picms/logs/player.log

# System logs
sudo journalctl -u picms-player -n 100

# Check for errors
sudo journalctl -u picms-player | grep -i error
```

### Common Log Messages

✓ **"Device registered successfully"** - Device connected to server
✓ **"Syncing with server"** - Checking for new content
✓ **"Downloaded video"** - Content downloaded successfully
✓ **"Starting playback"** - Videos playing

⚠ **"Connection refused"** - Cannot reach server
⚠ **"Authentication failed"** - Invalid API key
⚠ **"No videos assigned"** - No content to play

### Support Checklist

Before asking for help, have ready:
- [ ] Device name and serial
- [ ] Output of `sudo systemctl status picms-player`
- [ ] Last 50 lines of logs: `tail -50 /home/pi/picms/logs/player.log`
- [ ] Network configuration: `hostname -I`
- [ ] Server connectivity test result: `curl YOUR-SERVER/api/health`

---

## Quick Reference Card

```
╔══════════════════════════════════════════════════════════╗
║                 PiCMS QUICK REFERENCE                    ║
╠══════════════════════════════════════════════════════════╣
║ Installation:                                            ║
║   curl -sL http://SERVER:5000/static/client/install.sh  ║
║         | bash                                           ║
║                                                          ║
║ Status:     sudo systemctl status picms-player          ║
║ Restart:    sudo systemctl restart picms-player         ║
║ Logs:       tail -f /home/pi/picms/logs/player.log      ║
║ Config:     nano /home/pi/picms/config.json             ║
║                                                          ║
║ Files:      /home/pi/picms/videos/                      ║
║ Service:    /etc/systemd/system/picms-player.service    ║
╚══════════════════════════════════════════════════════════╝
```

---

## That's It!

Your Raspberry Pi is now a powerful digital signage player managed by PiCMS!

**What's Next?**
- Try different video rotations
- Create playlists for scheduled content
- Set up device groups for multiple displays
- Use emergency broadcast for urgent messages
- Deploy system updates remotely

**Enjoy your PiCMS system!** 🎉
