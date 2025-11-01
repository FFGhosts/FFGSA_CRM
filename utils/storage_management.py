"""
Storage Management Utilities
Functions for managing video storage, cleanup, and retention policies
"""
import os
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, Video, Assignment, PlaybackLog


def get_storage_statistics():
    """
    Get comprehensive storage statistics
    
    Returns:
        dict: Storage statistics including total size, usage breakdown, etc.
    """
    total_size = db.session.query(func.sum(Video.size)).scalar() or 0
    video_count = Video.query.count()
    
    # Get videos by assignment status
    assigned_videos = db.session.query(Video).join(Assignment).distinct().count()
    unassigned_videos = video_count - assigned_videos
    
    # Get videos by playback status
    played_videos = db.session.query(Video).join(PlaybackLog).distinct().count()
    never_played = video_count - played_videos
    
    return {
        'total_size': total_size,
        'total_size_gb': total_size / (1024 ** 3),
        'video_count': video_count,
        'assigned_videos': assigned_videos,
        'unassigned_videos': unassigned_videos,
        'played_videos': played_videos,
        'never_played': never_played
    }


def find_unused_videos(days_threshold=30):
    """
    Find videos that haven't been assigned or played in X days
    
    Args:
        days_threshold: Number of days to consider a video unused
        
    Returns:
        list: List of unused Video objects
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
    
    # Get all videos
    all_videos = Video.query.all()
    unused = []
    
    for video in all_videos:
        # Check if video has any active assignments
        has_active_assignments = Assignment.query.filter_by(video_id=video.id).first() is not None
        
        if has_active_assignments:
            continue
        
        # Check if video was played recently
        recent_playback = PlaybackLog.query.filter(
            PlaybackLog.video_id == video.id,
            PlaybackLog.started_at >= cutoff_date
        ).first()
        
        if not recent_playback:
            unused.append(video)
    
    return unused


def find_old_videos(days_threshold=90):
    """
    Find videos uploaded more than X days ago
    
    Args:
        days_threshold: Number of days to consider a video old
        
    Returns:
        list: List of old Video objects
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
    
    return Video.query.filter(Video.uploaded_at < cutoff_date).all()


def find_large_videos(size_threshold_mb=100):
    """
    Find videos larger than specified size
    
    Args:
        size_threshold_mb: Size threshold in megabytes
        
    Returns:
        list: List of large Video objects
    """
    size_bytes = size_threshold_mb * 1024 * 1024
    
    return Video.query.filter(Video.size > size_bytes).order_by(Video.size.desc()).all()


def calculate_potential_space_savings(video_ids):
    """
    Calculate how much space would be freed by deleting specified videos
    
    Args:
        video_ids: List of video IDs to check
        
    Returns:
        dict: Size information and breakdown
    """
    if not video_ids:
        return {'total_size': 0, 'total_size_gb': 0, 'video_count': 0}
    
    total_size = db.session.query(func.sum(Video.size)).filter(
        Video.id.in_(video_ids)
    ).scalar() or 0
    
    video_count = len(video_ids)
    
    return {
        'total_size': total_size,
        'total_size_gb': total_size / (1024 ** 3),
        'video_count': video_count
    }


def delete_videos_bulk(video_ids, delete_files=True, video_folder=None, thumbnail_folder=None):
    """
    Delete multiple videos at once
    
    Args:
        video_ids: List of video IDs to delete
        delete_files: Whether to delete physical files
        video_folder: Path to video storage folder
        thumbnail_folder: Path to thumbnail storage folder
        
    Returns:
        dict: Deletion results with success/failure counts
    """
    if not video_ids:
        return {'deleted': 0, 'failed': 0, 'errors': []}
    
    deleted = 0
    failed = 0
    errors = []
    
    for video_id in video_ids:
        try:
            video = Video.query.get(video_id)
            if not video:
                errors.append(f'Video ID {video_id} not found')
                failed += 1
                continue
            
            filename = video.filename
            
            # Delete database record (will cascade to assignments, playback logs, etc.)
            db.session.delete(video)
            db.session.commit()
            
            # Delete physical files if requested
            if delete_files and video_folder:
                video_path = os.path.join(video_folder, filename)
                if os.path.exists(video_path):
                    try:
                        os.remove(video_path)
                    except Exception as e:
                        errors.append(f'Failed to delete file {filename}: {e}')
                
                # Delete thumbnail if exists
                if thumbnail_folder:
                    thumbnail_name = os.path.splitext(filename)[0] + '.jpg'
                    thumbnail_path = os.path.join(thumbnail_folder, thumbnail_name)
                    if os.path.exists(thumbnail_path):
                        try:
                            os.remove(thumbnail_path)
                        except Exception as e:
                            errors.append(f'Failed to delete thumbnail {thumbnail_name}: {e}')
            
            deleted += 1
            
        except Exception as e:
            db.session.rollback()
            errors.append(f'Failed to delete video ID {video_id}: {e}')
            failed += 1
    
    return {
        'deleted': deleted,
        'failed': failed,
        'errors': errors
    }


def get_video_usage_info(video_id):
    """
    Get detailed usage information for a video
    
    Args:
        video_id: Video ID to check
        
    Returns:
        dict: Usage information including assignments, playback logs, etc.
    """
    video = Video.query.get(video_id)
    if not video:
        return None
    
    # Get assignment count
    assignment_count = Assignment.query.filter_by(video_id=video_id).count()
    
    # Get playback stats
    total_plays = PlaybackLog.query.filter_by(video_id=video_id).count()
    last_played = db.session.query(func.max(PlaybackLog.started_at)).filter_by(video_id=video_id).scalar()
    
    # Get unique devices that played this video
    unique_devices = db.session.query(func.count(func.distinct(PlaybackLog.device_id))).filter_by(video_id=video_id).scalar()
    
    return {
        'video_id': video_id,
        'filename': video.filename,
        'title': video.title,
        'size': video.size,
        'uploaded_at': video.uploaded_at,
        'assignment_count': assignment_count,
        'total_plays': total_plays,
        'last_played': last_played,
        'unique_devices': unique_devices,
        'is_assigned': assignment_count > 0,
        'has_been_played': total_plays > 0
    }
