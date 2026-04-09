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
OPENAI_LOCATION_FILTER = "l=2ef3d3b7-e015-45f9-90ff-b530f7dad8af%2Cd2b1576e-0e1e-4611-b587-6f65f326be14%2C28e2c82d-aa3c-4f77-8084-ebf8888b22cf"
OUTPUT_FILE = "data/scouted_roles.json"

# Professional context embedded directly (replaces jay_professional_context_v1.md)
PROFESSIONAL_CONTEXT = """# Jay Shukla — Comprehensive Professional Context
*Version 2 — Built from deep interview session, April 2026*
*For use by: Role Scouting Agent + Job Hunt 2026 Project*

---

## 1. Core Identity & Positioning

**One-line USP:**
"I find the users that global products overlook — and I turn those human observations into product decisions that move business metrics at scale."

**Positioning Paragraph:**
Product professional with 7+ years across ByteDance and Meta, specialising in Indian market growth for global tech platforms. Known for finding insight by getting close to real users — from Tier 2 Indian consumers to informal SMBs to Indian GenZs — and translating those observations into product decisions that move business metrics at scale. Consistently described by colleagues and managers as someone with "rooted insights" — grounded in how Indian users actually behave, not how global product teams assume they do. Operates effectively across zero-to-one building, monetisation strategy, competitive intelligence, market growth, and AI product development. Can zoom in (field observation, user research) and zoom out (CPO-level strategy, competitive positioning) with equal effectiveness.

**How colleagues describe Jay:**
- "Rooted insights" — grounded in real human behaviour, not assumptions
- Vigilant, Empathetic, Range (manager's three words)
- Top AI fluency and productivity among peers
- Strong multi-angle POV building across disciplines

---

## 2. Career Timeline

### Meta — International Product Growth Specialist (IPGS), India
**September 2024 – September 2026 (Contract)**
**Team:** International Product Growth & Insights, within the Internationalisation Org
**Reporting to:** International Product Growth Manager (IPGM)

#### Role Overview & Methodology
Core mission: Be the voice of the Indian market to enable product experiences that drive growth — people growth, revenue, engagement — across Meta's product surfaces.

**Repeatable Work Methodology:**
1. **Half Planning (H1/H2)** — Build a Half Plan identifying strong market needs based on local expertise, define product and non-product levers, set milestones and execution strategy
2. **Deep Discovery** — Go deep on priority areas through dogfooding, competitive benchmarking, user studies, field work, and data analysis
3. **Insight Writing** — Publish structured insights on Workplace (internal), tag relevant product POCs, generate awareness and traction
4. **Pitching & Buy-in** — Build pitch decks with product recommendations, opportunity sizing, and business cases; secure commitment and resources from product teams
5. **Execution Partnership** — Work with PMs, EMs, UXRs, and engineers to execute; track and follow up on commitments

**Key Deliverable Types:**
- Insights (market observations → product opportunities)
- Competitive intelligence write-ups (market updates, competitor moves, implications for Meta)
- Country context / POV narratives (long-form strategic pieces to influence product strategy)
- Product feedback via dogfooding (new features, internal AI tools)
- Product opportunity assessments

**North Star Performance Indicator:**
Product execution — how many insights or hypotheses were tested or executed by product teams, regardless of outcome.

---

#### Key Projects & Contributions at Meta

**1. SMB Over-Enforcement & Agentic Resolution System** *(Highest Impact)*
- **Origin:** Casual conversation at hometown bakery in Dahod — owner's WhatsApp accounts were blocked, devastating his business
- **Discovery:** Uncovered that Meta's enforcement model assumed a global context that didn't match how Indian SMBs actually operate (voice-led, informal digital literacy, different CRM usage patterns)
- **Work done:** Deep-dive data analysis surfacing over-enforcement patterns (false positives), multiple enforcement issues, and resolution gaps; mapped user journey of Indian SMBs trying to appeal blocked accounts; identified that email appeals were effectively unanswered
- **Influence:** Presented findings to product and policy teams; influenced policy change; advocated for dedicated product team focused on SMB resolution
- **Outcome:**
  - New product team created at Meta focused on SMB enforcement resolution
  - Agentic resolution system built (replacing ineffective email appeals)
  - 10M+ highly active businesses in India and Brazil impacted
  - **2.3% India revenue uplift — one of the single largest revenue-driving features in Meta India history**

**2. Shoppertainment — India Monetisation Big Bet**
- Core XFN member during Meta's identification of largest India monetisation opportunities
- Helped surface and define "Shoppertainment" (convergence of entertainment and commerce) as priority product opportunity for Indian creators
- Contributed to solving product bottlenecks converting active businesses to paying advertisers
- Outcome: Strategic direction adopted; contributed to Meta India revenue growth

**3. TikTok Re-entry Competitive Strategy**
- Key XFN partner in team building Meta's product strategy and preparedness for TikTok's potential India return (2024)
- Leveraged prior ByteDance/TikTok insider experience to provide competitive intelligence and product framing unavailable to other team members
- Strategy informed decisions at CPO level (Chris Cox)
- Outcome: Structural changes across product and non-product teams in India

**4. MetaAI India Growth & Field Work**
- Participated in multiple AI field work initiatives in India alongside product teams
- Conducted ~20 user interviews with AI enthusiasts (power users of ChatGPT, Gemini, MetaAI etc.)
- **Key Insight Discovered:** For Indian GenZ AI users, language aspects (structure, tone, persona) matter more than factual correctness as a driver of product preference — "language as a product growth lever"
- Covered segments: AI enthusiasts, enterprises, SMBs, GenZ consumers
- Voice-led AI opportunities identified as underserved product surface for India market
- Insights being considered for incorporation into new AI model development

**5. SMB Growth & Monetisation (Ongoing)**
- Consistently focused on driving growth for Indian SMBs across Meta's business products — advertising tools, WhatsApp API, Paid Messaging
- Identified India-specific product opportunities rooted in on-ground SMB behaviour observation
- Core hypothesis: Indian SMBs conduct business through voice-led WhatsApp operations — fundamentally different from global product assumptions
- Contributed to activating advertising business for Meta in India through deep on-ground discovery

**6. Indian GenZ Initiatives**
- Member of Meta's GenZ Product Council — selective group of 25 product professionals globally
- Responsibilities: Highlight product feedback, provide strategies, uncover nuanced GenZ user behaviours, serve as gatekeeper for products targeting this cohort
- Contributed to FB Dating US launch — dogfooded experience, identified product gaps, mobilised council for feedback, built product opportunity assessment, pitched to product teams (beyond formal job scope)
- Deep expertise in Indian GenZ segments — behaviours, AI usage patterns, content consumption, social dynamics

**7. Content Relevance & Creator Growth**
- Worked on content relevance opportunities for Indian market
- Focused on regional and long-tail creator segments
- Contributed to creator-focused product opportunities across Meta surfaces

**8. Beyond-Scope Contributions**
- Proactive dogfooding of new features even when outside priority areas
- Internal tools feedback (e.g., new Metamate versions)
- Consistently contributes beyond formal role boundaries

---

#### Stakeholders & Cross-Functional Partners
- **Product teams** (PMs, EMs, UXRs, Software Engineers) — primary execution partners
- **IPGS/IPGM counterparts** from Brazil, Indonesia, and other markets — cross-market collaboration on overlapping user needs
- **Product Analytics teams** — opportunity sizing, analytical support
- **International Marketing teams** — non-product lever execution (campaigns)
- **Policy teams** — influenced policy changes (SMB enforcement case)
- **Senior Leadership** — work has reached CPO level (Chris Cox)

---

#### Tools & Systems at Meta
- **Google Workspace** — collaboration
- **Workplace** — internal publishing, insight sharing, stakeholder engagement
- **Metamate** (Meta's internal AI) — primary productivity tool; top 5 percentile user (~25 hours/week); built personal AI operating system on top of it
- **Manus** — AI tool for advanced work
- **Unidash** — internal analytics dashboards
- **Internal AI tools** — on-demand dashboard building, data analysis

---

#### Personal AI Operating System (Metamate-based)
*Note: Cannot be shared externally due to company policy. Can be referenced conceptually in interviews.*

Built a personal second brain and operating system inside Metamate consisting of multiple agents and automations:
- Insight writer with built-in market research capability
- Competitive intelligence agent (surfaces top 5 competitor news daily for vetting)
- Stakeholder tagging and engagement automation
- Pitch deck builder
- Calendar automation
- Execution tracker
- Follow-up skill
- Personal writing DNA skill (replicates Jay's writing style)
- User research internal agent
- Web research agent

**Impact:** ~80% of housekeeping and low-ROI tasks automated; top 5 percentile Metamate user across Meta globally; ~25 hours/week on Metamate

---

#### Manager Feedback Summary
**Praised for:**
- Humane, empathy-led insights rooted in deep user understanding
- Nuanced, specific Indian user behaviour observations
- Multi-source synthesis (analytics, psychology, market insights, competitive intel, product sense)
- AI fluency and productivity
- Specificity of product opportunities (Needs → Product)

**Feedback for improvement:**
- Ruthlessly prioritise — focus on highest ROI opportunities rather than covering everything
- Influence product teams on small, actionable asks rather than big features
- Clear and concise communication (consistent feedback)
- Converting insights into execution more effectively

---

### Travel Tech Startup — Founder
**2022 – 2024**
- Built and iterated multiple travel tech products across B2C and B2B
- Extensive user research and market exploration in travel domain
- Identified "tar pit" ideas through experience — pivoted multiple times
- Did not achieve product-market fit
- Key learning: Importance of deliberate problem selection and disciplined execution over curiosity-driven pivoting

---

### ByteDance — Product Associate
**November 2018 – August 2022**
**Products:** Resso (Music Streaming App), TikTok SoundOn (Music Distribution & Marketing), TikTok Music Org

#### Resso — Founding Team Member
- Joined as intern; converted to full-time employee
- Part of founding team scaling Resso from alpha testing to India's largest music streaming app
- **Core product thesis:** Target Tier 2, 3 and beyond Indian users ignored by Spotify and global streaming apps; pure ML recommendation engine with no editorial bias
- **Key insight discovered:** 10% of content library drove 90% of listening time — identified cold start problem, used insight to shape recommendation engine strategy
- **Owned:** Editorial content curation strategy for Explore page; manual curation to enable music discovery
- **North star metrics:** ST/DAU growth and total user growth
- **Outcome:** Resso became India's largest music streaming platform, surpassing Spotify in India before government ban

#### Ghost Music Tab — TikTok Artist Activation
- Identified critical data gap: TikTok had no internal signal to distinguish real artists from potential musicians
- Contributed to building ML-powered "Ghost Music Tab" — activated for potential musicians, cross-referenced against real artist identity to enable Artist Profile on TikTok
- Outcome: Solved artist identity and activation problem at scale globally on TikTok

#### Creator Monetisation Research
- Participated in key research initiative identifying best creator monetisation avenues for TikTok
- Helped scope and define opportunity landscape for artist monetisation on the platform
- Outcome: TikTok identified events and ticketing as core creator monetisation strategy — this research contributed to that strategic direction

---

## 3. Core Strengths & Evidence

| Strength | Concrete Evidence |
|---|---|
| Indian market intelligence | Bakery → 10M businesses, 2.3% revenue uplift; Resso Tier 2 thesis → beat Spotify |
| User obsession & customer discovery | 20+ AI user interviews; bakery field observation; SMB on-ground research; GenZ field work |
| Zero to one building | Resso founding team member; travel startup founder |
| Data-driven insight generation | 10%/90% content insight; SMB over-enforcement analysis; opportunity sizing |
| Monetisation & revenue thinking | Shoppertainment; SMB advertiser conversion; 2.3% revenue uplift |
| Competitive & strategic intelligence | TikTok re-entry strategy; CPO-level influence; daily competitive monitoring |
| Cross-functional leadership | XFN partner across product, policy, data, marketing, engineering |
| AI fluency & productivity | Top 5% Metamate user; personal AI OS built; 80% task automation |
| Range across user segments | Tier 2 consumers, informal SMBs, regional creators, GenZ, enterprises, large advertisers |
| Beyond-scope initiative | FB Dating contribution; internal tools feedback; proactive dogfooding |

---

## 4. Skills Profile

### Product Skills
- Market sizing and opportunity assessment
- Insight writing and synthesis (multi-source: data + field + competitive + psychology)
- Competitive intelligence and benchmarking
- User research and customer discovery (field interviews, dogfooding, behavioural observation)
- Product feedback and opportunity assessment
- Stakeholder pitching and buy-in securing
- Cross-functional collaboration and execution partnership
- Half planning and strategic roadmap input
- Go-to-market and product growth strategy

### Data & Analytics
- Excel (proficient)
- Basic SQL (ByteDance experience)
- Internal dashboard tools (Unidash)
- AI-assisted data analysis (strong — uses AI tools to compensate for technical gaps)
- Self-rated: 6-7/10 on data tools; stronger with AI assistance

### AI Tools & Fluency
- **Metamate** — Expert (top 5 percentile, 25hrs/week, personal OS built)
- **Manus** — Proficient (regular work use)
- **Claude** — Regular use (personal and professional)
- **ChatGPT** — Regular use
- **NotebookLM** — Regular use
- **Claude Code** — Currently learning
- Overall AI fluency: Very high for workflow automation and productivity; building toward technical AI product depth

### Communication & Writing
- Long-form insight writing (core job skill)
- Competitive intelligence write-ups
- Pitch decks and product opportunity assessments
- Country context / strategic narratives
- Feedback area: Conciseness and structured communication (actively working on)

---

## 5. Job Search Criteria for Role Scouting Agent

### Non-Negotiable Criteria
| Criteria | Detail |
|---|---|
| Remote | P0 preference — fully remote strongly preferred (based in Vadodara). Will consider Hybrid/in-office as P1 to avoid over-limiting options |
| Compensation | Significant hike from ₹1.8L/month current; needs to cover ₹80K/month loan obligations + lifestyle |
| AI-native | Role must be at the frontier of AI — not AI-adjacent, genuinely AI-native |

### Strong Preferences
| Criteria | Detail |
|---|---|
| Travel | Role should include travel — conferences, field work, market visits |
| India focus | Role with India market growth component strongly preferred |
| Seniority | Senior IC or above — role should stretch toward entrepreneurship or senior product leadership |
| Brand | Open to non-brand-name companies if other criteria are met |

### Target User Audiences — Score HIGH Relevance for Roles Serving These Segments
Jay has deep, hands-on experience building for the following user cohorts. Roles targeting these audiences should be scored higher:

| User Segment | Depth of Experience |
|---|---|
| **Creators** (regional, long-tail, vernacular) | Strong — creator monetisation, Shoppertainment, TikTok artist activation |
| **Regional & Vernacular users** | Strong — Resso Tier 2/3 thesis, Indian language/tone AI insight, on-ground field work |
| **Indian GenZ** | Strong — GenZ Product Council (25 members globally), AI behaviour research, multiple initiatives |
| **Consumers** (Indian mass market) | Strong — Resso, MetaAI field work, content relevance, AI enthusiast research |
| **SMBs & Informal Businesses** | Very Strong — bakery insight, 10M businesses impacted, policy change, agentic resolution system |
| **Advertisers & Ad Tech** | Strong — SMB advertiser conversion, Meta advertising products, Shoppertainment monetisation, Paid Messaging, WhatsApp API |
| **Shoppers** | Moderate — Shoppertainment, commerce and creator convergence work |

### Role Types — Score HIGH Relevance
- India Growth / Market Expansion roles at global AI companies
- International Product Manager / Growth PM with India focus
- AI Product Manager (market intuition, user research, GTM — not engineering)
- Product Strategy roles with competitive intelligence component
- Developer Relations / Ecosystem Growth at AI companies expanding in India
- Roles combining field research + product influence + revenue impact

### Role Types — Score LOW Relevance
- Pure engineering or technical ML roles
- Roles requiring deep AI/ML engineering background
- Roles based outside India with no remote option
- Roles with no growth, market, or user research component
- Junior IC roles with limited strategic scope

---

## 6. Target Companies

| Company | Why | Fit Signal |
|---|---|---|
| OpenAI | Pioneer; unparalleled ChatGPT loyalty in India; wants India growth | India growth, AI product, user research |
| Google | Deep social/AI landscape experience; strong India context | AI roles, India market, product growth |
| Anthropic | High conviction on Claude's India growth potential; underleveraged in India | India expansion, AI product, market growth |
| Meta | Internal transfer to full-time; strong existing relationships | Already proven; internal network advantage |
| Polarsteps | Travel DNA; cultural fit; European work culture resonates | Travel, product, growth |

*Criteria-driven, not company-driven. Open to companies meeting the criteria above.*

---

## 7. Learning & Development

### Currently Learning
- Claude Code — building toward faster idea-to-execution capability
- AI tools depth — moving from AI enthusiast to AI power builder
- Structured and concise communication — active improvement area

### Regular Inputs
- Lenny's Podcast
- YC podcasts
- AI-focused video content
- Exploring new AI tools regularly
- Reading: Superintelligence (in progress); Zero to One (completed, highly influential)

### Skills Jay Wants to Build
1. **Ship fast like a startup** — idea to execution speed using AI
2. **Customer discovery mastery** — structured user research methodology
3. **Clear, concise communication** — CEO-level structured verbal and written communication

---

## 8. Personal Context for Agent
*Useful for understanding motivations, culture fit signals, and role alignment*

- **Location:** Vadodara, Gujarat — deep Tier 2 India roots; from Dahod originally
- **Personal situation:** Married, new home — remote is a life requirement
- **Financial motivation:** Active home loan (₹60K/month) + personal loan (₹20K/month); needs meaningful salary increase
- **Long-term vision:** Build multiple businesses and assets; eventually quit 9-to-5; holiday home in hills and Goa; farm with complete financial freedom
- **Entrepreneurial drive:** Sees product management as a path to entrepreneurship; wants roles that build toward founder capability
- **Values:** Deep empathy for overlooked users; cares about India's growth and development; mission-driven
- **Work style:** Entrepreneurial within large companies; goes beyond job scope; insight-first thinker
- **Travel:** Frequent international traveller; loves luxury travel with wife; credit card points optimizer
- **Inspiration:** Zero to One philosophy; build fast, ship fast, iterate

---

## 9. Interview Preparation Notes
*For agent to use when preparing Jay for interviews*

**Stories to always have ready:**
1. Resso — founding team, 10%/90% insight, beat Spotify
2. Ghost Music Tab — ML-powered artist activation
3. Dahod Bakery / SMB — 10M businesses, 2.3% revenue uplift, policy change
4. TikTok Re-entry Strategy — CPO-level influence, structural team changes
5. Shoppertainment — monetisation big bet identification
6. Metamate AI OS — 80% automation, top 5 percentile, personal operating system

**Consistent feedback themes to address proactively:**
- "I know I tend to go broad — I've been actively working on ruthless prioritisation"
- "I've received feedback on conciseness and I'm actively building that muscle"

**Strengths to lead with:**
- Rooted Indian market intelligence
- Field-level user observation → product impact at scale
- AI fluency and productivity
- Range across user segments and product surfaces
- Entrepreneurial initiative beyond formal scope
"""
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

