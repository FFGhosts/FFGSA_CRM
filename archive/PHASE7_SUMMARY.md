# Phase 7: Client-Side Enhancements

## Overview

Phase 7 adds comprehensive client-side management capabilities to piCMS, enabling remote control and monitoring of Raspberry Pi devices through the web interface.

## Features Implemented

### 1. Device Configuration Management
- **Key-Value Configuration Store**: Custom configuration parameters for each device
- **Configuration API**: GET/POST endpoints for reading and updating device config
- **Type Support**: String, integer, boolean, and JSON configuration values
- **Automatic Type Conversion**: `get_typed_value()` method for safe type handling

**API Endpoints:**
- `GET /api/devices/<id>/config` - Get all device configuration
- `POST /api/devices/<id>/config` - Update device configuration

### 2. Display Settings
- **Resolution Control**: Configurable width/height (default 1920x1080)
- **Screen Rotation**: 0°, 90°, 180°, 270° rotation support
- **Brightness Control**: 0-100% brightness adjustment
- **Screen Schedule**: Automatic on/off times (e.g., 08:00 - 22:00)
- **Screen Saver**: Configurable delay and enable/disable

**Configuration Options:**
```json
{
  "resolution_width": 1920,
  "resolution_height": 1080,
  "rotation": 0,
  "screen_on_time": "08:00",
  "screen_off_time": "22:00",
  "brightness": 100,
  "screen_saver_enabled": false,
  "screen_saver_delay": 300
}
```

### 3. Network Configuration
- **Connection Types**: Ethernet or WiFi
- **WiFi Settings**: SSID, password, security type (WPA2/WPA3/WEP)
- **IP Configuration**: DHCP or static IP setup
- **Static Network**: IP address, gateway, DNS configuration

**Configuration Options:**
```json
{
  "connection_type": "ethernet",
  "wifi_ssid": "",
  "wifi_password": "",
  "wifi_security": "WPA2",
  "use_dhcp": true,
  "static_ip": "",
  "static_gateway": "",
  "static_dns": ""
}
```

### 4. Audio Settings
- **Volume Control**: 0-100% volume adjustment
- **Mute Toggle**: Quick mute/unmute functionality
- **Output Selection**: HDMI, Analog (3.5mm), or USB audio output

**Configuration Options:**
```json
{
  "volume": 80,
  "muted": false,
  "audio_output": "hdmi"
}
```

### 5. Screenshot/Monitoring
- **Remote Screenshots**: Request screenshots from devices via web UI
- **Automatic Upload**: Devices capture and upload screenshots to server
- **Screenshot History**: View recent screenshots with metadata
- **Dimensions Tracking**: Resolution information for each screenshot

**API Endpoints:**
- `POST /api/devices/<id>/request-screenshot` - Request new screenshot
- `GET /api/devices/<id>/screenshots?limit=10` - Get recent screenshots
- `POST /api/devices/<id>/upload-screenshot` - Device uploads screenshot

**Features:**
- Screenshots saved to `/static/screenshots/`
- Automatic cleanup of old screenshots
- JPEG format with 80% quality
- Dimension extraction using PIL

### 6. Emergency Broadcast System
- **Urgent Messaging**: Override current playback with emergency content
- **Priority Levels**: 1 (Low) to 5 (Critical) priority system
- **Targeting Options**:
  - All active devices
  - Specific device groups
  - Individual devices
- **Content Types**:
  - Text messages displayed on screen
  - Emergency video playback
- **Duration Control**: Set broadcast duration or indefinite
- **Real-Time Activation**: Devices check every 10 seconds
- **Acknowledgment Tracking**: Monitor which devices received broadcast

**API Endpoints:**
- `POST /api/emergency-broadcast` - Create broadcast
- `GET /api/emergency-broadcast/<id>/cancel` - Cancel broadcast
- `GET /api/devices/<id>/emergency-broadcasts` - Get active broadcasts for device
- `POST /api/devices/<id>/emergency-broadcasts/<id>/acknowledge` - Device acknowledges

**Web Interface:**
- `/emergency-broadcast` - Emergency broadcast control page
- Visual priority indicators
- Active broadcast monitoring
- Recent broadcast history

