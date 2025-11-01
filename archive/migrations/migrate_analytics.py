"""
Database migration: Add analytics tables
Phase 3.1: Analytics Dashboard
"""
from app import create_app
from models import db

def migrate():
    """Add analytics tables to database"""
    app = create_app()
    
    with app.app_context():
        print("Adding analytics tables to database...")
        
        try:
            with db.engine.connect() as conn:
                # Create playback_logs table
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS playback_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id INTEGER NOT NULL,
                        video_id INTEGER,
                        playlist_id INTEGER,
                        started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        ended_at DATETIME,
                        duration_played INTEGER,
                        FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                        FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                    )
                """))
                print("  ✅ Created playback_logs table")
                
                conn.execute(db.text("""
                    CREATE INDEX IF NOT EXISTS idx_playback_logs_started_at 
                    ON playback_logs(started_at)
                """))
                print("  ✅ Created index on playback_logs.started_at")
                
                # Create view_counts table
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS view_counts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        video_id INTEGER NOT NULL UNIQUE,
                        total_views INTEGER NOT NULL DEFAULT 0,
                        unique_devices INTEGER NOT NULL DEFAULT 0,
                        last_viewed DATETIME,
                        FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
                    )
                """))
                print("  ✅ Created view_counts table")
                
                # Create device_usage table
                conn.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS device_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id INTEGER NOT NULL,
                        date DATE NOT NULL,
                        total_playtime INTEGER NOT NULL DEFAULT 0,
                        videos_played INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                        UNIQUE(device_id, date)
                    )
                """))
                print("  ✅ Created device_usage table")
                
                conn.execute(db.text("""
                    CREATE INDEX IF NOT EXISTS idx_device_usage_date 
                    ON device_usage(date)
                """))
                print("  ✅ Created index on device_usage.date")
                
                conn.commit()
                
            print("\n✅ Migration completed successfully!")
            print("\nAnalytics tables added:")
            print("  - playback_logs: Tracks when devices play videos")
            print("  - view_counts: Aggregated view counts per video")
            print("  - device_usage: Daily device usage statistics")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  ℹ️  Tables already exist, skipping migration")
            else:
                print(f"\n❌ Migration failed: {e}")
                raise

if __name__ == '__main__':
    migrate()
