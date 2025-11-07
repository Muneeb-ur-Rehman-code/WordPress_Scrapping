import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import random
from base_scraper import BaseScraper

class DealspotRScraper(BaseScraper):
    """Scraper for Dealspotr coupon website"""
    
    def __init__(self, headless=True, debug=False, config=None):
        """Initialize the scraper"""
        super().__init__(headless, debug, config)
        self.base_url = "https://dealspotr.com"
        
    def _try_close_popup(self, timeout=3):
        """Try to close popup by clicking X button or pressing ESC"""
        try:
            # Method 1: Click X button with SVG
            try:
                close_selectors = [
                    'svg.modal__x',
                    'svg[data-icon="xmark"]',
                    '.modal__x',
                    '.toggle-modal',
                    'button[aria-label*="close" i]',
                ]
                
                for selector in close_selectors:
                    try:
                        close_button = WebDriverWait(self.driver, timeout).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        close_button.click()
                        print("  SUCCESS: Closed popup using X button")
                        self._random_delay(1, 1.5)
                        return True
                    except:
                        continue
            except:
                pass
            
            # Method 2: Press ESC key
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                print("  SUCCESS: Closed popup with ESC key")
                self._random_delay(1, 1.5)
                return True
            except:
                pass
            
            print("  INFO: No popup found or already closed")
            return True
            
        except Exception as e:
            print(f"  WARNING: Error closing popup: {str(e)}")
            return False
    
    def search_store(self, store_name):
        """Search for a store and navigate to its promo codes page"""
        try:
            print(f"Searching for: {store_name}")
            
            self.driver.get(self.base_url)
            print("  -> Loaded homepage")
            
            self._random_delay(2, 3)
            
            # Find search input
            search_selectors = [
                'input.header--search',
                'input[placeholder*="Search for brands" i]',
                'input[type="text"]',
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"  SUCCESS: Found search input")
                    break
                except TimeoutException:
                    continue
            
            if not search_input:
                print("  ERROR: Search input not found")
                return False
            
            # Type store name
            clean_name = store_name.replace('.com', '').strip()
            
            search_input.click()
            self._random_delay(0.3, 0.5)
            search_input.clear()
            self._random_delay(0.2, 0.4)
            
            print(f"  -> Typing '{clean_name}'...")
            for char in clean_name:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.08, 0.15))
            
            self._random_delay(0.5, 1)
            search_input.send_keys(Keys.RETURN)
            
            print("  -> Waiting for search results...")
            self._random_delay(3, 5)
            
            # Find and click first store result
            try:
                # Store original window
                original_windows = set(self.driver.window_handles)
                
                store_link_selectors = [
                    '.storeblock--main .fs16.bold a',
                    '.storeblock--main a[href*="/promo-codes/"]',
                    '.flex--module .storeblock--main a',
                ]
                
                store_link = None
                for selector in store_link_selectors:
                    try:
                        store_link = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        print(f"  SUCCESS: Found store link using selector: {selector}")
                        break
                    except:
                        continue
                
                if not store_link:
                    print("  ERROR: No store link found in search results")
                    return False
                
                print("  SUCCESS: Found store name link")
                
                if self._safe_click_with_retry(store_link):
                    print("  SUCCESS: Clicked store name link")
                else:
                    print("  ERROR: Could not click store link")
                    return False
                
                # Wait for new window/tab to open
                print("  -> Waiting for new tab to open...")
                self._random_delay(2, 4)
                
                # Switch to new window
                new_windows = set(self.driver.window_handles)
                if len(new_windows) > len(original_windows):
                    new_window = (new_windows - original_windows).pop()
                    self.driver.switch_to.window(new_window)
                    print("  SUCCESS: Switched to new tab with promo codes")
                else:
                    print("  INFO: No new tab opened, continuing with current page")
                
            except TimeoutException:
                print("  ERROR: No store results found")
                return False
            
            print("  -> Waiting for promo codes page to load...")
            self._random_delay(2, 3)
            
            current_url = self.driver.current_url
            print(f"  -> Current URL: {current_url}")
            
            if '/promo-codes/' in current_url.lower():
                print(f"SUCCESS: Successfully navigated to promo codes page")
                return True
            else:
                print(f"WARNING: URL doesn't contain '/promo-codes/', but continuing...")
                return True
                
        except Exception as e:
            print(f"ERROR: Error during search: {str(e)}")
            import traceback
            if self.debug:
                traceback.print_exc()
            return False
    
    def scrape_store(self, store_name):
        """Scrape all coupons and deals for a specific store"""
        # Clear previous data
        self.coupons_data = []
        
        try:
            if not self.driver:
                self.setup_driver()
            
            if not self.search_store(store_name):
                print(f"ERROR: Could not access promo codes page for {store_name}")
                return []
            
            print("\nWaiting for page to fully load...")
            self._random_delay(2, 3)
            
            # Click first "Show Promo Code" button to go to new page with revealed codes
            print("\nClicking first 'Show Promo Code' button...")
            if not self._click_show_promo_code():
                print("WARNING: Could not click Show Promo Code button")
                return []
            
            print("\nParsing page content from NEW page...")
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            
            if self.debug:
                debug_file = f'debug_page_dealspotr_{store_name.replace(".com", "")}.html'
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"  -> Saved page HTML to: {debug_file}")
            
            print("\n🔍 Looking for codes and deals on NEW page...")
            
            # Find ALL code containers
            code_cards = soup.find_all('div', class_='copy-code', attrs={'data-promo-type': 'code'})
            
            # Find ALL deal containers
            deal_cards = soup.find_all('div', class_='open-link', attrs={'data-promo-type': 'sale'})
            
            total_offers = len(code_cards) + len(deal_cards)
            
            print(f"  ✅ Found {len(code_cards)} coupon codes (class='copy-code')")
            print(f"  ✅ Found {len(deal_cards)} deals (class='open-link')")
            print(f"  ✅ Total: {total_offers} offers\n")
            
            if total_offers == 0:
                print("ERROR: No offers to scrape")
                return []
            
            scraped_count = 0
            
            # Get limit from config
            max_codes = self.config.get('limits', {}).get('dealspotr_max_codes', 20)
            
            # Extract coupon codes (with limit)
            print(f"📋 Extracting CODES (limit: {max_codes})...")
            codes_processed = 0
            
            for index, card in enumerate(code_cards, 1):
                if codes_processed >= max_codes:
                    print(f"NOTE: Reached max codes limit ({max_codes}), skipping remaining code cards")
                    break
                
                try:
                    offer_data = self._extract_code_data(card, store_name, index)
                    
                    if offer_data and offer_data.get('title'):
                        self.coupons_data.append(offer_data)
                        scraped_count += 1
                        codes_processed += 1
                        code_display = offer_data.get('coupon_code', 'N/A')
                        print(f"SUCCESS [{scraped_count}/{total_offers}] CODE: {offer_data['title'][:35]}... | Code: {code_display}")
                    
                except Exception as e:
                    print(f"WARNING: Error extracting code {index}: {str(e)}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    continue
            
            # Extract ALL deals (no limit)
            print(f"\n🎁 Extracting DEALS...")
            for index, card in enumerate(deal_cards, 1):
                try:
                    offer_data = self._extract_deal_data(card, store_name, index)
                    
                    if offer_data and offer_data.get('title'):
                        self.coupons_data.append(offer_data)
                        scraped_count += 1
                        print(f"SUCCESS [{scraped_count}/{total_offers}] DEAL: {offer_data['title'][:50]}...")
                    
                except Exception as e:
                    print(f"WARNING: Error extracting deal {index}: {str(e)}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    continue
            
            print(f"\n🎉 SUCCESS: Extracted {scraped_count} offers (limited to {max_codes} codes)")
            
            return self.coupons_data
            
        except Exception as e:
            print(f"\nERROR: FATAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if self.debug:
                input("   Press Enter to close browser...")
            
            return []
    
    def _click_show_promo_code(self):
        """Click first 'Show Promo Code' button - opens NEW TAB"""
        try:
            # Track current windows before clicking
            original_windows = set(self.driver.window_handles)
            print(f"  -> Current tabs: {len(original_windows)}")
            
            # Find first "Show Promo Code" button
            show_code_selectors = [
                'div.btn.btn--code',
                'div.btn--code',
                '.btn--code',
            ]
            
            show_code_button = None
            for selector in show_code_selectors:
                try:
                    show_code_buttons = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if show_code_buttons:
                        show_code_button = show_code_buttons[0]
                        break
                except:
                    continue
            
            if not show_code_button:
                print("  ERROR: No 'Show Promo Code' button found")
                return False
            
            print(f"  -> Found 'Show Promo Code' button")
            print(f"  -> Clicking button (will open new tab)...")
            
            # Click the button
            if not self._safe_click_with_retry(show_code_button):
                return False
            
            print("  -> Waiting for new tab to open...")
            self._random_delay(2, 4)
            
            # Switch to new tab
            new_windows = set(self.driver.window_handles)
            print(f"  -> Tabs after click: {len(new_windows)}")
            
            if len(new_windows) > len(original_windows):
                new_window = (new_windows - original_windows).pop()
                self.driver.switch_to.window(new_window)
                print("  SUCCESS: Switched to new tab with revealed codes")
                
                # Wait for page to load
                self._random_delay(2, 3)
                
                # Close popup on new page
                print("  -> Closing popup on new tab...")
                self._try_close_popup(timeout=3)
                
                # Additional wait
                self._random_delay(2, 3)
                
                print(f"  -> Current URL: {self.driver.current_url}")
                print("  SUCCESS: New tab loaded with revealed codes")
                
                return True
            else:
                print("  WARNING: No new tab opened, codes may be revealed inline")
                self._try_close_popup(timeout=2)
                return True
            
        except Exception as e:
            print(f"  ERROR: Error clicking Show Promo Code: {str(e)}")
            return False
    
    def _extract_code_data(self, card, store_name, position):
        """Extract all fields from a code card on NEW page (codes revealed)"""
        data = {
            'source': 'Dealspotr',
            'store_name': store_name.replace('.com', '').strip().title(),
            'title': '',
            'description': '',
            'coupon_code': '',
            'deal_type': 'code',
            'expiry_date': '',
            'coupon_url': '',
            'category': '',
        }
        
        # Extract Title
        title_elem = card.find('div', class_='promoblock--title')
        if title_elem:
            # Remove "View more details" link
            view_more = title_elem.find('span', class_='toggle')
            if view_more:
                view_more.decompose()
            
            data['title'] = title_elem.get_text(strip=True)
            data['description'] = title_elem.get_text(strip=True)
        
        # Extract Discount Amount
        discount_elem = card.find('div', class_='promoblock--amountoff')
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            if not data['title']:
                data['title'] = discount_text
            else:
                if discount_text not in data['title']:
                    data['title'] = f"{discount_text}: {data['title']}"
        
        # Extract Coupon Code from revealed codebox
        code = ''
        
        # Method 1: input.codebox
        code_input = card.find('input', class_='codebox')
        if code_input and code_input.get('value'):
            code = code_input.get('value').strip()
        
        # Method 2: input with id starting with "display-code-r-"
        if not code:
            code_input = card.find('input', id=re.compile(r'^display-code-r-'))
            if code_input and code_input.get('value'):
                code = code_input.get('value').strip()
        
        # Method 3: input with id starting with "listcode-r-"
        if not code:
            code_input = card.find('input', id=re.compile(r'^listcode-r-'))
            if code_input and code_input.get('value'):
                code = code_input.get('value').strip()
        
        # Method 4: hidden input with id starting with "code-"
        if not code:
            code_input = card.find('input', id=re.compile(r'^code-'))
            if code_input and code_input.get('value'):
                code = code_input.get('value').strip()
        
        data['coupon_code'] = code if code else 'N/A'
        
        # Extract Categories
        categories = []
        
        label = card.find('div', class_='promoblock--label')
        if label:
            label_text = label.get_text(strip=True)
            if label_text and label_text not in ['', 'Code']:
                categories.append(label_text)
        
        # Verified badge
        verified_icon = card.find('svg', {'data-icon': 'badge-check'}) or card.find(class_='fa-badge-check')
        if verified_icon:
            categories.append('Verified')
        
        data['category'] = ', '.join(categories) if categories else 'General'
        
        # Extract URL
        data['coupon_url'] = self.driver.current_url
        
        # Extract expiry date
        data['expiry_date'] = self._extract_expiry_date(card)
        
        return data
    
    def _extract_deal_data(self, card, store_name, position):
        """Extract all fields from a deal card"""
        data = {
            'source': 'Dealspotr',
            'store_name': store_name.replace('.com', '').strip().title(),
            'title': '',
            'description': '',
            'coupon_code': '',
            'deal_type': 'deal',
            'expiry_date': '',
            'coupon_url': '',
            'category': '',
        }
        
        # Extract Title
        title_elem = card.find('div', class_='promoblock--title')
        if title_elem:
            # Remove "View more details" link
            view_more = title_elem.find('span', class_='toggle')
            if view_more:
                view_more.decompose()
            
            data['title'] = title_elem.get_text(strip=True)
            data['description'] = title_elem.get_text(strip=True)
        
        # Extract Discount Amount
        discount_elem = card.find('div', class_='promoblock--amountoff')
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            if not data['title']:
                data['title'] = discount_text
            else:
                if discount_text not in data['title']:
                    data['title'] = f"{discount_text}: {data['title']}"
        
        # Extract Categories
        categories = []
        
        label = card.find('div', class_='promoblock--label')
        if label:
            label_text = label.get_text(strip=True)
            if label_text:
                categories.append(label_text)
        
        data['category'] = ', '.join(categories) if categories else 'General'
        
        # Extract URL
        data['coupon_url'] = self.driver.current_url
        
        # Extract expiry date
        data['expiry_date'] = self._extract_expiry_date(card)
        
        return data
    
    def _extract_expiry_date(self, card):
        """Extract and parse expiry date"""
        try:
            text_content = card.get_text()
            
            # Pattern 1: "Expires MM/DD/YYYY"
            pattern1 = r'(?:Expires?|Ends?)\s+(\d{1,2})/(\d{1,2})/(\d{4})'
            match1 = re.search(pattern1, text_content, re.IGNORECASE)
            if match1:
                month, day, year = match1.groups()
                try:
                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            # Pattern 2: "Expires MM/DD"
            pattern2 = r'(?:Expires?|Ends?)\s+(\d{1,2})/(\d{1,2})'
            match2 = re.search(pattern2, text_content, re.IGNORECASE)
            if match2:
                month, day = match2.groups()
                year = datetime.now().year
                try:
                    date_obj = datetime(year, int(month), int(day))
                    if date_obj < datetime.now():
                        date_obj = datetime(year + 1, int(month), int(day))
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            # Pattern 3: "Expires in X days"
            pattern3 = r'(?:Expires? in|Ends? in)\s+(\d+)\s+days?'
            match3 = re.search(pattern3, text_content, re.IGNORECASE)
            if match3:
                days = int(match3.group(1))
                expiry_date = datetime.now() + timedelta(days=days)
                return expiry_date.strftime('%Y-%m-%d')
            
            return ''
            
        except Exception as e:
            return ''