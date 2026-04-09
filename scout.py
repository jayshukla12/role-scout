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
model = genai.GenerativeModel('gemini-1.5-pro-latest')  # Using Pro for better reading comprehension of the comprehensive context

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

        # Extract Job Data (URLs and their surrounding text container)
        jobs_data = await page.evaluate('''() => {
            const jobs = [];
            const links = document.querySelectorAll('a[href*="/jobs/results/"]');
            const seenUrls = new Set();
            
            links.forEach(a => {
                // Ensure it's a specific job URL, not just a category
                if (/jobs\\/results\\/\\d+/.test(a.href) && !seenUrls.has(a.href)) {
                    seenUrls.add(a.href);
                    
                    // Traverse up a few levels to get the job card container
                    let container = a.parentElement;
                    for (let i = 0; i < 5; i++) {
                        if (container && container.parentElement) {
                            container = container.parentElement;
                        }
                    }
                    
                    jobs.push({
                        url: a.href,
                        text: container ? container.innerText.replace(/\\s+/g, ' ').trim() : a.innerText
                    });
                }
            });
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
You are an expert Executive Job Scout & Hiring Manager. 
I am going to provide you with a Comprehensive Professional Context for a candidate named Jay Shukla.
Then, I will provide you with a JSON array of job listings extracted from a company's career page. 

YOUR TASK:
1. Review the candidate's context deeply. Note his strengths: Growth, Indian Market, SMBs, GenZ, non-technical PM, etc.
2. Evaluate each job listing in the provided array.
3. FILTERS:
   - Check the date in the job text if available (e.g. "Posted 3 days ago"). If it indicates the job is older than 3 months, DISCARD IT.
   - Calculate a 'relevance_score' (0-100) based on how well the job requirements match Jay's context. 
   - If the relevance_score is less than 50, DISCARD IT.
4. For the surviving jobs (score >= 50 and < 3 months old), generate a "tip_to_score". This should be a concise, highly tailored 1-paragraph summary of exactly how Jay should pitch himself for this specific role, explicitly citing his past experiences (e.g. Meta SMB insight, ByteDance Tier-2 methodology).
5. Extract the job 'title' and the 'date_published' (e.g. "3 days ago") from the text. 

CANDIDATE CONTEXT:
{context_text}

EXTRACTED JOBS JSON:
{json.dumps(jobs_data, indent=2)}

OUTPUT REQUIREMENT:
Return ONLY a valid JSON array of objects, with no markdown code blocks formatting. Just the raw JSON.
Format of each object:
{{
  "title": "Exact Title of the Role",
  "url": "original linked url",
  "relevance_score": 85,
  "tip_to_score": "To land this role, lean heavily into your experience with... highlight your 2.3% revenue uplift...",
  "date_published": "Posted 5 days ago"
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
    jobs_data = await scrape_jobs()
    
    # Step 2: Evaluate
    if jobs_data:
        results = evaluate_jobs(jobs_data, context_text)
        print(f"Kept {len(results)} jobs after filtering.")
        
        # Step 3: Ensure data persistence / merging
        # If we already have jobs, we don't want to lose them unless they are old.
        # But since the requirement is "give me most recent scrape session", 
        # we can just overwrite or maintain a deduplicated list. Let's maintain a deduplicated list.
        existing_data = []
        if os.path.exists(OUTPUT_FILE):
            try:
                with open(OUTPUT_FILE, "r") as f:
                    existing_data = json.load(f)
            except:
                pass
                
        # Merge by URL
        jobs_dict = {job['url']: job for job in existing_data}
        for job in results:
            jobs_dict[job['url']] = job  # Update or add new
            
        final_list = list(jobs_dict.values())
        
        with open(OUTPUT_FILE, "w") as f:
            json.dump(final_list, f, indent=2)
            
        print(f"Successfully saved {len(final_list)} jobs to {OUTPUT_FILE}")
    else:
        print("No jobs found to evaluate.")

if __name__ == "__main__":
    asyncio.run(main())
