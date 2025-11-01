"""
Analytics Routes Blueprint
Dashboard for viewing system analytics and statistics
"""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from datetime import datetime, timedelta

from models import db, PlaybackLog, ViewCount, DeviceUsage, Video, Device
from utils.analytics import (
    get_total_views, get_popular_videos, get_device_activity,
    get_storage_stats, get_daily_stats
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')


@analytics_bp.route('/')
@login_required
def index():
    """Analytics dashboard"""
    
    # Get summary statistics
    total_views = get_total_views()
    popular_videos = get_popular_videos(limit=10)
    activity = get_device_activity(days=30)
    storage = get_storage_stats()
    
    # Get most popular video
    most_popular = popular_videos[0] if popular_videos else None
    
    # Count active devices (seen in last 24 hours)
    active_devices = Device.query.filter(
        Device.last_seen >= datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    # Recent playback activity
    recent_logs = PlaybackLog.query.order_by(
        PlaybackLog.started_at.desc()
    ).limit(20).all()
    
    return render_template('analytics.html',
                         total_views=total_views,
                         most_popular=most_popular,
                         active_devices=active_devices,
                         storage=storage,
                         popular_videos=popular_videos,
                         activity=activity,
                         recent_logs=recent_logs)


@analytics_bp.route('/api/chart-data')
@login_required
def chart_data():
    """Get data for charts in JSON format"""
    
    # Popular videos data
    popular = get_popular_videos(limit=10)
    popular_data = {
        'labels': [v.title[:30] for v, vc in popular],
        'views': [vc.total_views for v, vc in popular]
    }
    
    # Device activity data
    activity = get_device_activity(days=30)
    activity_data = {
        'labels': [a.date.strftime('%Y-%m-%d') for a in activity],
        'devices': [a.active_devices for a in activity],
        'playtime': [a.total_playtime // 3600 for a in activity]  # Convert to hours
    }
    
    # Storage data
    storage = get_storage_stats()
    storage_data = {
        'used': storage['total_size'],
        'free': max(0, 100 * 1024 * 1024 * 1024 - storage['total_size'])  # Assume 100GB max
    }
    
    return jsonify({
        'popular': popular_data,
        'activity': activity_data,
        'storage': storage_data
    })


@analytics_bp.route('/video/<int:video_id>')
@login_required
def video_analytics(video_id):
    """Detailed analytics for a specific video"""
    video = Video.query.get_or_404(video_id)
    view_count = ViewCount.query.filter_by(video_id=video_id).first()
    
    # Get playback history
    playback_history = PlaybackLog.query.filter_by(
        video_id=video_id
    ).order_by(PlaybackLog.started_at.desc()).limit(50).all()
    
    return render_template('video_analytics.html',
                         video=video,
                         view_count=view_count,
                         playback_history=playback_history)


@analytics_bp.route('/device/<int:device_id>')
@login_required
def device_analytics(device_id):
    """Detailed analytics for a specific device"""
    device = Device.query.get_or_404(device_id)
    
    # Get usage statistics
    usage_stats = DeviceUsage.query.filter_by(
        device_id=device_id
    ).order_by(DeviceUsage.date.desc()).limit(30).all()
    
    # Get playback history
    playback_history = PlaybackLog.query.filter_by(
        device_id=device_id
    ).order_by(PlaybackLog.started_at.desc()).limit(50).all()
    
    return render_template('device_analytics.html',
                         device=device,
                         usage_stats=usage_stats,
                         playback_history=playback_history)
