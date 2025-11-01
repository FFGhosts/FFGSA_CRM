"""
Test playlist functionality with multiple videos
"""
from app import create_app
from models import db, Playlist, PlaylistItem, Video

def test_playlist_add_multiple_videos():
    """Test adding multiple videos to a playlist"""
    app = create_app()
    
    with app.app_context():
        # Create a test playlist
        playlist = Playlist(
            name="Test Playlist",
            description="Testing multiple video additions"
        )
        db.session.add(playlist)
        db.session.commit()
        print(f"✅ Created playlist: {playlist.name} (ID: {playlist.id})")
        
        # Get the first video
        video = Video.query.first()
        if not video:
            print("❌ No videos found in database")
            return
        
        print(f"\nAdding video '{video.title}' to playlist multiple times...")
        
        # Try adding the same video 3 times (simulating the user's issue)
        for i in range(3):
            try:
                # Calculate next position
                max_pos = db.session.query(db.func.max(PlaylistItem.position)).filter_by(
                    playlist_id=playlist.id
                ).scalar()
                next_position = (max_pos + 1) if max_pos is not None else 0
                
                # Create playlist item
                item = PlaylistItem(
                    playlist_id=playlist.id,
                    video_id=video.id,
                    position=next_position
                )
                db.session.add(item)
                db.session.commit()
                
                print(f"  ✅ Added video at position {next_position}")
                
            except Exception as e:
                db.session.rollback()
                print(f"  ❌ Failed to add video at position {i}: {e}")
        
        # Verify the items
        items = PlaylistItem.query.filter_by(playlist_id=playlist.id).order_by(PlaylistItem.position).all()
        print(f"\n✅ Playlist now has {len(items)} items")
        for item in items:
            print(f"   Position {item.position}: {item.video.title} "
                  f"({item.video.width}x{item.video.height}, {item.video.formatted_duration})")
        
        # Test reordering
        print(f"\nTesting reorder functionality...")
        if len(items) >= 2:
            try:
                # Swap first two items
                new_order = [items[1].id, items[0].id] + [item.id for item in items[2:]]
                
                # Use temporary negative positions
                for item in items:
                    item.position = -item.id
                db.session.flush()
                
                # Apply new order
                for idx, item_id in enumerate(new_order):
                    item = db.session.get(PlaylistItem, item_id)
                    item.position = idx
                
                db.session.commit()
                print("  ✅ Reordered successfully")
                
                # Verify new order
                items = PlaylistItem.query.filter_by(playlist_id=playlist.id).order_by(PlaylistItem.position).all()
                for item in items:
                    print(f"   Position {item.position}: Item ID {item.id}")
                    
            except Exception as e:
                db.session.rollback()
                print(f"  ❌ Reorder failed: {e}")

if __name__ == '__main__':
    test_playlist_add_multiple_videos()
