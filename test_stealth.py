from scrapers.retailmenot import RetailMeNotScraper
import time

scraper = RetailMeNotScraper(headless=False)
scraper.setup_driver()

print("\n🔍 Testing stealth mode...")
print("Opening test page...")

scraper.driver.get("https://bot.sannysoft.com/")
time.sleep(3)

# Check if we're detected
page_source = scraper.driver.page_source

if 'navigator.webdriver' in page_source:
    # Check the actual value
    result = scraper.driver.execute_script("return navigator.webdriver")
    print(f"\nnavigator.webdriver = {result}")
    
    if result is None or result == False:
        print("✅ STEALTH MODE ACTIVE - Not detected as bot!")
    else:
        print("⚠️  Still detected as bot")
else:
    print("✅ STEALTH MODE ACTIVE!")

input("\n👀 Check the browser - is the yellow bar gone? (Press Enter to close)")
scraper.close()