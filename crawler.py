from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Set, List
import threading
import time
from queue import Queue
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
from performance import timing_decorator

class WebBaboonCrawler:
    def __init__(self, urls_to_analyze: List[str], technologies: dict, max_depth: int, 
                 dynamic_only: bool = False, max_workers: int = 4):
        """
        Initialize the crawler with URLs to analyze and technology signatures.
        
        Args:
            urls_to_analyze: List of URLs to analyze with browser
            technologies: Dictionary of technology signatures
            max_depth: Maximum number of pages to crawl
            dynamic_only: If True, only perform dynamic analysis (DOM, XHR, network)
            max_workers: Maximum number of concurrent browser instances
        """
        self.pending_urls = urls_to_analyze
        self.technologies = technologies
        self.max_depth = max_depth
        self.dynamic_only = dynamic_only
        self.visited: Set[str] = set()
        self.all_detections: Dict[str, Any] = {}
        self.max_workers = max_workers
        self.drivers = {}  # Store WebDriver instances per thread
        self.results_lock = threading.Lock()
        self.start_time = None

    def setup_driver(self):
        """Set up and configure the Chrome WebDriver for the current thread."""
        thread_id = threading.get_ident()
        if thread_id not in self.drivers:
            options = Options()
            options.binary_location = CHROME_BINARY_PATH
            for option in CHROME_OPTIONS:
                options.add_argument(option)
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

            # Configure seleniumwire to capture all network traffic
            seleniumwire_options = {
                'enable_har': True,  # Enable HAR format for request logging
                'ignore_http_methods': ['OPTIONS'],  # Ignore OPTIONS requests
                'detect_proxy': False  # Disable proxy detection for better performance
            }

            service = Service(ChromeDriverManager().install())
            driver = seleniumwire_webdriver.Chrome(
                service=service, 
                options=options,
                seleniumwire_options=seleniumwire_options
            )

            # Inject XHR monitoring script
            xhr_monitor_script = """
                window._xhrRequests = [];
                var originalXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function() {
                    var xhr = new originalXHR();
                    var open = xhr.open;
                    xhr.open = function() {
                        window._xhrRequests.push({
                            method: arguments[0],
                            url: arguments[1]
                        });
                        return open.apply(xhr, arguments);
                    };
                    return xhr;
                };
            """
            
            driver.get("about:blank")  # Load blank page to inject script
            driver.execute_script(xhr_monitor_script)
            
            self.drivers[thread_id] = driver
        return self.drivers[thread_id]

    def cleanup_drivers(self):
        """Clean up all WebDriver instances."""
        for driver in self.drivers.values():
            try:
                # Clear requests and close any open windows
                del driver.requests
                driver.quit()
            except Exception as e:
                print(f"Error cleaning up driver: {e}")

    def cleanup(self):
        """Clean up all resources."""
        try:
            self.cleanup_drivers()
            print("\nCleaned up browser resources.")
        except Exception as e:
            print(f"\nError during cleanup: {e}")

    def wait_for_network_idle(self, driver, timeout=5, max_connections=0, poll_interval=0.5):
        """Wait for network requests to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            active_requests = len([r for r in driver.requests if not r.response])
            if active_requests <= max_connections:
                return True
            time.sleep(poll_interval)
        return False

    @timing_decorator
    def process_page(self, url: str) -> Dict[str, Any]:
        """Process a single page and return its detected technologies."""
        print(f"Analyzing dynamic content: {url}")
        driver = self.setup_driver()
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        try:
            # Clear previous requests
            del driver.requests
            
            # Load the page and wait for initial content
            driver.get(url)
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait for network activity to settle
            self.wait_for_network_idle(driver)
            
            # Create detector with dynamic-only mode and run detection
            # In hybrid mode (efficiency=2), we only want dynamic checks since static checks were done by EfficientCrawler
            detector = TechnologyDetector(driver, self.technologies, dynamic_only=True)
            detected = detector.detect_all()
            
            return detected

        except Exception as e:
            print(f"Error analyzing {url}: {e}")
            return {}
        finally:
            try:
                # Clear requests to free memory
                del driver.requests
            except:
                pass

    @timing_decorator
    def parallel_process_urls(self, urls: List[str]) -> List[tuple]:
        """Process multiple URLs in parallel using thread pool."""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all URLs for processing
            future_to_url = {
                executor.submit(self.process_page, url): url 
                for url in urls
            }
            
            # Process completed tasks as they finish
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append((url, result))
                except Exception as e:
                    print(f"Error processing results for {url}: {e}")
                    results.append((url, {}))
        
        return results

    @timing_decorator
    def crawl(self) -> Dict[str, Any]:
        """
        Start crawling the URLs and detect technologies.
        Returns a dictionary of detected technologies.
        """
        self.start_time = time.time()  # Record start time

        try:
            # Process URLs in parallel batches
            results = self.parallel_process_urls(self.pending_urls)
            
            # Merge results
            for url, detected in results:
                self.update_detections(url, detected)
                self.visited.add(url)

        except Exception as e:
            print(f"Error during crawling: {e}")
        finally:
            self.cleanup_drivers()

        # Convert sets back to lists for JSON serialization
        for tech in self.all_detections:
            self.all_detections[tech]['signatures'] = [
                dict(sig) for sig in self.all_detections[tech]['signatures']
            ]

        # Calculate actual execution time
        end_time = time.time()
        elapsed_time = end_time - self.start_time
        print(f"\nActual crawl time: {elapsed_time:.2f} seconds")

        return self.all_detections

    @timing_decorator
    def update_detections(self, url: str, detected: Dict[str, Any]) -> None:
        """Thread-safe update of detection results."""
        with self.results_lock:
            try:
                for tech, data in detected.items():
                    if tech == '_analysis':  # Skip analysis data
                        continue
                    if 'signatures' not in data:  # Skip invalid data
                        continue
                        
                    if tech not in self.all_detections:
                        self.all_detections[tech] = {
                            'signatures': []
                        }
                    
                    # Convert any tuples back to dictionaries and ensure no duplicates
                    existing_sigs = {
                        tuple(sorted(sig.items())) 
                        for sig in self.all_detections[tech]['signatures']
                    }
                    
                    for sig in data['signatures']:
                        if isinstance(sig, tuple):
                            sig = dict(sig)
                        sig_tuple = tuple(sorted(sig.items()))
                        if sig_tuple not in existing_sigs:
                            self.all_detections[tech]['signatures'].append(sig)
                            existing_sigs.add(sig_tuple)
            except Exception as e:
                print(f"Error updating detections for {url}: {e}")