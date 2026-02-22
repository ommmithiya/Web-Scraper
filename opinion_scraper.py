"""
El País Opinion Section Scraper
Scrapes articles from the Opinion section with all images
"""

import time
import json
import os
import shutil
import requests
import re
from collections import Counter
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class OpinionScraper:
    """Web scraper for El País Opinion section"""
    
    def __init__(self, headless=True):
        """
        Initialize the scraper
        
        Args:
            headless (bool): Run browser in headless mode (without GUI)
        """
        self.url = "https://elpais.com"
        self.driver = None
        self.headless = headless
        self.articles_data = []
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--lang=es-ES,es")
        chrome_options.add_experimental_option("prefs", {
            "intl.accept_languages": "es-ES,es"
        })
        
        print("Setting up Chrome WebDriver...")
        print("Downloading/updating ChromeDriver...")
        
        try:
            driver_path = ChromeDriverManager().install()
            
            if not driver_path.endswith('.exe'):
                driver_dir = os.path.dirname(driver_path)
                for file in os.listdir(driver_dir):
                    if file.endswith('.exe') and 'chromedriver' in file.lower():
                        driver_path = os.path.join(driver_dir, file)
                        break
            
            print(f"ChromeDriver path: {driver_path}")
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            raise
    
    def accept_cookies(self):
        """Handle cookie consent banner"""
        print("Looking for cookie consent banner...")
        
        cookie_selectors = [
            "//button[contains(., 'Aceptar')]",
            "//button[contains(., 'ACEPTAR')]",
            "//button[contains(@id, 'accept')]",
            "//button[contains(@id, 'cookie')]",
            "button[id*='accept']",
            "button[class*='accept']",
            ".didomi-button",
            "#didomi-notice-agree-button"
        ]
        
        for selector in cookie_selectors:
            try:
                if selector.startswith("//"):
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                button.click()
                print(f"Found cookie button using selector: {selector}")
                time.sleep(1)
                print("Cookie consent accepted")
                return
            except:
                continue
        
        print("No cookie banner found (or already accepted)")
    
    def verify_spanish_language(self):
        """Verify that the website is displaying content in Spanish"""
        try:
            html_lang = self.driver.find_element(By.TAG_NAME, "html").get_attribute("lang")
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            spanish_keywords = ["opinión", "noticias", "portada", "últimas"]
            spanish_detected = any(keyword in page_text for keyword in spanish_keywords)
            
            print(f"Website language: {html_lang}")
            
            if spanish_detected:
                print(f"Spanish content detected: {', '.join([k for k in spanish_keywords if k in page_text])}")
            else:
                print("Warning: Spanish keywords not detected in page content")
                
        except Exception as e:
            print(f"Could not verify language: {e}")
    
    def translate_text(self, text, source='es', target='en'):
        """
        Translate text from source language to target language using RapidAPI
        
        Args:
            text (str): Text to translate
            source (str): Source language code (default: 'es' for Spanish)
            target (str): Target language code (default: 'en' for English)
            
        Returns:
            str: Translated text or original text if translation fails
        """
        try:
            url = "https://google-translate113.p.rapidapi.com/api/v1/translator/text"
            
            headers = {
                "X-RapidAPI-Key": "d4cd034963msh7ddea756906b71ap154cf2jsnb8919e5bbd81",
                "X-RapidAPI-Host": "google-translate113.p.rapidapi.com",
                "Content-Type": "application/json"
            }
            
            payload = {
                "from": source,
                "to": target,
                "text": text
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                # The API typically returns translated text in 'trans' field
                if 'trans' in result:
                    return result['trans']
                elif 'translation' in result:
                    return result['translation']
                else:
                    # If structure is different, try to get the first value
                    return result.get('trans', result.get('translation', text))
            else:
                print(f"Translation API error: {response.status_code}")
                return text
                
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    def download_image(self, image_url, filename, folder="output"):
        """
        Download an image from URL and save it locally
        
        Args:
            image_url (str): URL of the image
            filename (str): Name to save the image as
            folder (str): Folder to save images in
        
        Returns:
            str: Path to saved image or None
        """
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                filepath = os.path.join(folder, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath
            else:
                return None
        except Exception as e:
            return None
    
    def scrape_full_article(self, url):
        """
        Navigate to article page and extract full content + metadata
        
        Args:
            url (str): Article URL
            
        Returns:
            dict: Article content including title, author, full text and images
        """
        article_content = {
            'title': 'N/A',
            'author': 'N/A',
            'full_article_text': 'N/A',
            'article_images': []
        }
        
        try:
            print(f"  → Opening article page...")
            self.driver.get(url)
            time.sleep(3)
            
            # Extract title from article page
            title_selectors = ['h1', 'h2.headline', '.article-title', 'header h1', '[itemprop="headline"]']
            for selector in title_selectors:
                try:
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title and len(title) >= 3:
                        article_content['title'] = title
                        print(f"  Title: {title[:60]}...")
                        break
                except:
                    continue
            
            # Extract author from article page
            author_selectors = ['.author', '.byline', 'address', '[itemprop="author"]', '.firma', '.signature']
            for selector in author_selectors:
                try:
                    author_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip()
                    if author:
                        article_content['author'] = author
                        print(f"  Author: {author}")
                        break
                except:
                    continue
            
            # Extract all text from article body
            text_selectors = [
                'article', '.article-body', '.article-content', 
                '[data-dtm-region*="articulo"]', '.c-d', 'main'
            ]
            
            for selector in text_selectors:
                try:
                    article_body = self.driver.find_element(By.CSS_SELECTOR, selector)
                    full_text = article_body.text.strip()
                    if full_text and len(full_text) > 100:
                        article_content['full_article_text'] = full_text
                        print(f"  Extracted {len(full_text)} characters of full text")
                        break
                except:
                    continue
            
            # Extract all images from article page
            try:
                img_elements = self.driver.find_elements(By.TAG_NAME, "img")
                
                for img in img_elements:
                    try:
                        img_url = None
                        for attr in ['src', 'data-src', 'data-lazy-src', 'currentSrc', 'srcset']:
                            img_url = img.get_attribute(attr)
                            if img_url:
                                if 'srcset' in attr:
                                    urls = [u.strip().split()[0] for u in img_url.split(',') if u.strip()]
                                    img_url = urls[-1] if urls else None
                                if img_url and img_url.startswith('http'):
                                    break
                        
                        if img_url and img_url.startswith('http'):
                            article_content['article_images'].append(img_url)
                    except:
                        continue
                
                if article_content['article_images']:
                    print(f"  Found {len(article_content['article_images'])} images")
            except:
                pass
            
        except Exception as e:
            print(f"  Error loading article: {e}")
        
        return article_content
    
    def scrape_opinion_section(self, max_articles=5):  # Scrape first 5 articles
        """
        Scrape articles from Opinion section with deep content extraction
        
        Args:
            max_articles (int): Maximum number of articles to scrape deeply (default: 5)
        
        Note: Clicks into each article to extract full content.
        """
        try:
            opinion_url = "https://elpais.com/opinion/"
            print(f"\nNavigating to Opinion section...")
            self.driver.get(opinion_url)
            time.sleep(5)  # Increased wait time
            
            print(f"Opinion section loaded")
            
            # Wait for articles to load
            print(f"Waiting for articles to load...")
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "article"))
                )
            except:
                print("Main selector failed, trying alternative...")
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article, [data-dtm-region], .article"))
                )
            
            # Scroll thoroughly to load all lazy content
            print(f"Scrolling to load all content...")
            # First scroll all the way down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Then scroll back up slowly
            for i in range(5, 0, -1):
                scroll_position = i * (self.driver.execute_script("return document.body.scrollHeight") // 6)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                time.sleep(0.5)
            
            # Finally back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Find all article elements
            articles = self.driver.find_elements(By.TAG_NAME, "article")
            print(f"Found {len(articles)} article elements on page")
            
            if len(articles) == 0:
                print("No articles found, trying alternative selectors...")
                articles = self.driver.find_elements(By.CSS_SELECTOR, "[data-dtm-region*='articulo']")
            
            print(f"\n{'='*80}")
            print("OPINION SECTION ARTICLES")
            print(f"{'='*80}\n")
            
            # First pass: Collect all article URLs to avoid stale element issues
            print("Collecting article URLs...")
            article_urls_list = []
            for idx, article in enumerate(articles):
                try:
                    # Find the main article link (usually the title link)
                    links = article.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        url = link.get_attribute("href")
                        link_text = link.text.strip()
                        
                        # Only accept URLs that look like actual articles:
                        # - Must contain /opinion/
                        # - Must have a date pattern /YYYY-MM-DD/ OR end with .html
                        # - Must NOT be a category page (ending with /)
                        if url and url.startswith("http") and "/opinion/" in url:
                            # Check if it's an actual article (has date or .html)
                            import re
                            has_date = re.search(r'/\d{4}-\d{2}-\d{2}/', url)
                            has_html = url.endswith('.html')
                            is_category = url.endswith('/')
                            
                            # Only add if it looks like an article with meaningful text
                            if (has_date or has_html) and not is_category and link_text and len(link_text) >= 10:
                                article_urls_list.append(url)
                                break
                except:
                    continue
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in article_urls_list:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            # Limit to max_articles
            unique_urls = unique_urls[:max_articles]
            
            print(f"Found {len(unique_urls)} unique articles to scrape\n")
            
            # Second pass: Process each article by navigating to its URL
            article_count = 0
            
            for idx, article_url in enumerate(unique_urls):
                try:
                    article_count += 1
                    print(f"\n{'='*80}")
                    print(f"Article #{article_count} of {len(unique_urls)}")
                    print(f"{'='*80}")
                    print(f"URL: {article_url}")
                    
                    # Navigate to article and extract all content
                    full_content = self.scrape_full_article(article_url)
                    
                    # Translate title to English
                    title_spanish = full_content['title']
                    title_english = self.translate_text(title_spanish, source='es', target='en')
                    
                    article_data = {
                        'title': title_spanish,
                        'title_en': title_english,
                        'author': full_content['author'],
                        'url': article_url,
                        'full_article_text': full_content['full_article_text'],
                        'article_images': full_content['article_images']
                    }
                    
                    # Download images from article page
                    images_downloaded = []
                    for img_idx, img_url in enumerate(full_content['article_images'], 1):
                        safe_filename = f"opinion_{article_count}_img_{img_idx}.jpg"
                        saved_path = self.download_image(img_url, safe_filename)
                        if saved_path:
                            images_downloaded.append(saved_path)
                    
                    # Print summary
                    print(f"\nCompleted Article #{article_count}")
                    print(f"  Title (ES): {article_data['title'][:80]}")
                    print(f"  Title (EN): {article_data['title_en'][:80]}")
                    print(f"  Author: {article_data['author']}")
                    if article_data['full_article_text'] != 'N/A':
                        print(f"  Full text: {len(article_data['full_article_text'])} characters")
                    if images_downloaded:
                        print(f"  Images: {len(images_downloaded)} downloaded")
                    
                    self.articles_data.append(article_data)
                    
                except Exception as e:
                    print(f"  Error processing article: {e}")
                    continue
            
            print(f"\n{'='*80}")
            print(f"Total de artículos de Opinión extraídos: {article_count}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"\nError scraping opinion section: {e}")
            import traceback
            traceback.print_exc()
    
    def save_to_json(self, filename="opinion_articles.json", folder="output"):
        """Save scraped articles to JSON file"""
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            filepath = os.path.join(folder, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.articles_data, f, ensure_ascii=False, indent=2)
            print(f"\nData saved to {filepath}")
        except Exception as e:
            print(f"\nError saving to JSON: {e}")
    
    def save_to_text(self, filename="opinion_articles.txt", folder="output"):
        """Save scraped articles to text file"""
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            filepath = os.path.join(folder, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("EL PAÍS - OPINION SECTION ARTICLES\n")
                f.write("="*80 + "\n\n")
                
                for idx, article in enumerate(self.articles_data, 1):
                    f.write(f"{'='*80}\n")
                    f.write(f"ARTICLE #{idx}\n")
                    f.write(f"{'='*80}\n\n")
                    
                    f.write(f"Título (ES): {article.get('title', 'N/A')}\n\n")
                    f.write(f"Title (EN): {article.get('title_en', 'N/A')}\n\n")
                    f.write(f"Autor: {article.get('author', 'N/A')}\n\n")
                    f.write(f"URL: {article.get('url', 'N/A')}\n\n")
                    
                    # Full article text from deep scraping
                    if article.get('full_article_text') and article.get('full_article_text') != 'N/A':
                        f.write(f"TEXTO COMPLETO DEL ARTÍCULO:\n")
                        f.write(f"{'-'*80}\n")
                        f.write(f"{article.get('full_article_text')}\n")
                        f.write(f"{'-'*80}\n\n")
                    
                    # Article images info
                    total_images = len(article.get('article_images', []))
                    if total_images > 0:
                        f.write(f"Imágenes: {total_images} imagen(es) descargada(s)\n\n")
                    else:
                        f.write("Imágenes: Ninguna\n\n")
                    
                    f.write("-"*80 + "\n\n")
                
                f.write("\n" + "="*80 + "\n")
                f.write(f"TOTAL: {len(self.articles_data)} artículos extraídos\n")
                f.write("="*80 + "\n")
            
            print(f"Text data saved to {filepath}")
        except Exception as e:
            print(f"Error saving to text file: {e}")
    
    def analyze_word_frequency(self):
        """Analyze word frequency in translated titles"""
        # Combine all translated titles
        all_titles = " ".join([article['title_en'] for article in self.articles_data])
        
        # Clean and split into words (remove punctuation, lowercase)
        words = re.findall(r'\b[a-zA-Z]+\b', all_titles.lower())
        
        # Count word occurrences
        word_counts = Counter(words)
        
        # Filter words that appear more than twice
        repeated_words = {word: count for word, count in word_counts.items() if count > 2}
        
        return repeated_words
    
    def save_translated_output(self, folder="output_translated"):
        """Save translated articles and analysis to separate folder"""
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
            
            # Save translated articles to JSON
            translated_data = []
            for article in self.articles_data:
                translated_data.append({
                    "title_spanish": article['title'],
                    "title_english": article['title_en'],
                    "author": article['author'],
                    "url": article['url'],
                    "full_article_text": article['full_article_text'],
                    "article_images": article['article_images']
                })
            
            json_filepath = os.path.join(folder, "translated_articles.json")
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(translated_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ Translated JSON saved to {json_filepath}")
            
            # Analyze word frequency
            repeated_words = self.analyze_word_frequency()
            
            # Save analysis to text file
            analysis_filepath = os.path.join(folder, "word_frequency_analysis.txt")
            with open(analysis_filepath, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("TRANSLATED ARTICLE HEADERS - WORD FREQUENCY ANALYSIS\n")
                f.write("="*80 + "\n\n")
                
                f.write("TRANSLATED HEADERS:\n")
                f.write("-"*80 + "\n")
                for idx, article in enumerate(self.articles_data, 1):
                    f.write(f"{idx}. {article['title_en']}\n")
                
                f.write("\n" + "="*80 + "\n\n")
                f.write("REPEATED WORDS (appearing more than twice):\n")
                f.write("-"*80 + "\n")
                
                if repeated_words:
                    # Sort by count (descending)
                    sorted_words = sorted(repeated_words.items(), key=lambda x: x[1], reverse=True)
                    for word, count in sorted_words:
                        f.write(f"{word}: {count} occurrences\n")
                else:
                    f.write("No words repeated more than twice.\n")
                
                f.write("\n" + "="*80 + "\n")
            
            print(f"✓ Word frequency analysis saved to {analysis_filepath}")
            
            # Print analysis to console
            print("\n" + "="*80)
            print("WORD FREQUENCY ANALYSIS")
            print("="*80)
            print("\nTranslated Headers:")
            for idx, article in enumerate(self.articles_data, 1):
                print(f"{idx}. {article['title_en']}")
            
            print("\nRepeated Words (more than twice):")
            if repeated_words:
                sorted_words = sorted(repeated_words.items(), key=lambda x: x[1], reverse=True)
                for word, count in sorted_words:
                    print(f"  {word}: {count} occurrences")
            else:
                print("  No words repeated more than twice.")
            print("="*80)
            
        except Exception as e:
            print(f"\nError saving translated output: {e}")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()


def cleanup_previous_output():
    """Delete previous output folders"""
    print("Cleaning up previous output...")
    try:
        for folder_name in ["output", "output_translated"]:
            if os.path.exists(folder_name):
                try:
                    shutil.rmtree(folder_name)
                    print(f"Deleted previous '{folder_name}' folder")
                except PermissionError:
                    for file in os.listdir(folder_name):
                        try:
                            os.remove(os.path.join(folder_name, file))
                        except:
                            pass
                    try:
                        os.rmdir(folder_name)
                        print(f"Deleted previous '{folder_name}' folder")
                    except:
                        print(f"Could not delete '{folder_name}' folder (may be in use)")
        
        print()
    except Exception as e:
        print(f"Error during cleanup: {e}\n")


def main():
    print("""
    EL PAÍS - OPINION SECTION SCRAPER
    
    This script will:
    - Clean up previous output files
    - Navigate to the Opinion section
    - Click into the first 5 opinion articles
    - Extract full article text, title, author, and images from each
    - Download all images and save JSON/TXT to 'output/' folder
    """)
    
    scraper = None
    
    try:
        # Cleanup previous output
        cleanup_previous_output()
        
        # Initialize scraper
        scraper = OpinionScraper(headless=False)
        scraper.setup_driver()
        
        # Navigate to El País homepage first
        print(f"\nNavigating to El País...")
        scraper.driver.get(scraper.url)
        time.sleep(2)
        
        # Accept cookies
        print("\nHandling cookies...")
        scraper.accept_cookies()
        
        # Verify Spanish language
        print("\nVerifying Spanish language...")
        scraper.verify_spanish_language()
        
        # Scrape Opinion section
        scraper.scrape_opinion_section(max_articles=5)
        
        # Save to JSON and text files
        if scraper.articles_data:
            scraper.save_to_json("opinion_articles.json", folder="output")
            scraper.save_to_text("opinion_articles.txt", folder="output")
            
            # Save translated output and analysis
            print("\nGenerating translated output and word frequency analysis...")
            scraper.save_translated_output(folder="output_translated")
            
            # Count ALL successful images
            total_images = 0
            for article in scraper.articles_data:
                if 'images' in article:
                    total_images += sum(1 for img in article['images'] if img.get('saved_path'))
            
            print(f"\n{'='*80}")
            print("FINAL SUMMARY")
            print(f"{'='*80}")
            print(f"Scraped {len(scraper.articles_data)} articles from Opinion section")
            print(f"Downloaded {total_images} image(s) total across all articles")
            print(f"\nAll files saved to 'output/' folder:")
            print(f"  - opinion_articles.json (JSON format)")
            print(f"  - opinion_articles.txt (Text format)")
            print(f"  - {total_images} image file(s)")
            print(f"\nTranslated output saved to 'output_translated/' folder:")
            print(f"  - translated_articles.json (JSON format with translations)")
            print(f"  - word_frequency_analysis.txt (Word frequency analysis)")
            print(f"{'='*80}\n")
        else:
            print("\nNo articles were scraped")
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if scraper and scraper.driver:
            print("\nClosing browser in 3 seconds...")
            time.sleep(3)
            scraper.driver.quit()
            print("Browser closed")


if __name__ == "__main__":
    main()
