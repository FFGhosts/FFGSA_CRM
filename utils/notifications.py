"""
Notification Service for Phase 6
Handles creating and sending notifications via multiple channels
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from flask import current_app, url_for
from models import db, Notification, NotificationPreference, User, NotificationType, NotificationPriority


class NotificationService:
    """Service for managing notifications"""
    
    @staticmethod
    def create_notification(
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        user_id: Optional[int] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        category: Optional[str] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        action_url: Optional[str] = None,
        icon: Optional[str] = None,
        expires_in_hours: Optional[int] = None
    ) -> Notification:
        """
        Create a new notification
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification
            user_id: User ID (None = all users)
            priority: Priority level
            category: Category (device, upload, backup, system)
            related_entity_type: Related entity type (device, video, etc)
            related_entity_id: Related entity ID
            action_url: URL for action button
            icon: Bootstrap icon class
            expires_in_hours: Auto-expire after N hours
        
        Returns:
            Created Notification object
        """
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            category=category,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            action_url=action_url,
            icon=icon,
            expires_at=expires_at
        )
        
        db.session.add(notification)
        db.session.commit()
        
        current_app.logger.info(f"Created notification: {title} (type={notification_type.value})")
        
        # Broadcast to browser if WebSocket enabled
        if user_id:
            NotificationService.broadcast_notification(notification)
        
        # Send email if configured
        if category:
            NotificationService.send_email_notification(notification, category)
        
        return notification
    
    @staticmethod
    def broadcast_notification(notification: Notification):
        """
        Broadcast notification via WebSocket
        
        Args:
            notification: Notification to broadcast
        """
        try:
            from socketio_events import socketio
            
            # Check user preference
            if notification.user_id:
                prefs = NotificationPreference.query.filter_by(
                    user_id=notification.user_id
                ).first()
                
                if prefs and notification.category:
                    if not prefs.should_notify(notification.category, 'browser'):
                        return
            
            notification_data = {
                'id': notification.id,
                'type': notification.notification_type.value,
                'title': notification.title,
                'message': notification.message,
                'priority': notification.priority.value,
                'category': notification.category,
                'icon': notification.icon,
                'action_url': notification.action_url,
                'created_at': notification.created_at.isoformat()
            }
            
            # Emit to specific user or broadcast to all
            if notification.user_id:
                socketio.emit('notification', notification_data, 
                            room=f'user_{notification.user_id}')
            else:
                socketio.emit('notification', notification_data, 
                            broadcast=True)
            
            current_app.logger.debug(f"Broadcasted notification {notification.id}")
        
        except Exception as e:
            current_app.logger.error(f"Failed to broadcast notification: {e}")
    
    @staticmethod
    def send_email_notification(notification: Notification, category: str):
        """
        Send email notification if user has it enabled
        
        Args:
            notification: Notification to send
            category: Notification category
        """
        try:
            from flask_mail import Message
            from app import mail
            from flask import render_template, url_for
            
            # Skip if email is suppressed (dev mode)
            if current_app.config.get('MAIL_SUPPRESS_SEND', True):
                current_app.logger.debug(f"Email suppressed (dev mode): {notification.title}")
                return
            
            # Skip if no email credentials configured
            if not current_app.config.get('MAIL_USERNAME'):
                current_app.logger.debug("Email not configured, skipping")
                return
            
            # Build base URL for links
            base_url = current_app.config.get('SERVER_NAME') or 'http://localhost:5000'
            if not base_url.startswith('http'):
                base_url = f'http://{base_url}'
            
            # If notification is for specific user
            if notification.user_id:
                user = User.query.get(notification.user_id)
                if user and user.email:
                    prefs = NotificationPreference.query.filter_by(
                        user_id=user.id
                    ).first()
                    
                    if prefs and prefs.should_notify(category, 'email'):
                        NotificationService._send_email(user.email, notification, base_url)
            
            # If notification is for all admins
            else:
                admins = User.query.filter_by(is_admin=True).all()
                for admin in admins:
                    if admin.email:
                        prefs = NotificationPreference.query.filter_by(
                            user_id=admin.id
                        ).first()
                        
                        if prefs and prefs.should_notify(category, 'email'):
                            NotificationService._send_email(admin.email, notification, base_url)
        
        except Exception as e:
            current_app.logger.error(f"Failed to send email notification: {e}")
    
    @staticmethod
    def _send_email(recipient_email: str, notification: Notification, base_url: str):
        """
        Actually send the email
        
        Args:
            recipient_email: Email address to send to
            notification: Notification object
            base_url: Base URL for action links
        """
        try:
            from flask_mail import Message
            from app import mail
            from flask import render_template
            
            msg = Message(
                subject=f"[FFGSA_CSM] {notification.title}",
                recipients=[recipient_email],
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            # Render HTML email from template
            msg.html = render_template(
                'emails/notification.html',
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type.value,
                priority=notification.priority.value,
                category=notification.category,
                action_url=notification.action_url,
                related_entity_type=notification.related_entity_type,
                related_entity_id=notification.related_entity_id,
                timestamp=notification.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                base_url=base_url
            )
            
            # Plain text fallback
            msg.body = f"""
{notification.title}

{notification.message}

