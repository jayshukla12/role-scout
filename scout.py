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
OPENAI_BASE_URL = "https://openai.com/careers/search"
OPENAI_LOCATION_FILTER = "l=d2b1576e-0e1e-4611-b587-6f65f326be14%2C28e2c82d-aa3c-4f77-8084-ebf8888b22cf"
SARVAM_URL = "https://www.sarvam.ai/careers"
OUTPUT_FILE = "data/scouted_roles.json"
REJECTED_FILE = "data/rejected_roles.json"

def load_identity():
    """Load Jay's professional context from the data directory."""
    path = os.path.join(os.path.dirname(__file__), "data", "identity.txt")
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read()
    return "No identity context found."

PROFESSIONAL_CONTEXT = load_identity()

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

async def get_browser_context(p):
    """Helper to initialize a stealthy browser context."""
    browser = await p.chromium.launch(headless=True)
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 900},
        locale="en-US",
    )
    return browser, ctx

EXTRACT_JS = '''() => {
    const cards = document.querySelectorAll("li.lLd3Je");
    return Array.from(cards).map(card => {
        const titleEl = card.querySelector("h3.QJPWVe");
        const locEl = card.querySelector(".r0wTof");
        const jsdata = (card.querySelector("[jsdata]")?.getAttribute("jsdata") || "");
        const jobId = jsdata.match(/;(\\d{10,})/)?.[1];
        
        if (!jobId || !titleEl) return null;
        return {
            title: titleEl.innerText.trim(),
            location: locEl ? locEl.innerText.trim() : "",
            url: "https://www.google.com/about/careers/applications/jobs/results/" + jobId,
            text: card.innerText.replace(/\\s+/g, " ").trim().substring(0, 1500)
        };
    }).filter(Boolean);
}'''

async def scrape_google_jobs():
    """Scrape Google Careers for targeted India PM/strategy/growth roles."""
    total_queries = len(SEARCH_QUERIES)
    print(f"\n[Google] Running {total_queries} targeted searches × {PAGES_PER_QUERY} pages each...")
    all_jobs = []
    seen_urls = set()

    async with async_playwright() as p:
        browser, ctx = await get_browser_context(p)
        await ctx.add_cookies([{
            "name": "CONSENT",
            "value": "YES+cb.20230501-14-p0.en+FX+414",
            "domain": ".google.com",
            "path": "/"
        }])
        page = await ctx.new_page()

        for q_idx, (query, location) in enumerate(SEARCH_QUERIES, 1):
            print(f"  [{q_idx}/{total_queries}] Query: '{query}' | Location: {location}")
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
                    print(f"    p{page_num}: {len(jobs)} cards, {len(new)} new")

                    if len(new) == 0:
                        break
                except Exception as e:
                    print(f"    p{page_num} failed: {e}")
                    break

            print(f"    → {query_new} new unique jobs from this query")

        await browser.close()

    print(f"  Google scraping complete: {len(all_jobs)} unique jobs")
    return all_jobs

async def scrape_openai_jobs():
    """Scrape OpenAI Careers for India roles."""
    print(f"\n[OpenAI] Scraping India careers page...")
    all_jobs = []

    async with async_playwright() as p:
        browser, ctx = await get_browser_context(p)
        page = await ctx.new_page()

        try:
            url = f"{OPENAI_BASE_URL}?{OPENAI_LOCATION_FILTER}"
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for job cards to load — OpenAI uses links with /careers/ paths
            try:
                await page.wait_for_selector("a[href*='/careers/']", timeout=12000)
            except:
                pass  # If no cards found, may still have content

            await page.wait_for_timeout(3000)

            # Extract OpenAI job cards
            openai_extract_js = '''() => {
                const jobs = [];
                const seen = new Set();
                const links = document.querySelectorAll("a[href*='/careers/']");

                links.forEach(link => {
                    const href = link.href;
                    if (!href || href.includes('/careers/search') || href.endsWith('/careers/') || seen.has(href)) return;
                    seen.add(href);

                    const card = link.closest("li, article, [role='listitem'], div") || link;
                    const titleEl = card.querySelector("h2, h3, h4");
                    const title = (titleEl || link).innerText.trim();

                    const locEl = card.querySelector("[class*='location'], [class*='department'], [class*='region']");
                    const location = locEl ? locEl.innerText.trim() : "Not listed";
                    const text = card.innerText.replace(/\\s+/g, " ").trim().substring(0, 1500);

                    if (title && href) {
                        jobs.push({ title, location, url: href, text });
                    }
                });
                return jobs;
            }'''

            openai_jobs = await page.evaluate(openai_extract_js)

            # Deduplicate by URL
            seen = set()
            unique = []
            for j in openai_jobs:
                if j["url"] not in seen:
                    seen.add(j["url"])
                    unique.append(j)

            all_jobs.extend(unique)
            print(f"  Found {len(openai_jobs)} cards, {len(unique)} unique jobs")

        except Exception as e:
            print(f"  OpenAI scraping failed: {e}")

        await browser.close()

    print(f"  OpenAI scraping complete: {len(all_jobs)} unique jobs")
    return all_jobs

