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
from tqdm import tqdm
from browser_use import Agent, Browser, Controller, ActionResult
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContext
from langchain.chat_models.base import BaseChatModel

from ..storage.models import JobInfo, ApplyType


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

    async def _collect_job_ids(self, page, num_scrolls: int = 6, max_pages: Optional[int] = None) -> Set[str]:
        """Collect job IDs by scrolling through search results and navigating through pages.
        
        Args:
            page: Browser page object
            num_scrolls: Number of times to scroll down per page
            max_pages: Maximum number of pages to process (None for all pages)
            
        Returns:
            Set of job IDs
        """
        job_ids = set()
        page_num = 1
        has_next_page = True

        # Get total number of pages
        total_pages = await page.evaluate('''
            (() => {
                const pageState = document.querySelector('.jobs-search-pagination__page-state');
                if (pageState) {
                    const match = pageState.textContent.match(/Page \d+ of (\d+)/);
                    if (match) {
                        return parseInt(match[1]);
                    }
                }
                return 1;  // Default to 1 if we can't find the page count
            })()
        ''')
        print(f"\nTotal available pages: {total_pages}")
        
        # If max_pages is specified, use the minimum of max_pages and total_pages
        pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
        print(f"Will process up to {pages_to_process} pages")
        
        with tqdm(total=pages_to_process, desc="Processing pages") as page_pbar:
            while has_next_page and page_num <= pages_to_process:
                print(f"\nProcessing page {page_num} of {pages_to_process}")
                
                # Collect jobs on current page
                with tqdm(total=num_scrolls, desc=f"Page {page_num} scrolls") as scroll_pbar:
                    for scroll_count in range(num_scrolls):
                        # Get job IDs in current view
                        new_ids = await page.evaluate('''
                            Array.from(document.querySelectorAll("[data-job-id]"))
                                .map(element => element.getAttribute("data-job-id"))
                        ''')
                        prev_count = len(job_ids)
                        job_ids.update(new_ids)
                        new_count = len(job_ids) - prev_count
                        
                        scroll_pbar.set_postfix({
                            "total_jobs": len(job_ids),
                            "new": f"+{new_count}"
                        })

                        # Scroll down
                        await page.evaluate('window.scrollBy(0, 800)')
                        await asyncio.sleep(random.uniform(0.8, 1.8))
                        scroll_pbar.update(1)

                # Try to go to next page if we haven't reached max_pages
                if page_num < pages_to_process:
                    try:
                        # Check if next page button exists and is not disabled
                        next_button = await page.evaluate('''
                            (() => {
                                const button = document.querySelector('button[aria-label="View next page"]');
                                if (!button || button.classList.contains('artdeco-button--disabled')) {
                                    return null;
                                }
                                return true;
                            })()
                        ''')
                        
                        if next_button:
                            print(f"Moving to page {page_num + 1}")
                            # Click next page button
                            await page.click('button[aria-label="View next page"]')
                            await asyncio.sleep(2)  # Wait for page to load
                            page_num += 1
                            page_pbar.update(1)
                        else:
                            has_next_page = False
                            print("\nReached last page or no more results.")
                    except Exception as e:
                        print(f"\nError navigating to next page: {e}")
                        has_next_page = False
                else:
                    has_next_page = False
                    print(f"\nReached maximum page limit ({pages_to_process})")

        print(f"\nCollected {len(job_ids)} unique job IDs across {page_num} pages (out of {total_pages} available pages)")
        return job_ids

    async def collect_job_ids(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        experience_levels: Optional[List[str]] = None,
        num_scrolls: int = 6,
        max_pages: Optional[int] = None
    ) -> Set[str]:
        """Collect job IDs from LinkedIn search results.
        
        This is a faster alternative to search_jobs() as it only collects IDs
        without visiting each job's details page.
        
        Args:
            keywords: List of search keywords
            location: Optional location filter
            experience_levels: Optional list of experience levels
            num_scrolls: Number of times to scroll down per page
            max_pages: Maximum number of pages to process (None for all pages)
            
        Returns:
            Set of job IDs
        """
        print("\nStarting job ID collection...")
        print(f"Searching for: '{keywords}'")
        if location:
            print(f"Location: {location}")
        if experience_levels:
            print(f"Experience levels: {', '.join(experience_levels)}")
            
        # Build and navigate to search URL
        search_url = self._build_search_url(keywords, location, experience_levels)
        page = await self.context.get_current_page()
        await self.context.navigate_to(search_url)
        await asyncio.sleep(2)

        # Collect job IDs
        return await self._collect_job_ids(page, num_scrolls, max_pages)

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
            // Try different possible selectors for the apply button
            const applyButton = 
                document.querySelector('.jobs-apply-button') ||
                document.querySelector('button[data-control-name="jobdetails_topcard_inapply"]') ||
                document.querySelector('.jobs-s-apply button') ||
                document.querySelector('.jobs-apply-button--top-card');
                
            if (applyButton) {
                // Try different ways to get button text
                const buttonText = 
                    applyButton.querySelector('.artdeco-button__text')?.innerText ||
                    applyButton.innerText || '';
                    
                const isEasyApply = buttonText.toLowerCase().includes('easy apply');
                if (isEasyApply) {
                    const jobId = 
                        applyButton.getAttribute('data-job-id') ||
                        window.location.href.split('currentJobId=')[1]?.split('&')[0] ||
                        window.location.href.split('/view/')[1]?.split('/')[0];
                        
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
                # Try different possible selectors for external apply button
                selectors = [
                    '.jobs-apply-button',
                    'button[data-control-name="jobdetails_topcard_inapply"]',
                    '.jobs-s-apply button',
                    '.jobs-apply-button--top-card',
                    'button[aria-label*="Apply"]',  # Buttons with "Apply" in aria-label
                    'a[aria-label*="Apply"]'  # Sometimes it's a link instead of button
                ]
                
                # Wait for any of these selectors to be available
                for selector in selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=1000)                        
                        popup_promise = page.wait_for_event("popup")
                        await page.click(selector)
                        popup = await popup_promise
                        await popup.wait_for_load_state()
                        apply_info['link'] = popup.url
                        await popup.close()
                        break
                    except:
                        continue
                        
                if not apply_info['link']:
                    apply_info['link'] = page.url
                    
            except Exception as e:
                print(f"Error getting external apply link: {str(e)}")
                apply_info['link'] = page.url
                
        return apply_info

    async def scrape_job_info(self, job_id: str) -> Optional[JobInfo]:
        """Scrape detailed information about a specific job.
        
        Args:
            job_id: ID of the job to scrape
            
        Returns:
            JobInfo object if successful, None if job not found or error
        """
        try:
            # Navigate to job details page
            job_url = f'https://www.linkedin.com/jobs/view/{job_id}/'
            page = await self.context.get_current_page()
            await self.context.navigate_to(job_url)
            await asyncio.sleep(random.uniform(2.0, 3.0))  # Random delay to avoid detection

            # Extract job information
            job_info = await self._extract_job_info(page)
            apply_info = await self._get_apply_info(page)
            
            # Create and return JobInfo object
            return JobInfo(
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
        except Exception as e:
            print(f"Error scraping job {job_id}: {str(e)}")
            return None

    async def search_jobs(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        experience_levels: Optional[List[str]] = None
    ) -> AsyncGenerator[JobInfo, None]:
        """Search for jobs on LinkedIn."""
        print("\nStarting job search...")
        print(f"Searching for: '{keywords}'")
        if location:
            print(f"Location: {location}")
        if experience_levels:
            print(f"Experience levels: {', '.join(experience_levels)}")
            
        # Build and navigate to search URL
        search_url = self._build_search_url(keywords, location, experience_levels)
        page = await self.context.get_current_page()
        await self.context.navigate_to(search_url)
        await asyncio.sleep(2)

        # Collect job IDs
        job_ids = await self._collect_job_ids(page)
        
        # Process each job
        with tqdm(total=len(job_ids), desc="Collecting job Metadata") as pbar:
            for job_id in job_ids:
                # Update progress bar with current job ID
                pbar.set_postfix({"job_id": job_id})
                
                # Navigate to job details
                job_url = f'https://www.linkedin.com/jobs/search/?currentJobId={job_id}'
                await self.context.navigate_to(job_url)
                await asyncio.sleep(random.uniform(3.8, 5.4))

                # Extract job information
                job_info = await self._extract_job_info(page)
                apply_info = await self._get_apply_info(page)
                
                # Create and yield JobInfo object
                job = JobInfo(
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
                
                pbar.update(1)
                yield job

    async def close(self):
        """Close browser instances."""
        await self.context.close()
        await self.browser.close()

    async def get_job_details(self, job_id: str) -> Optional[JobInfo]:
        """Get detailed information about a specific job."""
        browser_use = self.browser_use
        job_url = f'https://www.linkedin.com/jobs/view/{job_id}/'
        
        try:
            await browser_use.goto(job_url)
            return await self._extract_job_details(job_id)
        except:
            return None 