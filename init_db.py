"""
Database Initialization Script
Run this script to create all database tables and seed initial data
"""
import os
import sys
from app import create_app
from models import db, User, Video, Device, Assignment

def init_database():
    """Initialize database with tables and seed data"""
    
    app = create_app()
    
    with app.app_context():
        # Drop all tables (use with caution in production!)
        print("Dropping existing tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        # Create default admin user
        print("Creating default admin user...")
        admin = User(
            username=app.config['ADMIN_USERNAME'],
            email='admin@picms.local'
        )
        admin.set_password(app.config['ADMIN_PASSWORD'])
        db.session.add(admin)
        
        # Create sample data for testing (optional)
        if os.getenv('FLASK_ENV') == 'development':
            print("Adding sample data for development...")
            
            # Sample device
            device = Device(
                name='Pi Player 1',
                serial='RPI-001-TEST',
                ip_address='192.168.1.100',
                api_key_hash=Device.hash_api_key('test-api-key-123')
            )
            db.session.add(device)
        
        # Commit all changes
        db.session.commit()
        
        print("\n" + "="*50)
        print("Database initialized successfully!")
        print("="*50)
        print(f"\nAdmin credentials:")
        print(f"  Username: {app.config['ADMIN_USERNAME']}")
        print(f"  Password: {app.config['ADMIN_PASSWORD']}")
        print("\nIMPORTANT: Change the default password after first login!")
        print("="*50 + "\n")


if __name__ == '__main__':
    confirm = input("This will delete all existing data. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        init_database()
    else:
        print("Database initialization cancelled.")
        sys.exit(0)