async def scrape_sarvam_jobs():
    """Scrape Sarvam AI Careers for open positions."""
    print(f"\n[Sarvam AI] Scraping careers page...")
    all_jobs = []

    async with async_playwright() as p:
        browser, ctx = await get_browser_context(p)
        page = await ctx.new_page()

        try:
            await page.goto(SARVAM_URL + "#positions", wait_until="domcontentloaded", timeout=60000)

            # Wait for the job links to render
            try:
                await page.wait_for_selector("a[href*='/careers/jobs/']", timeout=15000)
            except:
                print("  Warning: Could not find job links via selector, continuing...")

            await page.wait_for_timeout(3000)

            # Focused extraction: target only /careers/jobs/{id} links
            sarvam_extract_js = '''() => {
                const jobs = [];
                const seen = new Set();
                const links = document.querySelectorAll("a[href*='/careers/jobs/']");

                links.forEach(link => {
                    const href = link.href;
                    if (!href || seen.has(href)) return;
                    seen.add(href);

                    // The link text is typically: "TitleLocationTypeModeTag"
                    // e.g. "Product ManagerBengaluru, Karnataka, IndiaFull TimeOn-Site"
                    const rawText = link.innerText.trim();
                    if (!rawText) return;

                    // Extract title: everything before the first location marker
                    // Common Indian locations start with city names
                    const locMarkers = [
                        "Bengaluru", "Bangalore", "Mumbai", "Delhi", "Hyderabad",
                        "Chennai", "Pune", "Gurgaon", "Gurugram", "Noida",
                        "Kolkata", "India", "Remote"
                    ];
                    
                    let title = rawText;
                    let location = "India";
                    
                    for (const marker of locMarkers) {
                        const idx = rawText.indexOf(marker);
                        if (idx > 0) {
                            title = rawText.substring(0, idx).trim();
                            // Extract location up to "Full Time" or "Part Time" or end
                            const afterTitle = rawText.substring(idx);
                            const typeIdx = afterTitle.search(/Full Time|Part Time|Contract/i);
                            location = typeIdx > 0 ? afterTitle.substring(0, typeIdx).trim() : afterTitle.trim();
                            break;
                        }
                    }

                    jobs.push({
                        title: title,
                        location: location,
                        url: href,
                        text: rawText.substring(0, 1500)
                    });
                });

                return jobs;
            }'''

            sarvam_jobs = await page.evaluate(sarvam_extract_js)

            seen = set()
            unique = []
            for j in sarvam_jobs:
                if j["url"] not in seen:
                    seen.add(j["url"])
                    unique.append(j)

            all_jobs.extend(unique)
            print(f"  Found {len(sarvam_jobs)} cards, {len(unique)} unique jobs")

            # Log titles for verification
            for j in unique:
                print(f"    → {j['title']} | {j['location']}")

        except Exception as e:
            print(f"  Sarvam AI scraping failed: {e}")

        await browser.close()

    print(f"  Sarvam AI scraping complete: {len(all_jobs)} unique jobs")
    return all_jobs

async def scrape_jobs():
    """Main scrape function — combines Google, OpenAI, and Sarvam AI careers."""
    google_jobs = await scrape_google_jobs()
    openai_jobs = await scrape_openai_jobs()
    sarvam_jobs = await scrape_sarvam_jobs()

    # Merge results with company tagging
    all_jobs = []

    for job in google_jobs:
        job["company"] = "Google"
        all_jobs.append(job)

    for job in openai_jobs:
        job["company"] = "OpenAI"
        all_jobs.append(job)

    for job in sarvam_jobs:
        job["company"] = "Sarvam AI"
        all_jobs.append(job)

    # Final dedup by URL
    seen_urls = set()
    final_jobs = []
    for job in all_jobs:
        if job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            final_jobs.append(job)

    print(f"\nTotal scraping complete: {len(final_jobs)} unique jobs (Google: {len(google_jobs)}, OpenAI: {len(openai_jobs)}, Sarvam AI: {len(sarvam_jobs)})")
    return final_jobs

