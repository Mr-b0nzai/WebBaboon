import argparse
from config import ASCII_ART, load_technologies
from crawler import WebBaboonCrawler
from efficient_detector import EfficientCrawler
from performance import print_metrics, reset_metrics, disable_metrics

def display_results(detected_techs, show_signatures=False):
    """Display the detected technologies and their details."""
    if not detected_techs:
        print("\nNo technologies detected or an error occurred.")
        return

    print("\nDetected Technologies:")
    if len(detected_techs) == 0:
        print("None found")
        return

    # Sort technologies by name and print
    for tech, data in sorted(detected_techs.items()):
        print(f"\n- {tech}")
        if show_signatures and 'signatures' in data:
            # Group signatures by type
            sig_by_type = {}
            for sig in data['signatures']:
                sig_type = sig['type']
                if sig_type not in sig_by_type:
                    sig_by_type[sig_type] = []
                sig_by_type[sig_type].append(sig)
            
            # Print signatures grouped by type
            for sig_type, sigs in sorted(sig_by_type.items()):
                print(f"  {sig_type.upper()}:")
                for sig in sigs:
                    line = f"    - {sig['detail']}"
                    if 'output' in sig:
                        if sig['type'] == 'js' and len(sig['output']) > 50:
                            # Truncate long JavaScript outputs
                            line += f" (output: {sig['output'][:50]}...)"
                        else:
                            line += f" (output: {sig['output']})"
                    print(line)

def main():
    """Main entry point for WebBaboon."""
    print(ASCII_ART)
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description=f"{ASCII_ART}\nWebBaboon is a web technology detection tool that crawls and analyzes websites to identify the technologies they use.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-u', '--url', required=True, help='The URL to analyze (e.g., example.com). If no protocol is specified, "https://" will be added.')
    parser.add_argument('-m', '--max-depth', type=int, default=1, help='Maximum depth of pages to crawl (default: 1)')
    parser.add_argument('-s', '--signatures', action='store_true', help='Show matched signatures in the output (default: disabled)')
    parser.add_argument('-e', '--efficiency', type=int, choices=[1, 2, 3], default=2, 
                      help='Efficiency level: 1=full browser analysis, 2=hybrid analysis (default), 3=static analysis only')
    parser.add_argument('-p', '--performance', action='store_true', help='Enable performance metrics output (default: disabled)')
    args = parser.parse_args()

    # Handle performance metrics
    if args.performance:
        reset_metrics()  # This also enables metrics
    else:
        disable_metrics()
    
    # Load technology signatures
    technologies = load_technologies()
    
    try:
        if args.efficiency == 1:  # Dynamic analysis only
            print("\nPerforming dynamic analysis only...")
            url = args.url
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            browser_crawler = WebBaboonCrawler(
                urls_to_analyze=[url],
                technologies=technologies,
                max_depth=args.max_depth,
                dynamic_only=True
            )
            try:
                results = browser_crawler.crawl()
                display_results(results, args.signatures)
            finally:
                browser_crawler.cleanup()
        else:
            # Phase 1: Static Analysis
            print("\nPerforming static analysis...")
            static_crawler = EfficientCrawler(args.url, technologies, args.max_depth)
            try:
                static_results = static_crawler.crawl()
                if args.efficiency == 3:  # Static analysis only
                    print("\nStatic Analysis Results:")
                    display_results(static_results, args.signatures)
                    return
            finally:
                static_crawler.cleanup()
            
            # Phase 2: Dynamic Analysis of requested URLs
            if args.efficiency == 2:  # Hybrid mode
                requested_urls = static_crawler.requested_urls
                print(f"\nAnalyzing {len(requested_urls)} URLs for dynamic content...")
                
                # Use browser crawler to analyze each URL that was actually requested
                browser_crawler = WebBaboonCrawler(
                    urls_to_analyze=list(requested_urls),
                    technologies=technologies,
                    max_depth=args.max_depth,
                    dynamic_only=True  # Always do dynamic-only in hybrid mode
                )
                try:
                    browser_results = browser_crawler.crawl()
                      # Merge results
                    for tech, data in browser_results.items():
                        if tech in static_results:
                            # Convert signatures to sets for deduplication
                            existing_sigs = {
                                (sig.get('type', ''), 
                                 sig.get('detail', ''), 
                                 str(sig.get('output', ''))) 
                                for sig in static_results[tech]['signatures']
                            }
                            
                            # Only add new unique signatures
                            for sig in data['signatures']:
                                sig_tuple = (
                                    sig.get('type', ''), 
                                    sig.get('detail', ''), 
                                    str(sig.get('output', ''))
                                )
                                if sig_tuple not in existing_sigs:
                                    static_results[tech]['signatures'].append(sig)
                                    existing_sigs.add(sig_tuple)
                        else:
                            static_results[tech] = data
                finally:
                    # Always clean up browser resources
                    browser_crawler.cleanup()
                    
            # Display combined results
            display_results(static_results, args.signatures)
            
            # Print performance metrics if enabled
            if args.performance:
                print_metrics()
            
    except Exception as e:
        print(f"\nError during analysis: {e}")
        if args.performance:
            print_metrics()  # Print metrics even if there's an error
        return

if __name__ == "__main__":
    main()