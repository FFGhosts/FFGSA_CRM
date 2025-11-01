#!/bin/bash
###############################################################################
# FFGSA_CSM Server - One-Step Installation Script for CentOS
# Installs and configures the FFGSA Content Signage Management server
###############################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="ffgsa-csm"
APP_DIR="/opt/ffgsa_csm"
SERVICE_NAME="ffgsa-csm"
GITHUB_REPO="https://github.com/FFGhosts/FFGSA_CRM.git"
PYTHON_VERSION="3.9"
VENV_DIR="$APP_DIR/venv"
SERVICE_USER="ffgsa"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║         FFGSA_CSM Server - Installation Script           ║"
echo "║              CentOS 7/8/9 Compatible                      ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo bash install.sh"
    exit 1
fi

echo -e "\n${GREEN}Step 1: Checking System Requirements${NC}"
echo "=================================================="

# Detect CentOS version
if [ -f /etc/centos-release ]; then
    CENTOS_VERSION=$(rpm -E %{rhel})
    echo "✓ Detected CentOS/RHEL $CENTOS_VERSION"
else
    echo -e "${RED}Error: This script is designed for CentOS/RHEL${NC}"
    exit 1
fi

echo -e "\n${GREEN}Step 2: Gathering Configuration${NC}"
echo "=================================================="

# Get GitHub repository URL
read -p "Enter GitHub repository URL [$GITHUB_REPO]: " INPUT_REPO
GITHUB_REPO=${INPUT_REPO:-$GITHUB_REPO}

# Get server IP/domain
DEFAULT_IP=$(hostname -I | awk '{print $1}')
read -p "Enter server IP/domain [$DEFAULT_IP]: " SERVER_HOST
SERVER_HOST=${SERVER_HOST:-$DEFAULT_IP}

# Get port
read -p "Enter application port [5000]: " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-5000}

# Get admin credentials
read -p "Enter admin username [admin]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}
read -sp "Enter admin password [admin123]: " ADMIN_PASS
echo
ADMIN_PASS=${ADMIN_PASS:-admin123}

echo -e "\n${GREEN}Step 3: Installing System Dependencies${NC}"
echo "=================================================="

# Update system
echo "Updating system packages..."
yum update -y -q

# Install EPEL repository (needed for some packages)
echo "Installing EPEL repository..."
yum install -y epel-release -q

# Install required packages
echo "Installing required packages..."
yum install -y \
    python3 \
    python3-pip \
    python3-devel \
    git \
    gcc \
    make \
    sqlite \
    sqlite-devel \
    nginx \
    firewalld \
    -q

echo -e "${GREEN}✓ System dependencies installed${NC}"

echo -e "\n${GREEN}Step 4: Creating Service User${NC}"
echo "=================================================="

# Create service user if doesn't exist
if id "$SERVICE_USER" &>/dev/null; then
    echo "User $SERVICE_USER already exists"
else
    useradd -r -s /bin/bash -d $APP_DIR $SERVICE_USER
    echo "✓ Created user: $SERVICE_USER"
fi

echo -e "\n${GREEN}Step 5: Cloning Application from GitHub${NC}"
echo "=================================================="

# Create application directory
mkdir -p $APP_DIR
cd /opt

# Clone or update repository
if [ -d "$APP_DIR/.git" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    sudo -u $SERVICE_USER git pull
else
    echo "Cloning repository..."
    if sudo -u $SERVICE_USER git clone $GITHUB_REPO $APP_DIR; then
        echo -e "${GREEN}✓ Repository cloned successfully${NC}"
    else
        echo -e "${RED}Error: Failed to clone repository${NC}"
        echo "Please check the repository URL and your access permissions"
        exit 1
    fi
fi

cd $APP_DIR

echo -e "\n${GREEN}Step 6: Setting Up Python Virtual Environment${NC}"
echo "=================================================="

# Create virtual environment
echo "Creating Python virtual environment..."
sudo -u $SERVICE_USER python3 -m venv $VENV_DIR

# Upgrade pip
echo "Upgrading pip..."
sudo -u $SERVICE_USER $VENV_DIR/bin/pip install --upgrade pip -q

# Install Python dependencies
echo "Installing Python packages (this may take a few minutes)..."
sudo -u $SERVICE_USER $VENV_DIR/bin/pip install -r requirements.txt -q

echo -e "${GREEN}✓ Python environment configured${NC}"

echo -e "\n${GREEN}Step 7: Creating Configuration${NC}"
echo "=================================================="

# Generate secret keys
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)

