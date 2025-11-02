"""
Client Control Routes (Phase 7)
Handles device configuration, monitoring, and emergency broadcasts
"""
from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
import os
import json

from models import (
    db, Device, DeviceConfig, DisplaySettings, NetworkConfig,
    AudioSettings, DeviceScreenshot, SystemUpdate, DeviceUpdate,
    EmergencyBroadcast, EmergencyBroadcastDevice, Video, DeviceGroup,
    NotificationType, NotificationPriority
)
from utils.permissions import operator_required
from utils.notifications import NotificationService

client_bp = Blueprint('client', __name__)


# ============================================================================
# RASPBERRY PI SETUP PAGE
# ============================================================================

@client_bp.route('/raspberry-setup', methods=['GET'])
def raspberry_setup_page():
    """Raspberry Pi one-step installation guide with automatic IP detection"""
    # Get the actual server host from request
    server_host = request.host
    
    # If accessed via localhost/127.0.0.1, detect actual network IP
    if server_host.startswith('localhost') or server_host.startswith('127.0.0.1'):
        try:
            import socket
            # Get the actual network IP by connecting to external address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Connect to Google DNS to find our IP
            network_ip = s.getsockname()[0]
            s.close()
            
            # Extract port if present
            port = ''
            if ':' in server_host:
                port = ':' + server_host.split(':')[1]
            
            server_host = network_ip + port
        except Exception:
            # Fall back to request.host if detection fails
            pass
    
    return render_template('raspberry_setup.html', server_host=server_host)


# ============================================================================
# DEVICE CONFIGURATION WEB UI
# ============================================================================

@client_bp.route('/devices/<int:device_id>/configure', methods=['GET'])
@login_required
@operator_required
def device_configuration_page(device_id):
    """Device configuration page"""
    device = Device.query.get_or_404(device_id)
    
    # Get existing settings or defaults
    display = DisplaySettings.query.filter_by(device_id=device_id).first()
    network = NetworkConfig.query.filter_by(device_id=device_id).first()
    audio = AudioSettings.query.filter_by(device_id=device_id).first()
    
    return render_template('device_configure.html',
                         device=device,
                         display=display,
                         network=network,
                         audio=audio)


# ============================================================================
# DEVICE CONFIGURATION MANAGEMENT
# ============================================================================

@client_bp.route('/api/devices/<int:device_id>/config', methods=['GET'])
@login_required
def get_device_config(device_id):
    """Get all configuration for a device"""
    device = Device.query.get_or_404(device_id)
    
    # Get all config key-value pairs
    configs = DeviceConfig.query.filter_by(device_id=device_id).all()
    
    # Get display settings
    display = DisplaySettings.query.filter_by(device_id=device_id).first()
    
    # Get network config
    network = NetworkConfig.query.filter_by(device_id=device_id).first()
    
    # Get audio settings
    audio = AudioSettings.query.filter_by(device_id=device_id).first()
    
    return jsonify({
        'device': {
            'id': device.id,
            'name': device.name,
            'software_version': device.software_version if hasattr(device, 'software_version') else '1.0.0'
        },
        'config': {cfg.config_key: cfg.get_typed_value() for cfg in configs},
        'display': {
            'resolution_width': display.resolution_width if display else 1920,
            'resolution_height': display.resolution_height if display else 1080,
            'rotation': display.rotation if display else 0,
            'screen_on_time': display.screen_on_time if display else '08:00',
            'screen_off_time': display.screen_off_time if display else '22:00',
            'brightness': display.brightness if display else 100,
            'screen_saver_enabled': display.screen_saver_enabled if display else False,
            'screen_saver_delay': display.screen_saver_delay if display else 300
        } if display else {},
        'network': {
            'connection_type': network.connection_type if network else 'ethernet',
            'wifi_ssid': network.wifi_ssid if network else '',
            'wifi_security': network.wifi_security if network else 'WPA2',
            'use_dhcp': network.use_dhcp if network else True,
            'static_ip': network.static_ip if network else '',
            'static_gateway': network.static_gateway if network else '',
            'static_dns': network.static_dns if network else ''
        } if network else {},
        'audio': {
            'volume': audio.volume if audio else 80,
            'muted': audio.muted if audio else False,
            'audio_output': audio.audio_output if audio else 'hdmi'
        } if audio else {}
    })


