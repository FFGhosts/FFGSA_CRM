#!/usr/bin/env python3
"""
Email Configuration Test Script
Tests SMTP settings and sends a test email
"""
import sys
from app import create_app
from flask_mail import Mail, Message
from flask import current_app

def test_email_config():
    """Test email configuration and send test email"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("EMAIL CONFIGURATION TEST")
        print("="*60)
        
        # Display current configuration
        print("\nCurrent Email Settings:")
        print(f"  MAIL_SERVER: {current_app.config.get('MAIL_SERVER')}")
        print(f"  MAIL_PORT: {current_app.config.get('MAIL_PORT')}")
        print(f"  MAIL_USE_TLS: {current_app.config.get('MAIL_USE_TLS')}")
        print(f"  MAIL_USE_SSL: {current_app.config.get('MAIL_USE_SSL')}")
        print(f"  MAIL_USERNAME: {current_app.config.get('MAIL_USERNAME')}")
        print(f"  MAIL_PASSWORD: {'*' * len(current_app.config.get('MAIL_PASSWORD', ''))}")
        print(f"  MAIL_DEFAULT_SENDER: {current_app.config.get('MAIL_DEFAULT_SENDER')}")
        print(f"  MAIL_SUPPRESS_SEND: {current_app.config.get('MAIL_SUPPRESS_SEND')}")
        
        # Check if email is configured
        if not current_app.config.get('MAIL_USERNAME'):
            print("\n❌ ERROR: MAIL_USERNAME is not configured!")
            return False
        
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            print("\n⚠️  WARNING: MAIL_SUPPRESS_SEND is True - emails will not be sent!")
            print("   Set MAIL_SUPPRESS_SEND=False in .env to enable sending")
            return False
        
        # Initialize Flask-Mail
        mail = Mail(app)
        
        # Get test recipient
        recipient = input("\nEnter recipient email address for test: ").strip()
        if not recipient:
            print("❌ No recipient provided. Test cancelled.")
            return False
        
        print(f"\n📧 Sending test email to: {recipient}")
        print("   Please wait...")
        
        try:
            # Create test message
            msg = Message(
                subject="FFGSA_CSM - Email Configuration Test",
                sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                recipients=[recipient]
            )
            
            msg.body = """
Hello!

This is a test email from your FFGSA_CSM system.

If you received this email, your email configuration is working correctly!

Email Settings:
- Server: {server}
- Port: {port}
- From: {sender}

Best regards,
FFGSA_CSM System
            """.format(
                server=current_app.config.get('MAIL_SERVER'),
                port=current_app.config.get('MAIL_PORT'),
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            msg.html = """
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <h2 style="color: #667eea;">FFGSA_CSM Email Test</h2>
        <p>Hello!</p>
        <p>This is a test email from your FFGSA_CSM system.</p>
        <p><strong style="color: #48bb78;">✓ If you received this email, your email configuration is working correctly!</strong></p>
        
        <div style="background: #f7fafc; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0;">Email Settings:</h3>
            <ul style="list-style: none; padding: 0;">
                <li><strong>Server:</strong> {server}</li>
                <li><strong>Port:</strong> {port}</li>
                <li><strong>From:</strong> {sender}</li>
            </ul>
        </div>
        
        <p style="color: #666; font-size: 12px; margin-top: 30px;">
            This is an automated test email from FFGSA_CSM Content Signage Management
        </p>
    </div>
</body>
</html>
            """.format(
                server=current_app.config.get('MAIL_SERVER'),
                port=current_app.config.get('MAIL_PORT'),
                sender=current_app.config.get('MAIL_DEFAULT_SENDER')
            )
            
            # Send email
            mail.send(msg)
            
            print("\n✅ SUCCESS! Test email sent successfully!")
            print(f"   Check inbox for: {recipient}")
            print("   (Don't forget to check spam folder)")
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to send test email")
            print(f"   Error: {str(e)}")
            print("\nPossible issues:")
            print("  • Check SMTP server address and port")
            print("  • Verify username and password are correct")
            print("  • Check if TLS/SSL settings are correct")
            print("  • Ensure firewall allows outgoing SMTP connections")
            print("  • Some SMTP servers require app passwords (not regular password)")
            return False

if __name__ == '__main__':
    try:
        success = test_email_config()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
