"""
LeadScraper Pro — Python Backend
FastAPI server with robust web scraping engine.
"""
import re
import time
import hashlib
from urllib.parse import urljoin, urlparse
from typing import Optional

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl


# ── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LeadScraper Pro API",
    description="Robust web scraping engine for lead generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 15


# ── Models ───────────────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 3


class ExtractedLead(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    source_url: str
    category_suggestion: Optional[str] = None


class ScrapeResponse(BaseModel):
    success: bool
    url: str
    leads: list[ExtractedLead]
    pages_scraped: int
    duration_ms: int
    error: Optional[str] = None


# ── Extraction Helpers ───────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

PHONE_RE = re.compile(
    r"(?:\+?1[-.\s]?)?"
    r"(?:\(?\d{3}\)?[-.\s]?)"
    r"\d{3}[-.\s]?\d{4}"
    r"|(?:\+?\d{1,3}[-.\s]?)?\d{4,5}[-.\s]?\d{4,6}"
)

SOCIAL_RE = re.compile(
    r"https?://(?:www\.)?(?:linkedin|twitter|facebook|instagram|github)\.com/[^\s\"'<>]+",
    re.IGNORECASE,
)

IGNORE_EMAIL_PATTERNS = {
    "example.com", "sentry.io", "wixpress.com", "w3.org",
    "schema.org", "google.com", "facebook.com", "twitter.com",
    ".png", ".jpg", ".gif", ".svg", ".css", ".js",
}


def extract_emails(text: str) -> list[str]:
    """Extract valid email addresses, filtering out junk."""
    raw = EMAIL_RE.findall(text)
    seen = set()
    result = []
    for email in raw:
        email_lower = email.lower()
        if email_lower in seen:
            continue
        if any(p in email_lower for p in IGNORE_EMAIL_PATTERNS):
            continue
        if email_lower.endswith((".png", ".jpg", ".gif", ".svg", ".css", ".js")):
            continue
        seen.add(email_lower)
        result.append(email)
    return result[:20]  # cap at 20


def extract_phones(text: str) -> list[str]:
    """Extract phone numbers."""
    raw = PHONE_RE.findall(text)
    seen = set()
    result = []
    for phone in raw:
        cleaned = re.sub(r"[^\d+]", "", phone)
        if len(cleaned) < 7 or len(cleaned) > 15:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(phone.strip())
    return result[:10]


def extract_socials(text: str) -> list[str]:
    """Extract social media profile URLs."""
    raw = SOCIAL_RE.findall(text)
    seen = set()
    result = []
    for url in raw:
        cleaned = url.rstrip(")/.,;:")
        if cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            result.append(cleaned)
    return result[:10]


def extract_company_info(soup: BeautifulSoup, url: str) -> dict:
    """Extract company name and description from meta tags and page structure."""
    info = {"name": "", "description": ""}

    # Company name: try OG title → meta title → <title> tag → domain
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        info["name"] = og_title["content"].strip()
    elif soup.title and soup.title.string:
        info["name"] = soup.title.string.strip()

    # Clean up common suffixes from titles
    for sep in [" | ", " - ", " — ", " :: ", " » "]:
        if sep in info["name"]:
            parts = info["name"].split(sep)
            info["name"] = parts[0].strip() if len(parts[0]) > 3 else parts[-1].strip()

    # Fallback to domain name
    if not info["name"]:
        parsed = urlparse(url)
        info["name"] = parsed.hostname.replace("www.", "").split(".")[0].title()

    # Description
    og_desc = soup.find("meta", property="og:description")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if og_desc and og_desc.get("content"):
        info["description"] = og_desc["content"].strip()[:300]
    elif meta_desc and meta_desc.get("content"):
        info["description"] = meta_desc["content"].strip()[:300]
    else:
        # Fallback: grab first <p> with reasonable text
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 50:
                info["description"] = text[:300]
                break

    return info


def extract_contact_name(soup: BeautifulSoup) -> Optional[str]:
    """Try to extract a contact person name from structured data or common patterns."""
    # Check JSON-LD for person schema
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string or ""
        if '"@type"' in text and '"Person"' in text:
            name_match = re.search(r'"name"\s*:\s*"([^"]+)"', text)
            if name_match:
                return name_match.group(1)

    # Check meta author
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        return author_meta["content"].strip()

    return None


# ── Categorization ───────────────────────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "Technology": [
        "software", "tech", "digital", "computer", "app", "cloud",
        "data", "ai", "machine learning", "saas", "devops", "cyber",
        "programming", "developer", "startup", "api", "platform",
    ],
    "Healthcare": [
        "health", "medical", "hospital", "clinic", "doctor", "pharma",
        "wellness", "therapy", "dental", "patient", "care", "nursing",
    ],
    "Finance": [
        "finance", "bank", "invest", "insurance", "fintech", "trading",
        "capital", "loan", "mortgage", "wealth", "fund", "credit",
    ],
    "E-commerce": [
        "shop", "store", "ecommerce", "e-commerce", "retail", "buy",
        "cart", "product", "marketplace", "sell", "order", "shipping",
    ],
    "Education": [
        "education", "school", "university", "college", "learning",
        "course", "training", "student", "teach", "academic", "tutor",
    ],
    "Real Estate": [
        "real estate", "property", "home", "house", "rent",
        "apartment", "mortgage", "realty", "listing", "broker",
    ],
    "Marketing": [
        "marketing", "agency", "advertis", "brand", "seo", "social media",
        "content", "campaign", "creative", "design", "growth",
    ],
    "Legal": [
        "law", "legal", "attorney", "lawyer", "firm",
        "litigation", "counsel", "court", "justice",
    ],
    "Manufacturing": [
        "manufactur", "industrial", "factory", "production",
        "supply chain", "logistics", "warehouse", "equipment",
    ],
}


