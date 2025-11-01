"""
Phase 4.4: Content Tagging & Organization Migration
Creates tables for tags and categories with many-to-many relationships to videos and playlists
"""
from app import create_app, db
from sqlalchemy import text, inspect

def migrate():
    """Run the tagging and categories migration"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        print("=" * 70)
        print("Content Tagging & Organization Migration - Phase 4.4")
        print("=" * 70)
        
        # Create tags table
        print("\n1. Creating tags table...")
        if 'tags' not in existing_tables:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE tags (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(50) UNIQUE NOT NULL,
                        color VARCHAR(7) DEFAULT '#6c757d',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
                conn.execute(text("CREATE INDEX idx_tags_name ON tags(name)"))
                conn.commit()
            print("   ✓ Tags table created")
        else:
            print("   ⊙ Tags table already exists")
        
        # Create categories table
        print("\n2. Creating categories table...")
        if 'categories' not in existing_tables:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE categories (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT,
                        parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                        color VARCHAR(7) DEFAULT '#0d6efd',
                        icon VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
                    )
                """))
                conn.execute(text("CREATE INDEX idx_categories_name ON categories(name)"))
                conn.commit()
            print("   ✓ Categories table created")
        else:
            print("   ⊙ Categories table already exists")
        
        # Create video_tags junction table
        print("\n3. Creating video_tags junction table...")
        if 'video_tags' not in existing_tables:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE video_tags (
                        video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
                        tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                        PRIMARY KEY (video_id, tag_id)
                    )
                """))
                conn.execute(text("CREATE INDEX idx_video_tags_video ON video_tags(video_id)"))
                conn.execute(text("CREATE INDEX idx_video_tags_tag ON video_tags(tag_id)"))
                conn.commit()
            print("   ✓ Video_tags junction table created")
        else:
            print("   ⊙ Video_tags junction table already exists")
        
        # Create playlist_tags junction table
        print("\n4. Creating playlist_tags junction table...")
        if 'playlist_tags' not in existing_tables:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE playlist_tags (
                        playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
                        tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                        PRIMARY KEY (playlist_id, tag_id)
                    )
                """))
                conn.execute(text("CREATE INDEX idx_playlist_tags_playlist ON playlist_tags(playlist_id)"))
                conn.execute(text("CREATE INDEX idx_playlist_tags_tag ON playlist_tags(tag_id)"))
                conn.commit()
            print("   ✓ Playlist_tags junction table created")
        else:
            print("   ⊙ Playlist_tags junction table already exists")
        
        # Create video_categories junction table
        print("\n5. Creating video_categories junction table...")
        if 'video_categories' not in existing_tables:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE video_categories (
                        video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
                        category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                        PRIMARY KEY (video_id, category_id)
                    )
                """))
                conn.execute(text("CREATE INDEX idx_video_categories_video ON video_categories(video_id)"))
                conn.execute(text("CREATE INDEX idx_video_categories_category ON video_categories(category_id)"))
                conn.commit()
            print("   ✓ Video_categories junction table created")
        else:
            print("   ⊙ Video_categories junction table already exists")
        
        # Create playlist_categories junction table
        print("\n6. Creating playlist_categories junction table...")
        if 'playlist_categories' not in existing_tables:
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE playlist_categories (
                        playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
                        category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                        PRIMARY KEY (playlist_id, category_id)
                    )
                """))
                conn.execute(text("CREATE INDEX idx_playlist_categories_playlist ON playlist_categories(playlist_id)"))
                conn.execute(text("CREATE INDEX idx_playlist_categories_category ON playlist_categories(category_id)"))
                conn.commit()
            print("   ✓ Playlist_categories junction table created")
        else:
            print("   ⊙ Playlist_categories junction table already exists")
        
        # Verify tables
        print("\n7. Verifying tables...")
        inspector = inspect(db.engine)
        final_tables = inspector.get_table_names()
        
        required_tables = ['tags', 'categories', 'video_tags', 'playlist_tags', 
                          'video_categories', 'playlist_categories']
        all_exist = all(table in final_tables for table in required_tables)
        
        if all_exist:
            print("   ✓ All tagging tables verified")
        else:
            missing = [t for t in required_tables if t not in final_tables]
            print(f"   ✗ Missing tables: {', '.join(missing)}")
        
        # Insert default categories
        print("\n8. Creating default categories...")
        with db.engine.connect() as conn:
            # Check if categories exist
            result = conn.execute(text("SELECT COUNT(*) FROM categories")).scalar()
            
            if result == 0:
                default_categories = [
                    ("Marketing", "Promotional and marketing content", None, "#dc3545", "megaphone"),
                    ("Training", "Educational and training videos", None, "#0d6efd", "book"),
                    ("Events", "Event recordings and highlights", None, "#198754", "calendar-event"),
                    ("Products", "Product demonstrations and showcases", None, "#fd7e14", "box"),
                    ("Announcements", "Company announcements and news", None, "#6f42c1", "bell"),
                    ("Safety", "Safety protocols and procedures", None, "#ffc107", "shield-check"),
                    ("Entertainment", "Entertainment and engaging content", None, "#20c997", "emoji-smile")
                ]
                
                for name, desc, parent, color, icon in default_categories:
                    conn.execute(text("""
                        INSERT INTO categories (name, description, parent_id, color, icon, created_at)
                        VALUES (:name, :desc, :parent, :color, :icon, CURRENT_TIMESTAMP)
                    """), {"name": name, "desc": desc, "parent": parent, "color": color, "icon": icon})
                
                conn.commit()
                print(f"   ✓ Created {len(default_categories)} default categories")
            else:
                print(f"   ⊙ Categories already exist ({result} total)")
        
        # Statistics
        print("\n9. Gathering statistics...")
        with db.engine.connect() as conn:
            tag_count = conn.execute(text("SELECT COUNT(*) FROM tags")).scalar()
            category_count = conn.execute(text("SELECT COUNT(*) FROM categories")).scalar()
            
            print(f"   ✓ Total tags: {tag_count}")
            print(f"   ✓ Total categories: {category_count}")
        
        print("\n" + "=" * 70)
        print("Migration completed!")
        print("=" * 70)
        print("\nContent Organization Features:")
        print("  - Tag videos and playlists with flexible labels")
        print("  - Organize content into hierarchical categories")
        print("  - Filter and search by tags and categories")
        print("  - Color-coded tags and categories for easy identification")
        print("  - Usage statistics for each tag and category")
        print("\nNext steps:")
        print("  1. Add tags to your videos and playlists")
        print("  2. Assign categories for better organization")
        print("  3. Use filters to find content quickly")
        print("=" * 70)

if __name__ == '__main__':
    migrate()
