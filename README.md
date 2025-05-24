# WebBaboon

WebBaboon is a powerful web technology detection tool that crawls websites and identifies the technologies they use. It can detect frameworks, libraries, analytics tools, and other web technologies by analyzing various aspects of web pages.

## Features

- Detects web technologies through multiple methods:
  - HTML content and meta tags
  - JavaScript variables and functions
  - DOM elements and attributes
  - HTTP headers
  - Cookies
  - Network requests
  - XHR requests
  - Script sources
- Version detection for popular technologies
- Crawls multiple pages on the same domain
- Headless operation for fast scanning
- Detailed signature reporting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/webbaboon.git
cd webbaboon
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure you have Google Chrome installed (required for the web driver).

## Usage

Basic usage:
```bash
python WebBaboon.py -u example.com
```

Specify crawl depth:
```bash
python WebBaboon.py -u example.com -m 3
```

### Command Line Options

- `-u, --url`: The URL to analyze (required)
- `-m, --max-depth`: Maximum number of pages to crawl (default: 1)

## Project Structure

- `WebBaboon.py`: Main entry point
- `crawler.py`: Web crawling functionality
- `detector.py`: Technology detection logic
- `utils.py`: Helper functions
- `config.py`: Configuration and constants
- `technologies.json`: Technology signatures database

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 