Category: {notification.category}
Priority: {notification.priority.value}
Time: {notification.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

{"View details: " + base_url + notification.action_url if notification.action_url else ""}

---
This is an automated notification from your FFGSA_CSM system.
Manage notification preferences: {base_url}/notifications
            """.strip()
            
            mail.send(msg)
            current_app.logger.info(f"Email sent to {recipient_email}: {notification.title}")
        
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {recipient_email}: {e}")
    
    @staticmethod
    def get_unread_notifications(user_id: int, limit: int = 10) -> List[Notification]:
        """
        Get unread notifications for user
        
        Args:
            user_id: User ID
            limit: Maximum number of notifications
        
        Returns:
            List of unread notifications
        """
        return Notification.query.filter_by(
            user_id=user_id,
            is_read=False,
            is_dismissed=False
        ).order_by(
            Notification.priority.desc(),
            Notification.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_all_notifications(
        user_id: int, 
        include_read: bool = True,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get all notifications for user
        
        Args:
            user_id: User ID
            include_read: Include read notifications
            limit: Maximum number of notifications
        
        Returns:
            List of notifications
        """
        query = Notification.query.filter_by(user_id=user_id, is_dismissed=False)
        
        if not include_read:
            query = query.filter_by(is_read=False)
        
        return query.order_by(
            Notification.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """
        Mark notification as read
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for security)
        
        Returns:
            True if successful
        """
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.mark_as_read()
            db.session.commit()
            return True
        
        return False
    
    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """
        Mark all notifications as read for user
        
        Args:
            user_id: User ID
        
        Returns:
            Number of notifications marked as read
        """
        count = Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })
        
        db.session.commit()
        return count
    
    @staticmethod
    def dismiss_notification(notification_id: int, user_id: int) -> bool:
        """
        Dismiss notification (soft delete)
        
        Args:
            notification_id: Notification ID
            user_id: User ID (for security)
        
        Returns:
            True if successful
        """
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.is_dismissed = True
            db.session.commit()
            return True
        
        return False
    
    @staticmethod
    def cleanup_old_notifications(days: int = 30) -> int:
        """
        Delete expired or old dismissed notifications
        
        Args:
            days: Delete notifications older than N days
        
        Returns:
            Number of notifications deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Delete expired
        expired_count = Notification.query.filter(
            Notification.expires_at < datetime.utcnow()
        ).delete()
        
        # Delete old dismissed
        old_dismissed = Notification.query.filter(
            Notification.is_dismissed == True,
            Notification.created_at < cutoff_date
        ).delete()
        
        db.session.commit()
        
        total = expired_count + old_dismissed
        current_app.logger.info(f"Cleaned up {total} old notifications")
        
        return total
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """
        Get count of unread notifications for user
        
        Args:
            user_id: User ID
        
        Returns:
            Number of unread notifications
        """
        return Notification.query.filter_by(
            user_id=user_id,
            is_read=False,
            is_dismissed=False
        ).count()
    
    @staticmethod
    def create_device_offline_alert(device_id: int, device_name: str, minutes_offline: int):
        """Helper: Create device offline alert"""
        return NotificationService.create_notification(
            title=f"Device Offline: {device_name}",
            message=f"Device has been offline for {minutes_offline} minutes.",
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH,
            category='device_offline',
            related_entity_type='device',
            related_entity_id=device_id,
            action_url=f"/devices/{device_id}",
            icon='bi-exclamation-triangle-fill',
            expires_in_hours=24
        )
    
    @staticmethod
    def create_backup_success_alert(backup_type: str, size_mb: float):
        """Helper: Create backup success notification"""
        return NotificationService.create_notification(
            title="Backup Completed Successfully",
            message=f"{backup_type.title()} backup completed ({size_mb:.1f} MB)",
            notification_type=NotificationType.SUCCESS,
            category='backup_success',
            icon='bi-check-circle-fill',
            expires_in_hours=48
        )
    
    @staticmethod
    def create_backup_failure_alert(backup_type: str, error: str):
        """Helper: Create backup failure alert"""
        return NotificationService.create_notification(
            title="Backup Failed",
            message=f"{backup_type.title()} backup failed: {error}",
            notification_type=NotificationType.ERROR,
            priority=NotificationPriority.URGENT,
            category='backup_failure',
            action_url="/backup",
            icon='bi-x-circle-fill',
            expires_in_hours=72
        )
    
    @staticmethod
    def create_upload_complete_alert(user_id: int, video_title: str):
        """Helper: Create upload complete notification"""
        return NotificationService.create_notification(
            title="Video Upload Complete",
            message=f"'{video_title}' has been uploaded successfully",
            notification_type=NotificationType.SUCCESS,
            user_id=user_id,
            category='upload_complete',
            icon='bi-cloud-upload-fill',
            expires_in_hours=12
        )
    
    @staticmethod
    def create_storage_warning_alert(used_percent: float, used_gb: float, total_gb: float):
        """Helper: Create storage warning alert"""
        return NotificationService.create_notification(
            title="Storage Space Warning",
            message=f"Storage is {used_percent:.1f}% full ({used_gb:.1f}/{total_gb:.1f} GB used)",
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH,
            category='storage_warning',
            action_url="/storage",
            icon='bi-hdd-fill',
            expires_in_hours=24
        )
    
    @staticmethod
    def create_schedule_conflict_alert(schedule1_name: str, schedule2_name: str):
        """Helper: Create schedule conflict alert"""
        return NotificationService.create_notification(
            title="Schedule Conflict Detected",
            message=f"Schedules '{schedule1_name}' and '{schedule2_name}' have overlapping times",
            notification_type=NotificationType.WARNING,
            category='schedule_conflict',
            action_url="/schedules/calendar",
            icon='bi-calendar-x-fill',
            expires_in_hours=48
        )
