#!/usr/bin/env python3
"""Update admin email address"""
from app import create_app, db
from models import User

app = create_app()
app.app_context().push()

admin = User.query.filter_by(username='admin').first()
if admin:
    admin.email = 'jhalil.ally@ffgsa.co.za'
    db.session.commit()
    print(f'✓ Updated admin email to: {admin.email}')
else:
    print('✗ Admin user not found')
