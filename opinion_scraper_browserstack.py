import time
import json
import os
import requests
import re
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.safari.options import Options as SafariOptions
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

load_dotenv('.env.browserstack')

BROWSERSTACK_USERNAME = os.getenv('BROWSERSTACK_USERNAME')
BROWSERSTACK_ACCESS_KEY = os.getenv('BROWSERSTACK_ACCESS_KEY')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')
RAPIDAPI_HOST = os.getenv('RAPIDAPI_HOST')

BROWSERSTACK_URL = f"https://{BROWSERSTACK_USERNAME}:{BROWSERSTACK_ACCESS_KEY}@hub-cloud.browserstack.com/wd/hub"

BROWSER_CONFIGS = [
    {
        'name': 'Chrome_Windows',
        'os': 'Windows',
        'os_version': '11',
        'browser': 'Chrome',
        'browser_version': 'latest',
        'resolution': '1920x1080'
    },
    {
        'name': 'Firefox_Windows',
        'os': 'Windows',
        'os_version': '10',
        'browser': 'Firefox',
        'browser_version': 'latest',
        'resolution': '1920x1080'
    },
    {
        'name': 'Edge_Windows',
        'os': 'Windows',
        'os_version': '11',
        'browser': 'Edge',
        'browser_version': 'latest',
        'resolution': '1920x1080'
    },
    {
        'name': 'iPhone_14_Safari',
        'device': 'iPhone 14',
        'os_version': '16',
        'browser': 'safari',
        'real_mobile': 'true'
    },
    {
        'name': 'Samsung_Galaxy_S23',
        'device': 'Samsung Galaxy S23',
        'os_version': '13.0',
        'browser': 'chrome',
        'real_mobile': 'true'
    }
]


