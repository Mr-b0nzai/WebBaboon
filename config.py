import json
from pathlib import Path

# Chrome configuration
CHROME_BINARY_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_OPTIONS = [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--window-size=1920,1080",
    # "--disable-gpu",
    # "--disable-software-rasterizer",
    "--disable-features=NetworkTimeServiceQuerying",
    "--disable-features=VizDisplayCompositor",
    "--log-level=3"
]

# Timeouts and delays
PAGE_LOAD_TIMEOUT = 30
WAIT_TIMEOUT = 10
CRAWL_DELAY = 1

# Load technology signatures
def load_technologies():
    tech_file = Path(__file__).parent / 'technologies.json'
    with open(tech_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# ASCII Art
ASCII_ART = r'''
 _       __     __    ____        __                    
| |     / /__  / /_  / __ )____ _/ /_  ____  ____  ____ 
| | /| / / _ \/ __ \/ __  / __ `/ __ \/ __ \/ __ \/ __ \
| |/ |/ /  __/ /_/ / /_/ / /_/ / /_/ / /_/ / /_/ / / / /
|__/|__/\___/_.___/_____/\__,_/_.___/\____/\____/_/ /_/ 
                                                        
''' 