# Create .env file
cat > $APP_DIR/.env << EOF
# ========================================
# FFGSA_CSM Environment Configuration
# ========================================

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$SECRET_KEY
DEBUG=False

# Database Configuration
DATABASE_URI=sqlite:///$APP_DIR/instance/database.db

# Security & Authentication
JWT_SECRET_KEY=$JWT_SECRET

# Admin credentials
ADMIN_USERNAME=$ADMIN_USER
ADMIN_PASSWORD=$ADMIN_PASS

BCRYPT_LOG_ROUNDS=12

# File Upload Configuration
MAX_CONTENT_MB=500
ALLOWED_EXTENSIONS=mp4,avi,mkv,mov,wmv,flv,webm

# CORS Configuration
CORS_ORIGINS=*

# Rate Limiting
RATELIMIT_ENABLED=True
RATELIMIT_STORAGE_URL=memory://
API_RATE_LIMIT=60

# Device Management
DEVICE_TIMEOUT_MINUTES=5
DEVICE_CLEANUP_DAYS=90

# Logging Configuration
LOG_LEVEL=INFO

# Server Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=$SERVER_PORT

# Email Configuration (Optional - Configure later)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=noreply@ffgsa.local
MAIL_SUPPRESS_SEND=True
EOF

chown $SERVICE_USER:$SERVICE_USER $APP_DIR/.env
chmod 600 $APP_DIR/.env

echo -e "${GREEN}✓ Configuration created${NC}"

echo -e "\n${GREEN}Step 8: Creating Required Directories${NC}"
echo "=================================================="

# Create directories
sudo -u $SERVICE_USER mkdir -p $APP_DIR/instance
sudo -u $SERVICE_USER mkdir -p $APP_DIR/logs
sudo -u $SERVICE_USER mkdir -p $APP_DIR/backups/{database,config,videos}
sudo -u $SERVICE_USER mkdir -p $APP_DIR/static/{videos,thumbnails,updates}

echo -e "${GREEN}✓ Directory structure created${NC}"

echo -e "\n${GREEN}Step 9: Initializing Database${NC}"
echo "=================================================="

# Initialize database
echo "Creating database tables..."
cd $APP_DIR
sudo -u $SERVICE_USER $VENV_DIR/bin/python init_db.py

echo -e "${GREEN}✓ Database initialized${NC}"

echo -e "\n${GREEN}Step 10: Creating Systemd Service${NC}"
echo "=================================================="

# Create systemd service file
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=FFGSA Content Signage Management Server
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python app.py
Restart=always
RestartSec=10
StandardOutput=append:$APP_DIR/logs/app.log
StandardError=append:$APP_DIR/logs/app.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}✓ Systemd service created${NC}"

echo -e "\n${GREEN}Step 11: Configuring Firewall${NC}"
echo "=================================================="

# Start and enable firewalld
systemctl start firewalld
systemctl enable firewalld

# Open application port
echo "Opening port $SERVER_PORT..."
firewall-cmd --permanent --add-port=${SERVER_PORT}/tcp
firewall-cmd --reload

echo -e "${GREEN}✓ Firewall configured${NC}"

echo -e "\n${GREEN}Step 12: Configuring Nginx (Optional)${NC}"
echo "=================================================="

read -p "Configure Nginx reverse proxy? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create Nginx configuration
    cat > /etc/nginx/conf.d/${APP_NAME}.conf << EOF
upstream ffgsa_csm {
    server 127.0.0.1:${SERVER_PORT};
}

