"""
Phase 5 Migration: Enhanced Scheduling & Calendar
Adds recurring schedule patterns and schedule exceptions
"""
from app import create_app
from models import db, Schedule
from sqlalchemy import inspect, text
import sys

def migrate_schedules():
    """Add enhanced scheduling fields to Schedule model"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('schedules')]
        
        print("Current Schedule columns:", existing_columns)
        
        migrations = []
        
        # Recurrence type (none, daily, weekly, monthly, yearly)
        if 'recurrence_type' not in existing_columns:
            migrations.append(
                "ALTER TABLE schedules ADD COLUMN recurrence_type VARCHAR(20) DEFAULT 'weekly'"
            )
            print("  → Will add 'recurrence_type' column")
        
        # Recurrence interval (e.g., every 2 weeks, every 3 months)
        if 'recurrence_interval' not in existing_columns:
            migrations.append(
                "ALTER TABLE schedules ADD COLUMN recurrence_interval INTEGER DEFAULT 1"
            )
            print("  → Will add 'recurrence_interval' column")
        
        # Recurrence end date (when to stop repeating)
        if 'recurrence_end_date' not in existing_columns:
            migrations.append(
                "ALTER TABLE schedules ADD COLUMN recurrence_end_date DATE NULL"
            )
            print("  → Will add 'recurrence_end_date' column")
        
        # All day event flag
        if 'is_all_day' not in existing_columns:
            migrations.append(
                "ALTER TABLE schedules ADD COLUMN is_all_day BOOLEAN DEFAULT 0"
            )
            print("  → Will add 'is_all_day' column")
        
        # Color for calendar display
        if 'color' not in existing_columns:
            migrations.append(
                "ALTER TABLE schedules ADD COLUMN color VARCHAR(7) DEFAULT '#3788d8'"
            )
            print("  → Will add 'color' column")
        
        if not migrations:
            print("✓ Schedule table already has all required columns")
            return True
        
        print(f"\nApplying {len(migrations)} migration(s)...")
        
        try:
            for migration in migrations:
                db.session.execute(text(migration))
            
            db.session.commit()
            print("✓ Schedule table migration completed successfully")
            return True
            
        except Exception as e:
            print(f"✗ Migration failed: {str(e)}")
            db.session.rollback()
            return False


def create_schedule_exceptions_table():
    """Create ScheduleException table for date-specific overrides"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'schedule_exceptions' in tables:
            print("✓ ScheduleException table already exists")
            return True
        
        print("Creating ScheduleException table...")
        
        try:
            db.session.execute(text("""
                CREATE TABLE schedule_exceptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id INTEGER NOT NULL,
                    exception_date DATE NOT NULL,
                    exception_type VARCHAR(20) NOT NULL,
                    override_video_id INTEGER NULL,
                    override_playlist_id INTEGER NULL,
                    reason TEXT NULL,
                    created_by INTEGER NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (schedule_id) REFERENCES schedules (id) ON DELETE CASCADE,
                    FOREIGN KEY (override_video_id) REFERENCES videos (id) ON DELETE SET NULL,
                    FOREIGN KEY (override_playlist_id) REFERENCES playlists (id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
                )
            """))
            
            # Create index for efficient lookups
            db.session.execute(text("""
                CREATE INDEX idx_schedule_exceptions_date 
                ON schedule_exceptions(schedule_id, exception_date)
            """))
            
            db.session.commit()
            print("✓ ScheduleException table created successfully")
            return True
            
        except Exception as e:
            print(f"✗ Table creation failed: {str(e)}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("Phase 5: Enhanced Scheduling & Calendar Migration")
    print("=" * 60)
    print()
    
    success = True
    
    # Step 1: Migrate schedules table
    print("Step 1: Migrating Schedule table...")
    if not migrate_schedules():
        success = False
    print()
    
    # Step 2: Create schedule_exceptions table
    print("Step 2: Creating ScheduleException table...")
    if not create_schedule_exceptions_table():
        success = False
    print()
    
    if success:
        print("=" * 60)
        print("✓ Phase 5 migration completed successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("✗ Phase 5 migration failed!")
        print("=" * 60)
        sys.exit(1)
