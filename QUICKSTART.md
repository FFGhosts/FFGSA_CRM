# PiCMS Quick Start Guide

## 🚀 Get Up and Running in 5 Minutes

### Option 1: Development Setup (Local Testing)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database
python init_db.py

# 3. Run the server
python app.py
```

Visit `http://localhost:5000` and login with:
- Username: `admin`
- Password: `admin123`

### Option 2: Production Setup (Docker)

```bash
# 1. Create environment file
cp .env.example .env
# Edit .env with secure passwords

# 2. Generate SSL certificate
mkdir ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem

# 3. Start containers
docker-compose up -d

# 4. Initialize database
docker-compose exec web python init_db.py
```

Visit `https://localhost` and login with your configured admin credentials.

## 📱 Setup Raspberry Pi Client

### On your Raspberry Pi:

```bash
# 1. Download player script
wget https://your-server/raspberry_client/player.py
wget https://your-server/raspberry_client/config.json
wget https://your-server/raspberry_client/install_service.sh

# 2. Edit config
nano config.json
# Set server_url to your server's address

# 3. Install service
chmod +x install_service.sh
sudo ./install_service.sh

# 4. Check status
sudo systemctl status picms_player
```

## 🎬 First Steps in the Web Dashboard

1. **Upload a Video**
   - Go to Videos → Upload Video
   - Select a video file (MP4, AVI, MKV, etc.)
   - Click Upload

2. **Add a Device**
   - Go to Devices → Add Device
   - Enter name and serial number
   - **Save the API key** (shown only once!)

3. **Create Assignment**
   - Go to Assignments → New Assignment
   - Select device(s) and video(s)
   - Click Create Assignment

4. **Monitor Status**
   - Dashboard shows device status
   - Green = Online, Gray = Offline
   - View what's currently playing

## 🔑 Important Notes

- **Change default password** immediately after first login
- **Save API keys** when creating devices (not shown again)
- **Use HTTPS** in production (included in Docker setup)
- **Backup database** regularly (`make backup`)

## 📊 Verify Everything Works

### Server Health Check
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-31T10:00:00"
}
```

### Check Raspberry Pi Logs
```bash
sudo journalctl -u picms_player -f
```

You should see:
- Device registration
- Video sync
- Download progress
- Playback started

## 🆘 Common Issues

**Can't login?**
- Check username/password in `.env` file
- Run `python init_db.py` to reset

**Videos not uploading?**
- Check disk space: `df -h`
- Verify MAX_CONTENT_LENGTH (500MB default)

**Raspberry Pi can't connect?**
- Verify server URL in config.json
- Check firewall: `sudo ufw status`
- Test connectivity: `ping YOUR_SERVER_IP`

**Videos won't play on Pi?**
- Install mpv: `sudo apt-get install mpv`
- Check video format (MP4 recommended)
- Test manually: `mpv /home/pi/videos/test.mp4`

## 📚 Next Steps

- Read the full [README.md](README.md)
- Check [API Documentation](README.md#api-documentation)
- See [Security Considerations](README.md#security-considerations)
- Review [Troubleshooting Guide](README.md#troubleshooting)

## 💡 Tips

- Use MP4 H.264 format for best compatibility
- Keep video files under 500MB (or adjust limit in config)
- Monitor device status regularly
- Set up automatic backups in production
- Use strong passwords and change defaults

---

**Need help?** Open an issue on GitHub or check the full documentation.
