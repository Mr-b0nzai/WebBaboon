from typing import Dict, List, Any, Optional
import re
import time
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from utils import check_dom_conditions, process_var_name
from performance import timing_decorator, metrics, metrics_lock

class TechnologyDetector:
    """
    Detects web technologies present on a page using various heuristics:
    HTML content, meta tags, cookies, headers, network requests, DOM, script sources, XHR, and JavaScript variables.
    """
    def __init__(self, driver: WebDriver, technologies: dict, dynamic_only: bool = False):
        # Initialize with Selenium WebDriver and a dictionary of technology signatures
        self.driver = driver
        self.technologies = technologies
        self.dynamic_only = dynamic_only
        
        # Always get requests for dynamic checks
        self.all_requests = list(driver.requests)
        
        # Only get static content if not in dynamic-only mode
        if not dynamic_only:
            self.html_content = driver.page_source  # Get the page's HTML source
            self.cookies = driver.get_cookies()     # Get cookies from the browser
            # Find the main request and get its headers
            main_request = next((r for r in self.all_requests if r.url == driver.current_url), None)
            self.headers = main_request.response.headers if main_request and main_request.response else {}
        else:
            # Initialize empty values for static content in dynamic-only mode
            self.html_content = ""
            self.cookies = []
            self.headers = {}
        
        # Get XHR requests from our injected monitor
        self.xhr_requests = driver.execute_script("return window._xhrRequests;") or []

    def check_html(self, tech: dict) -> List[dict]:
        """Check HTML content and meta tags for technology signatures."""
        matched_signatures = []
        # Search for regex patterns in the HTML content
        if 'html' in tech:
            for pattern in tech['html']:
                if re.search(pattern, self.html_content, re.IGNORECASE):
                    matched_signatures.append({'type': 'html', 'detail': pattern})
        # Search for meta tag patterns
        if 'meta' in tech:
            soup = BeautifulSoup(self.html_content, 'html.parser')
            for meta_name, pattern in tech['meta'].items():
                meta_tags = soup.find_all('meta', {'name': meta_name})
                for meta in meta_tags:
                    if 'content' in meta.attrs and re.search(pattern, meta['content'], re.IGNORECASE):
                        matched_signatures.append({'type': 'meta', 'detail': f"{meta_name}: {pattern}"})
        return matched_signatures

    def check_cookies(self, tech: dict) -> List[dict]:
        """Check cookies for technology signatures."""
        matched_signatures = []
        if 'cookies' in tech:
            for cookie_name, pattern in tech['cookies'].items():
                for cookie in self.cookies:
                    # Match cookie name and optionally its value
                    if 'name' in cookie and re.search(cookie_name, cookie['name'], re.IGNORECASE):
                        if pattern == "" or ('value' in cookie and re.search(pattern, cookie['value'], re.IGNORECASE)):
                            matched_signatures.append({'type': 'cookies', 'detail': cookie_name})
        return matched_signatures

    def check_headers(self, tech: dict) -> List[dict]:
        """Check HTTP headers for technology signatures."""
        matched_signatures = []
        if 'headers' in tech:
            for header_key, header_value in tech['headers'].items():
                if header_key in self.headers:
                    # Match header value if specified
                    if header_value == "" or re.search(header_value, self.headers[header_key], re.IGNORECASE):
                        matched_signatures.append({'type': 'headers', 'detail': f"{header_key}: {header_value}"})
        return matched_signatures

    @timing_decorator
    def check_network(self, tech: dict) -> List[dict]:
        """Check network requests for technology signatures."""
        matched_signatures = []
        if 'network' in tech:
            for pattern in tech['network']:
                # Check all requests including XHR
                for request in self.all_requests:
                    if hasattr(request, 'url') and re.search(pattern, request.url, re.IGNORECASE):
                        matched_signatures.append({
                            'type': 'network', 
                            'detail': pattern,
                            'output': request.url
                        })
                        break
        return matched_signatures

    @timing_decorator
    def check_dom(self, tech: dict) -> List[dict]:
        """Check DOM elements for technology signatures using CSS selectors and optional conditions."""
        if 'dom' not in tech:
            return []
        matched = []
        # If 'dom' is a list, just check for element existence
        if isinstance(tech['dom'], list):
            for selector in tech['dom']:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        matched.append({'type': 'dom', 'detail': selector})
                except Exception:
                    pass
        # If 'dom' is a dict, check for conditions on the elements
        elif isinstance(tech['dom'], dict):
            for selector, conditions in tech['dom'].items():
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if check_dom_conditions(element, conditions):
                            matched.append({'type': 'dom', 'detail': f"{selector} with conditions"})
                            break
                except Exception:
                    pass
        return matched

    def check_script_src(self, tech: dict) -> List[dict]:
        """Check <script> tag src attributes for technology signatures."""
        if 'scriptSrc' not in tech:
            return []
        soup = BeautifulSoup(self.html_content, 'html.parser')
        scripts = soup.find_all('script', src=True)
        matched = []
        for pattern in tech['scriptSrc']:
            for script in scripts:
                src = script['src']
                if re.search(pattern, src, re.IGNORECASE):
                    matched.append({'type': 'scriptSrc', 'detail': pattern})
                    break
        return matched

    @timing_decorator
    def check_xhr(self, tech: dict) -> List[dict]:
        """Check XHR (AJAX) requests for technology signatures."""
        if 'xhr' not in tech:
            return []
            
        matched = []
        # Check both selenium-wire requests and our monitored XHR requests
        xhr_urls = set()
        
        # Add URLs from selenium-wire requests
        for req in self.all_requests:
            if (hasattr(req, 'headers') and 
                req.headers.get('X-Requested-With') == 'XMLHttpRequest'):
                xhr_urls.add(req.url)
                
        # Add URLs from our injected monitor
        xhr_urls.update(xhr['url'] for xhr in self.xhr_requests)
        
        # Check patterns against all XHR URLs
        for pattern in tech['xhr']:
            for url in xhr_urls:
                if re.search(pattern, url, re.IGNORECASE):
                    matched.append({
                        'type': 'xhr', 
                        'detail': pattern,
                        'output': url
                    })
                    break
        return matched

    @timing_decorator
    def check_js(self, tech: dict, tech_name: str, detect_only: bool = True) -> List[dict]:
        """
        Check JavaScript variables for technology signatures.
        If detect_only is False, also try to extract version information.
        """
        if 'js' not in tech:
            return []
            
        matched = []
        for var, pattern_str in tech['js'].items():
            try:
                processed_var = process_var_name(var)
                # JavaScript to get the variable's value from the page
                get_value_script = f"""
                try {{
                    var val = {processed_var};
                    return typeof val !== 'undefined' ? String(val) : null;
                }} catch (e) {{
                    return null;
                }}
                """
                value = self.driver.execute_script(get_value_script)
                if value is None:
                    continue

                # Always create a signature with the variable name and output
                signature = {
                    'type': 'js', 
                    'detail': var,
                    'output': value
                }

                # Extract version information if available
                if not detect_only and ';version:' in pattern_str:
                    pattern, version_group = pattern_str.split(';version:')
                    try:
                        if re.search(re.escape(pattern), value):
                            match = re.search(re.escape(pattern), value)
                            if match and match.group(1):
                                signature['version'] = match.group(1)
                    except Exception as e:
                        print(f"Error matching version pattern for {var}: {e}")

                matched.append(signature)
            except Exception as e:
                print(f"Error checking JS variable {var}: {e}")
                continue

        return matched

    def detect_all(self) -> Dict[str, Any]:
        """
        Detect all technologies on the current page by running all checks.
        If dynamic_only is True, only run DOM, XHR, and network-related checks.
        Returns a dictionary of detected technologies and their matched signatures.
        """
        detected_techs = {}
        analysis_data = {
            'timing': {},
            'matches': {}
        }

        for tech_name, tech_data in self.technologies.items():
            matched_signatures = []
            tech_timing = {}
            tech_matches = {}
            
            if self.dynamic_only:
                # Only run dynamic checks
                for check in [
                    ('js', lambda t: self.check_js(t, tech_name)),
                    ('dom', self.check_dom),
                    ('network', self.check_network),
                    ('xhr', self.check_xhr),
                    ('cookies', self.check_cookies)
                ]:
                    start_time = time.time()
                    try:
                        results = check[1](tech_data) or []  # Ensure results is a list
                        tech_timing[check[0]] = time.time() - start_time
                        tech_matches[check[0]] = len(results)
                        matched_signatures.extend(results)
                    except Exception as e:
                        print(f"Error in {check[0]} check for {tech_name}: {e}")
                        tech_timing[check[0]] = time.time() - start_time
                        tech_matches[check[0]] = 0
            else:
                # Run all checks
                for check in [
                    ('html', self.check_html),
                    ('cookies', self.check_cookies),
                    ('headers', self.check_headers),
                    ('scriptSrc', self.check_script_src),
                    ('dom', self.check_dom),
                    ('xhr', self.check_xhr),
                    ('network', self.check_network),
                    ('js', lambda t: self.check_js(t, tech_name))
                ]:
                    start_time = time.time()
                    try:
                        results = check[1](tech_data) or []  # Ensure results is a list
                        tech_timing[check[0]] = time.time() - start_time
                        tech_matches[check[0]] = len(results)
                        matched_signatures.extend(results)
                    except Exception as e:
                        print(f"Error in {check[0]} check for {tech_name}: {e}")
                        tech_timing[check[0]] = time.time() - start_time
                        tech_matches[check[0]] = 0

            if matched_signatures:  # Only add technology if signatures were found
                detected_techs[tech_name] = {
                    'signatures': [dict(sig) if not isinstance(sig, dict) else sig 
                                 for sig in matched_signatures],  # Ensure signatures are dictionaries
                    'analysis': {
                        'timing': tech_timing,
                        'matches': tech_matches,
                        'total_matches': len(matched_signatures)
                    }
                }
                
                # Aggregate timing and match data
                for check_type, time_taken in tech_timing.items():
                    if time_taken > 0:  # Only track positive timings
                        analysis_data['timing'][check_type] = analysis_data['timing'].get(check_type, 0) + time_taken
                for check_type, match_count in tech_matches.items():
                    if match_count > 0:  # Only track positive matches
                        analysis_data['matches'][check_type] = analysis_data['matches'].get(check_type, 0) + match_count

        # Add overall analysis data if technologies were detected
        if detected_techs:
            detected_techs['_analysis'] = {
                'timing_by_check': analysis_data['timing'],
                'matches_by_check': analysis_data['matches'],
                'total_technologies': len([k for k in detected_techs.keys() if k != '_analysis'])
            }

        return detected_techs