"""
Analytics Utilities
Functions for calculating and aggregating analytics data
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, PlaybackLog, ViewCount, DeviceUsage, Video, Device


def get_total_views():
    """Get total video views across all devices"""
    return db.session.query(func.sum(ViewCount.total_views)).scalar() or 0


def get_popular_videos(limit=10):
    """Get most viewed videos"""
    return db.session.query(Video, ViewCount).join(
        ViewCount, Video.id == ViewCount.video_id
    ).order_by(ViewCount.total_views.desc()).limit(limit).all()


def get_device_activity(days=30):
    """Get device activity over specified days"""
    start_date = datetime.utcnow().date() - timedelta(days=days)
    
    activity = db.session.query(
        DeviceUsage.date,
        func.count(func.distinct(DeviceUsage.device_id)).label('active_devices'),
        func.sum(DeviceUsage.total_playtime).label('total_playtime')
    ).filter(
        DeviceUsage.date >= start_date
    ).group_by(DeviceUsage.date).order_by(DeviceUsage.date).all()
    
    return activity


def get_storage_stats():
    """Get storage usage statistics"""
    total_size = db.session.query(func.sum(Video.size)).scalar() or 0
    video_count = Video.query.count()
    
    # Group by resolution
    resolution_stats = db.session.query(
        Video.height,
        func.count(Video.id).label('count'),
        func.sum(Video.size).label('size')
    ).filter(Video.height.isnot(None)).group_by(Video.height).all()
    
    return {
        'total_size': total_size,
        'video_count': video_count,
        'resolution_stats': resolution_stats
    }


def get_daily_stats(days=7):
    """Get daily statistics for the last N days"""
    stats = []
    
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        
        # Total views for the day
        views = db.session.query(func.count(PlaybackLog.id)).filter(
            func.date(PlaybackLog.started_at) == date
        ).scalar() or 0
        
        # Active devices for the day
        devices = db.session.query(func.count(func.distinct(DeviceUsage.device_id))).filter(
            DeviceUsage.date == date
        ).scalar() or 0
        
        stats.append({
            'date': date,
            'views': views,
            'devices': devices
        })
    
    return list(reversed(stats))


def update_view_count(video_id, device_id):
    """Update view count for a video"""
    view_count = ViewCount.query.filter_by(video_id=video_id).first()
    
    if not view_count:
        view_count = ViewCount(video_id=video_id)
        db.session.add(view_count)
    
    view_count.total_views += 1
    view_count.last_viewed = datetime.utcnow()
    
    # Check if this is a unique device
    existing = db.session.query(PlaybackLog).filter(
        PlaybackLog.video_id == video_id,
        PlaybackLog.device_id == device_id
    ).first()
    
    if not existing:
        view_count.unique_devices += 1
    
    db.session.commit()


def update_device_usage(device_id, duration=0):
    """Update daily device usage statistics"""
    today = datetime.utcnow().date()
    
    usage = DeviceUsage.query.filter_by(
        device_id=device_id,
        date=today
    ).first()
    
    if not usage:
        usage = DeviceUsage(device_id=device_id, date=today)
        db.session.add(usage)
    
    usage.total_playtime += duration
    usage.videos_played += 1
    
    db.session.commit()
