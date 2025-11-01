"""
Phase 7: Client-Side Enhancements Migration
Adds tables for device configuration, display settings, network config,
system updates, screenshots, and emergency broadcasts
"""
import sys
from datetime import datetime
from sqlalchemy import text
from app import create_app, db
from models import Device

# Create app context
app = create_app()

def migrate():
    """Run Phase 7 migration"""
    with app.app_context():
        print("Starting Phase 7: Client-Side Enhancements migration...")
        
        # Create tables using raw SQL for full control
        try:
            # 1. Device Configuration table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS device_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    config_key VARCHAR(100) NOT NULL,
                    config_value TEXT,
                    config_type VARCHAR(50) DEFAULT 'string',
                    description TEXT,
                    is_system BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE,
                    UNIQUE (device_id, config_key)
                )
            """))
            print("✓ Created device_config table")
            
            # 2. Display Settings table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS display_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL UNIQUE,
                    resolution_width INTEGER DEFAULT 1920,
                    resolution_height INTEGER DEFAULT 1080,
                    rotation INTEGER DEFAULT 0,
                    screen_on_time VARCHAR(5) DEFAULT '08:00',
                    screen_off_time VARCHAR(5) DEFAULT '22:00',
                    brightness INTEGER DEFAULT 100,
                    screen_saver_enabled BOOLEAN DEFAULT 0,
                    screen_saver_delay INTEGER DEFAULT 300,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE
                )
            """))
            print("✓ Created display_settings table")
            
            # 3. Network Configuration table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS network_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL UNIQUE,
                    connection_type VARCHAR(20) DEFAULT 'ethernet',
                    wifi_ssid VARCHAR(100),
                    wifi_password VARCHAR(100),
                    wifi_security VARCHAR(20) DEFAULT 'WPA2',
                    use_dhcp BOOLEAN DEFAULT 1,
                    static_ip VARCHAR(15),
                    static_gateway VARCHAR(15),
                    static_dns VARCHAR(15),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE
                )
            """))
            print("✓ Created network_config table")
            
            # 4. System Updates table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS system_update (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version VARCHAR(20) NOT NULL UNIQUE,
                    release_date DATE DEFAULT CURRENT_DATE,
                    description TEXT,
                    file_path VARCHAR(255),
                    file_size INTEGER,
                    checksum VARCHAR(64),
                    is_critical BOOLEAN DEFAULT 0,
                    min_version VARCHAR(20),
                    status VARCHAR(20) DEFAULT 'available',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            """))
            print("✓ Created system_update table")
            
            # 5. Device Updates (tracking per-device update status)
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS device_update (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    update_id INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    download_progress INTEGER DEFAULT 0,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE,
                    FOREIGN KEY (update_id) REFERENCES system_update (id) ON DELETE CASCADE
                )
            """))
            print("✓ Created device_update table")
            
            # 6. Device Screenshots table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS device_screenshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    file_path VARCHAR(255) NOT NULL,
                    file_size INTEGER,
                    width INTEGER,
                    height INTEGER,
                    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE
                )
            """))
            print("✓ Created device_screenshot table")
            
            # 7. Audio Settings table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS audio_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL UNIQUE,
                    volume INTEGER DEFAULT 80,
                    muted BOOLEAN DEFAULT 0,
                    audio_output VARCHAR(50) DEFAULT 'hdmi',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE
                )
            """))
            print("✓ Created audio_settings table")
            
            # 8. Emergency Broadcasts table
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS emergency_broadcast (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    message TEXT NOT NULL,
                    video_id INTEGER,
                    priority INTEGER DEFAULT 1,
                    duration INTEGER,
                    target_all_devices BOOLEAN DEFAULT 1,
                    target_device_group_id INTEGER,
                    status VARCHAR(20) DEFAULT 'active',
                    created_by INTEGER NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES video (id) ON DELETE SET NULL,
                    FOREIGN KEY (target_device_group_id) REFERENCES device_group (id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by) REFERENCES user (id)
                )
            """))
            print("✓ Created emergency_broadcast table")
            
            # 9. Emergency Broadcast Devices (many-to-many)
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS emergency_broadcast_device (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcast_id INTEGER NOT NULL,
                    device_id INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    acknowledged_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (broadcast_id) REFERENCES emergency_broadcast (id) ON DELETE CASCADE,
                    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE,
                    UNIQUE (broadcast_id, device_id)
                )
            """))
            print("✓ Created emergency_broadcast_device table")
            
            # 10. Add version field to Device table if not exists
            try:
                db.session.execute(text("""
                    ALTER TABLE device ADD COLUMN software_version VARCHAR(20) DEFAULT '1.0.0'
                """))
                print("✓ Added software_version column to device table")
            except Exception as e:
                print(f"  (software_version column already exists or error: {e})")
            
            # 11. Add last_screenshot_at field to Device table
            try:
                db.session.execute(text("""
                    ALTER TABLE device ADD COLUMN last_screenshot_at TIMESTAMP
                """))
                print("✓ Added last_screenshot_at column to device table")
            except Exception as e:
                print(f"  (last_screenshot_at column already exists or error: {e})")
            
            db.session.commit()
            print("\n✓ Phase 7 migration completed successfully!")
            
            # Initialize default settings for existing devices
            print("\nInitializing default settings for existing devices...")
            devices = Device.query.all()
            
            for device in devices:
                # Create default display settings
                db.session.execute(text("""
                    INSERT OR IGNORE INTO display_settings (device_id)
                    VALUES (:device_id)
                """), {'device_id': device.id})
                
                # Create default audio settings
                db.session.execute(text("""
                    INSERT OR IGNORE INTO audio_settings (device_id)
                    VALUES (:device_id)
                """), {'device_id': device.id})
                
                # Create default network config (ethernet by default)
                db.session.execute(text("""
                    INSERT OR IGNORE INTO network_config (device_id, connection_type)
                    VALUES (:device_id, 'ethernet')
                """), {'device_id': device.id})
            
            db.session.commit()
            print(f"✓ Initialized settings for {len(devices)} devices")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)

