import re
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

def is_valid_identifier(name: str) -> bool:
    """Check if a string is a valid JavaScript identifier."""
    # JavaScript identifiers cannot contain spaces
    if ' ' in name:
        return False
    # Match valid JS identifier pattern
    return bool(re.match(r'^[a-zA-Z_$][\w$]*$', name))

def process_var_name(var_name: str) -> str:
    """Convert variable names to valid JS expressions."""
    # Handle space-separated variable names (e.g., for object property access)
    if ' ' in var_name:
        parts = var_name.split(' ')
        expression = parts[0]
        for part in parts[1:]:
            # Use bracket notation for each subsequent part
            expression += f"['{part}']"
        return expression

    # Handle dot-separated variable names
    parts = var_name.split('.')
    expression = parts[0]
    for part in parts[1:]:
        if is_valid_identifier(part):
            # Use dot notation for valid identifiers
            expression += '.' + part
        else:
            # Use bracket notation for invalid identifiers
            expression += f"['{part}']"
    return expression

def check_dom_conditions(element: WebElement, conditions: dict) -> bool:
    """Check if a DOM element matches the given conditions."""
    # Check attribute patterns if specified
    if 'attributes' in conditions:
        for attr, pattern in conditions['attributes'].items():
            value = element.get_attribute(attr)
            # Attribute must exist and match the regex pattern
            if not value or not re.search(pattern, value, re.IGNORECASE):
                return False
    # Check text pattern if specified
    if 'text' in conditions:
        text = element.text
        if not re.search(conditions['text'], text, re.IGNORECASE):
            return False
    return True

def get_page_links(driver: WebDriver, base_url: str) -> set:
    """Extract all internal links from the current page."""
    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = set()
    base_domain = urlparse(base_url).netloc

    # Find all anchor tags with href attributes
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Convert relative URLs to absolute
        absolute_url = urljoin(base_url, href)
        # Only add links that are internal (same domain)
        if urlparse(absolute_url).netloc == base_domain:
            links.add(absolute_url)

    return links