"""
Database Migration: Add Advanced Scheduling
Phase 4.3: Time-based Content Scheduling

This migration adds:
1. schedules table for time-based content playback
2. Support for time ranges, day-of-week selection, date ranges
3. Priority-based conflict resolution
4. Device and device group targeting

Run this script once to update the database schema.
"""
from app import create_app
from models import db, Schedule
from sqlalchemy import inspect

def migrate():
    """Run scheduling migration"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("=" * 70)
        print("Advanced Scheduling Migration - Phase 4.3")
        print("=" * 70)
        
        # 1. Create schedules table
        print("\n1. Creating schedules table...")
        if not inspector.has_table('schedules'):
            try:
                Schedule.__table__.create(db.engine)
                db.session.commit()
                print("   ✓ Created schedules table")
            except Exception as e:
                print(f"   ✗ Error creating schedules table: {e}")
                db.session.rollback()
        else:
            print("   ⊙ schedules table already exists")
        
        # 2. Verify table structure
        print("\n2. Verifying schedules table structure...")
        try:
            columns = [col['name'] for col in inspector.get_columns('schedules')]
            required_columns = [
                'id', 'name', 'description', 
                'video_id', 'playlist_id',
                'device_id', 'device_group_id',
                'start_time', 'end_time',
                'days_of_week', 'start_date', 'end_date',
                'priority', 'is_recurring', 'is_active',
                'created_by', 'created_at', 'updated_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"   ⚠ Missing columns: {', '.join(missing_columns)}")
            else:
                print("   ✓ All required columns present")
            
            print(f"   ✓ Total columns: {len(columns)}")
            
        except Exception as e:
            print(f"   ✗ Verification error: {e}")
        
        # 3. Check existing schedules
        print("\n3. Checking existing schedules...")
        try:
            schedule_count = Schedule.query.count()
            print(f"   ✓ Current schedules: {schedule_count}")
            
            if schedule_count > 0:
                active_count = Schedule.query.filter_by(is_active=True).count()
                print(f"   ✓ Active schedules: {active_count}")
        except Exception as e:
            print(f"   ✗ Error checking schedules: {e}")
        
        print("\n" + "=" * 70)
        print("Migration completed!")
        print("=" * 70)
        print("\nScheduling Features:")
        print("  - Time-based playback (e.g., 9:00 AM - 5:00 PM)")
        print("  - Day-of-week selection (weekdays, weekends, custom)")
        print("  - Date range support (seasonal/holiday content)")
        print("  - Priority-based conflict resolution")
        print("  - Target specific devices or groups")
        print("  - Recurring and one-time schedules")
        print("\nNext steps:")
        print("  1. Create your first schedule from the web dashboard")
        print("  2. Test schedule conflicts and priority resolution")
        print("  3. Devices will automatically fetch scheduled content")
        print("=" * 70)


if __name__ == '__main__':
    migrate()
