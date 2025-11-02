"""Fix notification enum case mismatch"""
from app import create_app
from models import db

app = create_app()

with app.app_context():
    # Update lowercase notification types to uppercase
    result = db.session.execute(db.text(
        "UPDATE notifications SET notification_type = 'SUCCESS' WHERE notification_type = 'success'"
    ))
    db.session.commit()
    print(f"Fixed {result.rowcount} notification records")
