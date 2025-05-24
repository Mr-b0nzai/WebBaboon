import re
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

def is_valid_identifier(name: str) -> bool:
    """Check if a string is a valid JavaScript identifier."""
    if ' ' in name:
        return False
    return bool(re.match(r'^[a-zA-Z_$][\w$]*$', name))

def process_var_name(var_name: str) -> str:
    """Convert variable names to valid JS expressions."""
    if ' ' in var_name:
        parts = var_name.split(' ')
        expression = parts[0]
        for part in parts[1:]:
            expression += f"['{part}']"
        return expression
    
    parts = var_name.split('.')
    expression = parts[0]
    for part in parts[1:]:
        if is_valid_identifier(part):
            expression += '.' + part
        else:
            expression += f"['{part}']"
    return expression

def check_dom_conditions(element: WebElement, conditions: dict) -> bool:
    """Check if a DOM element matches the given conditions."""
    if 'attributes' in conditions:
        for attr, pattern in conditions['attributes'].items():
            value = element.get_attribute(attr)
            if not value or not re.search(pattern, value, re.IGNORECASE):
                return False
    if 'text' in conditions:
        text = element.text
        if not re.search(conditions['text'], text, re.IGNORECASE):
            return False
    return True

def get_page_links(driver: WebDriver, base_url: str) -> set:
    """Extract all internal links from the current page."""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    links = set()
    base_domain = urlparse(base_url).netloc
    
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        absolute_url = urljoin(base_url, href)
        if urlparse(absolute_url).netloc == base_domain:
            links.add(absolute_url)
    
    return links

def format_version_check_script(tech_name: str) -> Optional[str]:
    """Generate a JavaScript version check script for common technologies."""
    version_checks = {
        'jQuery': r'try { return jQuery.fn.jquery; } catch(e) { try { return $.fn.jquery; } catch(e) { return null; } }',
        'Angular': r'try { return angular.version.full; } catch(e) { return null; }',
        'Bootstrap': r'try { return jQuery.fn.tooltip.Constructor.VERSION; } catch(e) { return null; }',
        'Vue.js': r'try { return Vue.version; } catch(e) { return null; }',
        'React': r'try { return React.version; } catch(e) { return null; }',
        'Lodash': r'try { return _.VERSION; } catch(e) { return null; }',
        'Moment.js': r'try { return moment.version; } catch(e) { return null; }',
        'Alpine.js': r'try { return Alpine.version; } catch(e) { return null; }',
        'Handlebars': r'try { return Handlebars.VERSION; } catch(e) { return null; }',
        'Backbone.js': r'try { return Backbone.VERSION; } catch(e) { return null; }',
        'Ember.js': r'try { return Ember.VERSION; } catch(e) { return null; }'
    }
    return version_checks.get(tech_name) 