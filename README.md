# El País Web Scraper

A Python web scraping tool for extracting articles from El País using Selenium.

## Requirements
- Python 3.8+
- Google Chrome
- Dependencies: Selenium, webdriver-manager, Requests, python-dotenv

## Setup
1. Run `.\install.bat` to install dependencies and activate virtual environment

## Usage
- Local scraping: `python .\opinion_scraper.py`
- BrowserStack (multi-threaded): `python .\opinion_scraper_browerstack.py`
- Run both: `python run_tests.py`

## Features
- Automated Chrome browser control
- Scrapes El País Opinion section
- Extracts 5 articles per run
- Saves results to Output folder
- BrowserStack integration for distributed testing
- Test credentials included in `.env.browserstack` (valid for ~10-20 runs; replace with your own for extended use)
