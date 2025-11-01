"""
Test backup functionality
"""
from app import create_app
from utils.backup import BackupManager, BackupError

app = create_app()

with app.app_context():
    try:
        print("Creating backup manager...")
        backup_manager = BackupManager()
        
        print(f"Backup directory: {backup_manager.backup_dir}")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        print("\nAttempting database backup...")
        result = backup_manager.backup_database("Test backup")
        
        print(f"\n✓ Backup successful!")
        print(f"  Timestamp: {result['timestamp']}")
        print(f"  Filename: {result['filename']}")
        print(f"  Size: {result['size']} bytes")
        print(f"  Path: {result['path']}")
        
    except BackupError as e:
        print(f"\n✗ Backup failed: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
