import subprocess
import os
import tempfile
import threading
import time
import requests
import re
import hashlib
from typing import Dict, Any, Set, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from utils import get_page_links
from performance import timing_decorator, print_metrics, reset_metrics

# Thread-local storage for BeautifulSoup objects and other reusable data
thread_local = threading.local()

def init_thread_local():
    """Initialize thread-local storage with default values."""
    if not hasattr(thread_local, 'initialized'):
        thread_local.soup = None
        thread_local.cache = {}  # Cache for frequently accessed data
        thread_local.initialized = True

def get_soup():
    """Get thread-local BeautifulSoup instance."""
    init_thread_local()
    return thread_local.soup

def set_soup(html_content):
    """Set thread-local BeautifulSoup instance."""
    init_thread_local()
    thread_local.soup = BeautifulSoup(html_content, 'html.parser')
    
def clear_thread_local():
    """Clear thread-local storage to prevent memory leaks."""
    if hasattr(thread_local, 'initialized'):
        thread_local.soup = None
        thread_local.cache.clear()
        thread_local.initialized = False

class EfficientDetector:
    """
    A lightweight version of the TechnologyDetector that analyzes static HTML and HTTP responses
    without using a browser.
    """
    def __init__(self, html_content: str, technologies: dict, headers: dict = None, cookies: dict = None):
        self.html_content = html_content
        self.technologies = technologies
        self.headers = headers or {}
        self.cookies = cookies or {}

    @timing_decorator
    def check_html(self, tech: dict) -> list:
        """Check HTML content and meta tags for technology signatures."""
        matched_signatures = []
        
        # Search for regex patterns in the HTML content
        if 'html' in tech:
            for pattern in tech['html']:
                if re.search(pattern, self.html_content, re.IGNORECASE):
                    matched_signatures.append({'type': 'html', 'detail': pattern})
        
        # Search for meta tag patterns
        if 'meta' in tech:
            soup = get_soup()
            if not soup:
                soup = BeautifulSoup(self.html_content, 'html.parser')
                set_soup(self.html_content)
            
            for meta_name, pattern in tech['meta'].items():
                meta_tags = soup.find_all('meta', {'name': meta_name})
                for meta in meta_tags:
                    if 'content' in meta.attrs and re.search(pattern, meta['content'], re.IGNORECASE):
                        matched_signatures.append({'type': 'meta', 'detail': f"{meta_name}: {pattern}"})
        
        return matched_signatures

    @timing_decorator
    def check_cookies(self, tech: dict) -> list:
        """Check cookies for technology signatures."""
        matched_signatures = []
        if 'cookies' in tech:
            for cookie_name, pattern in tech['cookies'].items():
                for cookie_key, cookie_value in self.cookies.items():
                    if re.search(cookie_name, cookie_key, re.IGNORECASE):
                        if pattern == "" or re.search(pattern, cookie_value, re.IGNORECASE):
                            matched_signatures.append({'type': 'cookies', 'detail': cookie_name})
        return matched_signatures

    @timing_decorator
    def check_headers(self, tech: dict) -> list:
        """Check HTTP headers for technology signatures."""
        matched_signatures = []
        if 'headers' in tech:
            for header_key, header_value in tech['headers'].items():
                if header_key in self.headers:
                    if header_value == "" or re.search(header_value, self.headers[header_key], re.IGNORECASE):
                        matched_signatures.append({'type': 'headers', 'detail': f"{header_key}: {header_value}"})
        return matched_signatures

    @timing_decorator
    def check_script_src(self, tech: dict) -> list:
        """Check <script> tag src attributes for technology signatures."""
        if 'scriptSrc' not in tech:
            return []
            
        soup = get_soup()
        if not soup:
            soup = BeautifulSoup(self.html_content, 'html.parser')
            set_soup(self.html_content)
            
        scripts = soup.find_all('script', src=True)
        matched = []
        
        for pattern in tech['scriptSrc']:
            for script in scripts:
                src = script['src']
                if re.search(pattern, src, re.IGNORECASE):
                    matched.append({'type': 'scriptSrc', 'detail': pattern})
                    break
        
        return matched

    def detect_tech(self, tech_item: tuple) -> tuple:
        """Detect a single technology. Returns tuple of (tech_name, signatures)."""
        tech_name, tech_data = tech_item
        matched_signatures = []
        matched_signatures.extend(self.check_html(tech_data))
        matched_signatures.extend(self.check_cookies(tech_data))
        matched_signatures.extend(self.check_headers(tech_data))
        matched_signatures.extend(self.check_script_src(tech_data))
        
        if matched_signatures:
            return (tech_name, {'signatures': matched_signatures})
        return None

    @timing_decorator
    def detect_all(self) -> Dict[str, Any]:
        """
        Detect technologies using static analysis methods with parallel processing.
        Returns a dictionary of detected technologies and their matched signatures.
        """
        detected_techs = {}
        
        # Use ThreadPoolExecutor for parallel technology detection
        with ThreadPoolExecutor(max_workers=min(32, len(self.technologies))) as executor:
            # Submit all technology detection tasks
            future_to_tech = {
                executor.submit(self.detect_tech, (tech_name, tech_data)): tech_name 
                for tech_name, tech_data in self.technologies.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_tech):
                result = future.result()
                if result:
                    tech_name, data = result
                    detected_techs[tech_name] = data

        return detected_techs