### 7. System Updates (Foundation)
- **Update Tracking**: SystemUpdate model for version management
- **Device Update Status**: Per-device update tracking with progress
- **Version Comparison**: Checksum verification
- **Update States**: pending, downloading, installing, completed, failed

**API Endpoints:**
- `GET /api/system-updates` - List available updates
- `GET /api/devices/<id>/check-updates` - Check updates for device

**Models:**
- `SystemUpdate`: Software versions, release dates, checksums
- `DeviceUpdate`: Per-device installation tracking with progress (0-100%)

### 8. Raspberry Pi Client Updates
The `player.py` client now includes:

**Phase 7 Features:**
- Configuration polling every 30 seconds
- Display settings application (brightness, rotation, screen schedule)
- Audio settings application (volume, mute, output selection)
- Screenshot capture and upload using `scrot`
- Emergency broadcast checking every 10 seconds
- Priority-based emergency handling
- Automatic emergency acknowledgment

**Emergency Mode:**
```python
# Emergency broadcasts have highest priority
# Checks every 10 seconds: EMERGENCY_CHECK_INTERVAL = 10
# Stops normal playback when emergency active
# Automatically resumes normal playback when emergency ends
```

**Configuration Updates:**
```python
# Client checks for config updates: CONFIG_CHECK_INTERVAL = 30
# Applies display settings (brightness, rotation, screen on/off)
# Applies audio settings (volume, mute)
# Captures screenshots on demand
```

## Database Schema

### New Tables Created

1. **device_config** - Key-value configuration storage
   - device_id, config_key, config_value, config_type
   - is_system flag for internal configs

2. **display_settings** - Screen configuration
   - device_id (one-to-one), resolution, rotation, brightness
   - screen_on_time, screen_off_time, screen_saver settings

3. **network_config** - Network configuration
   - device_id (one-to-one), connection_type
   - WiFi credentials, DHCP/static IP settings

4. **audio_settings** - Audio configuration
   - device_id (one-to-one), volume, muted, audio_output

5. **device_screenshot** - Screenshot metadata
   - device_id, file_path, dimensions, captured_at, file_size

6. **system_update** - Software versions
   - version, release_date, file_path, checksum
   - is_critical, status (available/deprecated/mandatory)

7. **device_update** - Per-device update tracking
   - device_id, update_id, status, download_progress
   - installed_at, error_message

8. **emergency_broadcast** - Emergency messages
   - title, message, video_id, priority (1-5)
   - duration, target settings, status, time range

9. **emergency_broadcast_device** - Delivery tracking
   - broadcast_id, device_id, status
   - acknowledged_at, displayed_at

## Migration

Migration script: `migrate_phase7_client_enhancements.py`

**Status:** ✅ Tables created successfully

Run migration:
```bash
python migrate_phase7_client_enhancements.py
```

Creates all 9 tables and adds columns to device table:
- `software_version` - Current client software version
- `last_screenshot_at` - Timestamp of last screenshot

## Usage

### Emergency Broadcast Example

1. Navigate to `/emergency-broadcast`
2. Fill in broadcast details:
   - Title: "Fire Drill"
   - Message: "Please evacuate the building"
   - Priority: 5 (Critical)
   - Duration: 300 seconds (5 minutes)
3. Select target devices (All, Group, or Specific)
4. Click "Send Emergency Broadcast"
5. Devices check for broadcasts every 10 seconds and immediately switch playback

### Device Configuration Example

```python
# Update device display settings
import requests

device_id = 1
data = {
    "display": {
        "brightness": 80,
        "rotation": 90,
        "screen_on_time": "07:00",
        "screen_off_time": "23:00"
    }
}

response = requests.post(
    f'http://localhost:5000/api/devices/{device_id}/config',
    json=data,
    headers={'X-CSRFToken': csrf_token}
)
```

### Screenshot Request

```javascript
// Request screenshot from device
async function requestScreenshot(deviceId) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')
        .getAttribute('content');
    
    const response = await fetch(`/api/devices/${deviceId}/request-screenshot`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken }
    });
    
    const result = await response.json();
    console.log(result.message);
}
```

## Raspberry Pi Client Setup

### Prerequisites

Install required packages on Raspberry Pi:
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip mpv scrot

