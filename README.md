# JP IT Staffing LLC - Assignments

This repository contains internship assignment projects:

## 📁 Repository Structure

- **[`Assignment-1/`](./Assignment-1)**: EmailPro – AI Email Campaign Manager (Flask + SQLite + Jinja2)
- **`Assignment-2/`**: *(Coming Soon)*

---

## 🚀 Assignment 1: EmailPro – AI Email Campaign Manager

An automated buyer discovery, AI classification, email campaign composer, and delivery analytics platform built using Python Flask, SQLite, and Google Gemini AI.

### Features in `Assignment-1`:
- **CSV Dataset Import & Deduplication**: Upload buyer `.csv` files, validate email syntaxes, and clean duplicate entries.
- **AI Recipient Classification**: Zero-shot AI and domain-rule classifier separating leads into `Business` vs. `Individual` tables.
- **Campaign Composer with Attachments**: Draft targeted outreach emails, auto-generate content using Gemini AI, and attach PowerPoint presentations (`presentation.pptx`).
- **Real-Time Analytics**: View success metrics, interactive Chart.js graphs, delivery status logs, and download CSV reports.

### Running Assignment 1:
```bash
cd Assignment-1
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.
