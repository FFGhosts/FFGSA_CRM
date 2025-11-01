"""
Database Migration: Add RBAC (Role-Based Access Control)
Phase 4.2: Multi-user Support & RBAC

This migration adds:
1. role column to users table (enum: admin, operator, viewer)
2. last_login column to users table
3. user_activities table for audit logging

Run this script once to update the database schema.
"""
from app import create_app
from models import db, User, UserRole, UserActivity
from sqlalchemy import text, inspect

def migrate():
    """Run RBAC migration"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("=" * 70)
        print("RBAC Migration - Phase 4.2")
        print("=" * 70)
        
        # 1. Add role column to users table
        print("\n1. Adding 'role' and 'last_login' columns to users table...")
        users_columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'role' not in users_columns:
            try:
                # SQLite doesn't support ENUM, so we use VARCHAR
                # Check if we're using SQLite
                if db.engine.dialect.name == 'sqlite':
                    db.session.execute(text(
                        "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'admin'"
                    ))
                else:
                    # PostgreSQL or MySQL with ENUM support
                    db.session.execute(text(
                        "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'admin'"
                    ))
                
                db.session.commit()
                print("   ✓ Added 'role' column")
            except Exception as e:
                print(f"   ✗ Error adding 'role' column: {e}")
                db.session.rollback()
        else:
            print("   ⊙ 'role' column already exists")
        
        if 'last_login' not in users_columns:
            try:
                db.session.execute(text(
                    "ALTER TABLE users ADD COLUMN last_login DATETIME"
                ))
                db.session.commit()
                print("   ✓ Added 'last_login' column")
            except Exception as e:
                print(f"   ✗ Error adding 'last_login' column: {e}")
                db.session.rollback()
        else:
            print("   ⊙ 'last_login' column already exists")
        
        # 2. Set all existing users to admin role
        print("\n2. Setting existing users to 'admin' role...")
        try:
            # Update role values directly in database to ADMIN (uppercase)
            db.session.execute(text(
                "UPDATE users SET role = 'ADMIN' WHERE role = 'admin' OR role IS NULL"
            ))
            db.session.commit()
            
            # Verify by querying users
            existing_users = User.query.all()
            print(f"   ✓ Updated all users to ADMIN role ({len(existing_users)} user(s))")
        except Exception as e:
            print(f"   ✗ Error updating user roles: {e}")
            db.session.rollback()
        
        # 3. Create user_activities table
        print("\n3. Creating user_activities table...")
        if not inspector.has_table('user_activities'):
            try:
                UserActivity.__table__.create(db.engine)
                db.session.commit()
                print("   ✓ Created user_activities table")
            except Exception as e:
                print(f"   ✗ Error creating user_activities table: {e}")
                db.session.rollback()
        else:
            print("   ⊙ user_activities table already exists")
        
        # 4. Verify migration
        print("\n4. Verifying migration...")
        try:
            users = User.query.all()
            activities_count = UserActivity.query.count()
            
            print(f"   ✓ Total users: {len(users)}")
            for user in users:
                print(f"     - {user.username}: {user.role.value if hasattr(user.role, 'value') else user.role}")
            print(f"   ✓ User activities table: {activities_count} records")
            
        except Exception as e:
            print(f"   ✗ Verification error: {e}")
        
        print("\n" + "=" * 70)
        print("Migration completed!")
        print("=" * 70)
        print("\nRole Definitions:")
        print("  - ADMIN: Full access (manage users, content, devices, settings)")
        print("  - OPERATOR: Manage content and devices (no user management)")
        print("  - VIEWER: Read-only access (dashboard and reports only)")
        print("\nNext steps:")
        print("  1. Review user roles and adjust as needed")
        print("  2. Create additional users with appropriate roles")
        print("  3. Test permission restrictions")
        print("=" * 70)


if __name__ == '__main__':
    migrate()