# Install Python dependencies
pip3 install requests Pillow
```

### Configuration

Edit `/home/pi/config.json`:
```json
{
  "server_url": "http://192.168.1.100:5000",
  "device_id": 1,
  "api_key": "your-device-api-key",
  "device_name": "Lobby Display",
  "serial": "RPI-ABCD1234"
}
```

### Service Installation

```bash
sudo cp picms_player.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable picms_player
sudo systemctl start picms_player
```

## Security Considerations

1. **WiFi Passwords**: Network configuration passwords stored in plaintext
   - TODO: Implement encryption for sensitive credentials

2. **Screenshot Privacy**: Screenshots may contain sensitive information
   - Implement automatic cleanup policy
   - Add access control for screenshot viewing

3. **Emergency Broadcast**: High-privilege operation
   - Restricted to operators and admins via `@require_permission('operator')`

4. **API Authentication**: All client endpoints require device API key
   - Headers: `X-Device-Key: <api_key>`

## Client-Side Commands

### Display Control
```bash
# Turn display on/off
vcgencmd display_power 1  # On
vcgencmd display_power 0  # Off
```

### Audio Control
```bash
# Set volume
amixer set PCM 80%

# Mute/unmute
amixer set PCM mute
amixer set PCM unmute
```

### Screenshot Capture
```bash
# Capture screenshot
scrot /tmp/screenshot.jpg -q 80
```

## Permissions

- **Viewer**: No access to client control features
- **Operator**: Full access to emergency broadcasts and device configuration
- **Admin**: Full access to all features including system updates

## Future Enhancements

1. **System Updates**: Complete implementation
   - File upload for update packages
   - Automatic rollback on failure
   - Update scheduling

2. **Network Management**: Enhanced features
   - WiFi network scanning
   - Connection status monitoring
   - VPN configuration

3. **Screenshot Monitoring**: Additional features
   - Scheduled automatic screenshots
   - Motion detection comparison
   - Screenshot annotations

4. **Display Settings**: Advanced options
   - Color calibration
   - Overscan adjustment
   - Multi-monitor support

5. **Audio Enhancements**:
   - Audio output testing
   - Volume normalization
   - Audio EQ settings

## Troubleshooting

### Emergency broadcasts not activating
1. Check device is online: `GET /api/devices`
2. Verify emergency broadcast is active: `GET /api/emergency-broadcast/<id>`
3. Check device emergency polling: Review device logs at `/home/pi/player.log`

### Screenshots not uploading
1. Verify `scrot` is installed: `which scrot`
2. Check permissions on `/tmp` directory
3. Review network connectivity
4. Check server logs for upload errors

### Configuration not applying
1. Verify device API key is valid
2. Check configuration polling interval (30 seconds)
3. Review device logs for errors
4. Confirm settings are saved in database

## API Reference

See `routes/client_routes.py` for complete API documentation.

**Key Routes:**
- Device Config: `/api/devices/<id>/config` (GET, POST)
- Screenshots: `/api/devices/<id>/screenshots` (GET), `/api/devices/<id>/request-screenshot` (POST)
- Emergency: `/api/emergency-broadcast` (POST), `/emergency-broadcast` (Web UI)
- Updates: `/api/system-updates` (GET), `/api/devices/<id>/check-updates` (GET)

## Testing

Test emergency broadcast:
```bash
curl -X POST http://localhost:5000/api/emergency-broadcast \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -d '{
    "title": "Test Alert",
    "message": "This is a test",
    "priority": 3,
    "target_all_devices": true
  }'
```

Test screenshot request:
```bash
curl -X POST http://localhost:5000/api/devices/1/request-screenshot \
  -H "X-CSRFToken: <token>"
```

## Phase Completion Status

✅ **Completed:**
1. Database models (9 tables)
2. Database migration script
3. API routes for all features
4. Emergency broadcast web UI
5. Raspberry Pi client updates
6. Display settings management
7. Audio settings management
8. Screenshot capture and upload
9. Emergency broadcast system
10. Device configuration API

⚠️ **Partial:**
1. System updates (foundation only, no UI)
2. Network configuration (no WiFi scanning)

🔄 **Next Phase Suggestions:**
- Phase 8: Analytics Dashboard (visual reports, charts)
- Phase 9: Content Scheduler Enhancements (recurring schedules)
- Phase 10: Multi-tenant Support (organization/department isolation)
