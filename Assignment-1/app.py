import io
import csv
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response

import config
from utils import (
    init_db,
    parse_csv,
    save_to_database,
    remove_duplicates,
    generate_statistics,
    load_settings,
    save_settings,
    send_campaign,
    generate_delivery_report
)
from emailClassifier import classify_emails

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

# Initialize database
init_db()

# 1. HOME PAGE (/)
@app.route('/')
def index():
    stats = generate_statistics()
    return render_template('index.html', stats=stats, page='dashboard')

# 2. UPLOAD PAGE (/upload)
@app.route('/upload', methods=['GET'])
def upload_page():
    stats = generate_statistics()
    return render_template('upload.html', stats=stats, summary=None, emails=stats['emails'], page='upload')

@app.route('/upload', methods=['POST'])
def upload_action():
    if 'csv_file' not in request.files:
        flash("No CSV file selected.", "error")
        return redirect(url_for('upload_page'))

    file = request.files['csv_file']
    if file.filename == '':
        flash("No file selected.", "error")
        return redirect(url_for('upload_page'))

    if file and file.filename.endswith('.csv'):
        try:
            saved_path = config.UPLOAD_FOLDER / "Email.csv"
            file.save(saved_path)

            with open(saved_path, "r", encoding="utf-8", errors="ignore") as f:
                parsed = parse_csv(f)

            save_to_database(parsed["valid_emails"])
            stats = generate_statistics()

            flash(f"Successfully processed {file.filename}! Imported {parsed['valid']} valid email records.", "success")
            return render_template('upload.html', stats=stats, summary=parsed, emails=stats['emails'], page='upload')
        except Exception as e:
            flash(f"CSV Import Error: {str(e)}", "error")

    return redirect(url_for('upload_page'))

@app.route('/remove-duplicates', methods=['POST'])
def remove_duplicates_action():
    removed_count = remove_duplicates()
    if removed_count > 0:
        flash(f"Successfully removed {removed_count} duplicate emails from database!", "success")
    else:
        flash("No duplicate emails found. All records are unique!", "success")
    return redirect(request.referrer or url_for('upload_page'))

# 3. CLASSIFY PAGE (/classify)
@app.route('/classify', methods=['GET'])
def classify_page():
    stats = generate_statistics()
    business_emails = [e for e in stats['emails'] if e.get('category', '').lower() == 'business']
    individual_emails = [e for e in stats['emails'] if e.get('category', '').lower() == 'individual']

    return render_template('classify.html',
                           stats=stats,
                           classification=None,
                           business_emails=business_emails,
                           individual_emails=individual_emails,
                           page='classify')

@app.route('/classify', methods=['POST'])
def classify_action():
    res = classify_emails()
    stats = generate_statistics()
    business_emails = [e for e in stats['emails'] if e.get('category', '').lower() == 'business']
    individual_emails = [e for e in stats['emails'] if e.get('category', '').lower() == 'individual']

    flash(f"AI Classification complete! Categorized {res['business_count']} Business and {res['individual_count']} Individual emails.", "success")
    return render_template('classify.html',
                           stats=stats,
                           classification=res,
                           business_emails=business_emails,
                           individual_emails=individual_emails,
                           page='classify')