# Title keywords that signal a likely-relevant (non-pure-engineering) role
RELEVANT_TITLE_KEYWORDS = [
    "manager", "strategy", "operations", "product", "growth", "business",
    "partnerships", "policy", "go-to-market", "gtm", "marketing", "sales",
    "monetization", "monetisation", "commerce", "lead", "director", "head of",
    "program", "principal", "analyst", "insights", "trust", "integrity",
    "payments", "platform", "consumer", "experience", "data", "ai", "intelligence",
]

def calculate_title_score(title):
    """Predicts a relevance score (0-100) based ONLY on the title.
    Used for 'Fast Triage' to avoid wasting tokens on non-relevant roles.
    """
    title = title.lower()
    score = 45  # Baseline score

    # Jay's Super-High-Signal Keywords (+25 each)
    super_signals = ["strategy", "product", "growth", "gtm", "go-to-market", "ai product", "india"]
    for word in super_signals:
        if word in title: score += 25

    # General High-Signal Keywords (+15 each)
    high_signals = ["manager", "lead", "director", "partnerships", "operations", "monetization", "commerce"]
    for word in high_signals:
        if word in title: score += 15

    # Negative/Discard Signals (-60)
    # These roles are highly unlikely to be the digital product/strategy roles Jay wants
    negative_signals = [
        "account manager", "account executive", "field sales", "sales manager",
        "music licensing", "content partnerships", "offline", "facilities",
        "customer success", "recruiter", "hr", "payroll", "legal", "counsel",
        "intern", "phd", "associate" # Associate often means junior at Google
    ]
    for word in negative_signals:
        if word in title: score -= 60
        
    return max(0, min(100, score))

def prefilter_jobs(jobs_data):
    """Stage 1: Bulk Keyword Filtering. 
    Stage 2: Title-Based Triage (Jay's 'Fast Triage' request).
    """
    skip_keywords = [
        "software engineer", "sre", "site reliability", "network engineer",
        "hardware engineer", "test engineer", "security engineer",
        "infrastructure engineer", "embedded", "firmware", "kernel", "devops"
    ]
    
    filtered = []
    skipped_count = 0
    triage_count = 0
    
    for job in jobs_data:
        title = job.get("title", "")
        title_lower = title.lower()
        
        # 1. Hard Engineer Skip
        if any(kw in title_lower for kw in skip_keywords):
            skipped_count += 1
            continue
            
        # 2. Fast Triage (Jay's Prediction Request)
        # Discard anything with a Title Score < 40 before Claude evaluation
        title_score = calculate_title_score(title)
        if title_score < 40:
            triage_count += 1
            continue
            
        filtered.append(job)
        
    print(f"  [Triage] {len(jobs_data)} starting roles:")
    print(f"    - Dropped {skipped_count} engineering roles")
    print(f"    - Discarded {triage_count} low-probability titles (Fast Triage)")
    print(f"    → {len(filtered)} roles sent to Claude Opus for full analysis.")
    return filtered

