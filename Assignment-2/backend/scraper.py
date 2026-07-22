"""
scraper.py – SerpApi search + BeautifulSoup email/phone extraction.

DEMO MODE: If SERPAPI_KEY is not set in .env the scraper falls back to a
set of realistic sample leads so the rest of the workflow still works.
"""

import os
import re
import requests
from bs4 import BeautifulSoup

SERPAPI_KEY = os.environ.get('SERPAPI_KEY', '').strip()

# ── Regex patterns ────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(
    r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}\b'
)
PHONE_RE = re.compile(
    r'(?:\+?\d[\d\s\-\.]{7,}\d)'
)

# Common throwaway / example domains to skip
_IGNORE_EMAIL_DOMAINS = {
    'example.com', 'domain.com', 'email.com', 'yoursite.com',
    'yourdomain.com', 'sentry.io', 'sentry-next.io',
    'wixpress.com', 'squarespace.com',
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0 Safari/537.36'
    )
}


# ── SerpApi search ────────────────────────────────────────────────────────────

def search_serpapi(keywords: str, countries: str, limit: int,
                   seed_urls: str = '') -> list[dict]:
    """
    Returns a list of raw results dicts:
      { 'title': str, 'url': str, 'country': str }
    """
    if not SERPAPI_KEY:
        return _demo_search_results(limit)

    try:
        from serpapi import GoogleSearch
    except ImportError:
        return _demo_search_results(limit)

    results = []
    country_list = [c.strip() for c in countries.split(',') if c.strip()]
    if not country_list:
        country_list = ['USA']

    per_country = max(1, limit // len(country_list))

    for country in country_list:
        query = f"{keywords} {country}"
        try:
            search = GoogleSearch({
                'q':       query,
                'api_key': SERPAPI_KEY,
                'num':     per_country + 5,   # fetch a few extra to filter
            })
            data    = search.get_dict()
            organic = data.get('organic_results', [])
            for r in organic[:per_country]:
                url = r.get('link', '')
                if url:
                    results.append({
                        'title':   r.get('title', 'Unknown Business'),
                        'url':     url,
                        'country': country,
                    })
        except Exception as exc:
            print(f"[SerpApi] error for '{query}': {exc}")

    # Also include any manually entered seed URLs
    for raw_url in (seed_urls or '').split('\n'):
        url = raw_url.strip()
        if url and url.startswith('http'):
            results.append({'title': url, 'url': url, 'country': country_list[0]})

    return results[:limit]


# ── Web scraper ───────────────────────────────────────────────────────────────

def scrape_contact_info(url: str) -> dict:
    """
    Visit a webpage and extract:
      email, phone, owner (if detectable)
    Returns a dict with those keys (may be empty strings).
    """
    email = phone = owner = ''

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        # ── Email: prefer mailto: links ───────────────────────────────────────
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().startswith('mailto:'):
                addr = href[7:].split('?')[0].strip().lower()
                if addr and '@' in addr and _valid_email(addr):
                    email = addr
                    break

        # ── Email: regex over page text ───────────────────────────────────────
        if not email:
            all_text = soup.get_text(' ', strip=True)
            for match in EMAIL_RE.findall(all_text):
                m = match.lower()
                if _valid_email(m):
                    email = m
                    break

        # ── Phone ─────────────────────────────────────────────────────────────
        all_text = soup.get_text(' ', strip=True)
        for ph in PHONE_RE.findall(all_text):
            cleaned = ph.strip()
            if len(re.sub(r'\D', '', cleaned)) >= 7:
                phone = cleaned[:25]
                break

        # ── Owner: look for common patterns ───────────────────────────────────
        #  e.g. "Contact: John Smith", "Owner: Jane Doe"
        owner_match = re.search(
            r'(?:owner|founder|contact|ceo|director)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)',
            all_text, re.I
        )
        if owner_match:
            owner = owner_match.group(1)

    except Exception as exc:
        print(f"[Scraper] {url} → {exc}")

    return {'email': email, 'phone': phone, 'owner': owner}


def compute_score(email: str, phone: str, owner: str) -> int:
    score = 0
    if email:  score += 60
    if phone:  score += 25
    if owner:  score += 15
    return min(score, 100)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _valid_email(addr: str) -> bool:
    domain = addr.split('@')[-1] if '@' in addr else ''
    return (
        '@' in addr
        and domain not in _IGNORE_EMAIL_DOMAINS
        and not addr.endswith(('.png', '.jpg', '.gif', '.svg'))
        and len(addr) < 120
    )


def _demo_search_results(limit: int) -> list[dict]:
    """Realistic demo data used when SERPAPI_KEY is not configured."""
    samples = [
        {
            'title':   'Soundtopia',
            'url':     'https://soundtopia.com',
            'country': 'USA',
            '_email':  'info@soundtopia.com',
            '_phone':  '+1-800-555-0101',
            '_owner':  'Sarah Mitchell',
        },
        {
            'title':   'Best Himalaya',
            'url':     'https://besthimalaya.com',
            'country': 'USA',
            '_email':  'info@besthimalaya.com',
            '_phone':  '+1-800-555-0202',
            '_owner':  '',
        },
        {
            'title':   'Himalayan Sound Craft',
            'url':     'https://himalayansoundcraft.com',
            'country': 'UK',
            '_email':  'contact@himalayansoundcraft.com',
            '_phone':  '+44-20-7946-0123',
            '_owner':  'David Carter',
        },
        {
            'title':   'Nepal Bowl World',
            'url':     'https://nepalbowlworld.com',
            'country': 'UK',
            '_email':  'wholesale@nepalbowlworld.com',
            '_phone':  '+44-161-555-9876',
            '_owner':  '',
        },
        {
            'title':   'Zen Singing Bowls Co.',
            'url':     'https://zensingbowls.com',
            'country': 'USA',
            '_email':  'zen@zensingbowls.com',
            '_phone':  '+1-555-876-5432',
            '_owner':  'Emma Rose',
        },
    ]
    return samples[:limit]


def get_demo_contact(url: str, demo_results: list) -> dict:
    """For demo mode, look up the pre-set contact info by URL."""
    for r in demo_results:
        if r.get('url') == url:
            return {
                'email': r.get('_email', ''),
                'phone': r.get('_phone', ''),
                'owner': r.get('_owner', ''),
            }
    return {'email': '', 'phone': '', 'owner': ''}
