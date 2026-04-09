import asyncio
import os
import re
import json
import urllib.request
import base64
import ssl
import certifi
from datetime import datetime
from playwright.async_api import async_playwright
import anthropic

# Load local environmental variables if they exist
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("Error: ANTHROPIC_API_KEY environment variable not set.")
    exit(1)

# SSL context using certifi (fixes macOS Python cert issues)
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

BASE_URL = "https://www.google.com/about/careers/applications/jobs/results"
CONTEXT_FILE = "jay_professional_context_v1.md"
OUTPUT_FILE = "data/scouted_roles.json"
PAGES_PER_QUERY = 3  # 3 pages × 20 = 60 jobs per search query

# Targeted keyword searches — each maps to roles Jay actually wants
# Format: (query_param, location_param)
SEARCH_QUERIES = [
    ("product+manager",         "India"),
    ("strategy+operations",     "India"),
    ("growth+manager",          "India"),
    ("go-to-market",            "India"),
    ("product+strategy",        "India"),
    ("business+development",    "India"),
    ("partnerships",            "India"),
    ("policy+manager",          "India"),
]

EXTRACT_JS = '''() => {
    const cards = document.querySelectorAll("li.lLd3Je");
    const jobs = [];
    cards.forEach(card => {
        const titleEl  = card.querySelector("h3.QJPWVe");
        const locEl    = card.querySelector(".r0wTof");
        const jsdataEl = card.querySelector("[jsdata]");
        const jsdata   = jsdataEl ? jsdataEl.getAttribute("jsdata") : "";
        const idMatch  = jsdata.match(/;(\\d{10,})/);
        const jobId    = idMatch ? idMatch[1] : null;
        if (!jobId || !titleEl) return;
        jobs.push({
            title:    titleEl.innerText.trim(),
            location: locEl ? locEl.innerText.trim() : "",
            url:      "https://www.google.com/about/careers/applications/jobs/results/" + jobId,
            text:     card.innerText.replace(/\\s+/g, " ").trim().substring(0, 1500)
        });
    });
    return jobs;
}'''

async def scrape_jobs():
    total_queries = len(SEARCH_QUERIES)
    print(f"Running {total_queries} targeted searches × {PAGES_PER_QUERY} pages each...")
    all_jobs = []
    seen_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        await ctx.add_cookies([{
            "name": "CONSENT",
            "value": "YES+cb.20230501-14-p0.en+FX+414",
            "domain": ".google.com",
            "path": "/"
        }])
        page = await ctx.new_page()

        for q_idx, (query, location) in enumerate(SEARCH_QUERIES, 1):
            print(f"\n[{q_idx}/{total_queries}] Query: '{query}' | Location: {location}")
            query_new = 0
            for page_num in range(1, PAGES_PER_QUERY + 1):
                url = f"{BASE_URL}?q={query}&location={location}"
                if page_num > 1:
                    url += f"&page={page_num}"
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_selector("li.lLd3Je", timeout=12000)
                    await page.wait_for_timeout(1200)

                    jobs = await page.evaluate(EXTRACT_JS)
                    new = [j for j in jobs if j["url"] not in seen_urls]
                    for j in new:
                        seen_urls.add(j["url"])
                    all_jobs.extend(new)
                    query_new += len(new)
                    print(f"  p{page_num}: {len(jobs)} cards, {len(new)} new")

                    if len(new) == 0:
                        break
                except Exception as e:
                    print(f"  p{page_num} failed: {e}")
                    break

            print(f"  → {query_new} new unique jobs from this query (running total: {len(all_jobs)})")

        await browser.close()

    print(f"\nScraping complete: {len(all_jobs)} unique jobs collected across all queries.")
    return all_jobs

# Title keywords that signal a likely-relevant (non-pure-engineering) role
RELEVANT_TITLE_KEYWORDS = [
    "manager", "strategy", "operations", "product", "growth", "business",
    "partnerships", "policy", "go-to-market", "gtm", "marketing", "sales",
    "monetization", "monetisation", "commerce", "lead", "director", "head of",
    "program", "principal", "analyst", "insights", "trust", "integrity",
    "payments", "platform", "consumer", "experience", "data", "ai", "intelligence",
]

