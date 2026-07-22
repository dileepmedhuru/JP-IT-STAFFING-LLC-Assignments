"""
app.py – Singing Bowl Export Desk  |  Flask backend + API
==========================================================
Run:  python backend/app.py
URL:  http://localhost:5000
"""

import os
import csv
import io
import sys
from datetime import datetime
from pathlib import Path

# ── Load .env before anything else ───────────────────────────────────────────
from dotenv import load_dotenv

_HERE    = Path(__file__).parent                        # backend/
_ROOT    = _HERE.parent                                 # project root
_DOTENV  = _ROOT / '.env'
if _DOTENV.exists():
    load_dotenv(_DOTENV, override=True)
else:
    load_dotenv(_ROOT / '.env.example', override=True)   # fallback to example

# ── Flask + extensions ────────────────────────────────────────────────────────
from flask import (
    Flask, jsonify, request, send_from_directory,
    send_file, abort,
)
from flask_cors      import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils  import secure_filename

# ── Path constants ────────────────────────────────────────────────────────────
FRONTEND_DIR = _ROOT / 'frontend'
UPLOAD_DIR   = _HERE / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

DB_URI = f"sqlite:///{_HERE / 'database.db'}"

# ── App factory ───────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    static_folder=str(FRONTEND_DIR),
    static_url_path='',
)
app.config['SQLALCHEMY_DATABASE_URI']        = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH']             = 50 * 1024 * 1024   # 50 MB

CORS(app)                                               # allow all origins

# ── Import models (after app is created) ─────────────────────────────────────
sys.path.insert(0, str(_HERE))
from models import db, Lead, AppStats

db.init_app(app)

with app.app_context():
    db.create_all()
    if not db.session.get(AppStats, 1):
        db.session.add(AppStats(id=1))
        db.session.commit()

# ── Config read from .env ─────────────────────────────────────────────────────
SERPAPI_KEY      = os.environ.get('SERPAPI_KEY', '').strip()
GMAIL_USER       = os.environ.get('GMAIL_USER', '').strip()
GMAIL_APP_PASS   = os.environ.get('GMAIL_APP_PASSWORD', '').strip()
WHATSAPP_NUMBER  = os.environ.get('WHATSAPP_NUMBER', '+977-9800000000').strip()


# ══════════════════════════════════════════════════════════════════════════════
#  FRONTEND SERVING
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def serve_index():
    return send_from_directory(str(FRONTEND_DIR), 'index.html')


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)