@app.route('/download-business-csv')
def download_business_csv():
    stats = generate_statistics()
    business_emails = [e for e in stats['emails'] if e.get('category', '').lower() == 'business']

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "Company", "Country"])

    for item in business_emails:
        domain = item["email"].split("@")[1] if "@" in item["email"] else "N/A"
        company = domain.split(".")[0].capitalize() + " Corp"
        writer.writerow([item["email"], company, "International"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=BusinessEmails.csv"}
    )

@app.route('/download-individual-csv')
def download_individual_csv():
    stats = generate_statistics()
    individual_emails = [e for e in stats['emails'] if e.get('category', '').lower() == 'individual']

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "Source"])

    for item in individual_emails:
        domain = item["email"].split("@")[1] if "@" in item["email"] else "Generic"
        writer.writerow([item["email"], f"Personal ({domain})"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=IndividualsEmails.csv"}
    )

# 4. SEND MAIL PAGE (/send_mail & /send)
@app.route('/send', methods=['GET'])
@app.route('/send_mail', methods=['GET'])
def send_mail_page():
    stats = generate_statistics()
    settings = load_settings()
    return render_template('send_mail.html', stats=stats, settings=settings, page='send')

@app.route('/send', methods=['POST'])
@app.route('/send_mail', methods=['POST'])
def send_mail_action():
    subject = request.form.get("subject", "Summer Internship Program")
    message = request.form.get("message", "")
    audience = request.form.get("audience", "All")
    mode = request.form.get("mode", "dry_run")
    dry_run = (mode.lower() == "dry_run")

    attachment_file = request.files.get("attachment")

    res = send_campaign(
        subject=subject,
        message=message,
        audience=audience,
        attachment_file=attachment_file,
        dry_run=dry_run
    )

    if dry_run:
        flash(f"Dry-Run Campaign Executed! Simulated sending to {res['delivered']} recipients.", "success")
    else:
        flash(f"Live Campaign Dispatched! Delivered: {res['delivered']}, Failed: {res['failed']}.", "success")

    return redirect(url_for('report_page'))

# 5. REPORT PAGE (/report)
@app.route('/report')
def report_page():
    report_data = generate_delivery_report()
    return render_template('report.html', report=report_data, page='report')

@app.route('/download-report')
def download_report():
    report_data = generate_delivery_report()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email Address", "Delivery Status", "Sent Timestamp"])

    for log in report_data.get("delivery_table", []):
        writer.writerow([log.get("email"), log.get("status"), log.get("sent_at")])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=Campaign_Delivery_Report.csv"}
    )

# 6. SETTINGS PAGE (/settings)
@app.route('/settings', methods=['GET'])
def settings_page():
    settings_data = load_settings()
    return render_template('settings.html', settings=settings_data, page='settings')

@app.route('/settings', methods=['POST'])
def settings_action():
    updated = {
        "gmail_email": request.form.get("gmail_email", "").strip(),
        "smtp_email": request.form.get("gmail_email", "").strip(),
        "app_password": request.form.get("app_password", "").strip(),
        "smtp_password": request.form.get("app_password", "").strip(),
        "gemini_api_key": request.form.get("gemini_api_key", "").strip(),
        "default_audience": request.form.get("default_audience", "Business").strip(),
        "daily_send_limit": int(request.form.get("daily_send_limit", 100)),
        "send_delay": float(request.form.get("send_delay", 2.0)),
        "default_subject": request.form.get("default_subject", "Summer Internship Program").strip(),
        "default_message": request.form.get("default_message", "").strip(),
        "sender_name": request.form.get("sender_name", "EmailPro Admin").strip()
    }
    save_settings(updated)
    flash("Settings successfully saved to settings.json!", "success")
    return redirect(url_for('settings_page'))

# API ROUTE: AI Email Copy Generator (/api/generate-email)
@app.route('/api/generate-email', methods=['POST'])
def api_generate_email():
    data = request.get_json() or {}
    topic = data.get("topic", "Summer Internship Program")
    audience = data.get("audience", "Business")
    settings = load_settings()

    try:
        import google.generativeai as genai
        key = settings.get("gemini_api_key")
        if key:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Write a professional email subject and body content for a {audience} audience about: '{topic}'. Return JSON with keys 'subject' and 'content'."
            response = model.generate_content(prompt)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            import json
            parsed = json.loads(text)
            return jsonify(parsed), 200
    except Exception:
        pass

    return jsonify({
        "subject": f"Invitation: {topic}",
        "content": f"Dear Partner,\n\nWe invite your organization to participate in our {topic}.\n\nPlease review the attached presentation catalog for details.\n\nBest regards,\nEmailPro Team"
    }), 200

if __name__ == '__main__':
    print("Starting EXPORT Automation System / EmailPro Web Server on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)