class BrowserStackScraper:
    def __init__(self, browser_config, max_articles=5):
        self.browser_config = browser_config
        self.browser_name = browser_config['name']
        self.max_articles = max_articles
        self.url = "https://elpais.com"
        self.driver = None
        self.articles_data = []
        
    def setup_driver(self):
        try:
            browser_type = self.browser_config.get('browser', 'chrome').lower()
            
            if browser_type == 'chrome':
                options = ChromeOptions()
            elif browser_type == 'firefox':
                options = FirefoxOptions()
            elif browser_type == 'edge':
                options = EdgeOptions()
            elif browser_type == 'safari':
                options = SafariOptions()
            else:
                options = ChromeOptions()
            
            for key, value in self.browser_config.items():
                if key != 'name':
                    options.set_capability(key, value)
            
            options.set_capability('browserstack.local', 'false')
            options.set_capability('browserstack.selenium_version', '4.17.0')
            options.set_capability('name', f'ElPais Opinion Scraper - {self.browser_name}')
            options.set_capability('build', f'Opinion Scraper Build - {datetime.now().strftime("%Y%m%d_%H%M%S")}')
            
            print(f"[{self.browser_name}] Connecting to BrowserStack...")
            self.driver = webdriver.Remote(command_executor=BROWSERSTACK_URL, options=options)
            print(f"[{self.browser_name}] Connected")
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            print(f"[{self.browser_name}] Connection failed: {e}")
            return False
    
    def accept_cookies(self):
        cookie_selectors = [
            "//button[contains(., 'Aceptar')]",
            "//button[contains(., 'ACEPTAR')]",
            "#didomi-notice-agree-button",
            "button[id*='accept']"
        ]
        
        for selector in cookie_selectors:
            try:
                if selector.startswith("//"):
                    button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                button.click()
                time.sleep(1)
                return
            except:
                continue
    
    def translate_text(self, text, source='es', target='en'):
        try:
            url = f"https://{RAPIDAPI_HOST}/api/v1/translator/text"
            headers = {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": RAPIDAPI_HOST,
                "Content-Type": "application/json"
            }
            payload = {"from": source, "to": target, "text": text}
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('trans', result.get('translation', text))
            return text
        except:
            return text
    
    def scrape_full_article(self, url):
        article_content = {'title': 'N/A', 'author': 'N/A', 'full_article_text': 'N/A'}
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            for selector in ['h1', 'h2.headline', '.article-title']:
                try:
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title and len(title) >= 3:
                        article_content['title'] = title
                        break
                except:
                    continue
            
            for selector in ['.author', '.byline', '[itemprop="author"]']:
                try:
                    author_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip()
                    if author:
                        article_content['author'] = author
                        break
                except:
                    continue
            
            for selector in ['article', '.article-body', '.article-content']:
                try:
                    article_body = self.driver.find_element(By.CSS_SELECTOR, selector)
                    full_text = article_body.text.strip()
                    if full_text and len(full_text) > 100:
                        article_content['full_article_text'] = full_text
                        break
                except:
                    continue
        except:
            pass
        
        return article_content
    
    def scrape_opinion_section(self):
        try:
            is_mobile = 'iPhone' in self.browser_name or 'Samsung' in self.browser_name
            initial_wait = 8 if is_mobile else 5
            scroll_wait = 4 if is_mobile else 2
            
            print(f"[{self.browser_name}] Scraping opinion section...")
            self.driver.get("https://elpais.com/opinion/")
            time.sleep(initial_wait)
            
            self.accept_cookies()
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            
            body_height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(3):
                scroll_position = ((i + 1) * body_height) // 3
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                time.sleep(scroll_wait)
            
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            articles = self.driver.find_elements(By.TAG_NAME, "article")
            min_text_length = 5 if is_mobile else 10
            
            article_urls = []
            for article in articles:
                try:
                    links = article.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        url = link.get_attribute("href")
                        link_text = link.text.strip()
                        
                        if url and "/opinion/" in url:
                            has_date = re.search(r'/\d{4}-\d{2}-\d{2}/', url)
                            has_html = url.endswith('.html')
                            is_category = url.endswith('/')
                            
                            if (has_date or has_html) and not is_category and link_text and len(link_text) >= min_text_length:
                                article_urls.append(url)
                                break
                except:
                    continue
            
            seen = set()
            unique_urls = []
            for url in article_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            unique_urls = unique_urls[:self.max_articles]
            
            for idx, article_url in enumerate(unique_urls, 1):
                try:
                    print(f"[{self.browser_name}] Article {idx}/{len(unique_urls)}")
                    full_content = self.scrape_full_article(article_url)
                    
                    article_data = {
                        'title': full_content['title'],
                        'title_en': self.translate_text(full_content['title']),
                        'author': full_content['author'],
                        'url': article_url,
                        'full_article_text': full_content['full_article_text'],
                        'browser': self.browser_name
                    }
                    
                    self.articles_data.append(article_data)
                except:
                    continue
            
            print(f"[{self.browser_name}] Completed: {len(self.articles_data)} articles")
        except Exception as e:
            print(f"[{self.browser_name}] Error: {e}")
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def run_scraper_on_browser(browser_config, max_articles=5):
    scraper = None
    try:
        scraper = BrowserStackScraper(browser_config, max_articles)
        
        if not scraper.setup_driver():
            return {
                'browser': browser_config['name'],
                'status': 'failed',
                'error': 'Failed to setup driver',
                'articles': []
            }
        
        scraper.driver.get(scraper.url)
        time.sleep(2)
        scraper.scrape_opinion_section()
        
        return {
            'browser': browser_config['name'],
            'status': 'success',
            'articles': scraper.articles_data,
            'count': len(scraper.articles_data)
        }
    except Exception as e:
        return {
            'browser': browser_config.get('name', 'Unknown'),
            'status': 'failed',
            'error': str(e),
            'articles': []
        }
    finally:
        if scraper:
            scraper.close()


def analyze_word_frequency(all_articles):
    all_titles = " ".join([article['title_en'] for article in all_articles])
    words = re.findall(r'\b[a-zA-Z]+\b', all_titles.lower())
    word_counts = Counter(words)
    return {word: count for word, count in word_counts.items() if count > 2}


def deduplicate_articles_by_url(all_articles):
    seen_urls = set()
    unique_articles = []
    
    for article in all_articles:
        url = article.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)
    
    return unique_articles


