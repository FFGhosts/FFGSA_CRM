# FFGSA_CSM - Content Signage Management System

<div align="center">
  <h3>🎬 Central video management system for Raspberry Pi digital signage players</h3>
  <p>Upload videos through a web dashboard, assign them to specific Raspberry Pis, and have them automatically download and play in fullscreen.</p>
</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Development Setup](#development-setup)
  - [Production Deployment (Docker)](#production-deployment-docker)
- [Raspberry Pi Client Setup](#raspberry-pi-client-setup)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## 🎯 Overview

FFGSA_CMS is a production-ready content management system designed for managing video playback on multiple Raspberry Pi devices. It consists of two main components:

1. **CMS Server** - Flask-based web application for managing videos, devices, and assignments
2. **Pi Client** - Python script that runs on Raspberry Pi devices to download and play assigned videos

---

## ✨ Features

### CMS Server
- 📊 **Dashboard** - Real-time overview of devices, videos, and system status
- 🎥 **Video Management** - Upload, organize, and delete video content
- 🖥️ **Device Management** - Register and monitor Raspberry Pi devices
- 🔗 **Assignment System** - Assign specific videos to specific devices
- 🔐 **Authentication** - Secure admin login with Flask-Login
- 🔑 **API Key Authentication** - Secure device-to-server communication
- 📝 **Logging** - Comprehensive API and application logging
- 🚦 **Rate Limiting** - Protection against API abuse
- 💾 **Database Support** - SQLite for development, PostgreSQL for production

### Raspberry Pi Client
- 🔄 **Auto-sync** - Automatically downloads assigned videos
- ▶️ **Video Playback** - Fullscreen loop playback using mpv
- 💓 **Heartbeat** - Regular status updates to server
- 🔧 **Auto-recovery** - Restarts playback if interrupted
- 🚀 **Systemd Service** - Auto-starts on boot
- 📦 **Local Caching** - Videos stored locally for offline playback

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CMS Server                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Web UI     │  │  REST API    │  │  Database    │ │
│  │  (Bootstrap) │  │  (Flask)     │  │ (PostgreSQL) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                           │                              │
└───────────────────────────┼──────────────────────────────┘
                            │ HTTPS/API
            ┌───────────────┼───────────────┐
            │               │               │
    ┌───────▼───────┐ ┌────▼──────┐ ┌─────▼──────┐
    │  Raspberry Pi │ │Raspberry Pi│ │Raspberry Pi│
    │   Player 1    │ │  Player 2  │ │  Player 3  │
    │   (mpv)       │ │   (mpv)    │ │   (mpv)    │
    └───────────────┘ └────────────┘ └────────────┘
```

---

## 📦 Prerequisites

### CMS Server (CentOS/RHEL)
- CentOS 7/8/9 or RHEL 7/8/9
- Python 3.8+
- Root or sudo access
- Internet connection
- Minimum 2GB RAM, 10GB disk space

### Raspberry Pi Client
- Raspberry Pi (3B+ or newer recommended)
- Raspberry Pi OS (Bullseye or newer)
- Network connectivity
- HDMI display

---

## 🚀 Quick Installation

### Server Installation (CentOS/RHEL)

**One-line install:**
```bash
curl -sL https://raw.githubusercontent.com/FFGhosts/FFGSA_CRM/main/install.sh | sudo bash
```

**Or download and run:**
```bash
wget https://raw.githubusercontent.com/FFGhosts/FFGSA_CRM/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

The installation script will:
- ✅ Install all system dependencies
- ✅ Clone the repository
- ✅ Set up Python virtual environment
- ✅ Create systemd service
- ✅ Configure firewall
- ✅ Initialize database
- ✅ Optional: Configure Nginx reverse proxy
- ✅ Set up automatic backups

**Installation takes 5-10 minutes.**

After installation, access the web interface at:
- With Nginx: `http://your-server-ip`
- Without Nginx: `http://your-server-ip:5000`

Default credentials:
- Username: `admin`
- Password: `admin123` (or what you set during installation)

### Raspberry Pi Client Installation

**One-line install from your server:**
```bash
curl -sL http://YOUR-SERVER:5000/static/client/install.sh | bash
```

See [RASPBERRY_PI_QUICKSTART.md](RASPBERRY_PI_QUICKSTART.md) for detailed instructions.

---

## 🎮 Service Management

### CentOS/RHEL Server

**Start/Stop/Restart:**
```bash
sudo systemctl start ffgsa-csm
sudo systemctl stop ffgsa-csm
sudo systemctl restart ffgsa-csm
sudo systemctl status ffgsa-csm
```

**Enable/Disable auto-start:**
```bash
sudo systemctl enable ffgsa-csm   # Start on boot
sudo systemctl disable ffgsa-csm  # Don't start on boot
```

**View logs:**
```bash
# System logs
sudo journalctl -u ffgsa-csm -f

# Application logs
sudo tail -f /opt/ffgsa_csm/logs/app.log
```

**Update application:**
```bash
cd /opt/ffgsa_csm
sudo -u ffgsa git pull
sudo -u ffgsa /opt/ffgsa_csm/venv/bin/pip install -r requirements.txt
sudo systemctl restart ffgsa-csm
```

**Edit configuration:**
```bash
sudo nano /opt/ffgsa_csm/.env
sudo systemctl restart ffgsa-csm
```

**Manual backup:**
```bash
sudo /opt/ffgsa_csm/backup.sh
```

**Uninstall:**
```bash
sudo systemctl stop ffgsa-csm
sudo systemctl disable ffgsa-csm
sudo rm /etc/systemd/system/ffgsa-csm.service
sudo systemctl daemon-reload
sudo userdel -r ffgsa
sudo rm -rf /opt/ffgsa_csm
```

---

## 🚀 Installation

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/FFGhosts/FFGSA_CRM.git
cd FFGSA_CRM
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Create .env file**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python init_db.py
```

6. **Run development server**
```bash
python app.py
```

Access the application at `http://localhost:5000`

**Default credentials:** `admin` / `admin123`

### Production Deployment (Docker)

1. **Clone and configure**
```bash
git clone https://github.com/FFGhosts/FFGSA_CRM.git
cd FFGSA_CRM
cp .env.example .env
# Edit .env with secure passwords and keys
```

2. **Generate SSL certificates**

For self-signed certificate:
```bash
make ssl-cert
```

For Let's Encrypt (recommended):
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

3. **Build and start containers**
```bash
docker-compose up -d
```

4. **Initialize database**
```bash
docker-compose exec web python init_db.py
```

Access the application at `https://yourdomain.com`

### Using Makefile

```bash
# Development setup
make setup

# Production setup (Docker)
make setup-prod

# View all available commands
make help
```

---

## 🍓 Raspberry Pi Client Setup

### Quick Installation

1. **Copy files to Raspberry Pi**
```bash
scp raspberry_client/* pi@raspberrypi.local:/home/pi/
```

2. **SSH into Raspberry Pi**
```bash
ssh pi@raspberrypi.local
```

3. **Run installation script**
```bash
cd /home/pi
chmod +x install_service.sh
sudo ./install_service.sh
```

4. **Edit configuration**
```bash
nano /home/pi/config.json
```

Update `server_url` to point to your CMS server:
```json
{
  "server_url": "http://YOUR_SERVER_IP:5000",
  "device_id": null,
  "api_key": null,
  "device_name": "Pi Player 1",
  "serial": "RPI-001"
}
```

5. **Restart service**
```bash
sudo systemctl restart picms_player
```

### Service Management

```bash
# Check status
sudo systemctl status picms_player

# View logs
sudo journalctl -u picms_player -f

# Stop/Start/Restart
sudo systemctl stop picms_player
sudo systemctl start picms_player
sudo systemctl restart picms_player
```

---

## 📖 Usage

### Web Dashboard

#### 1. Login
Navigate to `http://your-server-ip` and login with admin credentials.

#### 2. Upload Videos
- Go to **Videos** section
- Click **Upload Video**
- Fill in title, description, and select video file
- Click **Upload**

#### 3. Add Devices
- Go to **Devices** section
- Click **Add Device**
- Enter device name and serial number
- Save the generated API key (shown once)

#### 4. Create Assignments
- Go to **Assignments** section
- Click **New Assignment**
- Select device(s) and video(s)
- Click **Create Assignment**

#### 5. Monitor Status
- **Dashboard** shows real-time statistics
- Green badge = Online, Gray badge = Offline
- View current playing video per device

---

## 🔌 API Documentation

### Authentication
All API requests require the `X-Device-Key` header with a valid API key.

### Endpoints

#### Register Device
```http
POST /api/device/register
Content-Type: application/json

{
  "name": "Pi Player 1",
  "serial": "RPI-12345",
  "ip_address": "192.168.1.100"
}

Response:
{
  "device_id": 1,
  "api_key": "generated-key-here",
  "message": "Device registered successfully"
}
```

#### Get Assigned Videos
```http
GET /api/videos/{device_id}
X-Device-Key: your-api-key

Response:
{
  "device_id": 1,
  "device_name": "Pi Player 1",
  "videos": [
    {
      "id": 1,
      "title": "Video 1",
      "filename": "video1.mp4",
      "size": 12345678,
      "url": "/api/video/video1.mp4",
      "assigned_at": "2025-10-31T10:00:00"
    }
  ]
}
```

#### Download Video
```http
GET /api/video/{filename}
X-Device-Key: your-api-key

Response: Binary video file
```

#### Send Heartbeat
```http
POST /api/device/heartbeat
X-Device-Key: your-api-key
Content-Type: application/json

{
  "current_video": "video1.mp4",
  "status": "playing",
  "timestamp": "2025-10-31T10:00:00"
}

Response:
{
  "message": "Heartbeat received",
  "server_time": "2025-10-31T10:00:05"
}
```

#### Health Check
```http
GET /api/health

Response:
{
  "status": "healthy",
  "timestamp": "2025-10-31T10:00:00"
}
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Flask
FLASK_ENV=production
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Database
DATABASE_URI=postgresql://user:pass@localhost/picms

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password

# Security
BCRYPT_LOG_ROUNDS=12

# Rate Limiting
RATELIMIT_ENABLED=True

# Device Settings
DEVICE_TIMEOUT_MINUTES=5
```

### Database Configuration

**Development (SQLite):**
```python
DATABASE_URI=sqlite:///database.db
```

**Production (PostgreSQL):**
```python
DATABASE_URI=postgresql://user:pass@host:5432/dbname
```

---

## 🔧 Troubleshooting

### Server Issues

**Database connection error:**
```bash
# Check PostgreSQL is running
docker-compose ps
docker-compose logs db

# Reinitialize database
docker-compose exec web python init_db.py
```

**Videos not uploading:**
- Check `MAX_CONTENT_LENGTH` in config (default 500MB)
- Ensure `static/videos/` directory exists and is writable
- Check disk space: `df -h`

### Raspberry Pi Client Issues

**Player won't start:**
```bash
# Check service status
sudo systemctl status picms_player

# View detailed logs
sudo journalctl -u picms_player -n 100

# Test manually
python3 /home/pi/player.py
```

**Cannot connect to server:**
```bash
# Test connectivity
ping YOUR_SERVER_IP

# Test API
curl -X GET http://YOUR_SERVER_IP:5000/api/health
```

**Videos not playing:**
```bash
# Check mpv installation
mpv --version

# Test video playback
mpv /home/pi/videos/test.mp4

# Check video files
ls -lh /home/pi/videos/
```

---

## 🔐 Security Considerations

### Production Checklist

- [ ] Change default admin password
- [ ] Use strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable rate limiting
- [ ] Restrict CORS origins
- [ ] Set up firewall rules
- [ ] Regular database backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated

### API Security

- API keys are hashed using bcrypt before storage
- All device communication uses API key authentication
- Rate limiting prevents brute-force attacks
- HTTPS enforced in production (nginx config)

---

## 📈 Future Improvements

- [ ] **Scheduling** - Schedule videos by time/day of week
- [ ] **Real-time Monitoring** - WebSocket-based live dashboard
- [ ] **File Validation** - Checksum verification for downloads
- [ ] **Remote Logs** - Collect logs from devices
- [ ] **Playlists** - Create ordered playlists instead of loops
- [ ] **Multi-user Support** - Role-based access control
- [ ] **Video Preview** - Thumbnail generation and preview
- [ ] **Storage Management** - Automatic cleanup of old videos
- [ ] **Mobile App** - React Native mobile client
- [ ] **Analytics** - Playback statistics and reporting

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 💬 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Email: support@picms.example.com

---

## 🙏 Acknowledgments

- Flask framework and community
- Bootstrap for UI components
- mpv media player
- PostgreSQL and SQLAlchemy
- All open-source contributors

---

<div align="center">
  <p>Made with ❤️ for the Raspberry Pi community</p>
  <p>© 2025 PiCMS. All rights reserved.</p>
</div>
