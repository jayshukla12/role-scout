scout.py



import asyncio
import os
import re
import json
import urllib.request
from datetime import datetime
from playwright.async_api import async_playwright
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)
TARGET_URL = "https://www.google.com/about/careers/applications/jobs/results?location=India"
CONTEXT_FILE = "jay_professional_context_v1.md"
OUTPUT_FILE = "data/scouted_roles.json"
async def scrape_jobs():
    print(f"Scraping jobs from {TARGET_URL}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.add_cookies([{
            "name": "CONSENT",
            "value": "YES+cb.20230501-14-p0.en+FX+414",
            "domain": ".google.com",
            "path": "/"
        }])
        page = await context.new_page()
        
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
        
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
        jobs_data = await page.evaluate('''() => {
            const jobs = [];
            const links = document.querySelectorAll('a[href*="/jobs/results"]');
            const seenUrls = new Set();
            
            links.forEach(a => {
                const href = a.href;
                if (!seenUrls.has(href)) {
                    seenUrls.add(href);
                    let container = a.parentElement;
                    for (let i = 0; i < 6; i++) {
                        if (container && container.parentElement) {
                            container = container.parentElement;
                        }
                    }
                    jobs.push({
                        url: href,
                        text: container ? container.innerText.replace(/\\s+/g, ' ').trim() : a.innerText
                    });
                }
            });
            
            if (jobs.length === 0) {
                jobs.push({
                    url: document.location.href,
                    text: document.body.innerText.substring(0, 15000)
                });
            }
            return jobs;
        }''')
        
        await browser.close()
        return jobs_data
def evaluate_jobs(jobs_data, context_text):
    print(f"Evaluating {len(jobs_data)} extracted job snippets via REST API...")
    if not jobs_data:
        return []
    prompt = f"""
You are an expert Executive Job Scout & Hiring Manager evaluating roles for Jay Shukla.
I am providing you with his complete Comprehensive Professional Context document. 
YOUR TASK:
1. Review the ENTIRE context deeply. Do not rely just on a core USP; evaluate against his full history (Meta, ByteDance, Travel Startup), skills, and explicit Job Search Criteria.
2. Evaluate each job listing in the provided array against ALL data in his context.
3. FILTERS:
   - Check the date in the job text. If it is older than 3 months, DISCARD IT.
   - Calculate a 'relevance_score' (0-100) based on how well the job requirements match Jay's ENTIRE comprehensive profile. 
   - Temporarily, KEEP ALL JOBS regardless of score so we can verify the pipeline.
4. For all jobs, generate a "tip_to_score". This must explicitly reference specific stories or data from his timeline.
5. Ensure a robust JSON schema for future scaling.
CANDIDATE CONTEXT:
{context_text}
EXTRACTED JOBS JSON:
{json.dumps(jobs_data, indent=2)}
OUTPUT REQUIREMENT:
Return ONLY a valid JSON array of objects. Do not include markdown code blocks.
Format of each object:
{{
  "id": "A unique identifier derived from the url or title",
  "title": "Exact Title of the Role",
  "company": "Google",
  "location": "India",
  "url": "original linked url",
  "relevance_score": 85,
  "tip_to_score": "To land this role, lean heavily into your experience with... highlight your 2.3% revenue uplift...",
  "date_published": "Posted 5 days ago",
  "scraped_at": "{datetime.utcnow().isoformat()}Z"
}}
"""
    # Hit the direct API endpoint exactly identical to how we did it in the browser!
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            ai_data = json.loads(response.read().decode('utf-8'))
            
        raw_response = ai_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        print("Raw Gemini Response received.")
        
        # Safely extract the JSON array using Regex
        match = re.search(r'\[.*\]', raw_response, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            print("Gemini did not return a valid JSON array.")
            return []
        
    except Exception as e:
        print("REST API Call failed or JSON parsing failed.")
        print(str(e))
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
        
        existing_data = []
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r") as f:
                    existing_data = json.load(f)
            except:
                pass
                
        jobs_dict = {job.get('url', str(i)): job for i, job in enumerate(existing_data)}
        for job in results:
            if 'url' in job:
                jobs_dict[job['url']] = job
            
        final_list = list(jobs_dict.values())
    else:
        print("No jobs found to evaluate. Saving empty/existing state.")
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r") as f:
                    final_list = json.load(f)
            except:
                pass
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_list, f, indent=2)
        
    print(f"Successfully saved {len(final_list)} jobs to {OUTPUT_FILE}")
if __name__ == "__main__":
    asyncio.run(main())
    