server {
    listen 80;
    server_name ${SERVER_HOST};
    client_max_body_size 500M;

    location / {
        proxy_pass http://ffgsa_csm;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Test and restart Nginx
    nginx -t
    systemctl enable nginx
    systemctl restart nginx
    
    # Open HTTP port
    firewall-cmd --permanent --add-service=http
    firewall-cmd --reload
    
    echo -e "${GREEN}✓ Nginx configured${NC}"
else
    echo "Skipping Nginx configuration"
fi

echo -e "\n${GREEN}Step 13: Starting Service${NC}"
echo "=================================================="

# Enable and start service
systemctl enable ${SERVICE_NAME}.service
systemctl start ${SERVICE_NAME}.service

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet ${SERVICE_NAME}.service; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${YELLOW}⚠ Service may have issues starting${NC}"
    echo "Check logs: journalctl -u ${SERVICE_NAME} -f"
fi

echo -e "\n${GREEN}Step 14: Setting Up Log Rotation${NC}"
echo "=================================================="

# Create logrotate configuration
cat > /etc/logrotate.d/${APP_NAME} << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 $SERVICE_USER $SERVICE_USER
    sharedscripts
    postrotate
        systemctl reload ${SERVICE_NAME} > /dev/null 2>&1 || true
    endscript
}
EOF

echo -e "${GREEN}✓ Log rotation configured${NC}"

echo -e "\n${GREEN}Step 15: Creating Backup Cron Job${NC}"
echo "=================================================="

# Create backup script
cat > $APP_DIR/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/ffgsa_csm/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
cp /opt/ffgsa_csm/instance/database.db "$BACKUP_DIR/database_$DATE.db"
# Keep only last 30 backups
cd "$BACKUP_DIR"
ls -t database_*.db | tail -n +31 | xargs -r rm
EOF

chmod +x $APP_DIR/backup.sh
chown $SERVICE_USER:$SERVICE_USER $APP_DIR/backup.sh

# Add to crontab (daily at 2 AM)
(crontab -u $SERVICE_USER -l 2>/dev/null; echo "0 2 * * * $APP_DIR/backup.sh") | crontab -u $SERVICE_USER -

echo -e "${GREEN}✓ Backup cron job created${NC}"

echo -e "\n${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║              Installation Complete! ✓                     ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "\n${GREEN}Installation Summary:${NC}"
echo "=================================================="
echo -e "  Application Directory: ${BLUE}$APP_DIR${NC}"
echo -e "  Service Name: ${BLUE}$SERVICE_NAME${NC}"
echo -e "  Database: ${BLUE}$APP_DIR/instance/database.db${NC}"
echo -e "  Logs: ${BLUE}$APP_DIR/logs/${NC}"
echo -e "  Configuration: ${BLUE}$APP_DIR/.env${NC}"

echo -e "\n${GREEN}Access Information:${NC}"
echo "=================================================="
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "  URL: ${BLUE}http://$SERVER_HOST${NC}"
else
    echo -e "  URL: ${BLUE}http://$SERVER_HOST:$SERVER_PORT${NC}"
fi
echo -e "  Username: ${BLUE}$ADMIN_USER${NC}"
echo -e "  Password: ${BLUE}$ADMIN_PASS${NC}"

echo -e "\n${GREEN}Service Management:${NC}"
echo "=================================================="
echo -e "  Start service:     ${BLUE}systemctl start $SERVICE_NAME${NC}"
echo -e "  Stop service:      ${BLUE}systemctl stop $SERVICE_NAME${NC}"
echo -e "  Restart service:   ${BLUE}systemctl restart $SERVICE_NAME${NC}"
echo -e "  Service status:    ${BLUE}systemctl status $SERVICE_NAME${NC}"
echo -e "  View logs:         ${BLUE}journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  Application logs:  ${BLUE}tail -f $APP_DIR/logs/app.log${NC}"

echo -e "\n${GREEN}Update Application:${NC}"
echo "=================================================="
echo -e "  ${BLUE}cd $APP_DIR${NC}"
echo -e "  ${BLUE}sudo -u $SERVICE_USER git pull${NC}"
echo -e "  ${BLUE}sudo -u $SERVICE_USER $VENV_DIR/bin/pip install -r requirements.txt${NC}"
echo -e "  ${BLUE}systemctl restart $SERVICE_NAME${NC}"

echo -e "\n${GREEN}Configuration Files:${NC}"
echo "=================================================="
echo -e "  Edit settings:     ${BLUE}nano $APP_DIR/.env${NC}"
echo -e "  After changes:     ${BLUE}systemctl restart $SERVICE_NAME${NC}"

echo -e "\n${GREEN}Backup & Restore:${NC}"
echo "=================================================="
echo -e "  Backups location:  ${BLUE}$APP_DIR/backups/database/${NC}"
echo -e "  Manual backup:     ${BLUE}$APP_DIR/backup.sh${NC}"
echo -e "  Auto backup:       ${BLUE}Daily at 2 AM (last 30 kept)${NC}"

echo -e "\n${YELLOW}Security Recommendations:${NC}"
echo "=================================================="
echo "  1. Change admin password after first login"
echo "  2. Configure SSL/TLS certificate for HTTPS"
echo "  3. Set up email notifications in .env file"
echo "  4. Review firewall rules for your network"
echo "  5. Enable SELinux if disabled"

echo -e "\n${GREEN}Next Steps:${NC}"
echo "=================================================="
echo "  1. Access the web interface at the URL above"
echo "  2. Login with admin credentials"
echo "  3. Upload videos via Upload page"
echo "  4. Register Raspberry Pi devices"
echo "  5. Create playlists and assign to devices"
echo "  6. Configure email notifications"

echo -e "\n${GREEN}Installation completed successfully!${NC}\n"
