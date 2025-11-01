"""
Database Migration Script
Adds new metadata fields to Video model
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

def migrate_database():
    """Add new columns to videos table"""
    app = create_app()
    
    with app.app_context():
        print("Starting database migration...")
        
        try:
            # Add new columns to videos table
            with db.engine.connect() as conn:
                # Check if columns already exist
                result = conn.execute(db.text("PRAGMA table_info(videos)"))
                columns = [row[1] for row in result.fetchall()]
                
                migrations = []
                
                if 'width' not in columns:
                    migrations.append("ALTER TABLE videos ADD COLUMN width INTEGER")
                if 'height' not in columns:
                    migrations.append("ALTER TABLE videos ADD COLUMN height INTEGER")
                if 'codec' not in columns:
                    migrations.append("ALTER TABLE videos ADD COLUMN codec VARCHAR(50)")
                if 'bitrate' not in columns:
                    migrations.append("ALTER TABLE videos ADD COLUMN bitrate INTEGER")
                if 'framerate' not in columns:
                    migrations.append("ALTER TABLE videos ADD COLUMN framerate FLOAT")
                if 'video_format' not in columns:
                    migrations.append("ALTER TABLE videos ADD COLUMN video_format VARCHAR(50)")
                if 'has_thumbnail' not in columns:
                    migrations.append("ALTER TABLE videos ADD COLUMN has_thumbnail BOOLEAN DEFAULT 0")
                
                if migrations:
                    for migration in migrations:
                        print(f"Executing: {migration}")
                        conn.execute(db.text(migration))
                    conn.commit()
                    print(f"✅ Successfully added {len(migrations)} new columns")
                else:
                    print("ℹ️  All columns already exist, no migration needed")
            
            print("Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == '__main__':
    migrate_database()