def prefilter_jobs(jobs_data):
    """Drop roles that are clearly outside Jay's profile before sending to Claude."""
    skip_keywords = [
        # Pure engineering
        "software engineer", "sre ", "site reliability", "network engineer",
        "hardware engineer", "test engineer", "security engineer",
        "infrastructure engineer", "embedded", "firmware", "kernel", "devops",
        # Student / entry-level
        "intern", "phd intern", "apprentice",
        # Offline BD / traditional partnerships (not digital product)
        "strategic partner development", "partner development manager",
        "partner sales", "field sales", "account executive",
        "strategic partner manager",  # music/media BD roles, not product
    ]
    filtered = []
    for job in jobs_data:
        title_lower = job.get("title", "").lower()
        if any(kw in title_lower for kw in skip_keywords):
            continue
        filtered.append(job)
    print(f"  Pre-filter: {len(jobs_data)} → {len(filtered)} jobs (dropped eng/intern/BD roles)")
    return filtered

def evaluate_jobs(jobs_data, context_text):
    jobs_data = prefilter_jobs(jobs_data)
    print(f"Evaluating {len(jobs_data)} jobs via Claude API...")
    if not jobs_data:
        return []

    prompt = f"""
You are a world-class Executive Recruiter and Job Scout evaluating Google roles for Jay Shukla.
Read his full professional context below before scoring anything.

## HARD DISCARD RULES (score 0 and exclude — do not include in output):
1. Pure engineering / SWE / SRE / infra / hardware / firmware roles
2. Intern, PhD intern, or associate/entry-level roles
3. Traditional offline BD roles: "Strategic Partner Development Manager", "Partner Development Manager", "Field Sales", "Account Executive", "Partner Sales" — these are relationship/sales roles, NOT digital product roles
4. Roles requiring 8+ years of product management experience — Jay has 7 years total
5. Roles with no digital product, growth, strategy, or market component

## SCORE HIGH (70–95) — Jay is a strong fit when:
- Role is Product Manager for a CONSUMER product (YouTube, Maps, Pay, Search, Assistant, Workspace)
- Role involves India market growth, localisation, or expansion for a global tech platform
- Role involves creator economy, short-form video, live streaming, social commerce, shoppertainment
- Role involves SMBs, informal businesses, or advertiser growth in India
- Role involves AI product (non-engineering): GTM, adoption, user research, product intuition
- Role involves Indian GenZ, regional/vernacular users, Tier 2/3 consumers
- Role is Strategy & Operations with a market/product mandate (not pure process/admin ops)

## SCORE MEDIUM (50–69) — Reasonable fit:
- PM roles in B2B or enterprise products (Cloud, Workspace, Ads) where India market component exists
- Strategy roles with strong analytical and market intelligence component
- Growth/marketing roles with a product lens
- Roles requiring 6–7 years experience where Jay's seniority is appropriate

## SCORE LOW / DISCARD (<45):
- Pure offline BD/partnerships: signing deals, managing C-suite relationships, music licensing, content deals
- Traditional sales or account management
- Operations roles that are pure process/workflow with no market or product growth mandate
- Roles Jay is clearly overqualified or underqualified for

## JAY'S EXPERIENCE CALIBRATION:
- Total product experience: ~7 years (ByteDance + Meta)
- Appropriate for: Senior IC, Group PM, Lead PM, Strategy Lead — NOT "Senior/Staff PM requiring 8+ years"
- If a role says "8 years minimum PM experience", score it below 45 and exclude

## JAY'S BACKGROUND (cite these specifically in why_good_fit):
- Meta: 2.3% India revenue uplift from SMB enforcement fix — single largest revenue feature in Meta India history
- Meta: Shoppertainment strategy — convergence of entertainment & commerce for Indian creators
- Meta: GenZ Product Council (25 members globally); AI field work; MetaAI India growth
- ByteDance: Scaled Resso from alpha → India's largest music streaming app
- ByteDance: TikTok Shop SMB India lead; India's Shoppertainment big bet; CPO-level TikTok re-entry strategy
- Core superpower: Translates on-ground Indian user observations into product decisions at scale
- Founder: Co-founded a travel startup (zero-to-one experience)

## SCORING CALIBRATION EXAMPLES:
- "Product Manager, YouTube Live Living Room" (3 yrs exp req, consumer video product) → score 70–80
- "Process Excellence Lead" (AI automation strategy, process transformation) → score 65–72
- "Strategic Partner Manager, Music Content Partnerships" (BD/music licensing) → DISCARD
- "Senior PM, YouTube Creation" (8 yrs exp required) → DISCARD (experience mismatch)

## CANDIDATE FULL CONTEXT:
{context_text}

## JOBS TO EVALUATE:
{json.dumps(jobs_data, indent=2)}

## OUTPUT FORMAT:
Return ONLY a valid JSON array. No markdown fences, no explanation outside the array.
Each object must follow this exact schema:
{{
  "id": "slug derived from job url or title",
  "title": "Exact job title from listing",
  "company": "Google",
  "location": "Location from listing",
  "url": "exact url from input",
  "relevance_score": 82,
  "role_summary": "1-2 sentence plain-English summary of what this role does.",
  "why_good_fit": "Specific reasons Jay fits — cite his actual stories, metrics, and experiences.",
  "how_to_win": "Concrete, actionable pitch strategy tailored to this specific role.",
  "key_requirements": "Bullet-point summary of the main requirements from the listing.",
  "date_published": "Date string from listing, or 'Not listed' if absent",
  "scraped_at": "{datetime.utcnow().isoformat()}Z"
}}
"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=16000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_response = message.content[0].text.strip()
        print("Claude API response received.")

        # Strip markdown code fences if present
        raw_response = re.sub(r'^```(?:json)?\s*', '', raw_response)
        raw_response = re.sub(r'\s*```$', '', raw_response.strip())

        match = re.search(r'\[.*\]', raw_response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            print("Claude did not return a valid JSON array.")
            print("Response preview:", raw_response[:300])
            return []
    except Exception as e:
        print(f"Claude API call failed: {e}")
        return []

async def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    if not os.path.exists(CONTEXT_FILE):
        print(f"Error: Could not find context file at {CONTEXT_FILE}")
        exit(1)
        
    with open(CONTEXT_FILE, "r") as f:
        context_text = f.read()

    jobs_data = []
    try:
        jobs_data = await scrape_jobs()
    except Exception as e:
        print(f"Scraping failed: {e}")
    
    final_list = []
    if jobs_data:
        results = evaluate_jobs(jobs_data, context_text)
        print(f"Kept {len(results)} jobs after filtering.")
        # Each run is a fresh snapshot — no merging with old data to avoid stale results
        final_list = results
    else:
        print("Scraping returned nothing — keeping last saved results.")
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r") as f:
                    final_list = [j for j in json.load(f) if "role_summary" in j]
            except:
                pass

    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_list, f, indent=2)
        
    print(f"Successfully saved {len(final_list)} jobs to {OUTPUT_FILE}")
    upload_to_github(OUTPUT_FILE)

def upload_to_github(filepath):
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    if not GITHUB_TOKEN:
        print("No GitHub Token provided, skipping upload.")
        return

    print("Uploading to GitHub so your dashboard updates...")
    repo = "jayshukla12/role-scout"
    path = "data/scouted_roles.json"
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    
    req = urllib.request.Request(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    sha = None
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as response:
            data = json.loads(response.read().decode())
            sha = data["sha"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"Failed to get file SHA: {e}")
            return

    with open(filepath, "rb") as f:
        content = f.read()
    encoded_content = base64.b64encode(content).decode('utf-8')

    payload = {
        "message": "Automated local scout update",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v3+json"
    }, method="PUT")

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as response:
            print("Successfully uploaded and triggered website refresh!")
    except Exception as e:
        print(f"Failed to upload: {e}")

if __name__ == "__main__":
    asyncio.run(main())
