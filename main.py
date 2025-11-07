import sys
import json
import re
import time
from pathlib import Path
from scrapers.retailmenot import RetailMeNotScraper
from scrapers.simplycodes import SimplyCodesScraper
from scrapers.dealspotr import DealspotRScraper
from utils.excel_writer import ExcelWriter
from utils.dependencies import validate_dependencies


def load_config():
    """Load configuration from config.json"""
    config_file = Path('config.json')
    
    if not config_file.exists():
        print("❌ ERROR: config.json not found!")
        print("Creating default config.json...")
        
        default_config = {
            "scraper_settings": {
                "headless_mode": False,
                "debug_mode": True,
                "output_file": "scraped_coupons.xlsx"
            },
            "limits": {
                "dealspotr_max_codes": 20,
                "simplycodes_show_more_codes": 2,
                "simplycodes_show_more_deals": 2
            },
            "retry_settings": {
                "max_retries": 2,
                "retry_delay_min": 3,
                "retry_delay_max": 5
            },
            "delays": {
                "between_stores_min": 3,
                "between_stores_max": 5,
                "between_websites_min": 5,
                "between_websites_max": 8,
                "after_browser_reset_min": 2,
                "after_browser_reset_max": 4
            }
        }
        
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print("✅ Created default config.json")
        return default_config
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print("✅ Loaded configuration from config.json\n")
        return config
    except Exception as e:
        print(f"❌ ERROR: Could not load config.json: {str(e)}")
        sys.exit(1)


def get_user_input():
    """Get website and store selections from user"""
    
    print("\n" + "="*60)
    print("🎯 COUPON SCRAPER - Interactive Mode")
    print("="*60 + "\n")
    
    # Step 1: Select websites (MULTIPLE)
    print("📌 Available websites:")
    print("  1. RetailMeNot")
    print("  2. SimplyCodes")
    print("  3. Dealspotr")
    print("  (More coming soon...)")
    
    websites_input = input("\n🔹 Select website(s) (comma-separated numbers or names) [1]: ").strip().lower()
    
    # Parse website selections
    selected_websites = []
    
    if not websites_input:
        selected_websites = ['retailmenot']
    else:
        # Split by comma
        website_choices = [w.strip() for w in re.split(r'[,;]+', websites_input) if w.strip()]
        
        for choice in website_choices:
            if choice in ['1', 'retailmenot']:
                if 'retailmenot' not in selected_websites:
                    selected_websites.append('retailmenot')
            elif choice in ['2', 'simplycodes']:
                if 'simplycodes' not in selected_websites:
                    selected_websites.append('simplycodes')
            elif choice in ['3', 'dealspotr']:
                if 'dealspotr' not in selected_websites:
                    selected_websites.append('dealspotr')
            else:
                print(f"⚠️  Invalid selection: '{choice}' - skipping")
    
    if not selected_websites:
        print("⚠️  No valid websites selected. Defaulting to RetailMeNot")
        selected_websites = ['retailmenot']
    
    print(f"✅ Selected websites: {', '.join([w.title() for w in selected_websites])}\n")
    
    # Step 2: Get store names (MULTIPLE)
    print("📌 Enter store names to scrape")
    print("   You can enter multiple stores separated by commas. Examples:")
    print("     amazon, target, walmart")
    print("   Note: For SimplyCodes and Dealspotr, omit .com (e.g., 'walmart')")
    print("         For RetailMeNot, include .com (e.g., 'walmart.com')")

    stores_input = input("\n🔹 Store name(s) (comma-separated): ").strip()
    
    if not stores_input:
        print("❌ No stores provided. Exiting.")
        sys.exit(1)
    
    # Parse and clean store names
    stores = []
    for store in re.split(r'[,\n;|]+', stores_input):
        store_clean = store.strip()
        if not store_clean:
            continue
        store_clean = store_clean.lower()
        # Remove surrounding quotes
        store_clean = store_clean.strip('"\'')
        stores.append(store_clean)
    
    if not stores:
        print("❌ No valid stores found. Exiting.")
        sys.exit(1)
    
    # Remove duplicates while preserving order
    stores = list(dict.fromkeys(stores))
    
    print(f"\n✅ Stores to scrape: {', '.join(stores)}\n")
    
    return selected_websites, stores


