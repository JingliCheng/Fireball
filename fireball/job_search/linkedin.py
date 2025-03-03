"""
LinkedIn job search implementation using browser-use.
"""
from datetime import datetime
import asyncio
import random
import os
import sys
from typing import Dict, List, Optional, AsyncGenerator, Set
from urllib.parse import urlencode
from browser_use import Agent, Browser, Controller, ActionResult
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContext
from langchain.chat_models.base import BaseChatModel

from ..storage.models import Job, ApplyType

def find_chrome_windows():
    """Find Chrome executable in common Windows locations."""
    common_locations = [
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser("~") + "\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
    ]
    
    for location in common_locations:
        if os.path.exists(location):
            return location
    return None

class LinkedInJobSearch:
    """LinkedIn job search functionality."""
    
    # Experience level mapping
    EXPERIENCE_LEVELS = {
        "internship": "1",
        "entry": "2",
        "associate": "3",
        "mid-senior": "4",
        "director": "5",
        "executive": "6"
    }
    
    def __init__(
        self, 
        credentials: Dict[str, str], 
        llm: Optional[BaseChatModel] = None, 
        model_name: str = "gpt-4-mini",
        chrome_path: Optional[str] = None
    ):
        """Initialize LinkedIn job searcher.
        
        Args:
            credentials: LinkedIn credentials (username, password)
            llm: Optional pre-configured LLM instance
            model_name: Model name to use if llm not provided
            chrome_path: Optional path to Chrome executable
        """
        self.credentials = credentials
        self.llm = llm
        self.model_name = model_name
        
        # Initialize browser with config
        self.browser_config = BrowserConfig(
            chrome_instance_path=chrome_path,
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
        """Login to LinkedIn using browser-use Agent."""
        # Create login agent with sensitive data
        agent_login = Agent(
            task='go to linkedin.com and login with x_name and x_password.',
            llm=self.llm,  # Use LLM from interface
            sensitive_data={
                'x_name': self.credentials["username"],
                'x_password': self.credentials["password"]
            },
            browser_context=self.context
        )
        
        # Run login agent
        await agent_login.run()
        await asyncio.sleep(1)  # Wait for login to complete

    def _build_search_url(self, keywords: List[str], location: Optional[str], experience_levels: Optional[List[str]]) -> str:
        """Build LinkedIn job search URL with parameters.
        
        Args:
            keywords: List of search keywords
            location: Optional location filter
            experience_levels: Optional list of experience levels
            
        Returns:
            Complete search URL
        """
        params = {"keywords": " ".join(keywords)}
        
        if location:
            params["location"] = location
            
        if experience_levels:
            codes = [self.EXPERIENCE_LEVELS[level.lower()] 
                    for level in experience_levels 
                    if level.lower() in self.EXPERIENCE_LEVELS]
            if codes:
                params["f_E"] = ",".join(codes)
                
        return f"https://www.linkedin.com/jobs/search/?{urlencode(params)}"

    async def _collect_job_ids(self, page, num_scrolls: int = 6) -> Set[str]:
        """Collect job IDs by scrolling through search results.
        
        Args:
            page: Browser page object
            num_scrolls: Number of times to scroll down
            
        Returns:
            Set of job IDs
        """
        job_ids = set()
        for _ in range(num_scrolls):
            # Get job IDs in current view
            new_ids = await page.evaluate('''
                Array.from(document.querySelectorAll("[data-job-id]"))
                    .map(element => element.getAttribute("data-job-id"))
            ''')
            job_ids.update(new_ids)

            # Scroll down
            await page.evaluate('window.scrollBy(0, 800)')
            await asyncio.sleep(random.uniform(0.8, 1.8))
            
        return job_ids

    async def _extract_job_info(self, page) -> Dict[str, Optional[str]]:
        """Extract job information from the current page.
        
        Args:
            page: Browser page object
            
        Returns:
            Dictionary containing job details
        """
        # Extract basic info
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
        location = posted_days_ago = ppl_applied = None
        if len(second_head.split('·')) == 3:
            parts = [part.strip() for part in second_head.split('·')]
            location, posted_days_ago, ppl_applied = parts
            
        return {
            "job_title": job_title,
            "company_name": company_name,
            "location": location,
            "posted_days_ago": posted_days_ago,
            "ppl_applied": ppl_applied,
            "raw_description": second_head
        }

    async def _get_apply_info(self, page) -> Dict[str, str]:
        """Get application button information.
        
        Args:
            page: Browser page object
            
        Returns:
            Dictionary with apply link and type
        """
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
                
        return apply_info

    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        experience_levels: Optional[List[str]] = None
    ) -> AsyncGenerator[Job, None]:
        """Search for jobs on LinkedIn."""
        # Build and navigate to search URL
        search_url = self._build_search_url(keywords, location, experience_levels)
        page = await self.context.get_current_page()
        await self.context.navigate_to(search_url)
        await asyncio.sleep(2)

        # Collect job IDs
        job_ids = await self._collect_job_ids(page)

        # Process each job
        for job_id in job_ids:
            # Navigate to job details
            job_url = f'https://www.linkedin.com/jobs/search/?currentJobId={job_id}'
            await self.context.navigate_to(job_url)
            await asyncio.sleep(2)

            # Extract job information
            job_info = await self._extract_job_info(page)
            apply_info = await self._get_apply_info(page)
            
            # Create and yield Job object
            job = Job(
                job_id=job_id,
                job_title=job_info["job_title"],
                company_name=job_info["company_name"],
                location=job_info["location"],
                posted_days_ago=job_info["posted_days_ago"],
                ppl_applied=job_info["ppl_applied"],
                apply_link=apply_info["link"],
                apply_type=apply_info["type"],
                raw_description=job_info["raw_description"]
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