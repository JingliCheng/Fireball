"""
LinkedIn job search implementation using browser-use.
"""
from datetime import datetime
import asyncio
import random
import os
from typing import Dict, List, Optional, AsyncGenerator
from browser_use import Agent, Browser, Controller, ActionResult
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContext

from ..storage.models import Job, ApplyType

class LinkedInJobSearch:
    """LinkedIn job search functionality."""
    
    def __init__(self, credentials: Dict[str, str]):
        """Initialize LinkedIn job searcher."""
        self.credentials = credentials
        
        # Initialize browser with config
        self.browser_config = BrowserConfig(
            chrome_instance_path=os.getenv("CHROME_PATH"),  # Get chrome path from env
            disable_security=True,
        )
        self.context_config = BrowserContextConfig(
            browser_window_size={'width': 600, 'height': 800},
            viewport_expansion=400,
            wait_for_network_idle_page_load_time=3.0
        )
        
        self.browser = Browser(config=self.browser_config)
        self.context = BrowserContext(browser=self.browser, config=self.context_config)

    async def login(self):
        """Login to LinkedIn."""
        page = await self.context.get_current_page()
        await self.context.navigate_to("https://www.linkedin.com/login")
        
        # Fill in credentials
        await page.fill("#username", self.credentials["username"])
        await page.fill("#password", self.credentials["password"])
        
        # Click login button
        await page.click(".login__form_action_container button")
        await page.wait_for_load_state("networkidle")

    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        experience_levels: Optional[List[str]] = None
    ) -> AsyncGenerator[Job, None]:
        """Search for jobs on LinkedIn."""
        # Build search URL
        base_url = "https://www.linkedin.com/jobs/search/?"
        params = [f"keywords={'+'.join(keywords)}"]
        if location:
            params.append(f"location={location}")
        if experience_levels:
            level_codes = {
                "internship": "1", "entry": "2", "associate": "3",
                "mid-senior": "4", "director": "5", "executive": "6"
            }
            codes = [level_codes[level] for level in experience_levels if level in level_codes]
            if codes:
                params.append(f"f_E={','.join(codes)}")
        search_url = base_url + "&".join(params)

        # Navigate to search results
        page = await self.context.get_current_page()
        await self.context.navigate_to(search_url)
        await asyncio.sleep(2)

        # Collect job IDs while scrolling
        job_ids = set()
        for _ in range(6):
            # Get job IDs in current view
            new_ids = await page.evaluate('''
                Array.from(document.querySelectorAll("[data-job-id]"))
                    .map(element => element.getAttribute("data-job-id"))
            ''')
            job_ids.update(new_ids)

            # Scroll down
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(random.uniform(0.8, 1.8))

        # Process each job
        for job_id in job_ids:
            job_url = f'https://www.linkedin.com/jobs/search/?currentJobId={job_id}'
            await self.context.navigate_to(job_url)
            await asyncio.sleep(2)

            # Extract job details using JavaScript
            job_title = await page.evaluate('''
                document.querySelector('.t-24.job-details-jobs-unified-top-card__job-title')?.innerText || ''
            ''')

            company_name = await page.evaluate('''
                document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText || ''
            ''')

            second_head = await page.evaluate('''
                document.querySelector('.job-details-jobs-unified-top-card__primary-description-container')?.innerText || ''
            ''')

            # Parse location info
            location = None
            posted_days_ago = None
            ppl_applied = None
            if len(second_head.split('·')) == 3:
                location = second_head.split('·')[0].strip()
                posted_days_ago = second_head.split('·')[1].strip()
                ppl_applied = second_head.split('·')[2].strip()

            # Get apply button information
            apply_info = await page.evaluate('''(() => {
                const applyButton = document.querySelector('.jobs-apply-button');
                if (applyButton) {
                    const buttonText = applyButton.querySelector('.artdeco-button__text')?.innerText || '';
                    const isEasyApply = buttonText.includes('Easy Apply');
                    if (isEasyApply) {
                        return {
                            link: `https://www.linkedin.com/jobs/view/${jobId}/`,
                            type: 'Easy Apply'
                        };
                    }
                    return {
                        link: null,
                        type: 'Apply'
                    };
                }
                return {
                    link: window.location.href,
                    type: 'Unknown'
                };
            })()''')

            # Handle regular Apply button (gets external URL)
            if apply_info['type'] == 'Apply' and not apply_info['link']:
                try:
                    popup_promise = page.wait_for_event("popup")
                    await page.click('.jobs-apply-button')
                    popup = await popup_promise
                    await popup.wait_for_load_state()
                    apply_info['link'] = popup.url
                    await popup.close()
                except:
                    apply_info['link'] = page.url

            # Create Job object
            job = Job(
                job_id=job_id,
                job_title=job_title,
                company_name=company_name,
                location=location,
                posted_days_ago=posted_days_ago,
                ppl_applied=ppl_applied,
                apply_link=apply_info['link'],
                apply_type=apply_info['type'],
                raw_description=second_head
            )
            
            yield job

    async def close(self):
        """Close browser instances."""
        await self.context.close()
        await self.browser.close()

    async def get_job_details(self, job_id: str) -> Optional[Job]:
        """Get detailed information about a specific job."""
        browser_use = self.browser_use
        job_url = f'https://www.linkedin.com/jobs/view/{job_id}/'
        
        try:
            await browser_use.goto(job_url)
            return await self._extract_job_details(job_id)
        except:
            return None 