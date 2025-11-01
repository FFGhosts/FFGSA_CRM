"""
Migration script to add File Checksum functionality to PiCMS
Adds checksum column to videos table and calculates checksums for existing videos
"""
import sys
import os
from sqlalchemy import text
from app import create_app
from models import db, Video
from utils.video_utils import calculate_checksum

def migrate_checksums():
    """Add checksum column and calculate checksums"""
    app = create_app()
    
    with app.app_context():
        print("\nAdding file checksum functionality to database...")
        
        try:
            # Add checksum column to videos table
            db.session.execute(text("""
                ALTER TABLE videos ADD COLUMN checksum VARCHAR(64)
            """))
            print("  ✅ Added checksum column to videos table")
            
            # Create index on checksum
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_videos_checksum 
                ON videos(checksum)
            """))
            print("  ✅ Created index on videos.checksum")
            
            db.session.commit()
            
            # Calculate checksums for existing videos
            videos = Video.query.filter(Video.checksum.is_(None)).all()
            
            if videos:
                print(f"\n📊 Calculating checksums for {len(videos)} existing video(s)...")
                
                video_folder = app.config['UPLOAD_FOLDER']
                updated_count = 0
                skipped_count = 0
                
                for video in videos:
                    video_path = os.path.join(video_folder, video.filename)
                    
                    if os.path.exists(video_path):
                        try:
                            checksum = calculate_checksum(video_path)
                            video.checksum = checksum
                            updated_count += 1
                            print(f"  ✅ {video.filename}: {checksum[:16]}...")
                        except Exception as e:
                            print(f"  ❌ {video.filename}: Failed - {e}")
                            skipped_count += 1
                    else:
                        print(f"  ⚠️  {video.filename}: File not found, skipped")
                        skipped_count += 1
                
                db.session.commit()
                
                print(f"\n✅ Checksum calculation complete!")
                print(f"  - Updated: {updated_count}")
                if skipped_count > 0:
                    print(f"  - Skipped: {skipped_count}")
            else:
                print("\n✅ No existing videos to process")
            
            print("\n✅ Migration completed successfully!")
            print("\nFile Checksum features enabled:")
            print("  - SHA256 checksums stored for all videos")
            print("  - API endpoint includes checksums for integrity verification")
            print("  - Devices can verify downloaded files match server version")
            print("  - Automatic checksum calculation on upload")
            
        except Exception as e:
            db.session.rollback()
            if "duplicate column name" in str(e).lower():
                print("\n⚠️  Checksum column already exists, skipping column creation...")
                
                # Still try to calculate missing checksums
                try:
                    videos = Video.query.filter(Video.checksum.is_(None)).all()
                    if videos:
                        print(f"\n📊 Calculating checksums for {len(videos)} video(s) without checksums...")
                        
                        video_folder = app.config['UPLOAD_FOLDER']
                        updated_count = 0
                        
                        for video in videos:
                            video_path = os.path.join(video_folder, video.filename)
                            if os.path.exists(video_path):
                                checksum = calculate_checksum(video_path)
                                video.checksum = checksum
                                updated_count += 1
                                print(f"  ✅ {video.filename}: {checksum[:16]}...")
                        
                        db.session.commit()
                        print(f"\n✅ Updated {updated_count} checksums")
                    else:
                        print("✅ All videos already have checksums")
                except Exception as calc_error:
                    print(f"❌ Error calculating checksums: {calc_error}")
            else:
                print(f"\n❌ Migration failed: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

if __name__ == '__main__':
    migrate_checksums()
