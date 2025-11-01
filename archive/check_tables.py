#!/usr/bin/env python3
"""Quick script to check database tables"""
from app import create_app, db

app = create_app()
app.app_context().push()

result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
tables = [row[0] for row in result]

print(f"Total tables: {len(tables)}")
print("\nAll tables:")
for t in tables:
    print(f"  ✓ {t}")

phase7_tables = [
    'device_config', 
    'display_settings', 
    'network_config', 
    'audio_settings', 
    'system_update', 
    'device_update', 
    'emergency_broadcast',
    'emergency_broadcast_devices',
    'device_screenshots'
]

print(f"\nPhase 7 tables check:")
missing = []
for t in phase7_tables:
    if t in tables:
        print(f"  ✓ {t}")
    else:
        print(f"  ✗ {t} MISSING")
        missing.append(t)

if missing:
    print(f"\n⚠ Missing {len(missing)} Phase 7 tables: {missing}")
    print("\nRun: python migrate_phase7_client_enhancements.py")
else:
    print("\n✓ All Phase 7 tables exist!")
