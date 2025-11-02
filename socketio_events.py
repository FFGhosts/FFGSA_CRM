"""
WebSocket Event Handlers (Phase 4.1)
Real-time event handling for device status, playback monitoring, and notifications
"""
from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_login import current_user
from app import socketio
import logging

logger = logging.getLogger(__name__)

# Track connected clients
connected_clients = {}


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if current_user.is_authenticated:
        client_id = request.sid
        user_room = f'user_{current_user.id}'
        
        # Join user-specific room for notifications
        join_room(user_room)
        
        connected_clients[client_id] = {
            'user_id': current_user.id,
            'username': current_user.username,
            'rooms': [user_room]
        }
        logger.info(f'Client connected: {current_user.username} (SID: {client_id})')
        emit('connection_response', {
            'status': 'connected',
            'message': 'Connected to real-time server',
            'client_id': client_id
        })
    else:
        logger.warning(f'Unauthenticated connection attempt from {request.sid}')
        disconnect()


@socketio.on('join')
def handle_join(data):
    """
    Handle client joining a room
    Rooms: 'devices', 'monitoring', 'dashboard'
    """
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    room = data.get('room')
    if room:
        join_room(room)
        client_id = request.sid
        if client_id in connected_clients:
            if 'rooms' not in connected_clients[client_id]:
                connected_clients[client_id]['rooms'] = []
            connected_clients[client_id]['rooms'].append(room)
        logger.info(f'Client {current_user.username} joined room: {room}')
        emit('room_joined', {'room': room})


@socketio.on('leave')
def handle_leave(data):
    """Handle client leaving a room"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    room = data.get('room')
    if room:
        leave_room(room)
        client_id = request.sid
        if client_id in connected_clients and 'rooms' in connected_clients[client_id]:
            connected_clients[client_id]['rooms'].remove(room)
        logger.info(f'Client {current_user.username} left room: {room}')
        emit('room_left', {'room': room})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    if client_id in connected_clients:
        user_info = connected_clients[client_id]
        logger.info(f'Client disconnected: {user_info["username"]} (SID: {client_id})')
        del connected_clients[client_id]


@socketio.on('join_room')
def handle_join_room(data):
    """
    Join a specific room for targeted broadcasts
    Rooms: 'dashboard', 'devices', 'analytics', 'monitoring'
    """
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    room = data.get('room')
    if not room:
        emit('error', {'message': 'Room name required'})
        return
    
    join_room(room)
    client_id = request.sid
    if client_id in connected_clients:
        if room not in connected_clients[client_id]['rooms']:
            connected_clients[client_id]['rooms'].append(room)
    
    logger.info(f'{current_user.username} joined room: {room}')
    emit('room_joined', {'room': room, 'status': 'success'})


@socketio.on('leave_room')
def handle_leave_room(data):
    """Leave a specific room"""
    if not current_user.is_authenticated:
        return
    
    room = data.get('room')
    if not room:
        return
    
    leave_room(room)
    client_id = request.sid
    if client_id in connected_clients:
        if room in connected_clients[client_id]['rooms']:
            connected_clients[client_id]['rooms'].remove(room)
    
    logger.info(f'{current_user.username} left room: {room}')
    emit('room_left', {'room': room, 'status': 'success'})


@socketio.on('ping')
def handle_ping():
    """Respond to ping (keep-alive)"""
    emit('pong', {'timestamp': str(__import__('datetime').datetime.utcnow())})


@socketio.on('request_device_status')
def handle_device_status_request(data):
    """
    Request current status of all devices
    Client requests this on page load
    """
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    from models import Device
    
    devices = Device.query.all()
    device_list = []
    
    for device in devices:
        device_list.append({
            'id': device.id,
            'name': device.name,
            'serial': device.serial,
            'is_online': device.is_online,
            'current_video': device.current_video,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'ip_address': device.ip_address
        })
    
    emit('device_status_update', {'devices': device_list})


@socketio.on('request_stats')
def handle_stats_request():
    """
    Request current dashboard statistics
    """
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    from models import Video, Device, Assignment
    
    stats = {
        'total_videos': Video.query.count(),
        'total_devices': Device.query.count(),
        'online_devices': sum(1 for d in Device.query.all() if d.is_online),
        'total_assignments': Assignment.query.count()
    }
    
    emit('stats_update', stats)


# ============================================================================
# SERVER-SIDE BROADCAST FUNCTIONS
# These are called from other parts of the application to push updates
# ============================================================================

def broadcast_device_status(device_id, status_data):
    """
    Broadcast device status update to all connected clients in 'devices' room
    
    Args:
        device_id: Device ID
        status_data: Dictionary with device status information
    """
    if socketio is not None:
        socketio.emit('device_status_changed', {
            'device_id': device_id,
            'data': status_data
        }, room='devices', namespace='/')


def broadcast_device_online(device_id, device_name):
    """Broadcast when device comes online"""
    if socketio is not None:
        socketio.emit('device_online', {
            'device_id': device_id,
            'device_name': device_name,
            'timestamp': str(__import__('datetime').datetime.utcnow())
        }, room='devices', namespace='/')


def broadcast_device_offline(device_id, device_name):
    """Broadcast when device goes offline"""
    if socketio is not None:
        socketio.emit('device_offline', {
            'device_id': device_id,
            'device_name': device_name,
            'timestamp': str(__import__('datetime').datetime.utcnow())
        }, room='devices', namespace='/')


def broadcast_playback_started(device_id, device_name, video_title):
    """Broadcast when device starts playing a video"""
    if socketio is not None:
        socketio.emit('playback_started', {
            'device_id': device_id,
            'device_name': device_name,
            'video_title': video_title,
            'timestamp': str(__import__('datetime').datetime.utcnow())
        }, room='monitoring', namespace='/')


def broadcast_playback_stopped(device_id, device_name):
    """Broadcast when device stops playback"""
    if socketio is not None:
        socketio.emit('playback_stopped', {
            'device_id': device_id,
            'device_name': device_name,
            'timestamp': str(__import__('datetime').datetime.utcnow())
        }, room='monitoring', namespace='/')


def broadcast_command_completed(device_id, device_name, command_type, status):
    """Broadcast when a remote command completes"""
    if socketio is not None:
        socketio.emit('command_completed', {
            'device_id': device_id,
            'device_name': device_name,
            'command_type': command_type,
            'status': status,
            'timestamp': str(__import__('datetime').datetime.utcnow())
        }, room='devices', namespace='/')


def broadcast_stats_update(stats):
    """Broadcast updated dashboard statistics"""
    socketio.emit('stats_update', stats, room='dashboard', namespace='/')


def broadcast_alert(alert_type, message, severity='info'):
    """
    Broadcast alert notification to all connected clients
    
    Args:
        alert_type: Type of alert (device_offline, error, success, etc.)
        message: Alert message
        severity: info, success, warning, error
    """
    socketio.emit('alert', {
        'type': alert_type,
        'message': message,
        'severity': severity,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    }, namespace='/')
