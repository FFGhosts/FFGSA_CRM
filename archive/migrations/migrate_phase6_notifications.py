"""
Phase 6 Migration: Notification System & Alerts
Creates notification tables and preferences
"""
from app import create_app
from models import db
from sqlalchemy import inspect, text
import sys

def create_notifications_table():
    """Create notifications table"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        if 'notifications' in inspector.get_table_names():
            print("✓ Notifications table already exists")
            return True
        
        print("Creating notifications table...")
        
        try:
            db.session.execute(text("""
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NULL,
                    notification_type VARCHAR(20) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    priority VARCHAR(10) DEFAULT 'normal',
                    category VARCHAR(50) NULL,
                    related_entity_type VARCHAR(50) NULL,
                    related_entity_id INTEGER NULL,
                    is_read BOOLEAN DEFAULT 0,
                    is_dismissed BOOLEAN DEFAULT 0,
                    read_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NULL,
                    action_url VARCHAR(500) NULL,
                    icon VARCHAR(50) NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """))
            
            # Create indexes
            db.session.execute(text("""
                CREATE INDEX idx_notifications_user 
                ON notifications(user_id, is_read, created_at DESC)
            """))
            
            db.session.execute(text("""
                CREATE INDEX idx_notifications_type 
                ON notifications(notification_type, created_at DESC)
            """))
            
            db.session.commit()
            print("✓ Notifications table created successfully")
            return True
            
        except Exception as e:
            print(f"✗ Table creation failed: {str(e)}")
            db.session.rollback()
            return False


def create_notification_preferences_table():
    """Create notification preferences table"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        if 'notification_preferences' in inspector.get_table_names():
            print("✓ Notification preferences table already exists")
            return True
        
        print("Creating notification preferences table...")
        
        try:
            db.session.execute(text("""
                CREATE TABLE notification_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    email_enabled BOOLEAN DEFAULT 1,
                    browser_enabled BOOLEAN DEFAULT 1,
                    device_offline_email BOOLEAN DEFAULT 1,
                    device_offline_browser BOOLEAN DEFAULT 1,
                    upload_complete_email BOOLEAN DEFAULT 0,
                    upload_complete_browser BOOLEAN DEFAULT 1,
                    backup_success_email BOOLEAN DEFAULT 1,
                    backup_success_browser BOOLEAN DEFAULT 1,
                    backup_failure_email BOOLEAN DEFAULT 1,
                    backup_failure_browser BOOLEAN DEFAULT 1,
                    system_error_email BOOLEAN DEFAULT 1,
                    system_error_browser BOOLEAN DEFAULT 1,
                    schedule_conflict_email BOOLEAN DEFAULT 1,
                    schedule_conflict_browser BOOLEAN DEFAULT 1,
                    storage_warning_email BOOLEAN DEFAULT 1,
                    storage_warning_browser BOOLEAN DEFAULT 1,
                    daily_summary_email BOOLEAN DEFAULT 0,
                    weekly_report_email BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """))
            
            db.session.commit()
            print("✓ Notification preferences table created successfully")
            return True
            
        except Exception as e:
            print(f"✗ Table creation failed: {str(e)}")
            db.session.rollback()
            return False


def add_email_to_users():
    """Ensure users table has email notification field"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'email_notifications_enabled' not in existing_columns:
            print("Adding email_notifications_enabled column to users...")
            try:
                db.session.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN email_notifications_enabled BOOLEAN DEFAULT 1
                """))
                db.session.commit()
                print("✓ Column added successfully")
                return True
            except Exception as e:
                print(f"✗ Failed to add column: {str(e)}")
                db.session.rollback()
                return False
        else:
            print("✓ email_notifications_enabled column already exists")
            return True


if __name__ == '__main__':
    print("=" * 60)
    print("Phase 6: Notification System & Alerts Migration")
    print("=" * 60)
    print()
    
    success = True
    
    # Step 1: Create notifications table
    print("Step 1: Creating notifications table...")
    if not create_notifications_table():
        success = False
    print()
    
    # Step 2: Create notification preferences table
    print("Step 2: Creating notification preferences table...")
    if not create_notification_preferences_table():
        success = False
    print()
    
    # Step 3: Add email notification field to users
    print("Step 3: Updating users table...")
    if not add_email_to_users():
        success = False
    print()
    
    if success:
        print("=" * 60)
        print("✓ Phase 6 migration completed successfully!")
        print("=" * 60)
        print("\nNotification System Features:")
        print("  - In-app notifications with read/unread status")
        print("  - Email notifications for critical events")
        print("  - Per-user notification preferences")
        print("  - Real-time browser notifications via WebSockets")
        print("  - System health alerts")
        print("  - Notification history and center")
        print()
        sys.exit(0)
    else:
        print("=" * 60)
        print("✗ Phase 6 migration failed!")
        print("=" * 60)
        sys.exit(1)
