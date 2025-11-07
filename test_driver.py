from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_driver():
    options = Options()
    options.add_argument('--headless=new')
    
    try:
        # Method 1: Auto
        print("Testing auto driver...")
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.google.com")
        print(f"✅ Success! Title: {driver.title}")
        driver.quit()
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

if __name__ == "__main__":
    test_driver()