def save_results(results, output_folder="output_browserstack"):
    os.makedirs(output_folder, exist_ok=True)
    all_articles = []
    browser_summary = []
    
    for result in results:
        browser_name = result['browser']
        status = result['status']
        
        browser_info = {
            'browser': browser_name,
            'status': status,
            'articles_scraped': result.get('count', 0)
        }
        
        if status == 'failed':
            browser_info['error'] = result.get('error', 'Unknown error')
        
        browser_summary.append(browser_info)
        
        if status == 'success':
            all_articles.extend(result['articles'])
    
    json_path = os.path.join(output_folder, "all_articles.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(all_articles)} articles to {json_path}")
    
    if all_articles:
        unique_articles = deduplicate_articles_by_url(all_articles)
        unique_json_path = os.path.join(output_folder, "unique_articles.json")
        with open(unique_json_path, 'w', encoding='utf-8') as f:
            json.dump(unique_articles, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(unique_articles)} unique articles to {unique_json_path}")
    
    summary_path = os.path.join(output_folder, "browser_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(browser_summary, f, indent=2)
    print(f"Saved browser summary to {summary_path}")
    
    if all_articles:
        unique_articles = deduplicate_articles_by_url(all_articles)
        repeated_words = analyze_word_frequency(unique_articles)
        
        analysis_path = os.path.join(output_folder, "word_frequency_analysis.txt")
        with open(analysis_path, 'w', encoding='utf-8') as f:
            f.write("BROWSERSTACK CROSS-BROWSER TEST - WORD FREQUENCY ANALYSIS\n\n")
            
            f.write(f"Total Articles Scraped (all browsers): {len(all_articles)}\n")
            f.write(f"Unique Articles (deduplicated): {len(unique_articles)}\n")
            f.write(f"Browsers Tested: {len(browser_summary)}\n\n")
            
            f.write("BROWSER RESULTS:\n")
            for info in browser_summary:
                f.write(f"{info['browser']}: {info['status'].upper()} - {info['articles_scraped']} articles\n")
            
            f.write("\n\nUNIQUE ARTICLE TITLES (deduplicated):\n")
            for idx, article in enumerate(unique_articles, 1):
                browsers = [a['browser'] for a in all_articles if a.get('url') == article.get('url')]
                f.write(f"{idx}. {article['title_en']}\n")
                f.write(f"   Spanish: {article['title']}\n")
                f.write(f"   Browsers: {', '.join(browsers)}\n\n")
            
            f.write("\n\nREPEATED WORDS IN UNIQUE TITLES (appearing more than twice):\n")
            
            if repeated_words:
                sorted_words = sorted(repeated_words.items(), key=lambda x: x[1], reverse=True)
                for word, count in sorted_words:
                    f.write(f"{word}: {count} occurrences\n")
            else:
                f.write("No words repeated more than twice.\n")
        
        print(f"Saved word frequency analysis to {analysis_path}")


def main():
    print("EL PAÍS OPINION SCRAPER - BROWSERSTACK PARALLEL EXECUTION")
    print(f"\nTesting on {len(BROWSER_CONFIGS)} browsers:")
    for config in BROWSER_CONFIGS:
        print(f"  - {config['name']}")
    print()
    
    if not BROWSERSTACK_USERNAME or not BROWSERSTACK_ACCESS_KEY:
        print("ERROR: BrowserStack credentials not found!")
        print("Update .env.browserstack with your credentials")
        return
    
    print("Starting parallel execution...\n")
    start_time = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_browser = {
            executor.submit(run_scraper_on_browser, config, 5): config['name']
            for config in BROWSER_CONFIGS
        }
        
        for future in as_completed(future_to_browser):
            browser_name = future_to_browser[future]
            try:
                result = future.result()
                results.append(result)
                
                if result['status'] == 'success':
                    print(f"\n{browser_name} completed: {result['count']} articles scraped")
                else:
                    print(f"\n{browser_name} failed: {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                print(f"\n{browser_name} exception: {e}")
                results.append({
                    'browser': browser_name,
                    'status': 'failed',
                    'error': str(e),
                    'articles': []
                })
    
    elapsed_time = time.time() - start_time
    
    print("\nPARALLEL EXECUTION SUMMARY")
    print(f"Total time: {elapsed_time:.2f} seconds")
    print(f"Browsers tested: {len(results)}")
    
    successful = sum(1 for r in results if r['status'] == 'success')
    total_articles = sum(r.get('count', 0) for r in results)
    
    print(f"Successful: {successful}/{len(results)}")
    print(f"Total articles scraped: {total_articles}")
    print()
    
    if results:
        save_results(results)
        print("\nAll results saved to 'output_browserstack/' folder")
    
    print("\nView your BrowserStack test results at:")
    print("https://automate.browserstack.com/dashboard")


if __name__ == "__main__":
    main()
