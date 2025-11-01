"""
System Health Monitor for Phase 6
Monitors device status, storage, backups, and other system health metrics
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os
from flask import current_app
from models import db, Device, Video, Notification, NotificationType, NotificationPriority
from utils.notifications import NotificationService


class HealthMonitor:
    """Monitors system health and creates alerts"""
    
    # Health check thresholds
    DEVICE_OFFLINE_THRESHOLD = 10  # minutes
    STORAGE_WARNING_THRESHOLD = 80  # percent
    STORAGE_CRITICAL_THRESHOLD = 90  # percent
    BACKUP_WARNING_AGE = 7  # days
    
    @staticmethod
    def check_all_health() -> Dict[str, Any]:
        """
        Run all health checks
        
        Returns:
            Dict with health status for all components
        """
        results = {
            'checked_at': datetime.utcnow().isoformat(),
            'devices': HealthMonitor.check_device_health(),
            'storage': HealthMonitor.check_storage_health(),
            'backups': HealthMonitor.check_backup_health(),
            'system': HealthMonitor.check_system_health()
        }
        
        current_app.logger.info(f"Health check completed: {sum(len(v.get('alerts', [])) for v in results.values() if isinstance(v, dict))} alerts")
        
        return results
    
    @staticmethod
    def check_device_health() -> Dict[str, Any]:
        """
        Check device health status
        
        Returns:
            Dict with device health status and alerts
        """
        now = datetime.utcnow()
        offline_threshold = now - timedelta(minutes=HealthMonitor.DEVICE_OFFLINE_THRESHOLD)
        
        devices = Device.query.filter_by(is_active=True).all()
        
        online_devices = []
        offline_devices = []
        alerts = []
        
        for device in devices:
            if device.last_seen and device.last_seen > offline_threshold:
                online_devices.append({
                    'id': device.id,
                    'name': device.name,
                    'last_seen': device.last_seen.isoformat()
                })
            else:
                # Calculate how long device has been offline
                if device.last_seen:
                    offline_minutes = int((now - device.last_seen).total_seconds() / 60)
                else:
                    offline_minutes = 9999  # Never seen
                
                offline_devices.append({
                    'id': device.id,
                    'name': device.name,
                    'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                    'offline_minutes': offline_minutes
                })
                
                # Check if we've already alerted for this device recently
                recent_alert = Notification.query.filter(
                    Notification.category == 'device_offline',
                    Notification.related_entity_type == 'device',
                    Notification.related_entity_id == device.id,
                    Notification.created_at > now - timedelta(hours=1)
                ).first()
                
                if not recent_alert:
                    # Create alert notification
                    notification = NotificationService.create_device_offline_alert(
                        device.id,
                        device.name,
                        offline_minutes
                    )
                    alerts.append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'offline_minutes': offline_minutes,
                        'notification_id': notification.id
                    })
        
        return {
            'total_devices': len(devices),
            'online': len(online_devices),
            'offline': len(offline_devices),
            'online_devices': online_devices,
            'offline_devices': offline_devices,
            'alerts': alerts
        }
    
    @staticmethod
    def check_storage_health() -> Dict[str, Any]:
        """
        Check storage health status
        
        Returns:
            Dict with storage health status and alerts
        """
        import psutil
        from utils.storage_management import get_storage_statistics
        
        alerts = []
        
        try:
            # Get disk usage for the drive where app is running
            disk_usage = psutil.disk_usage('/')
            used_percent = disk_usage.percent
            used_gb = disk_usage.used / (1024 ** 3)
            total_gb = disk_usage.total / (1024 ** 3)
            
            # Check if storage is above warning threshold
            if used_percent >= HealthMonitor.STORAGE_CRITICAL_THRESHOLD:
                # Critical level
                recent_alert = Notification.query.filter(
                    Notification.category == 'storage_warning',
                    Notification.priority.in_(['high', 'urgent']),
                    Notification.created_at > datetime.utcnow() - timedelta(hours=6)
                ).first()
                
                if not recent_alert:
                    notification = NotificationService.create_storage_warning_alert(
                        used_percent,
                        used_gb,
                        total_gb
                    )
                    alerts.append({
                        'level': 'critical',
                        'used_percent': used_percent,
                        'notification_id': notification.id
                    })
            
            elif used_percent >= HealthMonitor.STORAGE_WARNING_THRESHOLD:
                # Warning level
                recent_alert = Notification.query.filter(
                    Notification.category == 'storage_warning',
                    Notification.created_at > datetime.utcnow() - timedelta(hours=12)
                ).first()
                
                if not recent_alert:
                    notification = NotificationService.create_storage_warning_alert(
                        used_percent,
                        used_gb,
                        total_gb
                    )
                    alerts.append({
                        'level': 'warning',
                        'used_percent': used_percent,
                        'notification_id': notification.id
                    })
            
            # Get video storage statistics
            storage_info = get_storage_statistics()
            
            return {
                'total_gb': total_gb,
                'used_gb': used_gb,
                'free_gb': total_gb - used_gb,
                'used_percent': used_percent,
                'video_count': storage_info['video_count'],
                'video_storage_gb': storage_info['total_size_gb'],
                'status': 'critical' if used_percent >= HealthMonitor.STORAGE_CRITICAL_THRESHOLD 
                         else 'warning' if used_percent >= HealthMonitor.STORAGE_WARNING_THRESHOLD 
                         else 'healthy',
                'alerts': alerts
            }
        except Exception as e:
            # If psutil or storage check fails, return basic info
            return {
                'status': 'unknown',
                'error': str(e),
                'alerts': []
            }
    
    @staticmethod
    def check_backup_health() -> Dict[str, Any]:
        """
        Check backup health status
        
        Returns:
            Dict with backup health status and alerts
        """
        from utils.backup import BackupManager
        
        backup_dir = os.path.join(current_app.root_path, 'backups')
        alerts = []
        
        # Check each backup type
        backup_status = {}
        for backup_type in ['database', 'videos', 'config']:
            type_dir = os.path.join(backup_dir, backup_type)
            
            if os.path.exists(type_dir):
                backup_mgr = BackupManager()
                backups = backup_mgr.list_backups(backup_type)
                
                if backups:
                    latest = backups[0]
                    age_days = (datetime.utcnow() - datetime.strptime(
                        latest['timestamp'], '%Y%m%d_%H%M%S'
                    )).days
                    
                    backup_status[backup_type] = {
                        'latest_backup': latest['timestamp'],
                        'age_days': age_days,
                        'status': 'warning' if age_days >= HealthMonitor.BACKUP_WARNING_AGE else 'healthy'
                    }
                    
                    # Alert if backup is too old
                    if age_days >= HealthMonitor.BACKUP_WARNING_AGE:
                        recent_alert = Notification.query.filter(
                            Notification.category == 'backup_failure',
                            Notification.message.like(f'%{backup_type}%'),
                            Notification.created_at > datetime.utcnow() - timedelta(days=1)
                        ).first()
                        
                        if not recent_alert:
                            notification = NotificationService.create_notification(
                                title=f"Backup Outdated: {backup_type.title()}",
                                message=f"Last {backup_type} backup is {age_days} days old",
                                notification_type=NotificationType.WARNING,
                                priority=NotificationPriority.HIGH,
                                category='backup_failure',
                                action_url='/backup',
                                icon='bi-exclamation-triangle-fill',
                                expires_in_hours=48
                            )
                            alerts.append({
                                'type': backup_type,
                                'age_days': age_days,
                                'notification_id': notification.id
                            })
                else:
                    backup_status[backup_type] = {
                        'status': 'no_backups',
                        'age_days': None
                    }
            else:
                backup_status[backup_type] = {
                    'status': 'not_configured',
                    'age_days': None
                }
        
        return {
            'backup_types': backup_status,
            'alerts': alerts
        }
    
    @staticmethod
    def check_system_health() -> Dict[str, Any]:
        """
        Check general system health
        
        Returns:
            Dict with system health status
        """
        # Count videos
        total_videos = Video.query.count()
        
        # Count active devices
        active_devices = Device.query.filter_by(is_active=True).count()
        
        # Get unread notification count (system-wide)
        unread_notifications = Notification.query.filter_by(
            is_read=False,
            is_dismissed=False
        ).count()
        
        return {
            'total_videos': total_videos,
            'active_devices': active_devices,
            'unread_notifications': unread_notifications,
            'status': 'healthy'
        }
    
    @staticmethod
    def check_schedule_conflicts():
        """
        Check for schedule conflicts and create alerts
        
        This should be called when schedules are created/modified
        """
        from models import Schedule
        from utils.schedule_utils import get_schedule_conflicts
        
        now = datetime.now()
        alerts = []
        
        # Check active schedules for conflicts
        active_schedules = Schedule.query.filter(
            Schedule.is_active == True,
            db.or_(
                Schedule.end_date.is_(None),
                Schedule.end_date >= now.date()
            )
        ).all()
        
        checked_pairs = set()
        
        for schedule in active_schedules:
            conflicts = get_schedule_conflicts(schedule, now.date())
            
            for conflict in conflicts:
                # Create unique pair identifier to avoid duplicate alerts
                pair_key = tuple(sorted([conflict.schedule1.id, conflict.schedule2.id]))
                
                if pair_key not in checked_pairs:
                    checked_pairs.add(pair_key)
                    
                    # Check for recent alert about this conflict
                    recent_alert = Notification.query.filter(
                        Notification.category == 'schedule_conflict',
                        Notification.message.like(f'%{conflict.schedule1.name}%'),
                        Notification.message.like(f'%{conflict.schedule2.name}%'),
                        Notification.created_at > datetime.utcnow() - timedelta(days=1)
                    ).first()
                    
                    if not recent_alert:
                        notification = NotificationService.create_schedule_conflict_alert(
                            conflict.schedule1.name,
                            conflict.schedule2.name
                        )
                        alerts.append({
                            'schedule1': conflict.schedule1.name,
                            'schedule2': conflict.schedule2.name,
                            'notification_id': notification.id
                        })
        
        return {
            'conflicts_found': len(alerts),
            'alerts': alerts
        }
