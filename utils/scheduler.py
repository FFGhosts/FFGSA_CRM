"""
Scheduled Tasks Module
Handles background scheduled tasks like automatic backups
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
scheduler = None


def scheduled_backup_task(app):
    """
    Scheduled task to create automatic backups
    Runs at configured hour (default 2 AM)
    """
    with app.app_context():
        from utils.backup import BackupManager, BackupError
        from utils.notifications import NotificationService
        
        try:
            backup_manager = BackupManager()
            description = f"Automatic backup - {datetime.now().strftime('%Y-%m-%d')}"
            
            result = backup_manager.create_full_backup(description)
            
            if result['success']:
                logger.info(f"Scheduled backup completed successfully: {result['timestamp']}")
                
                # Calculate total backup size
                total_size_mb = sum(
                    result.get(key, {}).get('size', 0) 
                    for key in ['database', 'videos', 'config']
                )
                
                # Create success notification
                NotificationService.create_backup_success_alert(
                    'Full',
                    total_size_mb
                )
                
                # Cleanup old backups
                retention_days = app.config.get('BACKUP_RETENTION_DAYS', 30)
                deleted_count = backup_manager.cleanup_old_backups(retention_days)
                logger.info(f"Cleaned up {deleted_count} old backups")
            
            else:
                logger.error(f"Scheduled backup completed with errors: {result['errors']}")
                error_msg = '; '.join(result['errors'])
                
                # Create failure notification
                NotificationService.create_backup_failure_alert(
                    'Full',
                    error_msg
                )
        
        except BackupError as e:
            logger.error(f"Scheduled backup failed: {e}")
            NotificationService.create_backup_failure_alert('Full', str(e))
        
        except Exception as e:
            logger.error(f"Unexpected error in scheduled backup: {e}")
            NotificationService.create_backup_failure_alert('Full', str(e))


def send_backup_notification(app, result, success=True):
    """
    Send email notification about backup status
    
    Args:
        app: Flask application instance
        result: Backup result dictionary
        success: Whether backup was successful
    """
    # TODO: Implement email notification
    # This would require email configuration (SMTP settings)
    # For now, just log
    email = app.config.get('BACKUP_EMAIL')
    if email:
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"Would send backup notification to {email}: Status={status}")


def scheduled_health_check_task(app):
    """
    Scheduled task to check system health
    Runs every 5 minutes
    """
    with app.app_context():
        from utils.health_monitor import HealthMonitor
        
        try:
            health_results = HealthMonitor.check_all_health()
            logger.debug(f"Health check completed: {health_results['checked_at']}")
        
        except Exception as e:
            logger.error(f"Error in health check task: {e}")


def init_scheduler(app):
    """
    Initialize and start the background scheduler
    
    Args:
        app: Flask application instance
    """
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return
    
    try:
        scheduler = BackgroundScheduler()
        
        # Schedule daily backup at configured hour
        if app.config.get('BACKUP_SCHEDULE_ENABLED'):
            backup_hour = app.config.get('BACKUP_SCHEDULE_HOUR', 2)
            
            scheduler.add_job(
                func=scheduled_backup_task,
                trigger=CronTrigger(hour=backup_hour, minute=0),
                args=[app],
                id='daily_backup',
                name='Daily automatic backup',
                replace_existing=True
            )
            logger.info(f"Backup scheduler started - Daily backups at {backup_hour}:00")
        
        # Schedule health checks every 5 minutes
        scheduler.add_job(
            func=scheduled_health_check_task,
            trigger=CronTrigger(minute='*/5'),
            args=[app],
            id='health_check',
            name='System health monitoring',
            replace_existing=True
        )
        logger.info("Health monitoring started - Checks every 5 minutes")
        
        scheduler.start()
        logger.info("Scheduler started successfully")
    
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {e}")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully"""
    global scheduler
    
    if scheduler is not None:
        try:
            scheduler.shutdown(wait=False)
            logger.info("Backup scheduler shut down")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
