# 🦍 WebBaboon

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/Mr-b0nzai/webbaboon)](https://github.com/Mr-b0nzai/webbaboon/issues)

<div align="center">
  <img src="https://raw.githubusercontent.com/Mr-b0nzai/webbaboon/main/assets/logo.png" alt="WebBaboon Logo" width="200"/>
  <p><em>🔍 A powerful web technology detection and analysis tool</em></p>
</div>

## 📋 Overview

WebBaboon is a sophisticated web technology detection tool that crawls websites and identifies the technologies they use. Whether you're a developer, security researcher, or just curious about what powers your favorite websites, WebBaboon provides detailed insights into frameworks, libraries, analytics tools, and other web technologies.

## ✨ Key Features

- 🕷️ **Multi-method Detection**
  - HTML content and meta tags analysis
  - JavaScript variables and functions inspection
  - DOM elements and attributes scanning
  - HTTP headers examination
  - Cookie analysis
  - Network request monitoring
  - XHR request tracking
  - Script source identification

- 📊 **Advanced Capabilities**
  - Version detection for popular technologies
  - Multi-page domain crawling
  - Headless operation for rapid scanning
  - Comprehensive signature reporting
  - Low memory footprint
  - Non-intrusive scanning

## 🚀 Quick Start

### Prerequisites

- Python 3.6 or higher
- Google Chrome (for web driver operations)
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Mr-b0nzai/webbaboon.git
cd webbaboon
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## 💻 Usage

### Basic Scan
```bash
python WebBaboon.py -u example.com
```

### Advanced Scan with Custom Depth
```bash
python WebBaboon.py -u example.com -m 3
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-u, --url` | Target URL to analyze (required) | - |
| `-m, --max-depth` | Maximum crawl depth | 1 |
| `-t, --timeout` | Request timeout in seconds | 30 |
| `-o, --output` | Output file path | stdout |

## 🏗️ Project Structure

```
webbaboon/
├── WebBaboon.py     # Main entry point
├── crawler.py       # Web crawling engine
├── detector.py      # Technology detection logic
├── utils.py         # Helper functions
├── config.py        # Configuration settings
└── technologies.json # Technology signatures
```

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  <p>If you find WebBaboon useful, please consider giving it a ⭐️!</p>
</div> 