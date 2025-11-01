"""
Migration script to add Remote Commands functionality to PiCMS
Adds device_commands table for sending commands to devices
"""
import sys
from sqlalchemy import text
from app import create_app
from models import db

def migrate_remote_commands():
    """Add device commands table"""
    app = create_app()
    
    with app.app_context():
        print("\nAdding remote commands table to database...")
        
        try:
            # Create device_commands table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS device_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    command_type VARCHAR(50) NOT NULL,
                    parameters TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at DATETIME,
                    completed_at DATETIME,
                    result TEXT,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """))
            print("  ✅ Created device_commands table")
            
            # Create indexes
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_device_commands_device 
                ON device_commands(device_id)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_device_commands_status 
                ON device_commands(status)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_device_commands_created 
                ON device_commands(created_at)
            """))
            print("  ✅ Created indexes on device_commands")
            
            db.session.commit()
            
            print("\n✅ Migration completed successfully!")
            print("\nRemote Commands table added:")
            print("  - device_commands: Store commands sent to devices")
            print("\nSupported Commands:")
            print("  - restart: Reboot the device")
            print("  - update: Update player software")
            print("  - clear_cache: Clear downloaded videos")
            print("  - sync_now: Force immediate video sync")
            print("\nCommand Workflow:")
            print("  1. Server creates command with 'pending' status")
            print("  2. Device polls /api/device/commands endpoint")
            print("  3. Device acknowledges command (status: 'acknowledged')")
            print("  4. Device executes command and reports result (status: 'completed' or 'failed')")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    migrate_remote_commands()
