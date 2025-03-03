from typing import List
from dotenv import load_dotenv
import os
import asyncio
import time
import random

from browser_use import Agent, Browser, Controller, ActionResult
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContext
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

load_dotenv(override=True)

start_time = time.time()

sensitive_data = {
    'linkedin_name': os.getenv("LINKEDIN_USERNAME"), 
    'linkedin_password': os.getenv("LINKEDIN_PASSWORD")
}

class Job(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    second_head: str
    location: str
    posted_days_ago: str
    ppl_applied: str
    apply_link: str
    apply_type: str  # Add this new field for "Easy Apply" or "Apply"

class Jobs(BaseModel):
    jobs: List[Job]

controller_out = Controller(output_model=Job)
print(os.getenv("CHROME_PATH"))

browser_config = BrowserConfig(
    # chrome_instance_path=r"C:\Users\fish\git_project\Fireball\GoogleChromePortable\GoogleChromePortable.exe",
    chrome_instance_path=os.getenv("CHROME_PATH"),
    disable_security=True,
)
context_config = BrowserContextConfig(
    browser_window_size={'width': 600, 'height': 800},
    viewport_expansion=400,  # Reasonable viewport expansion
    wait_for_network_idle_page_load_time=3.0  # Wait for network to be idle
)

browser = Browser(config=browser_config)
context = BrowserContext(browser=browser, config=context_config)

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    # llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', api_key=api_key)
    llm = ChatOpenAI(model='gpt-4o-mini')
    agent_login = Agent(
        task='go to linkedin.com and login with x_name and x_password.',
        llm=llm,
        sensitive_data=sensitive_data,
        browser_context=context  # Use persistent context
    )
    
    agent_goto_jobs = Agent(
        task=r"""go to https://www.linkedin.com/jobs/search/?f_E=2%2C4&geoId=103644278&keywords=machine%20learning%20engineer
        And wait for 5 seconds.
        """,
        llm=llm,
        browser_context=context
    )

    agent_recent_job_searches = Agent(
        task="""Locate the Recent job searches section. 
        Just go to the machine learning engineer, United States, Entry level, Mid-Senior level.
        Do not gather detailed information about each posting if required.
        """,
        llm=llm,
        browser_context=context
    )

    agent_get_job_info = Agent(
        task=f"""Get this page's job title, company name and location. You only need to find the job at the beginning of the page. Do not click on anything.
        """,
        llm=llm,
        browser_context=context,
        controller=controller_out
    )
    
    # await agent_login.run()
    # await asyncio.sleep(1)
    await agent_goto_jobs.run()
    await asyncio.sleep(1)
    # await agent_recent_job_searches.run()
    # await asyncio.sleep(1)
    jobs_list = []
    
    for area_index in range(1, 7):
        page = await context.get_current_page()
        
        job_ids = await page.evaluate('''
            Array.from(document.querySelectorAll("[data-job-id]"))
                .map(element => element.getAttribute("data-job-id"))
        ''')
        print(job_ids)
        jobs_list.extend(job_ids)

        await page.evaluate(f'window.scrollBy(0, 800);')
        await asyncio.sleep(random.uniform(0.8, 1.8))

    jobs_list = list(set(jobs_list))

    results_list = []
    for job_id in jobs_list:
        job_url = f'https://www.linkedin.com/jobs/search/?currentJobId={job_id}'
        page = await context.get_current_page()
        await context.navigate_to(job_url)
        await asyncio.sleep(2)

        job_title = await page.evaluate('''
            document.querySelector('.t-24.job-details-jobs-unified-top-card__job-title')?.innerText || ''
        ''')

        company_name = await page.evaluate('''
            document.querySelector('.job-details-jobs-unified-top-card__company-name')?.innerText || ''
        ''')

        second_head = await page.evaluate('''
            document.querySelector('.job-details-jobs-unified-top-card__primary-description-container')?.innerText || ''
        ''')
        # need to handle the case when there is no posted_days_ago and ppl_applied
        if len(second_head.split('·')) == 3:
            location = second_head.split('·')[0].strip()
            posted_days_ago = second_head.split('·')[1].strip()
            ppl_applied = second_head.split('·')[2].strip()
        else:
            location = None
            posted_days_ago = None
            ppl_applied = None
        
        # Get the apply button info
        apply_info = await page.evaluate('''(() => {
            const applyButton = document.querySelector('.jobs-apply-button');
            if (applyButton) {
                const buttonText = applyButton.querySelector('.artdeco-button__text')?.innerText || '';
                const isEasyApply = buttonText.includes('Easy Apply');
                if (isEasyApply) {
                    const jobId = applyButton.getAttribute('data-job-id');
                    return {
                        link: `https://www.linkedin.com/jobs/view/${jobId}/`,
                        type: 'Easy Apply'
                    };
                } else {
                    return {
                        link: null,  // We'll get this after clicking
                        type: 'Apply'
                    };
                }
            }
            return {
                link: window.location.href,
                type: 'Unknown'
            };
        })()''')

        # If it's a regular Apply button, click it and get the URL
        if apply_info['type'] == 'Apply':
            # Create a wait for popup before clicking
            popup_promise = page.wait_for_event("popup")
            
            # Click the apply button
            await page.click('.jobs-apply-button')
            
            try:
                # Wait for the popup and get its URL
                popup = await popup_promise
                await popup.wait_for_load_state()
                apply_info['link'] = popup.url
                await popup.close()
            except:
                # If no popup, use the current page URL as fallback
                apply_info['link'] = page.url

        result = Job(
            job_id=job_id,
            job_title=job_title, 
            company_name=company_name,
            second_head=second_head,
            location=location,
            posted_days_ago=posted_days_ago,
            ppl_applied=ppl_applied,
            apply_link=apply_info['link'],
            apply_type=apply_info['type']
        )
        
        results_list.append(result)

    await context.close()
    await browser.close()
    
    return results_list


# Run everything in a single event loop
results_list = asyncio.run(main())
print(results_list)

end_time = time.time()
print(f'Time taken: {end_time - start_time} seconds')
