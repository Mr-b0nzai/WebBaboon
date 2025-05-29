import argparse
from config import ASCII_ART, load_technologies
from crawler import WebBaboonCrawler

def display_results(detected_techs):
    """Display the detected technologies and their details."""
    if not detected_techs:
        print("No technologies detected or an error occurred.")
        return
    
    print("\nDetected Technologies:")
    for tech, data in sorted(detected_techs.items()):
        versions = set()
        # Collect all version information
        for sig in data['signatures']:
            if 'version' in sig:
                versions.add(sig['version'])
        
        # Display technology name and version if available
        version_str = f" (version: {', '.join(versions)})" if versions else ""
        print(f"- {tech}{version_str}")
        
        # Display detailed signatures
        for sig in data['signatures']:
            line = f"  {sig['type']}: {sig['detail']}"
            if 'output' in sig and sig['type'] != 'js_version':
                line += f" (output: {sig['output']})"
            print(line)

def main():
    """Main entry point for WebBaboon."""
    print(ASCII_ART)
    parser = argparse.ArgumentParser(
        description=f"{ASCII_ART}\nWebBaboon is a web technology detection tool that crawls and analyzes websites to identify the technologies they use.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-u', '--url', required=True, help='The URL to analyze (e.g., example.com). If no protocol is specified, "https://" will be added.')
    parser.add_argument('-m', '--max-depth', type=int, default=1, help='Maximum depth of pages to crawl (default: 1)')
    args = parser.parse_args()

    # Load technology signatures and initialize crawler
    technologies = load_technologies()
    crawler = WebBaboonCrawler(args.url, technologies, args.max_depth)
    
    # Run the crawler and display results
    results = crawler.crawl()
    display_results(results)

if __name__ == "__main__":
    main()