@client_bp.route('/api/devices/<int:device_id>/config', methods=['POST'])
@login_required
@operator_required
def update_device_config(device_id):
    """Update device configuration"""
    device = Device.query.get_or_404(device_id)
    data = request.get_json()
    
    try:
        # Update custom config keys
        if 'config' in data:
            for key, value in data['config'].items():
                config = DeviceConfig.query.filter_by(
                    device_id=device_id,
                    config_key=key
                ).first()
                
                if not config:
                    config = DeviceConfig(
                        device_id=device_id,
                        config_key=key
                    )
                    db.session.add(config)
                
                config.config_value = str(value)
                config.updated_at = datetime.now(timezone.utc)
        
        # Update display settings
        if 'display' in data:
            display = DisplaySettings.query.filter_by(device_id=device_id).first()
            if not display:
                display = DisplaySettings(device_id=device_id)
                db.session.add(display)
            
            # Check if rotation is changing
            old_rotation = display.rotation if display else 0
            new_rotation = data['display'].get('rotation')
            rotation_changed = new_rotation is not None and old_rotation != new_rotation
            
            for key, value in data['display'].items():
                if hasattr(display, key):
                    setattr(display, key, value)
            display.updated_at = datetime.now(timezone.utc)
            
            # Send immediate rotation command if changed
            if rotation_changed:
                from models import DeviceCommand
                rotate_cmd = DeviceCommand(
                    device_id=device_id,
                    command_type='rotate_screen',
                    parameters={'rotation': new_rotation},
                    issued_by=current_user.id,
                    status='pending'
                )
                db.session.add(rotate_cmd)
                current_app.logger.info(f'Rotation command sent to device {device.name}: {new_rotation}°')
        
        # Update network config
        if 'network' in data:
            network = NetworkConfig.query.filter_by(device_id=device_id).first()
            if not network:
                network = NetworkConfig(device_id=device_id)
                db.session.add(network)
            
            for key, value in data['network'].items():
                if hasattr(network, key) and key != 'wifi_password':
                    setattr(network, key, value)
            
            # Handle password separately (only if provided and not empty)
            if 'wifi_password' in data['network'] and data['network']['wifi_password']:
                network.wifi_password = data['network']['wifi_password']
            
            network.updated_at = datetime.now(timezone.utc)
        
        # Update audio settings
        if 'audio' in data:
            audio = AudioSettings.query.filter_by(device_id=device_id).first()
            if not audio:
                audio = AudioSettings(device_id=device_id)
                db.session.add(audio)
            
            for key, value in data['audio'].items():
                if hasattr(audio, key):
                    setattr(audio, key, value)
            audio.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Create notification
        NotificationService.create_notification(
            user_id=current_user.id,
            title='Device Configuration Updated',
            message=f'Configuration for {device.name} has been updated',
            notification_type=NotificationType.SUCCESS,
            category='device_config',
            related_entity_type='device',
            related_entity_id=device.id
        )
        
        current_app.logger.info(f"Configuration updated for device {device.name} by {current_user.username}")
        
        return jsonify({'success': True, 'message': 'Configuration updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating device config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SCREENSHOT/MONITORING
# ============================================================================

@client_bp.route('/api/devices/<int:device_id>/request-screenshot', methods=['POST'])
@login_required
def request_screenshot(device_id):
    """Request a screenshot from a device"""
    device = Device.query.get_or_404(device_id)
    
    # Store request in device config
    config = DeviceConfig.query.filter_by(
        device_id=device_id,
        config_key='screenshot_requested'
    ).first()
    
    if not config:
        config = DeviceConfig(
            device_id=device_id,
            config_key='screenshot_requested',
            config_type='bool',
            is_system=True
        )
        db.session.add(config)
    
    config.config_value = 'true'
    config.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Screenshot requested from {device.name}'})


@client_bp.route('/api/devices/<int:device_id>/screenshots', methods=['GET'])
@login_required
def get_device_screenshots(device_id):
    """Get recent screenshots for a device"""
    device = Device.query.get_or_404(device_id)
    limit = request.args.get('limit', 10, type=int)
    
    screenshots = DeviceScreenshot.query.filter_by(device_id=device_id)\
        .order_by(DeviceScreenshot.captured_at.desc())\
        .limit(limit).all()
    
    return jsonify({
        'device_id': device_id,
        'device_name': device.name,
        'screenshots': [{
            'id': s.id,
            'file_path': s.file_path,
            'width': s.width,
            'height': s.height,
            'captured_at': s.captured_at.isoformat(),
            'file_size': s.file_size
        } for s in screenshots]
    })


@client_bp.route('/api/devices/<int:device_id>/upload-screenshot', methods=['POST'])
def upload_screenshot(device_id):
    """Endpoint for devices to upload screenshots"""
    device = Device.query.get_or_404(device_id)
    
    if 'screenshot' not in request.files:
        return jsonify({'error': 'No screenshot file provided'}), 400
    
    file = request.files['screenshot']
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    try:
        # Create screenshots directory if not exists
        screenshots_dir = os.path.join(current_app.static_folder, 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'device_{device_id}_{timestamp}.jpg'
        filepath = os.path.join(screenshots_dir, filename)
        
        # Save file
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        
        # Get image dimensions
        try:
            from PIL import Image
            img = Image.open(filepath)
            width, height = img.size
        except:
            width, height = None, None
        
        # Create database record
        screenshot = DeviceScreenshot(
            device_id=device_id,
            file_path=f'/static/screenshots/{filename}',
            file_size=file_size,
            width=width,
            height=height,
            captured_at=datetime.now(timezone.utc)
        )
        db.session.add(screenshot)
        
        # Update device last_screenshot_at
        device.last_screenshot_at = datetime.now(timezone.utc)
        
        # Clear screenshot request flag
        config = DeviceConfig.query.filter_by(
            device_id=device_id,
            config_key='screenshot_requested'
        ).first()
        if config:
            config.config_value = 'false'
        
        db.session.commit()
        
        current_app.logger.info(f"Screenshot uploaded from device {device.name}")
        
        return jsonify({
            'success': True,
            'screenshot_id': screenshot.id,
            'file_path': screenshot.file_path
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading screenshot: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# EMERGENCY BROADCAST
# ============================================================================

@client_bp.route('/emergency-broadcast', methods=['GET'])
@login_required
@operator_required
def emergency_broadcast_page():
    """Emergency broadcast control page"""
    active_broadcasts = EmergencyBroadcast.query.filter_by(status='active')\
        .order_by(EmergencyBroadcast.created_at.desc()).all()
    
    recent_broadcasts = EmergencyBroadcast.query.filter(
        EmergencyBroadcast.status.in_(['expired', 'cancelled'])
    ).order_by(EmergencyBroadcast.created_at.desc()).limit(10).all()
    
    devices = Device.query.filter_by(is_active=True).all()
    device_groups = DeviceGroup.query.all()
    videos = Video.query.all()
    
    return render_template('emergency_broadcast.html',
                         active_broadcasts=active_broadcasts,
                         recent_broadcasts=recent_broadcasts,
                         devices=devices,
                         device_groups=device_groups,
                         videos=videos)


@client_bp.route('/api/emergency-broadcast', methods=['POST'])
@login_required
@operator_required
def create_emergency_broadcast():
    """Create a new emergency broadcast"""
    data = request.get_json()
    
    try:
        broadcast = EmergencyBroadcast(
            title=data['title'],
            message=data['message'],
            video_id=data.get('video_id'),
            priority=data.get('priority', 3),
            duration=data.get('duration'),
            target_all_devices=data.get('target_all_devices', True),
            target_device_group_id=data.get('target_device_group_id'),
            created_by=current_user.id,
            status='active'
        )
        
        # Set end time if duration specified
        if broadcast.duration:
            broadcast.end_time = datetime.now(timezone.utc) + timedelta(seconds=broadcast.duration)
        
        db.session.add(broadcast)
        db.session.flush()  # Get broadcast ID
        
        # Determine target devices
        if broadcast.target_all_devices:
            devices = Device.query.filter_by(is_active=True).all()
        elif broadcast.target_device_group_id:
            group = DeviceGroup.query.get(broadcast.target_device_group_id)
            devices = group.devices if group else []
        else:
            # Specific devices from data
            device_ids = data.get('device_ids', [])
            devices = Device.query.filter(Device.id.in_(device_ids)).all()
        
        # Create broadcast-device associations
        for device in devices:
            bd = EmergencyBroadcastDevice(
                broadcast_id=broadcast.id,
                device_id=device.id,
                status='pending'
            )
            db.session.add(bd)
        
        db.session.commit()
        
        # Send notification to all admins/operators
        NotificationService.create_notification(
            user_id=current_user.id,
            title='Emergency Broadcast Created',
            message=f'"{broadcast.title}" broadcast to {len(devices)} devices',
            notification_type=NotificationType.WARNING,
            category='emergency_broadcast',
            priority=NotificationPriority.HIGH,
            related_entity_type='emergency_broadcast',
            related_entity_id=broadcast.id
        )
        
        current_app.logger.warning(f"Emergency broadcast created by {current_user.username}: {broadcast.title}")
        
        return jsonify({
            'success': True,
            'broadcast_id': broadcast.id,
            'message': f'Emergency broadcast sent to {len(devices)} devices'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating emergency broadcast: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@client_bp.route('/api/emergency-broadcast/<int:broadcast_id>/cancel', methods=['POST'])
@login_required
@operator_required
def cancel_emergency_broadcast(broadcast_id):
    """Cancel an active emergency broadcast"""
    broadcast = EmergencyBroadcast.query.get_or_404(broadcast_id)
    
    broadcast.status = 'cancelled'
    broadcast.end_time = datetime.now(timezone.utc)
    db.session.commit()
    
    current_app.logger.info(f"Emergency broadcast cancelled by {current_user.username}: {broadcast.title}")
    
    return jsonify({'success': True, 'message': 'Broadcast cancelled'})


@client_bp.route('/api/devices/<int:device_id>/emergency-broadcasts', methods=['GET'])
def get_device_emergency_broadcasts(device_id):
    """Get active emergency broadcasts for a specific device (called by device)"""
    device = Device.query.get_or_404(device_id)
    
    # Get active broadcasts for this device
    now = datetime.now(timezone.utc)
    
    broadcasts = db.session.query(EmergencyBroadcast).join(
        EmergencyBroadcastDevice,
        EmergencyBroadcast.id == EmergencyBroadcastDevice.broadcast_id
    ).filter(
        EmergencyBroadcastDevice.device_id == device_id,
        EmergencyBroadcast.status == 'active',
        EmergencyBroadcast.start_time <= now,
        db.or_(
            EmergencyBroadcast.end_time.is_(None),
            EmergencyBroadcast.end_time > now
        )
    ).order_by(EmergencyBroadcast.priority.desc()).all()
    
    return jsonify({
        'broadcasts': [{
            'id': b.id,
            'title': b.title,
            'message': b.message,
            'video_id': b.video_id,
            'priority': b.priority,
            'duration': b.duration,
            'start_time': b.start_time.isoformat(),
            'end_time': b.end_time.isoformat() if b.end_time else None
        } for b in broadcasts]
    })


@client_bp.route('/api/devices/<int:device_id>/emergency-broadcasts/<int:broadcast_id>/acknowledge', methods=['POST'])
def acknowledge_emergency_broadcast(device_id, broadcast_id):
    """Device acknowledges receiving emergency broadcast"""
    bd = EmergencyBroadcastDevice.query.filter_by(
        broadcast_id=broadcast_id,
        device_id=device_id
    ).first_or_404()
    
    bd.status = 'acknowledged'
    bd.acknowledged_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify({'success': True})


# ============================================================================
# SYSTEM UPDATES
# ============================================================================

@client_bp.route('/system-updates', methods=['GET'])
@login_required
@operator_required
def system_updates_page():
    """System updates management page"""
    updates = SystemUpdate.query.order_by(SystemUpdate.release_date.desc()).all()
    devices = Device.query.filter_by(is_active=True).all()
    
    return render_template('system_updates.html',
                         updates=updates,
                         devices=devices)


@client_bp.route('/api/system-updates', methods=['GET'])
@login_required
def get_system_updates():
    """Get available system updates"""
    updates = SystemUpdate.query.order_by(SystemUpdate.release_date.desc()).all()
    
    return jsonify({
        'updates': [{
            'id': u.id,
            'version': u.version,
            'release_date': u.release_date.isoformat(),
            'description': u.description,
            'file_size': u.file_size,
            'is_critical': u.is_critical,
            'status': u.status
        } for u in updates]
    })


@client_bp.route('/api/system-updates', methods=['POST'])
@login_required
@operator_required
def create_system_update():
    """Create a new system update"""
    if 'update_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['update_file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Empty filename'}), 400
    
    try:
        # Create updates directory if not exists
        updates_dir = os.path.join(current_app.root_path, 'static', 'updates')
        os.makedirs(updates_dir, exist_ok=True)
        
        # Save file
        filename = f"update_{request.form['version'].replace('.', '_')}_{file.filename}"
        filepath = os.path.join(updates_dir, filename)
        file.save(filepath)
        
        # Calculate file size and checksum
        file_size = os.path.getsize(filepath)
        
        import hashlib
        with open(filepath, 'rb') as f:
            checksum = hashlib.sha256(f.read()).hexdigest()
        
        # Create database record
        update = SystemUpdate(
            version=request.form['version'],
            description=request.form.get('description', ''),
            file_path=f'/static/updates/{filename}',
            file_size=file_size,
            checksum=checksum,
            is_critical=request.form.get('is_critical') == 'true',
            status='available',
            created_by=current_user.id
        )
        db.session.add(update)
        db.session.commit()
        
        # Create notification
        NotificationService.create_notification(
            user_id=current_user.id,
            title='System Update Created',
            message=f'Version {update.version} is now available',
            notification_type=NotificationType.INFO,
            category='system_update',
            related_entity_type='system_update',
            related_entity_id=update.id
        )
        
        current_app.logger.info(f"System update created: {update.version} by {current_user.username}")
        
        return jsonify({
            'success': True,
            'update_id': update.id,
            'message': f'Update {update.version} created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating system update: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@client_bp.route('/api/system-updates/<int:update_id>/deploy', methods=['POST'])
@login_required
@operator_required
def deploy_system_update(update_id):
    """Deploy update to devices"""
    update = SystemUpdate.query.get_or_404(update_id)
    data = request.get_json()
    
    try:
        # Get target devices
        device_ids = data.get('device_ids', [])
        if not device_ids:
            return jsonify({'success': False, 'error': 'No devices selected'}), 400
        
        devices = Device.query.filter(Device.id.in_(device_ids)).all()
        
        # Create device update records
        deployed_count = 0
        for device in devices:
            # Check if already deployed
            existing = DeviceUpdate.query.filter_by(
                device_id=device.id,
                update_id=update_id
            ).first()
            
            if not existing:
                device_update = DeviceUpdate(
                    device_id=device.id,
                    update_id=update_id,
                    status='pending',
                    scheduled_at=datetime.now(timezone.utc)
                )
                db.session.add(device_update)
                deployed_count += 1
        
        db.session.commit()
        
        # Create notification
        NotificationService.create_notification(
            user_id=current_user.id,
            title='Update Deployed',
            message=f'Update {update.version} deployed to {deployed_count} device(s)',
            notification_type=NotificationType.SUCCESS,
            category='system_update',
            priority=NotificationPriority.HIGH
        )
        
        current_app.logger.info(f"Update {update.version} deployed to {deployed_count} devices by {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Update deployed to {deployed_count} device(s)',
            'deployed_count': deployed_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deploying update: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@client_bp.route('/api/system-updates/<int:update_id>', methods=['DELETE'])
@login_required
@operator_required
def delete_system_update(update_id):
    """Delete a system update"""
    update = SystemUpdate.query.get_or_404(update_id)
    
    try:
        # Delete file if exists
        if update.file_path:
            filepath = os.path.join(current_app.root_path, update.file_path.lstrip('/'))
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Delete database record (cascade will handle device_update records)
        db.session.delete(update)
        db.session.commit()
        
        current_app.logger.info(f"System update deleted: {update.version} by {current_user.username}")
        
        return jsonify({'success': True, 'message': 'Update deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting update: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@client_bp.route('/api/devices/<int:device_id>/check-updates', methods=['GET'])
def check_device_updates(device_id):
    """Check available updates for a device (called by device)"""
    device = Device.query.get_or_404(device_id)
    current_version = device.software_version if hasattr(device, 'software_version') else '1.0.0'
    
    # Get available updates newer than device version
    updates = SystemUpdate.query.filter(
        SystemUpdate.status.in_(['available', 'mandatory']),
        SystemUpdate.version > current_version
    ).order_by(SystemUpdate.version).all()
    
    return jsonify({
        'current_version': current_version,
        'updates_available': len(updates) > 0,
        'updates': [{
            'id': u.id,
            'version': u.version,
            'description': u.description,
            'file_path': u.file_path,
            'checksum': u.checksum,
            'is_critical': u.is_critical
        } for u in updates]
    })


# Register blueprint
def register_client_blueprint(app):
    """Register client control blueprint"""
    app.register_blueprint(client_bp)
