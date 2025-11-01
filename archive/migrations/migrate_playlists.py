"""
Database Migration Script - Add Playlist Tables
Adds playlists and playlist_items tables to support playlist functionality
"""
import os
from app import create_app
from models import db, Playlist, PlaylistItem
from sqlalchemy import inspect, text

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate_playlists():
    """Add playlist tables and update assignments table"""
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    with app.app_context():
        print("=" * 60)
        print("PiCMS Playlist Migration")
        print("=" * 60)
        
        # Check current state
        playlists_exists = check_table_exists('playlists')
        playlist_items_exists = check_table_exists('playlist_items')
        assignments_exists = check_table_exists('assignments')
        
        print(f"\nCurrent state:")
        print(f"  - playlists table exists: {playlists_exists}")
        print(f"  - playlist_items table exists: {playlist_items_exists}")
        print(f"  - assignments table exists: {assignments_exists}")
        
        try:
            # Step 1: Create playlist tables if they don't exist
            if not playlists_exists:
                print("\nCreating playlists table...")
                db.session.execute(text("""
                    CREATE TABLE playlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """))
                db.session.commit()
                print("✓ Created playlists table")
            else:
                print("\n✓ Playlists table already exists")
            
            if not playlist_items_exists:
                print("\nCreating playlist_items table...")
                db.session.execute(text("""
                    CREATE TABLE playlist_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        playlist_id INTEGER NOT NULL,
                        video_id INTEGER NOT NULL,
                        position INTEGER NOT NULL DEFAULT 0,
                        added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                        FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                        UNIQUE (playlist_id, position)
                    )
                """))
                db.session.commit()
                print("✓ Created playlist_items table")
            else:
                print("\n✓ Playlist_items table already exists")
            
            # Step 2: Migrate assignments table
            if assignments_exists:
                has_playlist_id = check_column_exists('assignments', 'playlist_id')
                
                if not has_playlist_id:
                    print("\nMigrating assignments table...")
                    
                    # SQLite requires recreating the table to add columns with constraints
                    # 1. Get existing assignments data
                    result = db.session.execute(text("SELECT * FROM assignments"))
                    existing_assignments = result.fetchall()
                    
                    print(f"  - Found {len(existing_assignments)} existing assignments")
                    
                    # 2. Rename old table
                    db.session.execute(text("ALTER TABLE assignments RENAME TO assignments_old"))
                    db.session.commit()
                    
                    # 3. Create new table with playlist_id column
                    db.session.execute(text("""
                        CREATE TABLE assignments (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            device_id INTEGER NOT NULL,
                            video_id INTEGER,
                            playlist_id INTEGER,
                            assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            priority INTEGER DEFAULT 0,
                            FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                            FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
                            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                            CHECK ((video_id IS NOT NULL AND playlist_id IS NULL) OR (video_id IS NULL AND playlist_id IS NOT NULL))
                        )
                    """))
                    db.session.commit()
                    
                    # 4. Copy data from old table
                    if existing_assignments:
                        for assignment in existing_assignments:
                            db.session.execute(text("""
                                INSERT INTO assignments (id, device_id, video_id, playlist_id, assigned_at, priority)
                                VALUES (:id, :device_id, :video_id, NULL, :assigned_at, :priority)
                            """), {
                                'id': assignment[0],
                                'device_id': assignment[1],
                                'video_id': assignment[2],
                                'assigned_at': assignment[3],
                                'priority': assignment[4]
                            })
                        db.session.commit()
                        print(f"  - Migrated {len(existing_assignments)} assignments")
                    
                    # 5. Drop old table
                    db.session.execute(text("DROP TABLE assignments_old"))
                    db.session.commit()
                    
                    print("✓ Updated assignments table with playlist_id column")
                else:
                    print("\n✓ Assignments table already has playlist_id column")
            
            # Verify migration
            inspector = inspect(db.engine)
            
            # Check playlists table columns
            playlist_columns = [col['name'] for col in inspector.get_columns('playlists')]
            print(f"\nPlaylists table columns: {', '.join(playlist_columns)}")
            
            # Check playlist_items table columns
            item_columns = [col['name'] for col in inspector.get_columns('playlist_items')]
            print(f"Playlist items table columns: {', '.join(item_columns)}")
            
            # Check assignments table columns
            assignment_columns = [col['name'] for col in inspector.get_columns('assignments')]
            print(f"Assignments table columns: {', '.join(assignment_columns)}")
            
            # Count existing records
            playlist_count = db.session.execute(text("SELECT COUNT(*) FROM playlists")).scalar()
            item_count = db.session.execute(text("SELECT COUNT(*) FROM playlist_items")).scalar()
            assignment_count = db.session.execute(text("SELECT COUNT(*) FROM assignments")).scalar()
            
            print(f"\n✓ Migration completed successfully!")
            print(f"\nDatabase statistics:")
            print(f"  - Playlists: {playlist_count}")
            print(f"  - Playlist items: {item_count}")
            print(f"  - Assignments: {assignment_count}")
            
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_playlists()
