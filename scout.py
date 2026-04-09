

scout.py



import asyncio
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright
import google.generativeai as genai
# Setup Gemini
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set.")
    exit(1)
genai.configure(api_key=API_KEY)
# Dynamically find the best available model to prevent 404 errors
available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
target_model = next((m for m in available_models if '1.5-flash' in m), None)
if not target_model:
    target_model = next((m for m in available_models if '1.5-pro' in m), None)
if not target_model:
    target_model = next((m for m in available_models if 'gemini-pro' in m), available_models[0])
# Strip 'models/' prefix depending on SDK expectations
clean_model_name = target_model.replace('models/', '')
print(f"Dynamically selected model: {clean_model_name}")
model = genai.GenerativeModel(clean_model_name)
TARGET_URL = "https://www.google.com/about/careers/applications/jobs/results?location=India"
CONTEXT_FILE = "jay_professional_context_v1.md"
OUTPUT_FILE = "data/scouted_roles.json"
async def scrape_jobs():
    print(f"Scraping jobs from {TARGET_URL}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
        
        # Wait a bit for dynamic content to be fully rendered
        await page.wait_for_timeout(5000)
        
        # Scroll down a few times to trigger lazy loading if any
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
        # Extract Job Data
        jobs_data = await page.evaluate('''() => {
            const jobs = [];
            // Try explicit Google Careers links
            const links = document.querySelectorAll('a[href*="/jobs/results"]');
            const seenUrls = new Set();
            
            links.forEach(a => {
                const href = a.href;
                if (!seenUrls.has(href)) {
                    seenUrls.add(href);
                    // Traverse up to find the card container
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
            
            // Fallback: If no links found, just return the whole body text as one chunk
            // so Gemini can at least see if jobs exist but the DOM changed.
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
    print(f"Evaluating {len(jobs_data)} extracted job snippets via Gemini...")
    
    if not jobs_data:
        print("No jobs found to evaluate.")
        return []
    # Prepare Prompt
    prompt = f"""
You are an expert Executive Job Scout & Hiring Manager evaluating roles for Jay Shukla.
I am providing you with his complete Comprehensive Professional Context document. 
YOUR TASK:
1. Review the ENTIRE context deeply. Do not rely just on a core USP; evaluate against his full history (Meta, ByteDance, Travel Startup), skills, and explicit Job Search Criteria.
2. Evaluate each job listing in the provided array against ALL data in his context.
3. FILTERS:
   - Check the date in the job text. If it is older than 3 months, DISCARD IT.
   - Calculate a 'relevance_score' (0-100) based on how well the job requirements match Jay's ENTIRE comprehensive profile. 
   - If the relevance_score is less than 50 or if it's a strongly technical/engineering role, DISCARD IT.
4. For the surviving jobs (score >= 50 and < 3 months old), generate a "tip_to_score". This must explicitly reference specific stories or data from his timeline (e.g. Meta SMB insight, ByteDance Tier-2 methodology, etc.).
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
    response = model.generate_content(prompt, generation_config={"temperature": 0.2})
    raw_response = response.text.strip()
    
    # Strip markdown if Gemini includes it
    if raw_response.startswith("```json"):
        raw_response = raw_response[7:]
    if raw_response.startswith("```"):
        raw_response = raw_response[3:]
    if raw_response.endswith("```"):
        raw_response = raw_response[:-3]
    try:
        evaluated_jobs = json.loads(raw_response.strip())
        return evaluated_jobs
    except Exception as e:
        print("Failed to parse JSON core response from Gemini:")
        print(raw_response)
        raise e
async def main():
    # Ensure data dir exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Read Context
    if not os.path.exists(CONTEXT_FILE):
        print(f"Error: Could not find context file at {CONTEXT_FILE}")
        exit(1)
        
    with open(CONTEXT_FILE, "r") as f:
        context_text = f.read()
    # Step 1: Scrape
    jobs_data = []
    try:
        jobs_data = await scrape_jobs()
    except Exception as e:
        print(f"Scraping failed: {e}")
    
    # Step 2: Evaluate
    final_list = []
    if jobs_data:
        results = evaluate_jobs(jobs_data, context_text)
        print(f"Kept {len(results)} jobs after filtering.")
        
        # Merge logic
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
    # ALWAYS write the file so the UI doesn't 404 Unreachable
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_list, f, indent=2)
        
    print(f"Successfully saved {len(final_list)} jobs to {OUTPUT_FILE}")
if __name__ == "__main__":
    asyncio.run(main())
