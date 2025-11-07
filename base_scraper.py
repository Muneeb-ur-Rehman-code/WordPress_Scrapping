"""Base scraper class with shared functionality for all scrapers"""

import time
import os
import platform
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class BaseScraper:
    """Base class for all coupon scrapers with shared functionality"""
    
    def __init__(self, headless=True, debug=False, config=None):
        """Initialize base scraper"""
        self.headless = headless
        self.debug = debug
        self.config = config or {}
        self.driver = None
        self.coupons_data = []
        self.base_url = ""  # To be set by child classes
        
    def setup_driver(self):
        """Setup Chrome WebDriver with anti-detection options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # Anti-detection measures
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Chrome preferences
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "directory_upgrade": True,
            "extensions_to_open": "",
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Standard arguments
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--silent')
        
        try:
            print("Setting up ChromeDriver...")
            
            try:
                driver_path = ChromeDriverManager().install()
                
                if platform.system() == "Windows":
                    if os.path.isdir(driver_path):
                        for root, dirs, files in os.walk(driver_path):
                            for file in files:
                                if file == 'chromedriver.exe':
                                    driver_path = os.path.join(root, file)
                                    break
                    
                    if not driver_path.endswith('.exe'):
                        possible_paths = [
                            os.path.join(driver_path, 'chromedriver.exe'),
                            os.path.join(driver_path, 'chromedriver-win32', 'chromedriver.exe'),
                            os.path.join(driver_path, 'chromedriver-win64', 'chromedriver.exe'),
                        ]
                        for path in possible_paths:
                            if os.path.exists(path):
                                driver_path = path
                                break
                
                if not os.path.exists(driver_path):
                    raise Exception(f"ChromeDriver not found at {driver_path}")
                
                service = Service(driver_path)
                service.log_path = 'NUL' if platform.system() == 'Windows' else '/dev/null'
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
            except Exception as e:
                print(f"WARNING: webdriver_manager issue: {str(e)}")
                print("Trying direct Chrome initialization...")
                self.driver = webdriver.Chrome(options=chrome_options)
        
        except Exception as e:
            print(f"ERROR: Failed to initialize Chrome: {str(e)}")
            raise Exception("Could not start Chrome browser")
        
        # Remove webdriver property
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            '''
        })
        
        self.driver.maximize_window()
        print("SUCCESS: Browser initialized (stealth mode activated)")
    
    def _random_delay(self, min_seconds, max_seconds):
        """Sleep for random duration"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def _safe_click_with_retry(self, element, max_retries=2):
        """Safely click element with retry logic"""
        for attempt in range(max_retries):
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                self._random_delay(0.3, 0.6)
                element.click()
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  WARNING: Click failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    self._random_delay(1, 1.5)
                    try:
                        self.driver.execute_script("arguments[0].click();", element)
                        return True
                    except:
                        continue
                else:
                    print(f"  ERROR: Click failed after {max_retries} attempts: {str(e)}")
                    return False
        return False
    
    def _try_close_popup(self, timeout=3, context="general"):
        """Try to close popup - can be overridden by child classes"""
        # Default implementation - child classes can override with site-specific logic
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            print(f"  SUCCESS: Closed popup ({context}) with ESC key")
            self._random_delay(1, 1.5)
            return True
        except:
            return False
    
    def open_new_tab(self, url=None):
        """Open a new tab and optionally navigate to URL"""
        try:
            # Open new tab
            self.driver.execute_script("window.open('');")
            # Switch to new tab
            self.driver.switch_to.window(self.driver.window_handles[-1])
            print(f"  ✅ Opened new tab (total tabs: {len(self.driver.window_handles)})")
            
            if url:
                self.driver.get(url)
                self._random_delay(2, 3)
            
            return True
        except Exception as e:
            print(f"  ❌ ERROR: Could not open new tab: {str(e)}")
            return False
    
    def close_current_tab(self):
        """Close current tab and switch to previous one"""
        try:
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[-1])
                print(f"  ✅ Closed tab (remaining tabs: {len(self.driver.window_handles)})")
                return True
            else:
                print("  ⚠️  WARNING: Cannot close last tab")
                return False
        except Exception as e:
            print(f"  ❌ ERROR: Could not close tab: {str(e)}")
            return False
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                print("\n✅ Browser closed")
            except:
                pass
    
    # Abstract methods to be implemented by child classes
    def search_store(self, store_name):
        """Search for a store - must be implemented by child class"""
        raise NotImplementedError("Child class must implement search_store()")
    
    def scrape_store(self, store_name):
        """Scrape store coupons - must be implemented by child class"""
        raise NotImplementedError("Child class must implement scrape_store()")