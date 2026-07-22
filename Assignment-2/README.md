# Singing Bowl Export Desk

A full-stack web application for finding business leads, scraping contact emails, and sending bulk catalog emails — built as Assignment 2 for JP IT Staffing LLC.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML, CSS, JavaScript |
| Backend | Python Flask + Flask-SQLAlchemy |
| Database | SQLite |
| Search | SerpApi (Google Search API) |
| Scraping | BeautifulSoup4 + Requests |
| Email | Gmail SMTP (smtplib) |

## Project Structure

```
assignment 2/
├── backend/
│   ├── app.py          # Flask server + all API routes
│   ├── models.py       # SQLAlchemy Lead + AppStats models
│   ├── scraper.py      # SerpApi search + BeautifulSoup scraping
│   └── mailer.py       # Gmail SMTP email sender
├── frontend/
│   ├── index.html      # Single-page dashboard
│   ├── style.css       # Custom CSS styling
│   └── script.js       # Vanilla JS frontend logic
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── test_mail.py        # SMTP diagnostic script
```

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure credentials
```bash
copy .env.example .env
```
Edit `.env` and fill in:
- `SERPAPI_KEY` — get free key at [serpapi.com](https://serpapi.com)
- `GMAIL_USER` — your Gmail address
- `GMAIL_APP_PASSWORD` — 16-char Gmail App Password (Google Account → Security → App Passwords)

### 3. Run the server
```bash
python backend/app.py
```

### 4. Open the dashboard
Visit **http://localhost:5000**

## Workflow

1. **Search Leads** — Enter keywords (e.g. `singing bowls wholesale`), countries, and limit → SerpApi fetches Google results → BeautifulSoup scrapes each site for emails and phone numbers
2. **Upload PDF** — Upload your catalog PDF to attach to emails
3. **Send Bulk Email** — Sends personalized HTML emails with PDF attachment to all leads via Gmail SMTP
4. **Export CSV** — Download all leads as a CSV file

## Features

- Real-time KPI dashboard (Total Leads, Contacted, Emails Sent, Failed)
- SerpApi + BeautifulSoup web scraping
- Gmail SMTP email dispatch with PDF attachment
- `{{variable}}` template substitution (ownerName, businessName, etc.)
- Lead table with per-row Send / Delete actions
- CSV export and database reset
- Demo mode (works without API keys using sample data)
