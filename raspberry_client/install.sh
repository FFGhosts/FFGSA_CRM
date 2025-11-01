#!/bin/bash
###############################################################################
# PiCMS Player - One-Step Installation Script
# Automatically installs and configures the PiCMS video player on Raspberry Pi
###############################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/home/pi/picms"
SERVICE_NAME="picms-player"
PYTHON_VERSION="3"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║         PiCMS Player - One-Step Installation             ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as pi user
if [ "$USER" != "pi" ]; then
    echo -e "${YELLOW}Warning: This script is designed to run as 'pi' user${NC}"
    echo -e "${YELLOW}Current user: $USER${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "\n${GREEN}Step 1: Gathering Configuration${NC}"
echo "=================================================="

# Get server URL
read -p "Enter PiCMS Server URL (e.g., http://192.168.1.100:5000): " SERVER_URL
if [ -z "$SERVER_URL" ]; then
    echo -e "${RED}Error: Server URL is required${NC}"
    exit 1
fi

# Get device name
HOSTNAME=$(hostname)
read -p "Enter Device Name [default: $HOSTNAME]: " DEVICE_NAME
DEVICE_NAME=${DEVICE_NAME:-$HOSTNAME}

# Get device serial
SERIAL=$(cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2)
if [ -z "$SERIAL" ]; then
    # Fallback to MAC address
    SERIAL="RPI-$(cat /sys/class/net/eth0/address | tr -d ':')"
fi
read -p "Enter Device Serial [default: $SERIAL]: " DEVICE_SERIAL
DEVICE_SERIAL=${DEVICE_SERIAL:-$SERIAL}

echo -e "\n${GREEN}Step 2: Installing System Dependencies${NC}"
echo "=================================================="

# Update package list
echo "Updating package list..."
sudo apt-get update -qq

# Install required packages
echo "Installing required packages..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    mpv \
    scrot \
    git \
    curl

echo -e "${GREEN}✓ System dependencies installed${NC}"

echo -e "\n${GREEN}Step 3: Installing Python Dependencies${NC}"
echo "=================================================="

# Install Python packages
echo "Installing Python packages..."
sudo pip3 install --quiet \
    requests \
    Pillow

echo -e "${GREEN}✓ Python dependencies installed${NC}"

echo -e "\n${GREEN}Step 4: Creating Installation Directory${NC}"
echo "=================================================="

# Create installation directory
sudo mkdir -p $INSTALL_DIR
sudo chown -R pi:pi $INSTALL_DIR

# Create subdirectories
mkdir -p $INSTALL_DIR/videos
mkdir -p $INSTALL_DIR/logs

echo -e "${GREEN}✓ Directory structure created${NC}"

echo -e "\n${GREEN}Step 5: Downloading Player Software${NC}"
echo "=================================================="

# Download player.py from server or use local copy
echo "Downloading player.py..."
if curl -f -s -o $INSTALL_DIR/player.py "$SERVER_URL/static/client/player.py" 2>/dev/null; then
    echo -e "${GREEN}✓ Downloaded from server${NC}"
else
    echo -e "${YELLOW}Warning: Could not download from server${NC}"
    echo "Please ensure player.py is in $INSTALL_DIR/"
    
    # Create a basic player.py if not exists
    if [ ! -f "$INSTALL_DIR/player.py" ]; then
        cat > $INSTALL_DIR/player.py << 'PLAYER_EOF'
#!/usr/bin/env python3
"""
PiCMS Video Player Client for Raspberry Pi
This is a placeholder - replace with the actual player.py from the repository
"""
import sys
print("PiCMS Player - Please replace this file with the actual player.py")
sys.exit(1)
PLAYER_EOF
        chmod +x $INSTALL_DIR/player.py
        echo -e "${YELLOW}Created placeholder player.py - needs to be replaced${NC}"
    fi
fi

chmod +x $INSTALL_DIR/player.py

echo -e "\n${GREEN}Step 6: Creating Configuration${NC}"
echo "=================================================="

# Create config.json
cat > $INSTALL_DIR/config.json << EOF
{
  "server_url": "$SERVER_URL",
  "device_id": null,
  "api_key": null,
  "device_name": "$DEVICE_NAME",
  "serial": "$DEVICE_SERIAL"
}
EOF

echo -e "${GREEN}✓ Configuration file created${NC}"

echo -e "\n${GREEN}Step 7: Registering Device with Server${NC}"
echo "=================================================="

# Try to register device
echo "Attempting to register device..."
RESPONSE=$(curl -s -X POST "$SERVER_URL/api/device/register" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$DEVICE_NAME\",\"serial\":\"$DEVICE_SERIAL\",\"ip_address\":\"$(hostname -I | awk '{print $1}')\"}")

