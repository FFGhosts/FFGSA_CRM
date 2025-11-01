"""
Permission Decorators and Activity Logging Utilities (Phase 4.2)
RBAC helper functions for route protection and audit logging
"""
from functools import wraps
from flask import abort, request, flash, redirect, url_for
from flask_login import current_user
from models import db, UserActivity
import json


def admin_required(f):
    """
    Decorator to restrict route access to Admin users only
    Usage: @admin_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('admin.login'))
        
        if not current_user.is_admin:
            flash('Administrator access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def operator_required(f):
    """
    Decorator to restrict route access to Operator and Admin users
    Usage: @operator_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('admin.login'))
        
        if not (current_user.is_admin or current_user.is_operator):
            flash('Operator or Administrator access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def content_manager_required(f):
    """
    Decorator for routes that manage content (videos, playlists)
    Allows Admin and Operator roles
    Usage: @content_manager_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('admin.login'))
        
        if not current_user.can_manage_content:
            flash('Content management access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


def device_manager_required(f):
    """
    Decorator for routes that manage devices
    Allows Admin and Operator roles
    Usage: @device_manager_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('admin.login'))
        
        if not current_user.can_manage_devices:
            flash('Device management access required.', 'danger')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ACTIVITY LOGGING UTILITIES
# ============================================================================

def log_activity(action, resource_type=None, resource_id=None, details=None):
    """
    Log user activity for audit trail
    
    Args:
        action (str): Action performed (e.g., 'login', 'upload_video', 'delete_device')
        resource_type (str): Type of resource affected ('video', 'device', 'user', 'playlist')
        resource_id (int): ID of the affected resource
        details (dict): Additional details about the action (will be JSON encoded)
    
    Example:
        log_activity('upload_video', 'video', video.id, {'filename': video.filename, 'size': video.size})
        log_activity('delete_device', 'device', device.id, {'name': device.name})
        log_activity('login', details={'method': 'password'})
    """
    if not current_user.is_authenticated:
        return
    
    try:
        activity = UserActivity(
            user_id=current_user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=request.remote_addr
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        # Don't fail the main operation if logging fails
        print(f"Error logging activity: {e}")
        db.session.rollback()


def log_activity_decorator(action, resource_type=None, get_resource_id=None):
    """
    Decorator to automatically log activity for a route
    
    Args:
        action (str): Action performed
        resource_type (str): Type of resource
        get_resource_id (callable): Function to extract resource_id from route kwargs
    
    Example:
        @log_activity_decorator('view_video', 'video', lambda kwargs: kwargs.get('id'))
        def view_video(id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the function first
            result = f(*args, **kwargs)
            
            # Log the activity
            resource_id = get_resource_id(kwargs) if get_resource_id else None
            log_activity(action, resource_type, resource_id)
            
            return result
        return decorated_function
    return decorator


def get_recent_activities(user_id=None, limit=50):
    """
    Get recent user activities
    
    Args:
        user_id (int): Filter by specific user ID (None = all users)
        limit (int): Maximum number of activities to return
    
    Returns:
        List of UserActivity objects
    """
    query = UserActivity.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    return query.order_by(UserActivity.timestamp.desc()).limit(limit).all()


def get_user_activity_summary(user_id, days=30):
    """
    Get activity summary for a user over specified days
    
    Args:
        user_id (int): User ID
        days (int): Number of days to look back
    
    Returns:
        dict: Summary statistics
    """
    from datetime import datetime, timedelta
    
    since_date = datetime.utcnow() - timedelta(days=days)
    
    activities = UserActivity.query.filter(
        UserActivity.user_id == user_id,
        UserActivity.timestamp >= since_date
    ).all()
    
    # Count by action type
    action_counts = {}
    for activity in activities:
        action_counts[activity.action] = action_counts.get(activity.action, 0) + 1
    
    return {
        'total_activities': len(activities),
        'action_counts': action_counts,
        'period_days': days,
        'first_activity': activities[-1].timestamp if activities else None,
        'last_activity': activities[0].timestamp if activities else None
    }
