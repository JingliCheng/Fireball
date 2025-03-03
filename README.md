# Fireball

An automated job application bot with intelligent job searching, applying, and resume enhancement capabilities.

## Project Structure

```
Fireball/
├── setup.py                   # Package setup file
├── requirements.txt           # Project dependencies
├── LICENSE                    # License file
├── .gitignore                # Git ignore file
├── .env                      # Env variables(you need to create it like the example)
├── .env.example              # Example environment variables
├── README.md                 # Project documentation
├── fireball/                 # Main package directory
│   ├── __init__.py
│   ├── job_search/           # Job search functionality
│   │   ├── __init__.py
│   │   └── linkedin.py       # LinkedIn implementation
│   ├── job_apply/            # Job application functionality
│   │   └── __init__.py      # Auto job application logic
│   ├── storage/              # Data storage
│   │   ├── __init__.py
│   │   ├── models.py         # Data models for job storage
│   │   └── json_store.py     # JSON storage implementation
│   ├── interfaces/           # Interface definitions
│   │   ├── __init__.py
│   │   └── interface.py      # Abstract interfaces
│   ├── personal/             # Personal information management
│   │   ├── __init__.py
│   │   └── models.py         # Personal data models
│   └── utils/                # Utility functions
│       └── __init__.py
├── data/                     # Data storage directory
│   ├── active/              # Active job data
│   └── backups/             # Backup storage
├── examples/                 # Example scripts
│   ├── linkedin_search.py    # LinkedIn search example
│   └── failed_applications_demo.py  # Failed applications demo
├── tests/                    # Test directory
├── playground/               # Development and testing
│   └── try7.py              # Working prototype
└── GoogleChromePortable/     # Portable Chrome installation
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install package in development mode:
```bash
pip install -e .
```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your credentials and configurations in `.env`:
```bash
cp .env.example .env
# Edit .env with your values
```

Example `.env` contents:
```env
# LinkedIn Credentials
LINKEDIN_USERNAME=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password

# Browser Configuration
CHROME_PATH=/path/to/chrome/executable

# Optional API Keys (if needed)
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Usage

Example of searching for jobs on LinkedIn:

```python
import asyncio
from fireball.job_search.linkedin import LinkedInJobSearch
from fireball.storage.json_store import JsonStorageManager

async def main():
    # Initialize LinkedIn job search
    linkedin = LinkedInJobSearch({
        "username": os.getenv("LINKEDIN_USERNAME"),
        "password": os.getenv("LINKEDIN_PASSWORD")
    })
    
    try:
        await linkedin.login()
        async for job in linkedin.search_jobs(
            keywords=["python developer"],
            location="United States",
            experience_levels=["entry", "mid-senior"]
        ):
            print(f"Found job: {job.job_title} at {job.company_name}")
    finally:
        await linkedin.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Features

- **Job Search**: Automated job searching on platforms like LinkedIn
- **Data Storage**: JSON-based storage for job data and application status
- **Browser Automation**: Uses browser-use for intelligent web interaction
- **Personal Info Management**: Handles resumes and personal profiles
- **Application Tracking**: Tracks application status and history

## Development

The project uses:
- browser-use for AI-powered web automation
- Pydantic for data modeling
- asyncio for asynchronous operations
- JSON for data storage

## License

See the [LICENSE](LICENSE) file for details. 