if echo "$RESPONSE" | grep -q "device_id"; then
    # Extract device_id and api_key from response
    DEVICE_ID=$(echo "$RESPONSE" | grep -o '"device_id":[0-9]*' | cut -d':' -f2)
    API_KEY=$(echo "$RESPONSE" | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)
    
    # Update config.json with device_id and api_key
    python3 << PYTHON_EOF
import json
with open('$INSTALL_DIR/config.json', 'r') as f:
    config = json.load(f)
config['device_id'] = $DEVICE_ID
config['api_key'] = '$API_KEY'
with open('$INSTALL_DIR/config.json', 'w') as f:
    json.dump(config, f, indent=2)
PYTHON_EOF
    
    echo -e "${GREEN}✓ Device registered successfully${NC}"
    echo -e "   Device ID: ${BLUE}$DEVICE_ID${NC}"
    echo -e "   API Key: ${BLUE}${API_KEY:0:20}...${NC}"
else
    echo -e "${YELLOW}⚠ Could not auto-register device${NC}"
    echo -e "${YELLOW}Please register manually via the web interface${NC}"
    echo -e "${YELLOW}Then update config.json with device_id and api_key${NC}"
fi

echo -e "\n${GREEN}Step 8: Creating Systemd Service${NC}"
echo "=================================================="

# Create systemd service file
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=PiCMS Video Player
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/player.py
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/player.log
StandardError=append:$INSTALL_DIR/logs/player.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

echo -e "${GREEN}✓ Systemd service created${NC}"

echo -e "\n${GREEN}Step 9: Configuring Auto-Start${NC}"
echo "=================================================="

# Enable service to start on boot
sudo systemctl enable ${SERVICE_NAME}.service

echo -e "${GREEN}✓ Service enabled for auto-start${NC}"

echo -e "\n${GREEN}Step 10: Optimizing Raspberry Pi Settings${NC}"
echo "=================================================="

# Disable screen blanking
if ! grep -q "xserver-command" /etc/lightdm/lightdm.conf 2>/dev/null; then
    echo "Disabling screen blanking..."
    sudo mkdir -p /etc/lightdm/lightdm.conf.d
    sudo tee /etc/lightdm/lightdm.conf.d/01-disable-screensaver.conf > /dev/null << 'EOF'
[Seat:*]
xserver-command=X -s 0 -dpms
EOF
fi

# Disable cursor
if command -v unclutter &> /dev/null; then
    echo "unclutter already installed"
else
    echo "Installing unclutter to hide mouse cursor..."
    sudo apt-get install -y unclutter
fi

echo -e "${GREEN}✓ Raspberry Pi optimized for digital signage${NC}"

echo -e "\n${GREEN}Step 11: Starting Service${NC}"
echo "=================================================="

# Start the service
sudo systemctl start ${SERVICE_NAME}.service

# Wait a moment for service to start
sleep 2

# Check service status
if sudo systemctl is-active --quiet ${SERVICE_NAME}.service; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${YELLOW}⚠ Service may have issues starting${NC}"
    echo "Check logs: sudo journalctl -u ${SERVICE_NAME} -f"
fi

echo -e "\n${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║              Installation Complete! ✓                     ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "\n${GREEN}Installation Summary:${NC}"
echo "=================================================="
echo -e "  Installation Directory: ${BLUE}$INSTALL_DIR${NC}"
echo -e "  Configuration File: ${BLUE}$INSTALL_DIR/config.json${NC}"
echo -e "  Log File: ${BLUE}$INSTALL_DIR/logs/player.log${NC}"
echo -e "  Service Name: ${BLUE}$SERVICE_NAME${NC}"
echo -e "  Device Name: ${BLUE}$DEVICE_NAME${NC}"
echo -e "  Device Serial: ${BLUE}$DEVICE_SERIAL${NC}"

echo -e "\n${GREEN}Useful Commands:${NC}"
echo "=================================================="
echo -e "  View logs:         ${BLUE}tail -f $INSTALL_DIR/logs/player.log${NC}"
echo -e "  Service status:    ${BLUE}sudo systemctl status $SERVICE_NAME${NC}"
echo -e "  Restart service:   ${BLUE}sudo systemctl restart $SERVICE_NAME${NC}"
echo -e "  Stop service:      ${BLUE}sudo systemctl stop $SERVICE_NAME${NC}"
echo -e "  View live logs:    ${BLUE}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  Edit config:       ${BLUE}nano $INSTALL_DIR/config.json${NC}"

echo -e "\n${GREEN}Next Steps:${NC}"
echo "=================================================="
echo "1. Assign videos to this device via the web interface"
echo "2. Device will automatically sync and start playback"
echo "3. Monitor device status at: $SERVER_URL/devices"

echo -e "\n${YELLOW}Note:${NC} Device will start playing assigned videos within 5 minutes"
echo -e "${YELLOW}Note:${NC} Screen rotation can be configured via: $SERVER_URL/devices/{id}/configure"

echo -e "\n${GREEN}Installation completed successfully!${NC}\n"
