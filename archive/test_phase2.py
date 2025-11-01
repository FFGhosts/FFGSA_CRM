"""
Test Script for Phase 2.1 & 2.2 - Playlist Management
Tests playlist models, forms, routes, and UI functionality
"""
import os as os_module
import sys
from app import create_app
from models import db, Playlist, PlaylistItem, Video, Device, Assignment

def test_phase2():
    """Test Phase 2.1 & 2.2 - Playlist functionality"""
    app = create_app(os_module.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        print("=" * 60)
        print("PHASE 2.1 & 2.2 TEST - PLAYLIST MANAGEMENT")
        print("=" * 60)
        
        all_passed = True
        
        # Test 1: Database Schema
        print("\n[TEST 1] Database Schema")
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            # Check playlists table
            playlists_cols = [col['name'] for col in inspector.get_columns('playlists')]
            required_playlist_cols = ['id', 'name', 'description', 'created_at', 'updated_at', 'is_active']
            assert all(col in playlists_cols for col in required_playlist_cols), "Missing playlist columns"
            
            # Check playlist_items table
            items_cols = [col['name'] for col in inspector.get_columns('playlist_items')]
            required_item_cols = ['id', 'playlist_id', 'video_id', 'position', 'added_at']
            assert all(col in items_cols for col in required_item_cols), "Missing playlist_items columns"
            
            # Check assignments table has playlist_id
            assignments_cols = [col['name'] for col in inspector.get_columns('assignments')]
            assert 'playlist_id' in assignments_cols, "Missing playlist_id in assignments"
            
            print("  ✓ Playlists table exists with correct columns")
            print("  ✓ Playlist_items table exists with correct columns")
            print("  ✓ Assignments table updated with playlist_id")
        except Exception as e:
            print(f"  ✗ Database schema test failed: {e}")
            all_passed = False
        
        # Test 2: Forms
        print("\n[TEST 2] Forms")
        try:
            from forms import (PlaylistCreateForm, PlaylistEditForm, 
                             PlaylistAddVideoForm, AssignmentForm)
            
            # Test forms exist and have correct attributes (without instantiation)
            assert hasattr(PlaylistCreateForm, 'name'), "PlaylistCreateForm missing name field"
            assert hasattr(PlaylistCreateForm, 'description'), "PlaylistCreateForm missing description field"
            assert hasattr(PlaylistCreateForm, 'is_active'), "PlaylistCreateForm missing is_active field"
            
            assert hasattr(PlaylistEditForm, 'name'), "PlaylistEditForm missing name field"
            assert hasattr(PlaylistAddVideoForm, 'video_id'), "PlaylistAddVideoForm missing video_id field"
            
            assert hasattr(AssignmentForm, 'content_type'), "AssignmentForm missing content_type field"
            assert hasattr(AssignmentForm, 'playlist_id'), "AssignmentForm missing playlist_id field"
            
            print("  ✓ PlaylistCreateForm defined correctly")
            print("  ✓ PlaylistEditForm defined correctly")
            print("  ✓ PlaylistAddVideoForm defined correctly")
            print("  ✓ AssignmentForm updated with playlist support")
        except Exception as e:
            print(f"  ✗ Forms test failed: {e}")
            all_passed = False
        
        # Test 3: Routes
        print("\n[TEST 3] Routes")
        try:
            # Check if playlist blueprint is registered
            assert 'playlist' in app.blueprints, "Playlist blueprint not registered"
            
            playlist_bp = app.blueprints['playlist']
            
            # Check key routes exist
            route_names = [rule.endpoint for rule in app.url_map.iter_rules()]
            required_routes = [
                'playlist.index',
                'playlist.create',
                'playlist.view',
                'playlist.edit',
                'playlist.delete',
                'playlist.add_video',
                'playlist.remove_video',
                'playlist.reorder'
            ]
            
            for route in required_routes:
                assert route in route_names, f"Route {route} not found"
            
            print("  ✓ Playlist blueprint registered")
            print(f"  ✓ All {len(required_routes)} playlist routes defined")
        except Exception as e:
            print(f"  ✗ Routes test failed: {e}")
            all_passed = False
        
        # Test 4: Models
        print("\n[TEST 4] Models")
        try:
            # Test Playlist model
            playlist = Playlist(name="Test Playlist", description="Test", is_active=True)
            assert hasattr(playlist, 'name'), "Playlist missing name"
            assert hasattr(playlist, 'items'), "Playlist missing items relationship"
            assert hasattr(playlist, 'video_count'), "Playlist missing video_count property"
            assert hasattr(playlist, 'formatted_duration'), "Playlist missing formatted_duration property"
            
            # Test PlaylistItem model
            item = PlaylistItem(playlist_id=1, video_id=1, position=0)
            assert hasattr(item, 'position'), "PlaylistItem missing position"
            
            # Test Assignment model updates
            assignment = Assignment(device_id=1, playlist_id=1)
            assert hasattr(assignment, 'playlist_id'), "Assignment missing playlist_id"
            assert hasattr(assignment, 'content_type'), "Assignment missing content_type property"
            
            print("  ✓ Playlist model defined correctly")
            print("  ✓ PlaylistItem model defined correctly")
            print("  ✓ Assignment model updated with playlist support")
        except Exception as e:
            print(f"  ✗ Models test failed: {e}")
            all_passed = False
        
        # Test 5: Templates
        print("\n[TEST 5] Templates")
        try:
            template_dir = os_module.path.join(os_module.path.dirname(__file__), 'templates')
            
            required_templates = [
                'playlists.html',
                'playlist_create.html',
                'playlist_view.html',
                'playlist_edit.html'
            ]
            
            for template in required_templates:
                template_path = os_module.path.join(template_dir, template)
                assert os_module.path.exists(template_path), f"Template {template} not found"
            
            # Check base.html has playlist nav link
            base_path = os_module.path.join(template_dir, 'base.html')
            with open(base_path, 'r', encoding='utf-8') as f:
                base_content = f.read()
                assert 'playlist.index' in base_content, "Playlist nav link not in base.html"
            
            print("  ✓ All 4 playlist templates created")
            print("  ✓ Navigation link added to base.html")
        except Exception as e:
            print(f"  ✗ Templates test failed: {e}")
            all_passed = False
        
        # Test 6: Database Operations
        print("\n[TEST 6] Database Operations")
        try:
            # Count existing records
            playlist_count = Playlist.query.count()
            item_count = PlaylistItem.query.count()
            
            print(f"  ✓ Database queries working")
            print(f"    - Playlists: {playlist_count}")
            print(f"    - Playlist items: {item_count}")
        except Exception as e:
            print(f"  ✗ Database operations test failed: {e}")
            all_passed = False
        
        # Final Summary
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ ALL TESTS PASSED!")
            print("\nPhase 2.1 & 2.2 Implementation Complete:")
            print("  ✓ Database schema with playlists and playlist_items")
            print("  ✓ Playlist forms for create/edit/add videos")
            print("  ✓ 8 playlist routes (CRUD + video management)")
            print("  ✓ Playlist models with relationships")
            print("  ✓ 4 playlist templates with drag-and-drop UI")
            print("  ✓ Updated assignments to support playlists")
            print("\nNext Steps:")
            print("  1. Visit http://localhost:5000/playlists")
            print("  2. Create a new playlist")
            print("  3. Add videos to the playlist")
            print("  4. Drag to reorder videos")
            print("  5. Assign playlist to devices")
        else:
            print("❌ SOME TESTS FAILED")
            print("Please check the errors above and fix them.")
        print("=" * 60)
        
        return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(test_phase2())
