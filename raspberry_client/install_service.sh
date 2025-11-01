#!/bin/bash
#
# PiCMS Player Service Installation Script
# This script installs and enables the PiCMS player service on Raspberry Pi
#

set -e

echo "================================================"
echo "PiCMS Player Service Installation"
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Configuration
INSTALL_DIR="/home/pi"
PLAYER_SCRIPT="$INSTALL_DIR/player.py"
CONFIG_FILE="$INSTALL_DIR/config.json"
SERVICE_FILE="/etc/systemd/system/picms_player.service"
VIDEOS_DIR="$INSTALL_DIR/videos"

# Create directories
echo "Creating directories..."
mkdir -p "$VIDEOS_DIR"
chown pi:pi "$VIDEOS_DIR"

# Copy player script if not exists
if [ ! -f "$PLAYER_SCRIPT" ]; then
    echo "ERROR: player.py not found in $INSTALL_DIR"
    echo "Please copy player.py to $INSTALL_DIR first"
    exit 1
fi

# Make player script executable
echo "Making player script executable..."
chmod +x "$PLAYER_SCRIPT"
chown pi:pi "$PLAYER_SCRIPT"

# Create default config if not exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default config file..."
    cat > "$CONFIG_FILE" << EOF
{
  "server_url": "http://192.168.0.100:5000",
  "device_id": null,
  "api_key": null,
  "device_name": "$(hostname)",
  "serial": "RPI-$(cat /sys/class/net/eth0/address | tr -d ':' | tr '[:lower:]' '[:upper:]')"
}
EOF
    chown pi:pi "$CONFIG_FILE"
fi

# Install dependencies
echo "Installing Python dependencies..."
apt-get update
apt-get install -y python3 python3-pip mpv

# Install Python packages
pip3 install requests

# Create systemd service file
echo "Creating systemd service..."
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=PiCMS Video Player
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $PLAYER_SCRIPT
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable picms_player.service

# Start service
echo "Starting service..."
systemctl start picms_player.service

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
echo "Service Status:"
systemctl status picms_player.service --no-pager
echo ""
echo "Useful Commands:"
echo "  Start service:   sudo systemctl start picms_player"
echo "  Stop service:    sudo systemctl stop picms_player"
echo "  Restart service: sudo systemctl restart picms_player"
echo "  View logs:       sudo journalctl -u picms_player -f"
echo "  Check status:    sudo systemctl status picms_player"
echo ""
echo "Configuration file: $CONFIG_FILE"
echo "Player script:      $PLAYER_SCRIPT"
echo "Videos directory:   $VIDEOS_DIR"
echo ""
echo "IMPORTANT: Edit $CONFIG_FILE to set your server URL!"
echo ""
