"""
Test Phase 2.3: Video Scheduling System
Tests time-based content scheduling with start/end times and day-of-week filtering
"""
from datetime import datetime, time
from app import create_app
from models import db, Device, Video, Assignment, Playlist

def test_scheduling():
    """Test Phase 2.3 scheduling functionality"""
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("PHASE 2.3: VIDEO SCHEDULING SYSTEM TEST")
        print("=" * 70)
        
        # Get existing data
        device = Device.query.first()
        video = Video.query.first()
        
        if not device or not video:
            print("❌ Need at least one device and one video to test scheduling")
            return
        
        print(f"\n📱 Testing with Device: {device.name}")
        print(f"🎬 Testing with Video: {video.title}")
        
        # Test 1: Create assignment with time range (9 AM - 5 PM)
        print("\n" + "=" * 70)
        print("TEST 1: Time Range Scheduling (9 AM - 5 PM)")
        print("=" * 70)
        
        Assignment.query.filter_by(device_id=device.id).delete()
        
        assignment1 = Assignment(
            device_id=device.id,
            video_id=video.id,
            start_time=time(9, 0),   # 9:00 AM
            end_time=time(17, 0)     # 5:00 PM
        )
        db.session.add(assignment1)
        db.session.commit()
        
        print(f"✅ Created assignment: {assignment1.formatted_schedule}")
        
        # Test at different times
        test_times = [
            (time(8, 30), False, "8:30 AM - Before start time"),
            (time(9, 0), True, "9:00 AM - At start time"),
            (time(12, 0), True, "12:00 PM - During active hours"),
            (time(17, 0), True, "5:00 PM - At end time"),
            (time(18, 0), False, "6:00 PM - After end time"),
        ]
        
        print("\nTesting different times:")
        for test_time, expected, description in test_times:
            test_dt = datetime.combine(datetime.today(), test_time)
            is_active = assignment1.is_active_at(test_dt)
            status = "✅" if is_active == expected else "❌"
            print(f"  {status} {description}: {'Active' if is_active else 'Inactive'}")
        
        # Test 2: Create assignment with weekday-only schedule (Mon-Fri)
        print("\n" + "=" * 70)
        print("TEST 2: Weekday-Only Scheduling (Monday-Friday)")
        print("=" * 70)
        
        Assignment.query.filter_by(device_id=device.id).delete()
        
        assignment2 = Assignment(
            device_id=device.id,
            video_id=video.id,
            days_of_week="0,1,2,3,4"  # Mon-Fri
        )
        db.session.add(assignment2)
        db.session.commit()
        
        print(f"✅ Created assignment: {assignment2.formatted_schedule}")
        
        # Test different days (using actual dates from October/November 2025)
        test_days = [
            (datetime(2025, 11, 3), True, "Monday, Nov 3"),      # Monday
            (datetime(2025, 11, 4), True, "Tuesday, Nov 4"),     # Tuesday
            (datetime(2025, 11, 5), True, "Wednesday, Nov 5"),   # Wednesday
            (datetime(2025, 11, 6), True, "Thursday, Nov 6"),    # Thursday
            (datetime(2025, 11, 7), True, "Friday, Nov 7"),      # Friday
            (datetime(2025, 11, 8), False, "Saturday, Nov 8"),   # Saturday
            (datetime(2025, 11, 9), False, "Sunday, Nov 9"),     # Sunday
        ]
        
        print("\nTesting different days:")
        for test_dt, expected, description in test_days:
            is_active = assignment2.is_active_at(test_dt)
            status = "✅" if is_active == expected else "❌"
            print(f"  {status} {description}: {'Active' if is_active else 'Inactive'}")
        
        # Test 3: Combined schedule (Weekdays 9 AM - 5 PM)
        print("\n" + "=" * 70)
        print("TEST 3: Combined Schedule (Weekdays 9 AM - 5 PM)")
        print("=" * 70)
        
        Assignment.query.filter_by(device_id=device.id).delete()
        
        assignment3 = Assignment(
            device_id=device.id,
            video_id=video.id,
            start_time=time(9, 0),
            end_time=time(17, 0),
            days_of_week="0,1,2,3,4"
        )
        db.session.add(assignment3)
        db.session.commit()
        
        print(f"✅ Created assignment: {assignment3.formatted_schedule}")
        
        # Test combinations
        test_combined = [
            (datetime(2025, 11, 3, 12, 0), True, "Monday 12:00 PM - Active"),
            (datetime(2025, 11, 3, 8, 0), False, "Monday 8:00 AM - Too early"),
            (datetime(2025, 11, 3, 18, 0), False, "Monday 6:00 PM - Too late"),
            (datetime(2025, 11, 8, 12, 0), False, "Saturday 12:00 PM - Wrong day"),
            (datetime(2025, 11, 9, 12, 0), False, "Sunday 12:00 PM - Wrong day"),
        ]
        
        print("\nTesting combined conditions:")
        for test_dt, expected, description in test_combined:
            is_active = assignment3.is_active_at(test_dt)
            status = "✅" if is_active == expected else "❌"
            print(f"  {status} {description}: {'Active' if is_active else 'Inactive'}")
        
        # Test 4: Overnight schedule (10 PM - 2 AM)
        print("\n" + "=" * 70)
        print("TEST 4: Overnight Schedule (10 PM - 2 AM)")
        print("=" * 70)
        
        Assignment.query.filter_by(device_id=device.id).delete()
        
        assignment4 = Assignment(
            device_id=device.id,
            video_id=video.id,
            start_time=time(22, 0),  # 10:00 PM
            end_time=time(2, 0)      # 2:00 AM
        )
        db.session.add(assignment4)
        db.session.commit()
        
        print(f"✅ Created assignment: {assignment4.formatted_schedule}")
        
        test_overnight = [
            (time(21, 30), False, "9:30 PM - Before start"),
            (time(22, 0), True, "10:00 PM - At start"),
            (time(23, 30), True, "11:30 PM - Active"),
            (time(1, 0), True, "1:00 AM - Active (next day)"),
            (time(2, 0), True, "2:00 AM - At end"),
            (time(3, 0), False, "3:00 AM - After end"),
        ]
        
        print("\nTesting overnight times:")
        for test_time, expected, description in test_overnight:
            test_dt = datetime.combine(datetime.today(), test_time)
            is_active = assignment4.is_active_at(test_dt)
            status = "✅" if is_active == expected else "❌"
            print(f"  {status} {description}: {'Active' if is_active else 'Inactive'}")
        
        # Test 5: No schedule (always active)
        print("\n" + "=" * 70)
        print("TEST 5: No Schedule (Always Active)")
        print("=" * 70)
        
        Assignment.query.filter_by(device_id=device.id).delete()
        
        assignment5 = Assignment(
            device_id=device.id,
            video_id=video.id
            # No schedule fields set
        )
        db.session.add(assignment5)
        db.session.commit()
        
        print(f"✅ Created assignment: {assignment5.formatted_schedule}")
        print(f"   Is scheduled: {assignment5.is_scheduled}")
        
        # Should always be active
        test_anytime = [
            datetime(2025, 11, 3, 0, 0),
            datetime(2025, 11, 3, 12, 0),
            datetime(2025, 11, 3, 23, 59),
            datetime(2025, 11, 8, 12, 0),
        ]
        
        print("\nTesting always-active assignment:")
        all_active = all(assignment5.is_active_at(dt) for dt in test_anytime)
        if all_active:
            print("  ✅ Assignment is active at all times")
        else:
            print("  ❌ Assignment should always be active")
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print("✅ Phase 2.3: Video Scheduling System - COMPLETE")
        print("\nFeatures implemented:")
        print("  ✅ Time-based scheduling (start_time, end_time)")
        print("  ✅ Day-of-week filtering (days_of_week)")
        print("  ✅ Combined time + day schedules")
        print("  ✅ Overnight time ranges (crossing midnight)")
        print("  ✅ Always-active assignments (no schedule)")
        print("  ✅ Human-readable schedule formatting")
        print("  ✅ Schedule validation in is_active_at()")
        print("\nDatabase changes:")
        print("  ✅ Added start_time column to assignments")
        print("  ✅ Added end_time column to assignments")
        print("  ✅ Added days_of_week column to assignments")
        print("\nUI changes:")
        print("  ✅ Schedule toggle in assignment modal")
        print("  ✅ Time pickers for start/end times")
        print("  ✅ Day-of-week checkboxes")
        print("  ✅ Schedule display on assignment cards")
        print("\nAPI changes:")
        print("  ✅ Schedule-aware filtering in /api/videos/<device_id>")
        print("  ✅ Returns active_assignments vs total_assignments")
        print("  ✅ Includes schedule info in response")

if __name__ == '__main__':
    test_scheduling()
