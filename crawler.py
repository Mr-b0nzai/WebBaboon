from typing import Dict, Any, Set
import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumwire import webdriver as seleniumwire_webdriver
from webdriver_manager.chrome import ChromeDriverManager
from config import CHROME_BINARY_PATH, CHROME_OPTIONS, PAGE_LOAD_TIMEOUT, WAIT_TIMEOUT, CRAWL_DELAY
from detector import TechnologyDetector
from utils import get_page_links

class WebBaboonCrawler:
    def __init__(self, url: str, technologies: dict, max_pages: int):
        self.url = url if url.startswith(('http://', 'https://')) else 'https://' + url
        self.technologies = technologies
        self.max_pages = max_pages
        self.visited: Set[str] = set()
        self.to_visit: Set[str] = {self.url}
        self.all_detections: Dict[str, Any] = {}
        self.driver = None

    def setup_driver(self):
        """Set up and configure the Chrome WebDriver."""
        options = Options()
        options.binary_location = CHROME_BINARY_PATH
        for option in CHROME_OPTIONS:
            options.add_argument(option)
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        service = Service(ChromeDriverManager().install())
        self.driver = seleniumwire_webdriver.Chrome(service=service, options=options)

    def process_page(self, url: str) -> None:
        """Process a single page and detect technologies."""
        print(f"Analyzing: {url}")
        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            print(f"Error loading {url}: {e}")
            return

        detector = TechnologyDetector(self.driver, self.technologies)
        detected = detector.detect_all()
        
        # Update all_detections with new findings
        for tech, data in detected.items():
            if tech not in self.all_detections:
                self.all_detections[tech] = {
                    'signatures': set(tuple(sorted(sig.items())) for sig in data['signatures'])
                }
            else:
                self.all_detections[tech]['signatures'].update(
                    tuple(sorted(sig.items())) for sig in data['signatures']
                )

        # Get new links to visit
        links = get_page_links(self.driver, self.url)
        self.to_visit.update(links - self.visited)

    def crawl(self) -> Dict[str, Any]:
        """Crawl the website and detect technologies."""
        try:
            self.setup_driver()
            
            while self.to_visit and len(self.visited) < self.max_pages:
                current_url = self.to_visit.pop()
                if current_url in self.visited:
                    continue

                self.process_page(current_url)
                self.visited.add(current_url)
                time.sleep(CRAWL_DELAY)

        except Exception as e:
            print(f"Error during crawling: {e}")
        finally:
            if self.driver:
                self.driver.quit()

        # Convert sets back to lists for JSON serialization
        for tech in self.all_detections:
            self.all_detections[tech]['signatures'] = [
                dict(sig) for sig in self.all_detections[tech]['signatures']
            ]

        return self.all_detections 