"""
API Routes Blueprint
REST API endpoints for Raspberry Pi devices to sync videos and report status
"""
import os
import time
import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from sqlalchemy.exc import IntegrityError

from models import db, Device, Video, Assignment, ApiLog, PlaybackLog

api_bp = Blueprint('api', __name__)

# Setup API logger
api_logger = logging.getLogger('api')


# ============================================================================
# AUTHENTICATION DECORATOR
# ============================================================================

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Device-Key')
        
        if not api_key:
            log_api_request(None, request.path, request.method, 401)
            return jsonify({'error': 'Missing API key'}), 401
        
        # Find device with matching API key
        device = None
        active_devices = Device.query.filter_by(is_active=True).all()
        
        current_app.logger.debug(f'API Key auth attempt - Found {len(active_devices)} active devices')
        
        for d in active_devices:
            current_app.logger.debug(f'Checking device {d.id} ({d.name})')
            if d.verify_api_key(api_key):
                device = d
                current_app.logger.info(f'API key verified for device {d.id} ({d.name})')
                break
        
        if not device:
            current_app.logger.warning(f'Invalid API key attempt from {request.remote_addr}')
            log_api_request(None, request.path, request.method, 401)
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Store device in request context
        request.device = device  # type: ignore
        
        return f(*args, **kwargs)
    
    return decorated_function


def log_api_request(device_id, endpoint, method, status_code, response_time=None):
    """Log API request to database and file"""
    try:
        # Log to database
        log_entry = ApiLog(
            device_id=device_id,
            endpoint=endpoint,
            method=method,
            ip_address=request.remote_addr,
            status_code=status_code,
            response_time=response_time
        )
        db.session.add(log_entry)
        db.session.commit()
        
        # Log to file
        api_logger.info(f'{method} {endpoint} - Device:{device_id} IP:{request.remote_addr} Status:{status_code}')
    except Exception as e:
        current_app.logger.error(f'Error logging API request: {e}')


# ============================================================================
# DEVICE REGISTRATION
# ============================================================================