def scrape_store_with_retry(scraper, store_name, website_name, config):
    """Scrape a store with retry mechanism"""
    max_retries = config['retry_settings']['max_retries']
    retry_delay_min = config['retry_settings']['retry_delay_min']
    retry_delay_max = config['retry_settings']['retry_delay_max']
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                print(f"\n🔄 RETRY {attempt}/{max_retries} for {store_name} on {website_name}")
                time.sleep(random.uniform(retry_delay_min, retry_delay_max))
            
            coupons = scraper.scrape_store(store_name)
            return coupons
            
        except Exception as e:
            print(f"\n❌ ERROR scraping {store_name} (Attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
            
            if attempt < max_retries:
                print(f"   Will retry in {retry_delay_min}-{retry_delay_max} seconds...")
            else:
                print(f"   Max retries reached. Skipping {store_name}.")
                return []
    
    return []


def main():
    """Main execution function"""
    
    try:
        # Validate dependencies first
        print("Checking dependencies...\n")
        if not validate_dependencies():
            sys.exit(1)
        
        # Load config
        config = load_config()
        
        # Get user input
        websites, stores = get_user_input()
        
        # Configuration from JSON
        output_file = config['scraper_settings']['output_file']
        headless_mode = config['scraper_settings']['headless_mode']
        debug_mode = config['scraper_settings']['debug_mode']
        
        print("="*60)
        print("🚀 Starting scraper...")
        print(f"   Websites: {', '.join([w.title() for w in websites])}")
        print(f"   Stores: {', '.join(stores)}")
        print(f"   Output: {output_file}")
        print(f"   Headless: {headless_mode}")
        print(f"   Debug: {debug_mode}")
        print("="*60 + "\n")
        
        # Create writer once
        writer = ExcelWriter(filename=output_file)
        
        total_scraped = 0
        scraper = None
        
        # NEW FLOW: Website by website, all stores per website
        for website_index, website in enumerate(websites, 1):
            print("\n" + "█"*60)
            print(f"🌐 WEBSITE [{website_index}/{len(websites)}]: {website.upper()}")
            print("█"*60 + "\n")
            
            try:
                # Initialize scraper for this website
                if website == 'retailmenot':
                    scraper = RetailMeNotScraper(headless=headless_mode, debug=debug_mode, config=config)
                elif website == 'simplycodes':
                    scraper = SimplyCodesScraper(headless=headless_mode, debug=debug_mode, config=config)
                elif website == 'dealspotr':
                    scraper = DealspotRScraper(headless=headless_mode, debug=debug_mode, config=config)
                else:
                    print(f"❌ Scraper for {website} not implemented")
                    continue
                
                # Setup driver once for all stores on this website
                if not scraper.driver:
                    scraper.setup_driver()
                
                # Process each store for this website
                for store_index, store in enumerate(stores, 1):
                    print("\n" + "─"*60)
                    print(f"🏪 STORE [{store_index}/{len(stores)}]: {store} (on {website.title()})")
                    print("─"*60 + "\n")
                    
                    # Format store name based on website requirements
                    store_formatted = store
                    if website in ['simplycodes', 'dealspotr']:
                        store_formatted = store.replace('.com', '').strip()
                    else:  # retailmenot
                        if not store.endswith('.com'):
                            store_formatted = store + '.com'
                    
                    # Open new tab for each store (except first)
                    if store_index > 1:
                        print(f"Opening new tab for {store_formatted}...")
                        scraper.open_new_tab()
                        time.sleep(2)
                    
                    try:
                        # Scrape with retry
                        coupons = scrape_store_with_retry(scraper, store_formatted, website, config)
                        scraped_count = len(coupons)
                        
                        if scraped_count:
                            writer.save_coupons(coupons, mode='append')
                            print(f"\n✅ Saved {scraped_count} items from {store} ({website.title()}) to {output_file}")
                        else:
                            print(f"\n⚠️  No items scraped for {store} on {website.title()}")
                        
                        total_scraped += scraped_count
                        
                    except Exception as e:
                        print(f"\n❌ FATAL ERROR for {store} on {website.title()}: {str(e)}")
                        import traceback
                        if debug_mode:
                            traceback.print_exc()
                    
                    # Delay before next store
                    if store_index < len(stores):
                        delay = random.uniform(
                            config['delays']['between_stores_min'],
                            config['delays']['between_stores_max']
                        )
                        print(f"\n⏳ Waiting {delay:.1f}s before next store...")
                        time.sleep(delay)
                
                # Close this website's scraper
                print(f"\n✅ Finished scraping all stores on {website.title()}")
                scraper.close()
                scraper = None
                
                # Delay before next website
                if website_index < len(websites):
                    delay = random.uniform(
                        config['delays']['between_websites_min'],
                        config['delays']['between_websites_max']
                    )
                    print(f"\n⏳ Waiting {delay:.1f}s before next website...\n")
                    time.sleep(delay)
                
            except Exception as e:
                print(f"\n❌ ERROR with website {website}: {str(e)}")
                import traceback
                if debug_mode:
                    traceback.print_exc()
                
                # Close scraper if error
                if scraper:
                    try:
                        scraper.close()
                    except:
                        pass
                continue
        
        # Final summary
        print("\n" + "="*60)
        print("🎉 SCRAPING COMPLETED!")
        print("="*60)
        print(f"📊 Total items scraped: {total_scraped}")
        print(f"📁 Saved to: {output_file}")
        print("="*60 + "\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Always close browser
        if 'scraper' in locals() and scraper:
            try:
                scraper.close()
            except:
                pass


if __name__ == "__main__":
    import random  # Need this for delays
    main()