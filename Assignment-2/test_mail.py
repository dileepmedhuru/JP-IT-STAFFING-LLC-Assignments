"""
test_mail.py – Diagnose Gmail SMTP. Run: python test_mail.py
"""
import smtplib
import ssl
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

GMAIL_USER = os.environ.get('GMAIL_USER', '').strip()
GMAIL_PASS = os.environ.get('GMAIL_APP_PASSWORD', '').strip()

print(f"Gmail User   : {GMAIL_USER}")
print(f"App Password : {'*' * len(GMAIL_PASS)} ({len(GMAIL_PASS)} chars)")
print()

if not GMAIL_USER or not GMAIL_PASS:
    print("[ERROR] Credentials missing from .env!")
    exit(1)

print("Testing Gmail SMTP SSL (port 465)...")
try:
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        print("[OK] Login successful via SSL:465")

        # Send test email to yourself
        from email.mime.text import MIMEText
        msg = MIMEText(
            "<h2>SMTP Test - Singing Bowl Export Desk</h2><p>SMTP is working!</p>",
            'html'
        )
        msg['From']    = GMAIL_USER
        msg['To']      = GMAIL_USER
        msg['Subject'] = 'SMTP Test - Singing Bowl Export Desk'
        s.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        print(f"[OK] Test email sent to {GMAIL_USER} - check your inbox!")

except smtplib.SMTPAuthenticationError as e:
    print(f"[FAIL] Authentication error: {e}")
    print()
    print("To fix:")
    print("  1. Open https://myaccount.google.com/security")
    print("  2. Enable 2-Step Verification")
    print("  3. Go to App Passwords -> Generate new 16-char password")
    print("  4. Update GMAIL_APP_PASSWORD in .env (no spaces)")

except smtplib.SMTPException as e:
    print(f"[FAIL] SMTP error: {e}")

except Exception as e:
    print(f"[FAIL] Unexpected error: {type(e).__name__}: {e}")