class EfficientCrawler:
    def __init__(self, url: str, technologies: dict, max_depth: int):
        """Initialize the efficient crawler with URL and technology signatures."""
        self.url = url if url.startswith(('http://', 'https://')) else 'https://' + url
        self.technologies = technologies
        self.max_depth = max_depth
        self.visited: Set[str] = set()  # URLs that have been visited
        self.requested_urls: Set[str] = set()  # URLs that were actually requested
        self.to_visit: Set[str] = {self.url}
        self.all_detections: Dict[str, Any] = {}
        self.temp_dir = None
        try:
            self.temp_dir = tempfile.mkdtemp(prefix='webbaboon_')
            print(f"Created temporary directory: {self.temp_dir}")
        except Exception as e:
            print(f"Error creating temporary directory: {e}")
            self.temp_dir = None

    def cleanup(self):
        """Clean up temporary files, directory, and thread-local storage."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # Clean up temporary files
                for filename in os.listdir(self.temp_dir):
                    filepath = os.path.join(self.temp_dir, filename)
                    try:
                        if os.path.exists(filepath):
                            os.unlink(filepath)
                    except Exception as e:
                        print(f"Error deleting temporary file {filepath}: {e}")
                
                # Remove directory only if it still exists
                if os.path.exists(self.temp_dir):
                    os.rmdir(self.temp_dir)
                    print(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                print(f"Warning: Error during cleanup of {self.temp_dir}: {e}")
        
        # Clean up thread-local storage regardless of temp dir status
        clear_thread_local()

    def extract_urls_from_response(self, html_content: str, base_url: str) -> Set[str]:
        """Extract all URLs from HTML content and response."""
        urls = set()
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract URLs from various HTML elements
            for tag in soup.find_all(['a', 'script', 'link', 'img', 'iframe']):
                href = tag.get('href') or tag.get('src')
                if href:
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, href)
                    if absolute_url.startswith(('http://', 'https://')):
                        urls.add(absolute_url)
                        
        except Exception as e:
            print(f"Error extracting URLs from {base_url}: {e}")
        
        return urls

    @timing_decorator
    def process_page(self, url: str) -> None:
        """Process a single page using curl and static analysis."""
        print(f"Analyzing: {url}")
        
        try:
            # Create a unique filename for this URL in the temp directory
            url_hash = hashlib.md5(url.encode()).hexdigest()
            output_file = os.path.join(self.temp_dir, f"{url_hash}.html")
            headers_file = os.path.join(self.temp_dir, f"{url_hash}.headers")
            
            # Use curl to fetch the page with headers
            curl_cmd = [
                'curl',
                '-L',  # Follow redirects
                '-s',  # Silent mode
                '-k',  # Allow insecure connections
                '-D', headers_file,  # Save headers to file
                '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',  # User agent
                '-o', output_file,  # Save response body to file
                url
            ]
            
            # Run curl command
            subprocess.run(curl_cmd, check=True)
            
            # Read the response headers
            with open(headers_file, 'r', encoding='utf-8', errors='ignore') as f:
                headers_text = f.read()
            headers = {}
            for line in headers_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            # Read the response body
            with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            # Parse cookies from headers
            cookies = {}
            if 'Set-Cookie' in headers:
                cookie_headers = headers['Set-Cookie'].split(', ')
                for cookie in cookie_headers:
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        cookies[name] = value.split(';')[0]
            
            # Create detector and run analysis
            detector = EfficientDetector(html_content, self.technologies, headers, cookies)
            detected = detector.detect_all()
            
            # Update detections
            if detected:
                with threading.Lock():
                    for tech, data in detected.items():
                        if tech in self.all_detections:
                            self.all_detections[tech]['signatures'].extend(data['signatures'])
                        else:
                            self.all_detections[tech] = data
            
            # Extract and queue new URLs to visit
            if self.max_depth > 0:
                new_urls = self.extract_urls_from_response(html_content, url)
                base_domain = urlparse(self.url).netloc
                for new_url in new_urls:
                    if urlparse(new_url).netloc == base_domain and new_url not in self.visited:
                        self.to_visit.add(new_url)
            
            # Mark URL as visited and requested
            self.visited.add(url)
            self.requested_urls.add(url)
                    
        except subprocess.CalledProcessError as e:
            print(f"Curl error for {url}: {e}")
        except Exception as e:
            print(f"Error processing {url}: {e}")
            
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
                if os.path.exists(headers_file):
                    os.remove(headers_file)
            except Exception as e:
                print(f"Error cleaning up temporary files: {e}")

    @timing_decorator
    def crawl(self) -> Dict[str, Any]:
        """
        Crawl the website using curl and static analysis.
        Returns a dictionary of detected technologies.
        """
        try:
            # Continue crawling until there are no more URLs or max_depth is reached
            while self.to_visit and len(self.visited) < self.max_depth:
                current_url = self.to_visit.pop()
                if current_url in self.visited:
                    continue

                self.process_page(current_url)
                self.visited.add(current_url)

        except Exception as e:
            print(f"Error during crawling: {e}")
        finally:
            # Always clean up temporary files
            self.cleanup()

        # Convert sets back to lists for JSON serialization
        for tech in self.all_detections:
            self.all_detections[tech]['signatures'] = [
                dict(sig) for sig in self.all_detections[tech]['signatures']
            ]

        return self.all_detections
