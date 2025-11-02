"""Fix notification enum case mismatch"""
from app import create_app
from models import db

app = create_app()

with app.app_context():
    # Update all lowercase notification types to uppercase
    fixes = [
        ("UPDATE notifications SET notification_type = 'SUCCESS' WHERE notification_type = 'success'", 'success'),
        ("UPDATE notifications SET notification_type = 'WARNING' WHERE notification_type = 'warning'", 'warning'),
        ("UPDATE notifications SET notification_type = 'ERROR' WHERE notification_type = 'error'", 'error'),
        ("UPDATE notifications SET notification_type = 'INFO' WHERE notification_type = 'info'", 'info'),
    ]
    
    total_fixed = 0
    for sql, name in fixes:
        result = db.session.execute(db.text(sql))
        if result.rowcount > 0:
            print(f"Fixed {result.rowcount} '{name}' records")
            total_fixed += result.rowcount
    
    db.session.commit()
    print(f"\nTotal fixed: {total_fixed} notification records")
