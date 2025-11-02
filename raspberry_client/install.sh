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
GITHUB_REPO="https://github.com/FFGhosts/FFGSA_CRM.git"
GITHUB_RAW="https://raw.githubusercontent.com/FFGhosts/FFGSA_CRM/main/raspberry_client"

echo -e "${BLUE}"
echo "â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—"
echo "â•‘                                                           â•‘"
echo "â•‘         PiCMS Player - One-Step Installation             â•‘"
echo "â•‘                                                           â•‘"
echo "â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•"
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
    python3-requests \
    python3-pil \
    mpv \
    scrot \
    git \
    curl \
    unclutter

echo -e "${GREEN}âœ“ System dependencies installed${NC}"

echo -e "\n${GREEN}Step 3: Installing Python Dependencies${NC}"
echo "=================================================="

# Verify Python packages
echo "Verifying Python packages..."
python3 -c "import requests; import PIL" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Required Python packages not installed${NC}"
    exit 1
fi

echo -e "${GREEN}âœ“ Python dependencies installed${NC}"

echo -e "\n${GREEN}Step 4: Creating Installation Directory${NC}"
echo "=================================================="

# Create installation directory
sudo mkdir -p $INSTALL_DIR
sudo chown -R pi:pi $INSTALL_DIR

# Create subdirectories
mkdir -p $INSTALL_DIR/videos
mkdir -p $INSTALL_DIR/logs

echo -e "${GREEN}âœ“ Directory structure created${NC}"

echo -e "\n${GREEN}Step 5: Downloading Player Software from GitHub${NC}"
echo "=================================================="

# Download player files from GitHub
echo "Downloading player.py..."
if curl -f -s -L -o $INSTALL_DIR/player.py "$GITHUB_RAW/player.py"; then
    echo -e "${GREEN}âœ“ Downloaded player.py${NC}"
    chmod +x $INSTALL_DIR/player.py
else
    echo -e "${RED}Error: Could not download player.py from GitHub${NC}"
    echo "Please check your internet connection and try again"
    exit 1
fi

echo "Downloading install_service.sh..."
if curl -f -s -L -o $INSTALL_DIR/install_service.sh "$GITHUB_RAW/install_service.sh"; then
    echo -e "${GREEN}âœ“ Downloaded install_service.sh${NC}"
    chmod +x $INSTALL_DIR/install_service.sh
else
    echo -e "${YELLOW}âš  Could not download install_service.sh${NC}"
fi

echo -e "${GREEN}âœ“ Player software downloaded from GitHub${NC}"

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

echo -e "${GREEN}âœ“ Configuration file created${NC}"

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
    
    echo -e "${GREEN}âœ“ Device registered successfully${NC}"
    echo -e "   Device ID: ${BLUE}$DEVICE_ID${NC}"
    echo -e "   API Key: ${BLUE}${API_KEY:0:20}...${NC}"
else
    echo -e "${YELLOW}âš  Could not auto-register device${NC}"
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

echo -e "${GREEN}âœ“ Systemd service created${NC}"

echo -e "\n${GREEN}Step 9: Configuring Auto-Start${NC}"
echo "=================================================="

# Enable service to start on boot
sudo systemctl enable ${SERVICE_NAME}.service

echo -e "${GREEN}âœ“ Service enabled for auto-start${NC}"

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

# Disable cursor (unclutter already installed in Step 2)
echo "Cursor hiding enabled via unclutter"

echo -e "${GREEN}âœ“ Raspberry Pi optimized for digital signage${NC}"

echo -e "\n${GREEN}Step 11: Starting Service${NC}"
echo "=================================================="

# Start the service
sudo systemctl start ${SERVICE_NAME}.service

# Wait a moment for service to start
sleep 2

# Check service status
if sudo systemctl is-active --quiet ${SERVICE_NAME}.service; then
    echo -e "${GREEN}âœ“ Service started successfully${NC}"
else
    echo -e "${YELLOW}âš  Service may have issues starting${NC}"
    echo "Check logs: sudo journalctl -u ${SERVICE_NAME} -f"
fi

echo -e "\n${BLUE}"
echo "â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—"
echo "â•‘                                                           â•‘"
echo "â•‘              Installation Complete! âœ“                     â•‘"
echo "â•‘                                                           â•‘"
echo "â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•"
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
