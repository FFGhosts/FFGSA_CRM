"""
Migration script to add Device Groups functionality to PiCMS
Adds device_groups table and device_group_members relationship table
"""
import sys
from sqlalchemy import text
from app import create_app
from models import db

def migrate_device_groups():
    """Add device groups tables"""
    app = create_app()
    
    with app.app_context():
        print("\nAdding device groups tables to database...")
        
        try:
            # Create device_groups table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS device_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    color VARCHAR(7) DEFAULT '#6c757d'
                )
            """))
            print("  ✅ Created device_groups table")
            
            # Create index on name
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_device_groups_name 
                ON device_groups(name)
            """))
            print("  ✅ Created index on device_groups.name")
            
            # Create device_group_members table (many-to-many relationship)
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS device_group_members (
                    device_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (device_id, group_id),
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                    FOREIGN KEY (group_id) REFERENCES device_groups(id) ON DELETE CASCADE
                )
            """))
            print("  ✅ Created device_group_members table")
            
            # Create indexes
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_device_group_members_device 
                ON device_group_members(device_id)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_device_group_members_group 
                ON device_group_members(group_id)
            """))
            print("  ✅ Created indexes on device_group_members")
            
            db.session.commit()
            
            print("\n✅ Migration completed successfully!")
            print("\nDevice Groups tables added:")
            print("  - device_groups: Store group information")
            print("  - device_group_members: Many-to-many relationship between devices and groups")
            print("\nFeatures enabled:")
            print("  - Create device groups with names, descriptions, and colors")
            print("  - Assign devices to multiple groups")
            print("  - Bulk assignment of content to all devices in a group")
            print("  - Filter and organize devices by group")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    migrate_device_groups()
