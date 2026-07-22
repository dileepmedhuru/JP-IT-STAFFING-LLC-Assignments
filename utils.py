import re
import json
import sqlite3
import smtplib
import pandas as pd
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import config

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def get_db_connection():
    """Establish SQLite connection to uploads/database.db."""
    conn = sqlite3.connect(config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        category TEXT DEFAULT 'Unclassified',
        status TEXT DEFAULT 'Valid',
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT,
        message TEXT,
        attachment TEXT,
        sent_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaign_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        status TEXT,
        sent_at TEXT,
        campaign_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

# Initialize DB on module import
init_db()

def validate_email(email):
    """Validates email syntax."""
    if not email or not isinstance(email, str):
        return False
    clean = email.strip().lower()
    return bool(EMAIL_REGEX.match(clean)) and not clean.endswith(('.png', '.jpg', '.jpeg', '.gif'))

def load_settings():
    """Loads configuration settings from settings.json."""
    default = {
        "gmail_email": "export.emailpro@gmail.com",
        "smtp_email": "export.emailpro@gmail.com",
        "app_password": "",
        "smtp_password": "",
        "daily_send_limit": 100,
        "send_delay": 2.0,
        "gemini_api_key": "",
        "default_audience": "Business",
        "default_subject": "Latest Swinging Bowls",
        "default_message": "Hello, We would like to introduce our Singing Bowl products. Thank you.",
        "sender_name": "EmailPro Admin"
    }
    if config.SETTINGS_FILE.exists():
        try:
            with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default.update(saved)
                return default
        except Exception:
            pass
    save_settings(default)
    return default

def save_settings(data):
    """Saves settings data to settings.json."""
    with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def parse_csv(file_storage):
    """Parses uploaded CSV file, returns total, valid, invalid, duplicates, and valid list."""
    df = pd.read_csv(file_storage)
    
    email_col = None
    for col in df.columns:
        if "email" in col.lower():
            email_col = col
            break
    if not email_col and len(df.columns) > 0:
        email_col = df.columns[0]

    raw_emails = df[email_col].dropna().astype(str).str.strip().tolist()

    total = len(raw_emails)
    valid_list = []
    invalid_count = 0
    seen = set()
    duplicates_count = 0

    for e in raw_emails:
        clean = e.lower()
        if not validate_email(clean):
            invalid_count += 1
            continue
        if clean in seen:
            duplicates_count += 1
        else:
            seen.add(clean)
            valid_list.append(clean)

    return {
        "total": total,
        "valid": len(valid_list),
        "invalid": invalid_count,
        "duplicates": duplicates_count,
        "valid_emails": valid_list
    }

def save_to_database(email_list):
    """Inserts valid emails into SQLite database emails table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    duplicates = 0

    for email in email_list:
        try:
            cursor.execute(
                "INSERT INTO emails (email, category, status, created_at) VALUES (?, 'Unclassified', 'Valid', ?)",
                (email, now_str)
            )
            inserted += 1
        except Exception:
            duplicates += 1

    conn.commit()
    conn.close()
    return inserted, duplicates

def remove_duplicates():
    """Deletes duplicate email records from SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM emails 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM emails 
            GROUP BY LOWER(TRIM(email))
        )
    """)
    removed = cursor.rowcount
    conn.commit()
    conn.close()
    return removed

def generate_statistics():
    """Generates metrics for dashboard and reports."""
    conn = get_db_connection()
    
    emails_rows = conn.execute("SELECT * FROM emails ORDER BY id DESC").fetchall()
    emails = [dict(r) for r in emails_rows]

    total_emails = len(emails)
    business_count = len([e for e in emails if e.get("category", "").lower() == "business"])
    individual_count = len([e for e in emails if e.get("category", "").lower() == "individual"])

    logs_rows = conn.execute("SELECT * FROM campaign_logs ORDER BY id DESC").fetchall()
    logs = [dict(l) for l in logs_rows]

    delivered_count = len([l for l in logs if l.get("status", "").lower() in ["delivered", "sent", "success"]])
    failed_count = len([l for l in logs if l.get("status", "").lower() in ["failed", "bounced", "error"]])
    total_sends = len(logs)

    success_rate = round((delivered_count / total_sends * 100), 1) if total_sends > 0 else 0.0

    conn.close()

    return {
        "total_emails": total_emails,
        "business_count": business_count,
        "individual_count": individual_count,
        "delivered_count": delivered_count,
        "failed_count": failed_count,
        "total_sends": total_sends,
        "success_rate": success_rate,
        "emails": emails,
        "logs": logs
    }

def send_campaign(subject, message, audience="All", attachment_file=None, dry_run=True):
    """Executes campaign dispatch to target audience."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if audience.lower() in ["all", "both"]:
        recipients_rows = cursor.execute("SELECT * FROM emails").fetchall()
    else:
        target_cat = "Business" if "business" in audience.lower() else "Individual"
        recipients_rows = cursor.execute("SELECT * FROM emails WHERE LOWER(category) = ?", (target_cat.lower(),)).fetchall()

    recipients = [dict(r) for r in recipients_rows]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    saved_attachment_path = None
    if attachment_file and hasattr(attachment_file, 'filename') and attachment_file.filename:
        saved_attachment_path = config.UPLOAD_FOLDER / attachment_file.filename
        attachment_file.save(saved_attachment_path)
        attachment_name = attachment_file.filename
    else:
        # Default presentation.pptx
        default_pptx = config.UPLOAD_FOLDER / "presentation.pptx"
        if default_pptx.exists():
            saved_attachment_path = default_pptx
            attachment_name = "presentation.pptx"
        else:
            attachment_name = "None"

    cursor.execute(
        "INSERT INTO campaigns (subject, message, attachment, sent_at) VALUES (?, ?, ?, ?)",
        (subject, message, attachment_name, now_str)
    )
    campaign_id = cursor.lastrowid
    conn.commit()

    if not recipients:
        conn.close()
        return {
            "campaign_id": campaign_id,
            "total": 0,
            "delivered": 0,
            "failed": 0,
            "message": "No recipients found in selected audience category."
        }

    delivered_count = 0
    failed_count = 0
    smtp_settings = load_settings()

    for r in recipients:
        email_addr = r["email"]

        if dry_run:
            status = "Delivered"
            delivered_count += 1
        else:
            try:
                msg = MIMEMultipart()
                msg['From'] = f"{smtp_settings.get('sender_name', 'EmailPro Admin')} <{smtp_settings.get('gmail_email')}>"
                msg['To'] = email_addr
                msg['Subject'] = subject
                msg.attach(MIMEText(message, 'plain', 'utf-8'))

                if saved_attachment_path and saved_attachment_path.exists():
                    ext = saved_attachment_path.suffix.lower().replace(".", "")
                    with open(saved_attachment_path, "rb") as f:
                        part = MIMEBase("application", ext)
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={saved_attachment_path.name}")
                    msg.attach(part)

                server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
                server.starttls()
                server.login(smtp_settings.get("gmail_email"), smtp_settings.get("app_password"))
                server.send_message(msg)
                server.quit()
                status = "Delivered"
                delivered_count += 1
            except Exception as e:
                print(f"SMTP error sending to {email_addr}: {e}")
                status = "Failed"
                failed_count += 1

        cursor.execute(
            "INSERT INTO campaign_logs (email, status, sent_at, campaign_id) VALUES (?, ?, ?, ?)",
            (email_addr, status, now_str, campaign_id)
        )

    conn.commit()
    conn.close()

    return {
        "campaign_id": campaign_id,
        "total": len(recipients),
        "delivered": delivered_count,
        "failed": failed_count,
        "mode": "Dry-Run" if dry_run else "Live SMTP"
    }

def generate_delivery_report():
    """Generates campaign delivery report data."""
    stats = generate_statistics()
    conn = get_db_connection()
    logs_rows = conn.execute("SELECT email, status, sent_at FROM campaign_logs ORDER BY id DESC").fetchall()
    delivery_table = [dict(r) for r in logs_rows]
    conn.close()

    stats["delivery_table"] = delivery_table
    return stats
