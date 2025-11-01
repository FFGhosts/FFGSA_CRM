"""
Reprocess existing videos to extract metadata and generate thumbnails
"""
import os
from app import create_app
from models import db, Video
from utils.video_utils import extract_video_metadata, generate_thumbnail, get_thumbnail_path, VideoProcessingError

def reprocess_videos():
    """Reprocess all videos that are missing metadata or thumbnails"""
    app = create_app()
    
    with app.app_context():
        videos = Video.query.all()
        print(f"Found {len(videos)} videos to check\n")
        
        for video in videos:
            print(f"Processing: {video.title} (ID: {video.id})")
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video.filename)
            
            if not os.path.exists(video_path):
                print(f"  ❌ Video file not found: {video.filename}")
                continue
            
            # Extract metadata if missing
            if video.width is None or video.duration is None:
                try:
                    metadata = extract_video_metadata(video_path)
                    video.duration = metadata.get('duration')
                    video.width = metadata.get('width')
                    video.height = metadata.get('height')
                    video.codec = metadata.get('codec')
                    video.bitrate = metadata.get('bitrate')
                    video.framerate = metadata.get('framerate')
                    video.video_format = metadata.get('format')
                    db.session.commit()
                    print(f"  ✅ Extracted metadata: {video.width}x{video.height}, {video.duration}s")
                except VideoProcessingError as e:
                    print(f"  ❌ Failed to extract metadata: {e}")
            else:
                print(f"  ℹ️  Metadata already exists")
            
            # Generate thumbnail if missing
            if not video.has_thumbnail:
                try:
                    thumbnail_path = get_thumbnail_path(video.filename, app.config['THUMBNAIL_FOLDER'])
                    if generate_thumbnail(video_path, thumbnail_path):
                        video.has_thumbnail = True
                        db.session.commit()
                        print(f"  ✅ Generated thumbnail")
                except VideoProcessingError as e:
                    print(f"  ❌ Failed to generate thumbnail: {e}")
            else:
                print(f"  ℹ️  Thumbnail already exists")
            
            print()

if __name__ == '__main__':
    reprocess_videos()