async def scrape_google_jobs():
    """Scrape Google Careers for targeted India PM/strategy/growth roles."""
    total_queries = len(SEARCH_QUERIES)
    print(f"\n[Google] Running {total_queries} targeted searches × {PAGES_PER_QUERY} pages each...")
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
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await ctx.new_page()

        try:
            url = f"{OPENAI_BASE_URL}?{OPENAI_LOCATION_FILTER}"
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for job cards to load — OpenAI uses job-related class names
            # Attempt to wait for common job card selectors
            try:
                await page.wait_for_selector("a[href*='/careers'], div[role='listitem'], li[role='listitem']", timeout=12000)
            except:
                pass  # If no cards found, may still have content

            await page.wait_for_timeout(1500)

            # Extract OpenAI job cards — using a more flexible selector
            openai_extract_js = '''() => {
                const jobs = [];
                // Try multiple selectors for OpenAI's job cards
                let cards = document.querySelectorAll("[role='listitem']");
                if (cards.length === 0) cards = document.querySelectorAll("li");
                if (cards.length === 0) cards = document.querySelectorAll("div.job-card, div[data-job], a[href*='/careers/']");

                cards.forEach(card => {
                    const titleEl = card.querySelector("h2, h3, [class*='title'], [class*='job-title']");
                    const locEl = card.querySelector("[class*='location'], span[class*='location']");
                    const linkEl = card.querySelector("a[href]");

                    if (!titleEl || !linkEl) return;

                    const title = titleEl.innerText.trim();
                    const location = locEl ? locEl.innerText.trim() : "Not listed";
                    const url = linkEl.href;
                    const text = card.innerText.replace(/\\s+/g, " ").trim().substring(0, 1500);

                    if (title && url) {
                        jobs.push({
                            title: title,
                            location: location,
                            url: url,
                            text: text
                        });
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

async def scrape_jobs():
    """Main scrape function — combines Google and OpenAI careers."""
    google_jobs = await scrape_google_jobs()
    openai_jobs = await scrape_openai_jobs()

    # Merge results with company tagging
    all_jobs = []

    for job in google_jobs:
        job["company"] = "Google"
        all_jobs.append(job)

    for job in openai_jobs:
        job["company"] = "OpenAI"
        all_jobs.append(job)

    # Final dedup by URL
    seen_urls = set()
    final_jobs = []
    for job in all_jobs:
        if job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            final_jobs.append(job)

    print(f"\nTotal scraping complete: {len(final_jobs)} unique jobs (Google: {len(google_jobs)}, OpenAI: {len(openai_jobs)})")
    return final_jobs

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
You are a world-class Executive Recruiter and Job Scout evaluating roles from Google, OpenAI, and other leading AI/tech companies for Jay Shukla.
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

## PRIORITY ASSIGNMENT:
Assign a priority level to guide Jay's application sequence:
- **P0** (Apply this week): Relevance score ≥70 AND aligns with non-negotiables (remote, AI-native, India growth)
- **P1** (Shortlist): Relevance score 55–69 OR strong fit with one mismatch
- **P2** (Monitor): Relevance score <55 OR worth watching but not urgent

## OUTPUT FORMAT:
Return ONLY a valid JSON array. No markdown fences, no explanation outside the array.
Each object must follow this exact schema:
{{
  "id": "slug derived from job url or title",
  "title": "Exact job title from listing",
  "company": "Company name from listing (Google, OpenAI, etc)",
  "location": "Location from listing",
  "url": "exact url from input",
  "relevance_score": 82,
  "priority": "P0|P1|P2",
  "role_summary": "1-2 sentence plain-English summary of what this role does.",
  "why_good_fit": "Specific reasons Jay fits — cite his actual stories, metrics, and experiences.",
  "how_to_win": "Concrete, actionable pitch strategy tailored to this specific role.",
  "job_description": "2-3 sentence prose summary of what this role does day-to-day, who it serves, and what success looks like — written for the candidate, not HR.",
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

    jobs_data = []
    try:
        jobs_data = await scrape_jobs()
    except Exception as e:
        print(f"Scraping failed: {e}")

    final_list = []
    if jobs_data:
        results = evaluate_jobs(jobs_data, PROFESSIONAL_CONTEXT)
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
