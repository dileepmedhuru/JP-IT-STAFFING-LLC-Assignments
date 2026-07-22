import json
import pandas as pd
import config
from utils import get_db_connection, load_settings

PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "protonmail.com"}

def classify_single_email(email):
    """Domain classification logic according to specification."""
    if not email or not isinstance(email, str) or "@" not in email:
        return "Individual"

    clean = email.lower().strip()
    domain = clean.split("@")[1].strip()
    if domain in PERSONAL_DOMAINS:
        return "Individual"
    return "Business"

def classify_with_gemini(emails_list, gemini_key):
    """Uses Google Gemini API for zero-shot batch classification if key is configured."""
    if not gemini_key or len(gemini_key.strip()) < 10:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)

        prompt = f"""You are an email classifier.
Classify each email into either "Business" or "Individual".

Rules:
- Personal free domains (gmail.com, yahoo.com, hotmail.com, outlook.com) -> Individual
- Corporate / company domains (company.com, startup.ai, techcorp.in) -> Business

Return ONLY a valid JSON object mapping each email string to "Business" or "Individual".
Emails:
{json.dumps(emails_list, indent=2)}
"""
        response = None
        for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    break
            except Exception:
                continue

        if not response or not response.text:
            return None

        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(text)
        return {k.lower().strip(): v.capitalize().strip() for k, v in parsed.items()}
    except Exception as e:
        print(f"Gemini API fallback to local domain rules: {e}")
        return None

def save_business_csv(business_emails):
    """Saves business emails list to uploads/BusinessEmails.csv."""
    path = config.UPLOAD_FOLDER / "BusinessEmails.csv"
    df = pd.DataFrame([{"email": e, "category": "Business"} for e in business_emails])
    df.to_csv(path, index=False)
    return str(path)

def save_individual_csv(individual_emails):
    """Saves individual emails list to uploads/IndividualsEmails.csv."""
    path = config.UPLOAD_FOLDER / "IndividualsEmails.csv"
    df = pd.DataFrame([{"email": e, "category": "Individual"} for e in individual_emails])
    df.to_csv(path, index=False)
    return str(path)

def classify_emails():
    """Reads SQLite database, classifies emails, updates DB, and outputs CSVs."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        rows = cursor.execute("SELECT * FROM emails").fetchall()
        emails = [dict(r) for r in rows]

        if not emails:
            conn.close()
            return {"total": 0, "business_count": 0, "individual_count": 0, "business_emails": [], "individual_emails": []}

        settings = load_settings()
        gemini_key = settings.get("gemini_api_key", "")

        email_strings = [e["email"] for e in emails]
        gemini_map = None
        if gemini_key:
            gemini_map = classify_with_gemini(email_strings, gemini_key)

        business_emails = []
        individual_emails = []

        for item in emails:
            email = item["email"]
            if gemini_map and email.lower() in gemini_map:
                category = gemini_map[email.lower()]
            else:
                category = classify_single_email(email)

            if category == "Business":
                business_emails.append(email)
            else:
                individual_emails.append(email)

            cursor.execute("UPDATE emails SET category = ? WHERE id = ?", (category, item["id"]))

        conn.commit()
        conn.close()

        save_business_csv(business_emails)
        save_individual_csv(individual_emails)

        return {
            "total": len(emails),
            "business_count": len(business_emails),
            "individual_count": len(individual_emails),
            "business_emails": business_emails,
            "individual_emails": individual_emails
        }
    except Exception as e:
        print(f"Classification error fallback: {e}")
        return {"total": 0, "business_count": 0, "individual_count": 0, "business_emails": [], "individual_emails": []}
