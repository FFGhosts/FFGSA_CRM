# PiCMS Project Structure

```
PiCMS/
├── app.py                      # Main Flask application entry point
├── config.py                   # Configuration management
├── models.py                   # SQLAlchemy database models
├── init_db.py                  # Database initialization script
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker orchestration
├── nginx.conf                  # Nginx reverse proxy config
├── Makefile                    # Build automation
│
├── routes/                     # Flask blueprints
│   ├── __init__.py
│   ├── admin_routes.py         # Web dashboard routes
│   └── api_routes.py           # REST API endpoints
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Base template with navigation
│   ├── login.html              # Login page
│   ├── index.html              # Dashboard
│   ├── upload.html             # Video management
│   ├── devices.html            # Device management
│   ├── assignments.html        # Assignment management
│   └── errors/                 # Error pages
│       ├── 404.html
│       ├── 500.html
│       └── 413.html
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css           # Custom CSS
│   ├── js/
│   │   └── main.js             # Custom JavaScript
│   └── videos/                 # Uploaded video storage
│       └── .gitkeep
│
├── logs/                       # Application logs
│   ├── .gitkeep
│   ├── api.log                 # API request logs
│   └── app.log                 # Application logs
│
└── raspberry_client/           # Raspberry Pi client
    ├── player.py               # Main player script
    ├── config.json             # Client configuration
    ├── install_service.sh      # Service installer
    ├── picms_player.service    # Systemd service file
    └── README.md               # Client documentation
```

## Component Overview

### Backend (Flask)
- **app.py** - Application factory, extensions initialization, error handlers
- **config.py** - Environment-based configuration (Dev/Prod/Test)
- **models.py** - User, Video, Device, Assignment, ApiLog models
- **routes/admin_routes.py** - Web UI endpoints (login, dashboard, CRUD operations)
- **routes/api_routes.py** - REST API for Raspberry Pi devices

### Frontend (Bootstrap 5)
- **templates/** - Jinja2 templates with responsive design
- **static/css/style.css** - Custom styling and animations
- **static/js/main.js** - Client-side interactions, form validation

### Database Models
1. **User** - Admin authentication
2. **Video** - Video metadata and storage info
3. **Device** - Raspberry Pi device registry with API keys
4. **Assignment** - Many-to-many relationship (Device ↔ Video)
5. **ApiLog** - API request logging

### Raspberry Pi Client
- **player.py** - Auto-sync, download, and playback manager
- **config.json** - Server URL, credentials, device info
- **install_service.sh** - Automated installation
- **picms_player.service** - Systemd service for auto-start

### Deployment
- **Docker** - Containerized Flask app with Gunicorn
- **PostgreSQL** - Production database
- **Nginx** - Reverse proxy with SSL/TLS
- **Docker Compose** - Multi-container orchestration

## Key Features

✅ Video upload and management
✅ Device registration and monitoring
✅ Video-to-device assignment
✅ REST API with key authentication
✅ Real-time device status tracking
✅ Automatic video sync on Raspberry Pi
✅ Fullscreen video playback loop
✅ Systemd service for auto-start
✅ Docker deployment support
✅ SSL/HTTPS support
✅ Rate limiting and security
✅ Comprehensive logging
