from typing import Dict, List, Any, Optional
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from utils import check_dom_conditions, process_var_name, format_version_check_script

class TechnologyDetector:
    def __init__(self, driver: WebDriver, technologies: dict):
        self.driver = driver
        self.technologies = technologies
        self.html_content = driver.page_source
        self.cookies = driver.get_cookies()
        main_request = next((r for r in driver.requests if r.url == driver.current_url), None)
        self.headers = main_request.response.headers if main_request and main_request.response else {}
        self.network_requests = [req.url for req in driver.requests]

    def check_html(self, tech: dict) -> List[dict]:
        """Check HTML content for technology signatures."""
        matched_signatures = []
        if 'html' in tech:
            for pattern in tech['html']:
                if re.search(pattern, self.html_content, re.IGNORECASE):
                    matched_signatures.append({'type': 'html', 'detail': pattern})
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
                    if 'name' in cookie and re.search(cookie_name, cookie['name'], re.IGNORECASE):
                        if pattern == "" or ('value' in cookie and re.search(pattern, cookie['value'], re.IGNORECASE)):
                            matched_signatures.append({'type': 'cookies', 'detail': cookie_name})
        return matched_signatures

    def check_headers(self, tech: dict) -> List[dict]:
        """Check headers for technology signatures."""
        matched_signatures = []
        if 'headers' in tech:
            for header_key, header_value in tech['headers'].items():
                if header_key in self.headers:
                    if header_value == "" or re.search(header_value, self.headers[header_key], re.IGNORECASE):
                        matched_signatures.append({'type': 'headers', 'detail': f"{header_key}: {header_value}"})
        return matched_signatures

    def check_network(self, tech: dict) -> List[dict]:
        """Check network requests for technology signatures."""
        matched_signatures = []
        if 'network' in tech:
            for pattern in tech['network']:
                for request in self.network_requests:
                    if re.search(pattern, request, re.IGNORECASE):
                        matched_signatures.append({'type': 'network', 'detail': pattern})
        return matched_signatures

    def check_dom(self, tech: dict) -> List[dict]:
        """Check DOM for technology signatures."""
        if 'dom' not in tech:
            return []
        matched = []
        if isinstance(tech['dom'], list):
            for selector in tech['dom']:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        matched.append({'type': 'dom', 'detail': selector})
                except Exception:
                    pass
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
        """Check script src attributes for technology signatures."""
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

    def check_xhr(self, tech: dict) -> List[dict]:
        """Check XHR requests for technology signatures."""
        if 'xhr' not in tech:
            return []
        matched = []
        xhr_requests = [req for req in self.driver.requests if req.headers.get('X-Requested-With') == 'XMLHttpRequest']
        for pattern in tech['xhr']:
            for req in xhr_requests:
                if re.search(pattern, req.url, re.IGNORECASE):
                    matched.append({'type': 'xhr', 'detail': pattern})
                    break
        return matched

    def check_js(self, tech: dict, tech_name: str, detect_only: bool = True) -> List[dict]:
        """Check JavaScript for technology signatures."""
        if 'js' not in tech:
            return []
        matched = []

        if not detect_only:
            version_check = format_version_check_script(tech_name)
            if version_check:
                try:
                    version = self.driver.execute_script(version_check)
                    if version:
                        matched.append({
                            'type': 'js_version',
                            'detail': f'Version check: {tech_name}',
                            'version': version
                        })
                except Exception as e:
                    print(f"Error checking version for {tech_name}: {e}")

        for var, pattern_str in tech['js'].items():
            try:
                processed_var = process_var_name(var)
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

                if detect_only:
                    matched.append({'type': 'js', 'detail': var})
                    continue

                signature = {'type': 'js', 'detail': var, 'output': value}
                if ';version:' in pattern_str:
                    pattern, version_group = pattern_str.split(';version:')
                    try:
                        if value and re.search(re.escape(pattern), value):
                            match = re.search(re.escape(pattern), value)
                            if match and match.group(1):
                                signature['version'] = match.group(1)
                    except Exception as e:
                        print(f"Error matching pattern for {var}: {e}")
                matched.append(signature)
            except Exception as e:
                print(f"Error checking JS variable {var}: {e}")

        return matched

    def detect_all(self) -> Dict[str, Any]:
        """Detect all technologies on the current page."""
        detected_techs = {}
        for tech_name, tech_data in self.technologies.items():
            matched_signatures = []
            matched_signatures.extend(self.check_html(tech_data))
            matched_signatures.extend(self.check_cookies(tech_data))
            matched_signatures.extend(self.check_headers(tech_data))
            matched_signatures.extend(self.check_network(tech_data))
            matched_signatures.extend(self.check_dom(tech_data))
            matched_signatures.extend(self.check_script_src(tech_data))
            matched_signatures.extend(self.check_xhr(tech_data))
            matched_signatures.extend(self.check_js(tech_data, tech_name, detect_only=True))

            if matched_signatures:
                detected_techs[tech_name] = {'signatures': matched_signatures}
                # Extract versions for detected technologies
                version_matches = self.check_js(tech_data, tech_name, detect_only=False)
                if version_matches:
                    detected_techs[tech_name]['signatures'].extend(version_matches)

        return detected_techs 