def evaluate_jobs(jobs_data, context_text):
    """Deep analysis via Claude Opus. 
    NOTE: In the persistence-aware architecture, jobs_data here is already pre-filtered to contain ONLY UNKNOWN ROLES.
    """
    print(f"Evaluating {len(jobs_data)} roles via Claude Opus 4.6 (Intelligence Phase)...")
    if not jobs_data:
        return []

    prompt = f"""
<role_scout_instructions>
Act as an Executive Recruiter evaluating roles for Jay Shukla. 
Jay's context is provided below. Score roles 0-100 and assign priority (P0-P2).

<hard_discard_rules>
- Pure engineering/SRE/infra/hardware/firmware
- Intern/PhD/Entry-level (associate at Google)
- Relationship sales/Offline BD (Strategic Partner Development, Field Sales)
- 10+ years experience requirements (Jay has 7)
</hard_discard_rules>

<scoring_guide>
- HIGH (70-95): Consumer PM, India growth/localmarket, Creator economy, SMB growth, AI Product (GTM/UX), Vernacular users.
- MEDIUM (50-69): B2B/Enterprise PM with India component, Strategy with market mandates, high-affinity roles with 8-9yr requirement.
- DISCARD (<45): Pure process ops, relationship management, account management.
</scoring_guide>

<output_requirements>
- Return ONLY a valid JSON array.
- Field Schema: {{"id", "title", "company", "location", "url", "relevance_score", "priority", "role_summary", "why_good_fit", "how_to_win", "job_description", "date_published", "scraped_at"}}
- Cite Jay's specifically: Meta 2.3% revenue uplift, ByteDance Resso scaling, TikTok SMB lead.
</output_requirements>

<candidate_context>
{context_text}
</candidate_context>

<jobs_to_evaluate>
{json.dumps(jobs_data)}
</jobs_to_evaluate>
</role_scout_instructions>
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
        print(f"Response length: {len(raw_response)} characters")
        print(f"Response preview (first 200 chars): {raw_response[:200]}")

        # Strip markdown code fences if present
        raw_response = re.sub(r'^```(?:json)?\s*', '', raw_response)
        raw_response = re.sub(r'\s*```$', '', raw_response.strip())

        match = re.search(r'\[.*\]', raw_response, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                result = json.loads(json_str)
                print(f"Successfully parsed {len(result)} roles from Claude response.")
                return result
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Captured JSON length: {len(json_str)}")
                print(f"First 500 chars: {json_str[:500]}")
                print(f"Last 500 chars: {json_str[-500:]}")
                return []
        else:
            print("Claude did not return a valid JSON array.")
            print("Response preview:", raw_response[:300])
            return []
    except Exception as e:
        print(f"Claude API call failed: {e}")
        import traceback
        traceback.print_exc()
        return []

async def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # 1. Load Persistence Layer (Previous Brain Memory)
    existing_brain = {}
    rejected_urls = set()

    # Load passing roles
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r") as f:
                data = json.load(f)
                # Map URL -> Full Evaluated Job Object
                roles_list = data.get("roles", []) if isinstance(data, dict) else data
                existing_brain = {j["url"]: j for j in roles_list if "url" in j}
            print(f"Loaded {len(existing_brain)} previously analyzed (passing) roles from memory.")
        except Exception as e:
            print(f"Warning: Could not load persistence layer: {e}")

    # Load rejected roles (to avoid re-analyzing)
    if os.path.exists(REJECTED_FILE):
        try:
            with open(REJECTED_FILE, "r") as f:
                rejected_data = json.load(f)
                rejected_urls = set(rejected_data.get("rejected_urls", []))
            print(f"Loaded {len(rejected_urls)} previously rejected roles (will skip re-analysis).")
        except Exception as e:
            print(f"Warning: Could not load rejected roles: {e}")

    # 2. Discovery Phase
    jobs_data = []
    try:
        jobs_data = await scrape_jobs()
    except Exception as e:
        print(f"Scraping failed: {e}")

    final_results = []
    if jobs_data:
        # Step A: Pre-filter out junk (Eng roles/Fast Triage)
        candidates = prefilter_jobs(jobs_data)
        
        # Step B: Persistence Check - Separate New vs Known vs Rejected
        to_analyze = []
        already_known = []
        already_rejected = []

        for job in candidates:
            if job["url"] in existing_brain:
                already_known.append(existing_brain[job["url"]])
            elif job["url"] in rejected_urls:
                already_rejected.append(job)
            else:
                to_analyze.append(job)

        print(f"  [Memory Check] {len(candidates)} candidates:")
        print(f"    - {len(already_known)} roles already analyzed (passing, cached)")
        print(f"    - {len(already_rejected)} roles previously rejected (skipping re-analysis)")
        print(f"    - {len(to_analyze)} truly new roles found")

        # Step C: Selective Evaluation via Claude Opus
        new_evaluations = []
        newly_rejected_urls = []
        if to_analyze:
            new_evaluations = evaluate_jobs(to_analyze, PROFESSIONAL_CONTEXT)
            # Track URLs that were evaluated but rejected (not returned by Claude)
            analyzed_urls = {job["url"] for job in new_evaluations}
            newly_rejected_urls = [job["url"] for job in to_analyze if job["url"] not in analyzed_urls]
            print(f"    → Claude analyzed {len(to_analyze)} new roles. Kept {len(new_evaluations)}, rejected {len(newly_rejected_urls)}.")
        else:
            print("    → No new roles to analyze. Skipping Claude Opus call entirely (Tokens saved: 100%)")

        # Step D: Smart Merge
        # We only keep results for jobs that were ACTUALLY FOUND in the current scrape
        # This prevents ghost roles from staying on the dashboard after they are removed from Google.
        final_results = new_evaluations + already_known

        # Step E: Update Rejected URLs Cache
        # Add newly rejected URLs to the cache
        updated_rejected_urls = rejected_urls | set(newly_rejected_urls)
        rejected_data = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "rejected_urls": list(updated_rejected_urls)
        }
        with open(REJECTED_FILE, "w") as f:
            json.dump(rejected_data, f, indent=2)
    else:
        print("Scraping returned nothing — keeping last saved results to avoid empty dashboard.")
        final_results = list(existing_brain.values())

    # 3. Save & Synchronize
    output_data = {
        "last_synced": datetime.utcnow().isoformat() + "Z",
        "roles": final_results
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)
        
    print(f"Successfully saved {len(final_results)} jobs (Brain updated).")
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