def categorize(text: str) -> Optional[str]:
    """Auto-detect industry category from page content."""
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score
    if scores:
        return max(scores, key=scores.get)
    return None


# ── Scraping Engine ──────────────────────────────────────────────────────────

def fetch_page(url: str) -> Optional[tuple[str, int]]:
    """Fetch a page and return (html, status_code)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return resp.text, resp.status_code
    except requests.RequestException:
        return None


def find_internal_links(soup: BeautifulSoup, base_url: str, max_links: int = 10) -> list[str]:
    """Find internal links worth crawling (contact, about, team pages)."""
    priority_patterns = ["contact", "about", "team", "people", "staff", "our-team", "company"]
    parsed_base = urlparse(base_url)
    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Same domain only
        if parsed.hostname != parsed_base.hostname:
            continue

        # Skip anchors, files, etc.
        if parsed.path in seen or parsed.path == parsed_base.path:
            continue
        if any(ext in parsed.path.lower() for ext in [".pdf", ".jpg", ".png", ".gif", ".zip", ".csv"]):
            continue

        seen.add(parsed.path)

        # Prioritize useful pages
        path_lower = parsed.path.lower()
        is_priority = any(p in path_lower for p in priority_patterns)
        if is_priority:
            links.insert(0, full_url)
        else:
            links.append(full_url)

    return links[:max_links]


def scrape_url(url: str, max_pages: int = 3) -> ScrapeResponse:
    """Main scraping function: fetch page(s), extract leads."""
    start_time = time.time()
    all_emails: list[str] = []
    all_phones: list[str] = []
    all_socials: list[str] = []
    company_info = {"name": "", "description": ""}
    contact_name: Optional[str] = None
    full_text = ""
    pages_scraped = 0

    # Normalize URL
    url_str = str(url)
    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str

    # Scrape main page
    result = fetch_page(url_str)
    if not result:
        duration = int((time.time() - start_time) * 1000)
        return ScrapeResponse(
            success=False, url=url_str, leads=[], pages_scraped=0,
            duration_ms=duration, error="Failed to fetch the website. Check the URL and try again.",
        )

    html, _ = result
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True)
    full_text += " " + text
    pages_scraped += 1

    company_info = extract_company_info(soup, url_str)
    contact_name = extract_contact_name(soup)
    all_emails.extend(extract_emails(html))
    all_phones.extend(extract_phones(text))
    all_socials.extend(extract_socials(html))

    # Crawl internal pages (contact, about, team)
    if max_pages > 1:
        internal_links = find_internal_links(soup, url_str, max_links=max_pages - 1)
        for link in internal_links:
            if pages_scraped >= max_pages:
                break
            sub_result = fetch_page(link)
            if not sub_result:
                continue
            sub_html, _ = sub_result
            sub_soup = BeautifulSoup(sub_html, "lxml")
            sub_text = sub_soup.get_text(separator=" ", strip=True)
            full_text += " " + sub_text
            pages_scraped += 1

            all_emails.extend(extract_emails(sub_html))
            all_phones.extend(extract_phones(sub_text))
            all_socials.extend(extract_socials(sub_html))

            # Try to find contact name from sub-pages
            if not contact_name:
                contact_name = extract_contact_name(sub_soup)

    # Deduplicate
    all_emails = list(dict.fromkeys(all_emails))
    all_phones = list(dict.fromkeys(all_phones))
    all_socials = list(dict.fromkeys(all_socials))

    # Categorize
    category = categorize(full_text)

    # Build leads
    leads: list[ExtractedLead] = []

    if all_emails:
        # One lead per email
        for i, email in enumerate(all_emails[:10]):
            leads.append(ExtractedLead(
                company_name=company_info["name"],
                contact_name=contact_name if i == 0 else None,
                email=email,
                phone=all_phones[i] if i < len(all_phones) else (all_phones[0] if all_phones else None),
                website=url_str,
                description=company_info["description"],
                source_url=url_str,
                category_suggestion=category,
            ))
    elif all_phones:
        # No emails, but have phones
        for i, phone in enumerate(all_phones[:5]):
            leads.append(ExtractedLead(
                company_name=company_info["name"],
                contact_name=contact_name if i == 0 else None,
                email=None,
                phone=phone,
                website=url_str,
                description=company_info["description"],
                source_url=url_str,
                category_suggestion=category,
            ))
    else:
        # No contact info, still create a company lead
        leads.append(ExtractedLead(
            company_name=company_info["name"],
            contact_name=contact_name,
            email=None,
            phone=None,
            website=url_str,
            description=company_info["description"],
            source_url=url_str,
            category_suggestion=category,
        ))

    duration = int((time.time() - start_time) * 1000)
    return ScrapeResponse(
        success=True,
        url=url_str,
        leads=leads,
        pages_scraped=pages_scraped,
        duration_ms=duration,
    )


# ── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "LeadScraper Pro API", "version": "1.0.0"}


@app.post("/api/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(req: ScrapeRequest):
    """Scrape a website and return extracted leads."""
    try:
        result = scrape_url(str(req.url), req.max_pages)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
