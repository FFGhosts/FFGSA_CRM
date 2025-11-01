#!/usr/bin/env python3
"""Check email notification status"""
from app import create_app, db
from models import NotificationPreference, User

app = create_app()
app.app_context().push()

print("\n" + "="*60)
print("EMAIL NOTIFICATION STATUS")
print("="*60)

print("\nEmail Configuration:")
print(f"  ✓ MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
print(f"  ✓ MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
print(f"  ✓ MAIL_SUPPRESS_SEND: {app.config.get('MAIL_SUPPRESS_SEND')}")

if app.config.get('MAIL_SUPPRESS_SEND'):
    print("\n  ⚠️  WARNING: Email sending is currently DISABLED")
    print("     Set MAIL_SUPPRESS_SEND=False in .env to enable")
else:
    print("\n  ✓ Email sending is ENABLED")

print("\nUser Email Addresses:")
users = User.query.all()
for user in users:
    email_status = user.email if user.email else "❌ No email set"
    print(f"  {user.username}: {email_status}")

print("\nNotification Preferences:")
prefs = NotificationPreference.query.all()
if prefs:
    for p in prefs:
        user = db.session.get(User, p.user_id)
        print(f"\n  {user.username}:")
        print(f"    Global: Email Enabled={p.email_enabled}, Browser Enabled={p.browser_enabled}")
        print(f"    Device Offline: Browser={p.device_offline_browser}, Email={p.device_offline_email}")
        print(f"    Upload Complete: Browser={p.upload_complete_browser}, Email={p.upload_complete_email}")
        print(f"    Backup Success: Browser={p.backup_success_browser}, Email={p.backup_success_email}")
        print(f"    Backup Failure: Browser={p.backup_failure_browser}, Email={p.backup_failure_email}")
        print(f"    System Error: Browser={p.system_error_browser}, Email={p.system_error_email}")
        print(f"    Schedule Conflict: Browser={p.schedule_conflict_browser}, Email={p.schedule_conflict_email}")
        print(f"    Storage Warning: Browser={p.storage_warning_browser}, Email={p.storage_warning_email}")
        print(f"    Daily Summary: Email={p.daily_summary_email}")
        print(f"    Weekly Report: Email={p.weekly_report_email}")
else:
    print("  No custom preferences set")
    print("  Defaults will be used (most notifications enabled)")

print("\n" + "="*60)
print("To configure notification preferences, go to:")
print("http://localhost:5000/notification-preferences")
print("="*60 + "\n")