@api_bp.route('/device/register', methods=['POST'])
def register_device():
    """
    Register a new device or return existing device info
    
    Request JSON:
    {
        "name": "Pi Player 1",
        "serial": "RPI-12345",
        "ip_address": "192.168.1.100"
    }
    
    Response JSON:
    {
        "device_id": 1,
        "api_key": "generated-key-here",
        "message": "Device registered successfully"
    }
    """
    start_time = time.time()
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name')
        serial = data.get('serial')
        ip_address = data.get('ip_address')
        
        if not name or not serial:
            return jsonify({'error': 'Name and serial are required'}), 400
        
        # Check if device already exists
        device = Device.query.filter_by(serial=serial).first()
        
        if device:
            # Re-registration: Generate new API key
            api_key = Device.generate_api_key()
            
            # Update device with new credentials
            device.name = name  # Update name in case it changed
            device.ip_address = ip_address
            device.api_key_hash = Device.hash_api_key(api_key)
            device.last_seen = datetime.utcnow()
            db.session.commit()
            
            response_time = (time.time() - start_time) * 1000
            log_api_request(device.id, '/device/register', 'POST', 200, response_time)
            
            current_app.logger.info(f'Device re-registered with new API key: {serial}')
            
            return jsonify({
                'device_id': device.id,
                'api_key': api_key,
                'message': 'Device re-registered successfully',
                'note': 'New API key generated'
            }), 200
        
        # Generate API key
        api_key = Device.generate_api_key()
        
        # Create new device
        device = Device(
            name=name,
            serial=serial,
            ip_address=ip_address,
            api_key_hash=Device.hash_api_key(api_key),
            last_seen=datetime.utcnow()
        )
        
        db.session.add(device)
        db.session.commit()
        
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, '/device/register', 'POST', 201, response_time)
        
        current_app.logger.info(f'New device registered: {serial}')
        
        return jsonify({
            'device_id': device.id,
            'api_key': api_key,
            'message': 'Device registered successfully'
        }), 201
    
    except Exception as e:
        current_app.logger.error(f'Error registering device: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# VIDEO SYNC
# ============================================================================

@api_bp.route('/videos/<int:device_id>', methods=['GET'])
@require_api_key
def get_device_videos(device_id):
    """
    Get list of videos assigned to a device (filtered by schedule)
    
    Response JSON:
    {
        "device_id": 1,
        "device_name": "Pi Player 1",
        "videos": [
            {
                "id": 1,
                "title": "Video 1",
                "filename": "video1.mp4",
                "size": 12345678,
                "duration": 120,
                "url": "/api/video/video1.mp4",
                "assigned_at": "2025-10-31T10:00:00",
                "from_playlist": null
            }
        ],
        "active_assignments": 2,
        "total_assignments": 5
    }
    """
    start_time = time.time()
    
    try:
        # Verify device matches authenticated device
        if request.device.id != device_id:  # type: ignore
            log_api_request(request.device.id, f'/videos/{device_id}', 'GET', 403)  # type: ignore
            return jsonify({'error': 'Unauthorized device'}), 403
        
        device = request.device  # type: ignore
        current_time = datetime.now()
        
        # Get all assignments for this device
        assignments = Assignment.query.filter_by(device_id=device_id).all()
        total_assignments = len(assignments)
        
        # Filter assignments by schedule
        active_assignments = [a for a in assignments if a.is_active_at(current_time)]
        
        # Phase 4.3: Get scheduled content (higher priority than regular assignments)
        from models import Schedule
        active_schedules = Schedule.query.filter_by(
            device_id=device_id,
            is_active=True
        ).order_by(Schedule.priority.desc()).all()
        
        # Filter schedules by current time and get highest priority
        scheduled_content = None
        current_date = current_time.date()
        current_time_only = current_time.time()
        for schedule in active_schedules:
            if schedule.is_active_on_date(current_date) and schedule.is_active_at_time(current_time_only):
                scheduled_content = schedule
                break  # Highest priority schedule wins
        
        videos_list = []
        seen_videos = set()  # Track video IDs to avoid duplicates
        
        # If there's an active schedule, only return scheduled content
        if scheduled_content:
            if scheduled_content.video_id:
                video = scheduled_content.video
                videos_list.append({
                    'id': video.id,
                    'title': video.title,
                    'filename': video.filename,
                    'size': video.size,
                    'duration': video.duration,
                    'url': f'/api/video/{video.filename}',
                    'checksum': video.checksum,
                    'assigned_at': scheduled_content.created_at.isoformat(),
                    'from_playlist': None,
                    'scheduled': True,
                    'schedule_priority': scheduled_content.priority,
                    'schedule_end_time': scheduled_content.end_time.strftime('%H:%M')
                })
            elif scheduled_content.playlist_id:
                playlist = scheduled_content.playlist
                for item in playlist.items:
                    video = item.video
                    videos_list.append({
                        'id': video.id,
                        'title': video.title,
                        'filename': video.filename,
                        'size': video.size,
                        'duration': video.duration,
                        'url': f'/api/video/{video.filename}',
                        'checksum': video.checksum,
                        'assigned_at': scheduled_content.created_at.isoformat(),
                        'from_playlist': playlist.name,
                        'playlist_position': item.position,
                        'scheduled': True,
                        'schedule_priority': scheduled_content.priority,
                        'schedule_end_time': scheduled_content.end_time.strftime('%H:%M')
                    })
            
            # Return only scheduled content
            response_time = (time.time() - start_time) * 1000
            log_api_request(device.id, f'/videos/{device_id}', 'GET', 200, response_time)
            
            return jsonify({
                'device_id': device.id,
                'device_name': device.name,
                'videos': videos_list,
                'active_assignments': len(active_assignments),
                'total_assignments': total_assignments,
                'scheduled_content': True,
                'schedule_active_until': scheduled_content.end_time.strftime('%H:%M'),
                'server_time': current_time.isoformat()
            }), 200
        
        for assignment in active_assignments:
            if assignment.video_id:
                # Direct video assignment
                video = assignment.video
                if video.id not in seen_videos:
                    videos_list.append({
                        'id': video.id,
                        'title': video.title,
                        'filename': video.filename,
                        'size': video.size,
                        'duration': video.duration,
                        'url': f'/api/video/{video.filename}',
                        'checksum': video.checksum,
                        'assigned_at': assignment.assigned_at.isoformat(),
                        'from_playlist': None,
                        'schedule': assignment.formatted_schedule if assignment.is_scheduled else None
                    })
                    seen_videos.add(video.id)
            
            elif assignment.playlist_id:
                # Playlist assignment - include all videos in playlist
                playlist = assignment.playlist
                for item in playlist.items:
                    video = item.video
                    if video.id not in seen_videos:
                        videos_list.append({
                            'id': video.id,
                            'title': video.title,
                            'filename': video.filename,
                            'size': video.size,
                            'duration': video.duration,
                            'url': f'/api/video/{video.filename}',
                            'checksum': video.checksum,
                            'assigned_at': assignment.assigned_at.isoformat(),
                            'from_playlist': playlist.name,
                            'playlist_position': item.position,
                            'schedule': assignment.formatted_schedule if assignment.is_scheduled else None
                        })
                        seen_videos.add(video.id)
        
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, f'/videos/{device_id}', 'GET', 200, response_time)
        
        return jsonify({
            'device_id': device.id,
            'device_name': device.name,
            'videos': videos_list,
            'active_assignments': len(active_assignments),
            'total_assignments': total_assignments,
            'server_time': current_time.isoformat()
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching videos for device {device_id}: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# VIDEO DOWNLOAD
# ============================================================================

@api_bp.route('/video/<filename>', methods=['GET'])
@require_api_key
def download_video(filename):
    """
    Serve video file to authenticated device
    
    Validates that the device has this video assigned before serving
    """
    start_time = time.time()
    
    try:
        device = request.device  # type: ignore
        
        # Find video by filename
        video = Video.query.filter_by(filename=filename).first()
        
        if not video:
            log_api_request(device.id, f'/video/{filename}', 'GET', 404)
            return jsonify({'error': 'Video not found'}), 404
        
        # Check if device has this video assigned
        assignment = Assignment.query.filter_by(
            device_id=device.id,
            video_id=video.id
        ).first()
        
        if not assignment:
            log_api_request(device.id, f'/video/{filename}', 'GET', 403)
            return jsonify({'error': 'Video not assigned to this device'}), 403
        
        # Serve file
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, f'/video/{filename}', 'GET', 200, response_time)
        
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER'],
            filename,
            as_attachment=True
        )
    
    except Exception as e:
        current_app.logger.error(f'Error serving video {filename}: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# HEARTBEAT
# ============================================================================

@api_bp.route('/device/heartbeat', methods=['POST'])
@require_api_key
def device_heartbeat():
    """
    Receive heartbeat from device with status update
    
    Request JSON:
    {
        "current_video": "video1.mp4",
        "status": "playing",
        "video_id": 1,
        "timestamp": "2025-10-31T10:00:00"
    }
    
    Response JSON:
    {
        "message": "Heartbeat received",
        "server_time": "2025-10-31T10:00:05"
    }
    """
    start_time = time.time()
    
    try:
        device = request.device  # type: ignore
        data = request.get_json() or {}
        
        # Update device status
        was_online = device.is_online
        device.last_seen = datetime.utcnow()
        current_video = data.get('current_video')
        previous_video = device.current_video
        device.current_video = current_video
        device.ip_address = request.remote_addr
        
        # Log playback activity for analytics
        video_id = data.get('video_id')
        status = data.get('status', 'unknown')
        
        if video_id and status == 'playing':
            # Check if there's an existing playback log for this device/video without end time
            existing_log = PlaybackLog.query.filter_by(
                device_id=device.id,
                video_id=video_id,
                ended_at=None
            ).first()
            
            if not existing_log:
                # Create new playback log
                playback_log = PlaybackLog(
                    device_id=device.id,
                    video_id=video_id
                )
                db.session.add(playback_log)
        
        elif status == 'stopped' and current_video:
            # End the current playback log
            video = Video.query.filter_by(filename=current_video).first()
            if video:
                playback_log = PlaybackLog.query.filter_by(
                    device_id=device.id,
                    video_id=video.id,
                    ended_at=None
                ).first()
                
                if playback_log:
                    playback_log.ended_at = datetime.utcnow()
                    duration = (playback_log.ended_at - playback_log.started_at).total_seconds()
                    playback_log.duration_played = int(duration)
        
        db.session.commit()
        
        # Emit WebSocket events for real-time monitoring (Phase 4.1)
        from socketio_events import broadcast_device_status, broadcast_playback_started, broadcast_playback_stopped
        
        # Broadcast device status update
        status_data = {
            'is_online': device.is_online,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'current_video': device.current_video,
            'ip_address': device.ip_address
        }
        broadcast_device_status(device.id, status_data)
        
        # Broadcast playback changes
        if current_video and current_video != previous_video:
            video = Video.query.get(video_id) if video_id else None
            video_title = video.title if video else current_video
            broadcast_playback_started(device.id, device.name, video_title)
        elif not current_video and previous_video:
            broadcast_playback_stopped(device.id, device.name)
        
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, '/device/heartbeat', 'POST', 200, response_time)
        
        return jsonify({
            'message': 'Heartbeat received',
            'server_time': datetime.utcnow().isoformat()
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error processing heartbeat: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# DEVICE STATUS
# ============================================================================

@api_bp.route('/device/status', methods=['GET'])
@require_api_key
def device_status():
    """
    Get device status and configuration
    
    Response JSON:
    {
        "device_id": 1,
        "name": "Pi Player 1",
        "is_active": true,
        "assigned_videos_count": 3,
        "last_seen": "2025-10-31T10:00:00"
    }
    """
    start_time = time.time()
    
    try:
        device = request.device  # type: ignore
        
        # Count assigned videos
        videos_count = Assignment.query.filter_by(device_id=device.id).count()
        
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, '/device/status', 'GET', 200, response_time)
        
        return jsonify({
            'device_id': device.id,
            'name': device.name,
            'serial': device.serial,
            'is_active': device.is_active,
            'assigned_videos_count': videos_count,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'current_video': device.current_video
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching device status: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# SCHEDULE ENDPOINTS (Phase 5)
# ============================================================================

@api_bp.route('/device/<int:device_id>/active-schedule', methods=['GET'])
@require_api_key
def get_active_schedule(device_id):
    """
    Get currently active schedule for device based on time and priority
    
    Response JSON:
    {
        "has_schedule": true,
        "schedule": {
            "id": 1,
            "name": "Morning Videos",
            "content_type": "playlist",
            "content_name": "Morning Playlist",
            "video_filename": "video.mp4",  # if single video
            "playlist_videos": [...],  # if playlist
            "priority": 5,
            "start_time": "09:00",
            "end_time": "17:00"
        }
    }
    """
    try:
        from datetime import datetime
        from utils.schedule_utils import resolve_schedule_for_device
        
        device = request.device  # type: ignore
        
        # Security check: ensure device can only query its own schedule
        if device.id != device_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get active schedule
        active_schedule = resolve_schedule_for_device(device_id, datetime.now())
        
        if not active_schedule:
            return jsonify({
                'has_schedule': False,
                'message': 'No active schedule at this time'
            }), 200
        
        # Build schedule response
        schedule_data = {
            'id': active_schedule.id,
            'name': active_schedule.name,
            'content_type': active_schedule.content_type,
            'content_name': active_schedule.content_name,
            'priority': active_schedule.priority,
            'start_time': active_schedule.start_time.strftime('%H:%M'),
            'end_time': active_schedule.end_time.strftime('%H:%M')
        }
        
        # Add content details
        if active_schedule.content_type == 'video':
            schedule_data['video_filename'] = active_schedule.video.filename
        elif active_schedule.content_type == 'playlist':
            # Include all videos in the playlist
            from models import PlaylistVideo
            playlist_videos = PlaylistVideo.query.filter_by(
                playlist_id=active_schedule.playlist_id
            ).order_by(PlaylistVideo.position).all()
            
            schedule_data['playlist_videos'] = [{
                'id': pv.video.id,
                'filename': pv.video.filename,
                'title': pv.video.title,
                'position': pv.position
            } for pv in playlist_videos]
        
        return jsonify({
            'has_schedule': True,
            'schedule': schedule_data
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching active schedule: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# REMOTE COMMANDS (Phase 3.3)
# ============================================================================

@api_bp.route('/device/commands', methods=['GET'])
@require_api_key
def get_device_commands():
    """
    Get pending commands for device
    
    Response JSON:
    {
        "commands": [
            {
                "id": 1,
                "command_type": "restart",
                "parameters": null,
                "created_at": "2025-11-01T10:00:00"
            }
        ]
    }
    """
    start_time = time.time()
    
    try:
        device = request.device  # type: ignore
        
        # Get pending commands for this device
        from models import DeviceCommand
        commands = DeviceCommand.query.filter_by(
            device_id=device.id,
            status='pending'
        ).order_by(DeviceCommand.created_at).all()
        
        command_list = []
        for cmd in commands:
            command_list.append({
                'id': cmd.id,
                'command_type': cmd.command_type,
                'parameters': cmd.parameters,
                'created_at': cmd.created_at.isoformat()
            })
        
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, '/api/device/commands', 'GET', 200, response_time)
        
        return jsonify({
            'commands': command_list,
            'count': len(command_list)
        }), 200
    
    except Exception as e:
        current_app.logger.error(f'Error fetching device commands: {e}')
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/device/commands/<int:command_id>/acknowledge', methods=['POST'])
@require_api_key
def acknowledge_command(command_id):
    """
    Acknowledge that device received command
    
    Request JSON:
    {
        "acknowledged": true
    }
    """
    start_time = time.time()
    
    try:
        device = request.device  # type: ignore
        from models import DeviceCommand
        
        command = DeviceCommand.query.filter_by(
            id=command_id,
            device_id=device.id
        ).first()
        
        if not command:
            return jsonify({'error': 'Command not found'}), 404
        
        command.status = 'acknowledged'
        command.acknowledged_at = datetime.utcnow()
        db.session.commit()
        
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, f'/api/device/commands/{command_id}/acknowledge', 'POST', 200, response_time)
        
        return jsonify({'message': 'Command acknowledged'}), 200
    
    except Exception as e:
        current_app.logger.error(f'Error acknowledging command: {e}')
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/device/commands/<int:command_id>/complete', methods=['POST'])
@require_api_key
def complete_command(command_id):
    """
    Mark command as completed with result
    
    Request JSON:
    {
        "status": "completed",  # or "failed"
        "result": "Restarted successfully"
    }
    """
    start_time = time.time()
    
    try:
        device = request.device  # type: ignore
        data = request.get_json() or {}
        from models import DeviceCommand
        
        command = DeviceCommand.query.filter_by(
            id=command_id,
            device_id=device.id
        ).first()
        
        if not command:
            return jsonify({'error': 'Command not found'}), 404
        
        status = data.get('status', 'completed')
        if status not in ('completed', 'failed'):
            return jsonify({'error': 'Invalid status. Must be "completed" or "failed"'}), 400
        
        command.status = status
        command.completed_at = datetime.utcnow()
        command.result = data.get('result', '')
        db.session.commit()
        
        response_time = (time.time() - start_time) * 1000
        log_api_request(device.id, f'/api/device/commands/{command_id}/complete', 'POST', 200, response_time)
        
        return jsonify({'message': 'Command completed'}), 200
    
    except Exception as e:
        current_app.logger.error(f'Error completing command: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint (no authentication required)
    
    Response JSON:
    {
        "status": "healthy",
        "timestamp": "2025-10-31T10:00:00"
    }
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

# ============================================================================
# BACKUP API ENDPOINTS (Phase 4.5)
# ============================================================================

@api_bp.route('/backup/trigger', methods=['POST'])
def trigger_backup():
    """Trigger a backup via API (admin or API key required)"""
    from flask_login import current_user
    from utils.backup import BackupManager, BackupError
    
    # Check if user is authenticated admin OR has valid API key
    if not (current_user.is_authenticated and current_user.is_admin):
        # Fall back to API key authentication
        api_key = request.headers.get('X-Device-Key')
        if not api_key:
            return jsonify({'error': 'Authentication required'}), 401
        
        device = Device.query.filter_by(api_key=api_key).first()
        if not device:
            return jsonify({'error': 'Invalid API key'}), 401
    
    data = request.get_json() or {}
    backup_type = data.get('backup_type', 'full')
    description = data.get('description', 'API triggered backup')
    
    try:
        backup_manager = BackupManager()
        
        if backup_type == 'full':
            skip_videos = data.get('skip_videos', False)
            result = backup_manager.create_full_backup(description, skip_videos=skip_videos)
            return jsonify({
                'success': result['success'],
                'timestamp': result['timestamp'],
                'backups': {
                    'database': result.get('database'),
                    'videos': result.get('videos'),
                    'config': result.get('config')
                },
                'errors': result.get('errors', []),
                'skipped': result.get('skipped', [])
            }), 200
        
        elif backup_type == 'database':
            result = backup_manager.backup_database(description)
            return jsonify({
                'success': True,
                'type': 'database',
                'timestamp': result['timestamp'],
                'size': result['size'],
                'checksum': result['checksum']
            }), 200
        
        elif backup_type == 'videos':
            result = backup_manager.backup_videos(description)
            return jsonify({
                'success': True,
                'type': 'videos',
                'timestamp': result['timestamp'],
                'size': result['size'],
                'video_count': result['video_count'],
                'thumbnail_count': result['thumbnail_count']
            }), 200
        
        else:
            return jsonify({'error': f'Invalid backup type: {backup_type}'}), 400
    
    except BackupError as e:
        api_logger.error(f'API backup failed: {e}')
        return jsonify({'error': str(e)}), 500
    
    except Exception as e:
        api_logger.error(f'Unexpected API backup error: {e}')
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/backup/status', methods=['GET'])
def backup_status():
    """Get backup statistics and latest backup info (admin or API key required)"""
    from flask_login import current_user
    from utils.backup import BackupManager
    
    # Check authentication
    if not (current_user.is_authenticated and current_user.is_admin):
        api_key = request.headers.get('X-Device-Key')
        if not api_key or not Device.query.filter_by(api_key=api_key).first():
            return jsonify({'error': 'Authentication required'}), 401
    
    try:
        backup_manager = BackupManager()
        stats = backup_manager.get_backup_stats()
        latest_backups = backup_manager.list_backups()[:5]  # Last 5 backups
        
        return jsonify({
            'stats': stats,
            'latest_backups': [
                {
                    'type': b['type'],
                    'timestamp': b['timestamp'],
                    'size': b['size'],
                    'description': b.get('description', '')
                }
                for b in latest_backups
            ]
        }), 200
    
    except Exception as e:
        api_logger.error(f'API backup status error: {e}')
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/backup/list', methods=['GET'])
def list_backups_api():
    """List all backups via API (admin or API key required)"""
    from flask_login import current_user
    from utils.backup import BackupManager
    
    # Check authentication
    if not (current_user.is_authenticated and current_user.is_admin):
        api_key = request.headers.get('X-Device-Key')
        if not api_key or not Device.query.filter_by(api_key=api_key).first():
            return jsonify({'error': 'Authentication required'}), 401
    
    backup_type = request.args.get('type')  # Optional filter
    
    try:
        backup_manager = BackupManager()
        backups = backup_manager.list_backups(backup_type)
        
        return jsonify({
            'backups': [
                {
                    'type': b['type'],
                    'timestamp': b['timestamp'],
                    'filename': b['filename'],
                    'size': b['size'],
                    'checksum': b['checksum'],
                    'description': b.get('description', '')
                }
                for b in backups
            ],
            'count': len(backups)
        }), 200
    
    except Exception as e:
        api_logger.error(f'API list backups error: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# CONTENT LISTING ENDPOINTS (for UI dropdowns)
# ============================================================================

@api_bp.route('/videos', methods=['GET'])
def list_videos():
    """Get list of all videos for dropdowns"""
    try:
        videos = Video.query.order_by(Video.title).all()
        return jsonify({
            'videos': [{
                'id': v.id,
                'title': v.title,
                'filename': v.filename,
                'duration': v.duration
            } for v in videos]
        })
    except Exception as e:
        api_logger.error(f'Error listing videos: {e}')
        return jsonify({'error': 'Internal server error'}), 500


@api_bp.route('/playlists', methods=['GET'])
def list_playlists():
    """Get list of all playlists for dropdowns"""
    try:
        from models import Playlist
        playlists = Playlist.query.order_by(Playlist.name).all()
        return jsonify({
            'playlists': [{
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'video_count': p.videos.count()
            } for p in playlists]
        })
    except Exception as e:
        api_logger.error(f'Error listing playlists: {e}')
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@api_bp.errorhandler(500)
def api_internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


# Setup API logger file handler
def setup_api_logger(app):
    """Setup API-specific file logger"""
    handler = logging.FileHandler(app.config['API_LOG_FILE'])
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    api_logger.addHandler(handler)
    api_logger.setLevel(logging.INFO)
