"""
mailer.py - Send HTML emails via Gmail SMTP with optional PDF attachment.

SIMULATION MODE: If GMAIL_USER / GMAIL_APP_PASSWORD are not set in .env,
the email is not dispatched but the action is logged and counted as
"sent" so the rest of the dashboard workflow still works.
"""

import os
import ssl
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders


def render_template(template: str, variables: dict) -> str:
    """Replace {{key}} placeholders with values from the variables dict."""
    def replacer(m):
        key = m.group(1).strip()
        return str(variables.get(key, m.group(0)))   # keep original if key missing
    return re.sub(r'\{\{(\w+)\}\}', replacer, template)


def send_email(
    to_email:  str,
    subject:   str,
    html_body: str,
    pdf_path:  str | None = None,
    simulate:  bool = False,
) -> dict:
    """
    Send an email via Gmail SMTP SSL (port 465).

    Credentials are read fresh from env each call so .env reloads are picked up.

    Returns:
        { 'success': bool, 'simulated': bool, 'message': str }
    """
    # Read credentials fresh every call (not at import time)
    gmail_user = os.environ.get('GMAIL_USER', '').strip()
    gmail_pass = os.environ.get('GMAIL_APP_PASSWORD', '').strip()

    simulated = simulate or not gmail_user or not gmail_pass

    if simulated:
        print(f"[Mailer SIMULATED] To={to_email} | Subject={subject}")
        return {
            'success':   True,
            'simulated': True,
            'message':   f'Simulated - email to {to_email} logged (no SMTP credentials set).',
        }

    try:
        # Build the email message
        msg = MIMEMultipart('mixed')
        msg['From']    = gmail_user
        msg['To']      = to_email
        msg['Subject'] = subject

        # HTML body
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        # PDF attachment (if provided and file exists on disk)
        if pdf_path and os.path.isfile(pdf_path):
            with open(pdf_path, 'rb') as fh:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(fh.read())
            encoders.encode_base64(part)
            filename = os.path.basename(pdf_path)
            part.add_header('Content-Disposition',
                            f'attachment; filename="{filename}"')
            msg.attach(part)

        # Send via SSL on port 465 (same method confirmed working in test_mail.py)
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to_email, msg.as_string())

        print(f"[Mailer] Sent -> {to_email}")
        return {
            'success':   True,
            'simulated': False,
            'message':   f'Email dispatched to {to_email}.',
        }

    except smtplib.SMTPAuthenticationError as e:
        msg_txt = f'Gmail authentication failed: {e}. Check GMAIL_USER and GMAIL_APP_PASSWORD in .env'
        print(f"[Mailer ERROR] {msg_txt}")
        return {'success': False, 'simulated': False, 'message': msg_txt}

    except smtplib.SMTPRecipientsRefused as e:
        msg_txt = f'Recipient refused: {to_email} - {e}'
        print(f"[Mailer ERROR] {msg_txt}")
        return {'success': False, 'simulated': False, 'message': msg_txt}

    except Exception as exc:
        msg_txt = f'SMTP error ({type(exc).__name__}): {exc}'
        print(f"[Mailer ERROR] {msg_txt}")
        return {'success': False, 'simulated': False, 'message': msg_txt}
