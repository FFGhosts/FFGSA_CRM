# System Updates Feature - Quick Reference

## Overview
Complete system update management for deploying software updates to Raspberry Pi devices remotely.

## Access
**URL:** http://localhost:5000/system-updates  
**Navigation:** Updates menu item (operators/admins only)

## Features

### 1. Upload Updates
- **Supported formats:** .tar.gz, .zip, .deb
- **Max file size:** 500MB
- **Required fields:**
  - Version (e.g., 2.0.0)
  - Update file
- **Optional fields:**
  - Description
  - Critical flag (forces immediate update)

### 2. Deploy Updates
- Select specific devices or all devices
- View device current versions
- Track online/offline status
- Automatic deployment within 5 minutes

### 3. Track Status
- View all available updates
- See deployed devices per update
- Monitor file size and checksums
- Check device software versions

## Usage

### Upload New Update
1. Navigate to **System Updates** page
2. Fill in version number (semantic versioning: X.Y.Z)
3. Add description (optional)
4. Check "Critical Update" if mandatory
5. Choose update file
6. Click **Upload Update**

### Deploy to Devices
1. Find the update in the list
2. Click **Deploy** button
3. Select target devices
4. Click **Deploy Update**
5. Devices will check and install within 5 minutes

### Delete Update
1. Find the update to remove
2. Click trash icon (🗑️)
3. Confirm deletion
4. File and database records removed

## API Endpoints

### For Web UI
- `GET /system-updates` - Management page
- `GET /api/system-updates` - List updates
- `POST /api/system-updates` - Upload update
- `POST /api/system-updates/<id>/deploy` - Deploy to devices
- `DELETE /api/system-updates/<id>` - Delete update

### For Devices
- `GET /api/devices/<id>/check-updates` - Check for updates
- Device compares current version with available updates
- Returns list of newer versions

## Device Update Process

1. **Device polls** every 5 minutes (SYNC_INTERVAL)
2. **Checks for updates** via API
3. **Downloads update file** if available
4. **Verifies checksum** for integrity
5. **Installs update** (details in player.py)
6. **Reports status** back to server
7. **Restarts** if necessary

## Update File Structure

Update packages should contain:
```
update_package.tar.gz
├── player.py          # Updated player code
├── requirements.txt   # Python dependencies
├── install.sh         # Installation script
└── README.md          # Update notes
```

## Status Tracking

### Update Status
- **available** - Ready to deploy
- **mandatory** - Must be installed
- **deprecated** - Old version

### Device Update Status
- **pending** - Queued for installation
- **downloading** - Fetching update file
- **installing** - Installing update
- **completed** - Successfully installed
- **failed** - Installation error

## Security

- **File verification:** SHA256 checksum validation
- **Permissions:** Operator/Admin only
- **Audit trail:** Created by user tracked
- **Notifications:** Updates trigger system notifications

## Best Practices

1. **Test updates** on a single device first
2. **Use semantic versioning** (major.minor.patch)
3. **Write clear descriptions** of changes
4. **Mark critical updates** appropriately
5. **Monitor deployment status** after releasing
6. **Keep backup** of previous versions
7. **Schedule during off-hours** for critical systems

## Troubleshooting

### Update not installing
- Check device is online
- Verify device has storage space
- Check device logs at `/home/pi/player.log`
- Ensure update version is newer than current

### Download failed
- Verify update file exists at file_path
- Check file permissions on server
- Test file download manually
- Verify checksum matches

### Device stuck in "downloading"
- Restart device
- Check network connectivity
- Verify update file size isn't too large
- Review device logs for errors

## Example: Creating an Update

```bash
# 1. Package your update
cd /path/to/updated/player
tar -czf update_2.0.0.tar.gz player.py requirements.txt install.sh

# 2. Upload via web UI
# - Go to System Updates page
# - Fill version: 2.0.0
# - Description: "Fixed video rotation bug"
# - Upload update_2.0.0.tar.gz

# 3. Deploy to test device first
# - Click Deploy
# - Select single test device
# - Monitor logs

# 4. Deploy to all devices
# - Once verified, click Deploy again
# - Select all devices
# - Confirm deployment
```

## Integration with Raspberry Pi Client

The `player.py` client automatically:
- Checks for updates every sync interval
- Downloads via authenticated API
- Validates checksums
- Runs installation scripts
- Reports installation status
- Restarts if required

No manual intervention needed on devices!

## Database Schema

```sql
-- system_update table
CREATE TABLE system_update (
    id INTEGER PRIMARY KEY,
    version VARCHAR(20) UNIQUE,
    release_date DATE,
    description TEXT,
    file_path VARCHAR(255),
    file_size INTEGER,
    checksum VARCHAR(64),
    is_critical BOOLEAN,
    status VARCHAR(20),
    created_by INTEGER,
    created_at TIMESTAMP
);

-- device_update table  
CREATE TABLE device_update (
    id INTEGER PRIMARY KEY,
    device_id INTEGER,
    update_id INTEGER,
    status VARCHAR(20),
    download_progress INTEGER,
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

## Files Created
- `/routes/client_routes.py` - Update management routes
- `/templates/system_updates.html` - Update management UI
- `/static/updates/` - Update file storage directory

## Phase 7 Complete! ✅

All 8 tasks completed:
1. ✅ Client Configuration Models
2. ✅ Configuration Management Routes  
3. ✅ System Update Mechanism
4. ✅ Screenshot/Monitoring Feature
5. ✅ Audio Control System
6. ✅ Emergency Broadcast Feature
7. ✅ Raspberry Pi Client Updates
8. ✅ Client Control UI

The piCMS system now has complete remote device management capabilities!