# ══════════════════════════════════════════════════════════════════════════════
#  API – CONFIG / STATUS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/config', methods=['GET'])
def api_config():
    """Return connection status for Search API and Mail."""
    return jsonify({
        'serpapi': {
            'connected': bool(SERPAPI_KEY),
            'mode':      'SerpApi' if SERPAPI_KEY else 'Demo Mode',
        },
        'mail': {
            'connected': bool(GMAIL_USER),
            'email':     GMAIL_USER or 'Not configured',
            'simulated': not bool(GMAIL_APP_PASS),
        },
        'whatsapp': WHATSAPP_NUMBER,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  API – STATS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/stats', methods=['GET'])
def api_stats():
    stats = db.session.get(AppStats, 1)
    return jsonify(stats.to_dict())


def _refresh_stats():
    """Recount from the leads table and update AppStats."""
    stats = db.session.get(AppStats, 1)
    stats.total_leads = Lead.query.count()
    stats.contacted   = Lead.query.filter_by(contacted=True).count()
    db.session.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  API – LEADS
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/leads', methods=['GET'])
def api_leads():
    leads = Lead.query.order_by(Lead.id.desc()).all()
    return jsonify([l.to_dict() for l in leads])


@app.route('/api/leads/<int:lead_id>', methods=['DELETE'])
def api_delete_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    _refresh_stats()
    return jsonify({'success': True})


# ══════════════════════════════════════════════════════════════════════════════
#  API – SEARCH (SerpApi + scraper)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/search', methods=['POST'])
def api_search():
    data      = request.get_json(force=True) or {}
    keywords  = data.get('keywords',  'singing bowls wholesale').strip()
    countries = data.get('countries', 'USA').strip()
    limit     = max(1, min(int(data.get('limit', 5)), 50))
    seed_urls = data.get('seed_urls', '').strip()

    from scraper import (
        search_serpapi, scrape_contact_info,
        compute_score, _demo_search_results, get_demo_contact,
    )

    is_demo       = not bool(SERPAPI_KEY)
    raw_results   = search_serpapi(keywords, countries, limit, seed_urls)
    demo_cache    = _demo_search_results(limit) if is_demo else []

    imported = 0
    emails_found = 0

    for r in raw_results:
        url     = r.get('url', '')
        title   = r.get('title', 'Unknown')
        country = r.get('country', countries.split(',')[0].strip())

        # Skip if exact URL already stored
        if Lead.query.filter_by(website=url).first():
            continue

        if is_demo:
            contact = get_demo_contact(url, demo_cache)
        else:
            contact = scrape_contact_info(url)

        email = contact.get('email', '')
        phone = contact.get('phone', '')
        owner = contact.get('owner', '')

        if email:
            emails_found += 1

        score = compute_score(email, phone, owner)

        # Extract clean domain for "source"
        try:
            from urllib.parse import urlparse
            source = urlparse(url).netloc or url
        except Exception:
            source = url

        lead = Lead(
            business_name = title,
            owner         = owner,
            email         = email,
            phone         = phone,
            country       = country,
            source        = source,
            score         = score,
            website       = url,
        )
        db.session.add(lead)
        imported += 1

    db.session.commit()
    _refresh_stats()

    return jsonify({
        'success':      True,
        'imported':     imported,
        'emails_found': emails_found,
        'demo_mode':    is_demo,
        'message':      (
            f'Search complete. Extracted {emails_found} emails '
            f'and imported {imported} leads.'
            + (' [Demo Mode – set SERPAPI_KEY for real results]' if is_demo else '')
        ),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  API – PDF UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {'pdf'}

def _allowed(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    if not _allowed(file.filename):
        return jsonify({'error': 'Only PDF files are accepted'}), 400

    filename = secure_filename(file.filename)
    save_path = UPLOAD_DIR / filename
    file.save(str(save_path))

    url = f'http://localhost:5000/uploads/{filename}'
    return jsonify({
        'success':  True,
        'filename': filename,
        'url':      url,
        'path':     str(save_path),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  API – SEND EMAIL (single lead)
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/send-email/<int:lead_id>', methods=['POST'])
def api_send_email(lead_id):
    lead = Lead.query.get_or_404(lead_id)

    data          = request.get_json(force=True) or {}
    subject       = data.get('subject', 'Handcrafted Singing Bowl Export Catalog')
    html_template = data.get('template', _default_template())
    pdf_path      = data.get('pdf_path', _latest_pdf())

    if not lead.email:
        return jsonify({'error': 'This lead has no email address'}), 400

    from mailer import render_template, send_email

    variables = {
        'ownerName':      lead.owner or lead.business_name,
        'businessName':   lead.business_name,
        'whatsappNumber': WHATSAPP_NUMBER,
        'unsubscribeUrl': f'http://localhost:5000/unsubscribe/{lead.id}',
        'country':        lead.country,
    }
    html_body = render_template(html_template, variables)

    result = send_email(
        to_email  = lead.email,
        subject   = subject,
        html_body = html_body,
        pdf_path  = pdf_path if pdf_path else None,
    )

    if result['success']:
        lead.contacted = True
        stats = db.session.get(AppStats, 1)
        stats.emails_sent  += 1
        stats.contacted     = Lead.query.filter_by(contacted=True).count() + 1
        db.session.commit()
        _refresh_stats()

        return jsonify({
            'success':   True,
            'simulated': result.get('simulated', False),
            'message':   result['message'],
            'lead':      lead.to_dict(),
            'stats':     db.session.get(AppStats, 1).to_dict(),
        })
    else:
        stats = db.session.get(AppStats, 1)
        stats.failed += 1
        db.session.commit()
        return jsonify({'error': result['message']}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  API – SEND BULK EMAIL
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/send-bulk-email', methods=['POST'])
def api_send_bulk():
    data          = request.get_json(force=True) or {}
    subject       = data.get('subject', 'Handcrafted Singing Bowl Export Catalog')
    html_template = data.get('template', _default_template())
    pdf_path      = data.get('pdf_path', _latest_pdf())

    from mailer import render_template, send_email

    # Send to ALL leads that have an email (including already-contacted ones)
    all_leads_with_email = Lead.query.filter(Lead.email != '').all()

    if not all_leads_with_email:
        total = Lead.query.count()
        if total == 0:
            return jsonify({'error': 'No leads in database. Please run Search Leads first to import leads.'}), 400
        else:
            return jsonify({'error': f'Found {total} lead(s) but none have email addresses. Try searching again or add leads manually.'}), 400

    pending = all_leads_with_email   # send to everyone with an email

    progress = []
    sent = 0
    failed = 0

    for lead in pending:
        variables = {
            'ownerName':      lead.owner or lead.business_name,
            'businessName':   lead.business_name,
            'whatsappNumber': WHATSAPP_NUMBER,
            'unsubscribeUrl': f'http://localhost:5000/unsubscribe/{lead.id}',
            'country':        lead.country,
        }
        html_body = render_template(html_template, variables)
        result = send_email(
            to_email  = lead.email,
            subject   = subject,
            html_body = html_body,
            pdf_path  = pdf_path if pdf_path else None,
        )

        if result['success']:
            lead.contacted = True
            sent += 1
            progress.append({'email': lead.email, 'status': 'sent', 'simulated': result.get('simulated', False)})
        else:
            failed += 1
            progress.append({'email': lead.email, 'status': 'failed', 'error': result['message']})

    stats = db.session.get(AppStats, 1)
    stats.emails_sent += sent
    stats.failed      += failed
    db.session.commit()
    _refresh_stats()

    return jsonify({
        'success':  True,
        'sent':     sent,
        'failed':   failed,
        'progress': progress,
        'stats':    db.session.get(AppStats, 1).to_dict(),
        'leads':    [l.to_dict() for l in Lead.query.order_by(Lead.id.desc()).all()],
    })


# ══════════════════════════════════════════════════════════════════════════════
#  API – EXPORT CSV
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/export', methods=['GET'])
def api_export():
    leads = Lead.query.order_by(Lead.id.asc()).all()
    if not leads:
        return jsonify({'error': 'No leads to export'}), 400

    output = io.StringIO()
    fieldnames = ['id', 'business_name', 'owner', 'email', 'phone',
                  'country', 'source', 'score', 'contacted', 'website']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for lead in leads:
        row = lead.to_dict()
        row['contacted'] = 'Yes' if row['contacted'] else 'No'
        writer.writerow({k: row.get(k, '') for k in fieldnames})

    output.seek(0)
    mem = io.BytesIO(output.getvalue().encode('utf-8'))
    mem.seek(0)

    filename = f'singing_bowl_leads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name=filename)


# ══════════════════════════════════════════════════════════════════════════════
#  API – RESET DATABASE
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/reset', methods=['POST'])
def api_reset():
    Lead.query.delete()
    stats = db.session.get(AppStats, 1)
    stats.total_leads = 0
    stats.contacted   = 0
    stats.emails_sent = 0
    stats.failed      = 0
    db.session.commit()
    return jsonify({'success': True})


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _latest_pdf() -> str | None:
    """Return path to the most recently uploaded PDF, or None."""
    pdfs = sorted(UPLOAD_DIR.glob('*.pdf'), key=os.path.getmtime, reverse=True)
    return str(pdfs[0]) if pdfs else None


def _default_template() -> str:
    return """<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
  <h2 style="color:#b8860b;">Handcrafted Singing Bowl Export Catalog</h2>
  <p>Dear <strong>{{ownerName}}</strong>,</p>
  <p>We are delighted to reach out to <strong>{{businessName}}</strong> regarding our
     exclusive collection of handcrafted singing bowls, sourced directly from skilled
     artisans in the Himalayan region.</p>
  <p>Our products are crafted with the finest quality metals and tuned to specific
     frequencies for therapeutic and meditative use. We offer competitive wholesale
     pricing, custom packaging, and reliable international shipping to
     <strong>{{country}}</strong>.</p>
  <p>Please find our full export catalog attached for your reference. We would love
     to discuss how we can build a long-term business relationship with you.</p>
  <p>📱 WhatsApp: <strong>{{whatsappNumber}}</strong></p>
  <hr style="border:none;border-top:1px solid #eee;margin:24px 0;"/>
  <p style="font-size:12px;color:#999;">
    To unsubscribe from future communications,
    <a href="{{unsubscribeUrl}}">click here</a>.
  </p>
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(debug=True, port=5000)
