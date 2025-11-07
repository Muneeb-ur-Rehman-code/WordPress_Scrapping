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

class SimplyCodesScraper(BaseScraper):
    """Scraper for SimplyCodes coupon website"""
    
    def __init__(self, headless=True, debug=False, config=None):
        """Initialize the scraper"""
        super().__init__(headless, debug, config)
        self.base_url = "https://simplycodes.com"
        
    def _try_close_popup(self, timeout=3):
        """Try to close popup by clicking X button or clicking outside"""
        try:
            # Method 1: Click X button
            try:
                close_selectors = [
                    'span.iconify.i-ph\\:x',
                    'button[aria-label*="close" i]',
                    'button[aria-label*="Close" i]',
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
            
            # Method 3: Click outside popup (backdrop)
            try:
                self.driver.execute_script("""
                    // Click outside any dialog/modal
                    var dialogs = document.querySelectorAll('[role="dialog"]');
                    if (dialogs.length > 0) {
                        var backdrop = dialogs[0].parentElement;
                        if (backdrop) {
                            backdrop.click();
                        }
                    }
                """)
                print("  SUCCESS: Closed popup by clicking outside")
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
        """Search for a store using the search bar"""
        try:
            print(f"Searching for: {store_name}")
            
            self.driver.get(self.base_url)
            print("  -> Loaded homepage")
            
            self._random_delay(2, 3)
            
            # Click search icon (magnifying glass) - Optional, input might be visible
            try:
                search_icon_selectors = [
                    'span.iconify.i-ph\\:magnifying-glass-bold',
                    'span[class*="magnifying-glass"]',
                ]
                
                search_icon = None
                for selector in search_icon_selectors:
                    try:
                        search_icon = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        break
                    except:
                        continue
                
                if search_icon:
                    search_icon.click()
                    print("  SUCCESS: Clicked search icon")
                    self._random_delay(1, 1.5)
                else:
                    print("  INFO: Search icon not found, input may already be visible")
                    
            except Exception as e:
                print(f"  WARNING: Could not click search icon: {str(e)}")
            
            # Find search input
            search_selectors = [
                'input[data-testid="desktop-search-input"]',
                'input.desktop-input',
                'input[placeholder*="shopping" i]',
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"  SUCCESS: Found search input")
                    break
                except TimeoutException:
                    continue
            
            if not search_input:
                print("  ERROR: Search input not found")
                return False
            
            # Ensure input is visible and interactable
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_input)
            self._random_delay(0.5, 0.8)
            
            # Type store name (WITHOUT .com for SimplyCodes)
            clean_name = store_name.replace('.com', '').strip()
            
            try:
                search_input.click()
                print("  SUCCESS: Clicked search input")
            except:
                self.driver.execute_script("arguments[0].click();", search_input)
                print("  SUCCESS: Clicked search input (via JS)")
            
            self._random_delay(0.3, 0.5)
            search_input.clear()
            self._random_delay(0.2, 0.4)
            
            print(f"  -> Typing '{clean_name}'...")
            for char in clean_name:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.08, 0.15))
            
            # Wait for dropdown results to appear
            print("  -> Waiting for search results dropdown...")
            self._random_delay(1.5, 2.5)
            
            # Try to click first search result from dropdown
            try:
                first_result_link = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'div.results-item a'))
                )
                
                print("  SUCCESS: Found first search result in dropdown")
                
                if self._safe_click_with_retry(first_result_link):
                    print("  SUCCESS: Clicked first search result")
                else:
                    print("  WARNING: Could not click search result, trying Enter key")
                    search_input.send_keys(Keys.RETURN)
                
            except TimeoutException:
                print("  WARNING: No dropdown results found, trying Enter key")
                try:
                    search_input.send_keys(Keys.RETURN)
                    print("  -> Pressed Enter")
                except:
                    print("  WARNING: Could not submit search")
                    return False
            
            print("  -> Waiting for store page to load...")
            self._random_delay(3, 5)
            
            current_url = self.driver.current_url
            print(f"  -> Current URL: {current_url}")
            
            # Check if we're on a store page
            if '/store/' in current_url.lower():
                print(f"SUCCESS: Successfully navigated to store page")
                return True
            else:
                print(f"WARNING: URL doesn't contain '/store/', checking page content...")
                try:
                    self._random_delay(2, 3)
                    promotion_containers = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="promotion-container"]')
                    if len(promotion_containers) > 0:
                        print(f"  SUCCESS: Found {len(promotion_containers)} promotion containers on page")
                        return True
                    else:
                        print(f"  ERROR: No promotion containers found, not on store page")
                        return False
                except:
                    return False
                
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
                print(f"ERROR: Could not access store page for {store_name}")
                return []
            
            print("\nWaiting for page to fully load...")
            self._random_delay(2, 3)
            
            # Find and click first "Show Code" button to reveal all codes
            print("\nClicking 'Show Code' to reveal all codes...")
            if not self._click_show_code_to_reveal():
                print("WARNING: Could not click Show Code button, trying to continue...")
            
            # Click "Show more" buttons for codes and deals
            print("\nClicking 'Show more' buttons...")
            self._click_show_more_buttons()
            
            print("\nParsing page content...")
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            
            if self.debug:
                debug_file = f'debug_page_simplycodes_{store_name.replace(".com", "")}.html'
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"  -> Saved page HTML to: {debug_file}")
            
            print("\n🔍 Looking for coupon and deal cards by class...")
            
            # Find ALL coupon-card-container divs (CODES)
            code_cards = soup.find_all('div', class_='coupon-card-container')
            
            # Find ALL deal-card-container divs (DEALS)
            deal_cards = soup.find_all('div', class_='deal-card-container')
            
            total_offers = len(code_cards) + len(deal_cards)
            
            print(f"  ✅ Found {len(code_cards)} coupon-card-container divs (CODES)")
            print(f"  ✅ Found {len(deal_cards)} deal-card-container divs (DEALS)")
            print(f"  ✅ Total: {total_offers} offers\n")
            
            if total_offers == 0:
                print("ERROR: No offers to scrape")
                return []
            
            scraped_count = 0
            
            # Extract ALL coupon codes
            print("📋 Extracting CODES...")
            for index, card in enumerate(code_cards, 1):
                try:
                    offer_data = self._extract_code_data(card, store_name, index)
                    
                    if offer_data and offer_data.get('title'):
                        self.coupons_data.append(offer_data)
                        scraped_count += 1
                        code_display = offer_data.get('coupon_code', 'N/A')
                        print(f"SUCCESS [{scraped_count}/{total_offers}] CODE: {offer_data['title'][:35]}... | Code: {code_display}")
                    
                except Exception as e:
                    print(f"WARNING: Error extracting code {index}: {str(e)}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    continue
            
            # Extract ALL deals
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
            
            print(f"\n🎉 SUCCESS: Extracted {scraped_count}/{total_offers} offers")
            
            return self.coupons_data
            
        except Exception as e:
            print(f"\nERROR: FATAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if self.debug:
                input("   Press Enter to close browser...")
            
            return []
    
    def _click_show_code_to_reveal(self):
        """Click first 'Show Code' button to reveal all codes, then close popup"""
        try:
            # Find first "Show Code" button
            show_code_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[data-testid="promotion-copy-code-button"]')
            
            # Filter for buttons containing "Show Code" text
            show_code_button = None
            for button in show_code_buttons:
                try:
                    if 'show code' in button.text.lower():
                        show_code_button = button
                        break
                except:
                    continue
            
            if not show_code_button:
                print("  INFO: No 'Show Code' button found")
                return False
            
            print("  -> Clicking 'Show Code' button...")
            
            # Store original window handle
            original_window = self.driver.current_window_handle
            original_windows = set(self.driver.window_handles)
            
            # Click the button
            if not self._safe_click_with_retry(show_code_button):
                return False
            
            print("  -> Waiting for new page...")
            self._random_delay(3, 5)
            
            # Check if new window/tab opened
            new_windows = set(self.driver.window_handles)
            
            if len(new_windows) > len(original_windows):
                # New window opened, switch to it
                new_window = (new_windows - original_windows).pop()
                self.driver.switch_to.window(new_window)
                print("  -> Switched to new window")
                self._random_delay(2, 3)
            
            # Close popup
            print("  -> Closing popup...")
            self._try_close_popup(timeout=3)
            
            # Additional wait for codes to be revealed
            self._random_delay(2, 3)
            
            print("  SUCCESS: All codes should now be revealed")
            
            return True
            
        except Exception as e:
            print(f"  ERROR: Error clicking Show Code: {str(e)}")
            return False
    
    def _click_show_more_buttons(self):
        """Click 'Show more' buttons - Uses config limits"""
        try:
            # Get limits from config
            codes_clicks_limit = self.config.get('limits', {}).get('simplycodes_show_more_codes', 2)
            deals_clicks_limit = self.config.get('limits', {}).get('simplycodes_show_more_deals', 2)
            
            print(f"  -> Show More limits: {codes_clicks_limit} clicks for codes, {deals_clicks_limit} clicks for deals")
            print("  -> Looking for 'Show more' buttons in specific sections...\n")
            
            # Scroll to top first
            self.driver.execute_script("window.scrollTo(0, 0);")
            self._random_delay(1, 1.5)
            
            # Phase 1: Click CODES "Show more" button
            print("  📋 Phase 1: Expanding CODES section (#verified-promos-section)...")
            codes_clicks = 0
            
            for i in range(codes_clicks_limit):
                try:
                    self._random_delay(1.5, 2.5)
                    
                    # Find codes section
                    codes_section = None
                    try:
                        codes_section = self.driver.find_element(By.ID, 'verified-promos-section')
                    except:
                        try:
                            codes_section = self.driver.find_element(By.CSS_SELECTOR, 'section[id*="verified"], section[id*="promo"]')
                        except:
                            print(f"    ⚠️  WARNING: Could not find codes section")
                            break
                    
                    if codes_section:
                        show_more_buttons = codes_section.find_elements(By.XPATH, ".//button[contains(text(), 'Show more')]")
                        
                        print(f"    🔍 DEBUG: Found {len(show_more_buttons)} 'Show more' buttons in CODES section")
                        
                        if len(show_more_buttons) > 0:
                            button = show_more_buttons[0]
                            
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            self._random_delay(0.8, 1.2)
                            
                            try:
                                button.click()
                                codes_clicks += 1
                                print(f"    ✅ SUCCESS: Clicked CODES 'Show more' #{codes_clicks}")
                            except:
                                self.driver.execute_script("arguments[0].click();", button)
                                codes_clicks += 1
                                print(f"    ✅ SUCCESS: Clicked CODES 'Show more' #{codes_clicks} via JS")
                            
                            self._random_delay(2, 3)
                        else:
                            print(f"    ℹ️  INFO: No more 'Show more' buttons in CODES section (attempt {i+1}/{codes_clicks_limit})")
                            break
                    else:
                        print(f"    ⚠️  WARNING: Codes section not found")
                        break
                        
                except Exception as e:
                    print(f"    ⚠️  WARNING: Could not click codes 'Show more': {str(e)}")
                    break
            
            print(f"    ✅ Completed CODES section: {codes_clicks}/{codes_clicks_limit} clicks")
            
            # Small scroll down
            print("\n  🔽 Scrolling to deals section...")
            self.driver.execute_script("window.scrollBy(0, 400);")
            self._random_delay(1.5, 2)
            
            # Phase 2: Click DEALS "Show more" button
            print("\n  🎁 Phase 2: Expanding DEALS section (#best-deal-section)...")
            deals_clicks = 0
            
            for i in range(deals_clicks_limit):
                try:
                    self._random_delay(1.5, 2.5)
                    
                    # Find deals section
                    deals_section = None
                    try:
                        deals_section = self.driver.find_element(By.ID, 'best-deal-section')
                    except:
                        try:
                            deals_section = self.driver.find_element(By.CSS_SELECTOR, 'section[id*="deal"]')
                        except:
                            print(f"    ⚠️  WARNING: Could not find deals section")
                            break
                    
                    if deals_section:
                        show_more_buttons = deals_section.find_elements(By.XPATH, ".//button[contains(text(), 'Show more')]")
                        
                        print(f"    🔍 DEBUG: Found {len(show_more_buttons)} 'Show more' buttons in DEALS section")
                        
                        if len(show_more_buttons) > 0:
                            button = show_more_buttons[0]
                            
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                            self._random_delay(0.8, 1.2)
                            
                            try:
                                button.click()
                                deals_clicks += 1
                                print(f"    ✅ SUCCESS: Clicked DEALS 'Show more' #{deals_clicks}")
                            except:
                                self.driver.execute_script("arguments[0].click();", button)
                                deals_clicks += 1
                                print(f"    ✅ SUCCESS: Clicked DEALS 'Show more' #{deals_clicks} via JS")
                            
                            self._random_delay(2, 3)
                        else:
                            print(f"    ℹ️  INFO: No more 'Show more' buttons in DEALS section (attempt {i+1}/{deals_clicks_limit})")
                            break
                    else:
                        print(f"    ⚠️  WARNING: Deals section not found")
                        break
                        
                except Exception as e:
                    print(f"    ⚠️  WARNING: Could not click deals 'Show more': {str(e)}")
                    break
            
            print(f"    ✅ Completed DEALS section: {deals_clicks}/{deals_clicks_limit} clicks")
            
            # Final scroll
            print("\n  🔽 Final scroll to load all content...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self._random_delay(2, 3)
            
            self.driver.execute_script("window.scrollTo(0, 0);")
            self._random_delay(1, 2)
            
            print(f"\n  ✅ Finished: {codes_clicks} codes clicks + {deals_clicks} deals clicks = {codes_clicks + deals_clicks} total")
            
        except Exception as e:
            print(f"  ⚠️  WARNING: Error clicking 'Show more' buttons: {str(e)}")
    
    def _extract_code_data(self, card, store_name, position):
        """Extract all fields from a coupon code card"""
        data = {
            'source': 'SimplyCodes',
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
        title_elem = card.find('h3', {'data-testid': 'promotion-title'})
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)
        
        # Extract Description
        desc_elem = card.find('p', {'data-testid': 'promotion-subtitle'})
        if desc_elem:
            data['description'] = desc_elem.get_text(strip=True)
        
        # Extract Coupon Code (revealed code from button)
        code = self._extract_revealed_code(card)
        if code:
            data['coupon_code'] = code
        
        # Extract Verified status and other tags
        categories = []
        
        verified_elem = card.find('p', class_='text-citron')
        if verified_elem and 'verified' in verified_elem.get_text().lower():
            categories.append('Verified')
        
        # Extract Top Pick badge
        top_pick_elem = card.find('div', class_='bg-citron')
        if top_pick_elem and 'top pick' in top_pick_elem.get_text().lower():
            categories.append('Top Pick')
        
        data['category'] = ', '.join(categories) if categories else 'General'
        
        # Extract URL
        link_elem = card.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('/'):
                data['coupon_url'] = f"{self.base_url}{href}"
            else:
                data['coupon_url'] = href
        else:
            data['coupon_url'] = f"{self.base_url}/store/{store_name.replace('.com', '')}"
        
        # Extract expiry date
        data['expiry_date'] = self._extract_expiry_date(card)
        
        return data
    
    def _extract_deal_data(self, card, store_name, position):
        """Extract all fields from a deal card"""
        data = {
            'source': 'SimplyCodes',
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
        title_elem = card.find('h3', {'data-testid': 'promotion-title'})
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)
        
        # Extract Description
        desc_elem = card.find('span', {'data-testid': 'promotion-subtitle'})
        if not desc_elem:
            desc_elem = card.find('p', {'data-testid': 'promotion-subtitle'})
        if desc_elem:
            data['description'] = desc_elem.get_text(strip=True)
        
        # Extract tags/categories
        categories = []
        
        special_tags = card.find_all('span')
        for tag in special_tags:
            tag_text = tag.get_text(strip=True)
            if tag_text and tag_text not in ['Get deal', 'Show more']:
                if 'special offer' in tag_text.lower():
                    categories.append('Special Offer')
        
        data['category'] = ', '.join(categories) if categories else 'General'
        
        # Extract URL
        link_elem = card.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('/'):
                data['coupon_url'] = f"{self.base_url}{href}"
            else:
                data['coupon_url'] = href
        else:
            data['coupon_url'] = f"{self.base_url}/store/{store_name.replace('.com', '')}"
        
        # Extract expiry date
        data['expiry_date'] = self._extract_expiry_date(card)
        
        return data
    
    def _extract_revealed_code(self, card):
        """Extract revealed coupon code from card (after clicking Show Code)"""
        try:
            # Method 1: Look for code in button text
            button = card.find('button', {'data-testid': 'promotion-copy-code-button'})
            if button:
                button_text = button.get_text(strip=True)
                
                exclude_words = ['show code', 'get code', 'copy', 'copied', 'get deal', 'show more']
                
                if button_text.lower() not in exclude_words:
                    if re.match(r'^[A-Z0-9]{3,20}$', button_text):
                        return button_text
            
            # Method 2: Look for code in specific highlighted elements
            code_containers = card.find_all(['span', 'div', 'p'])
            for elem in code_containers:
                elem_text = elem.get_text(strip=True)
                
                if elem_text.lower() in ['show code', 'get code', 'copy', 'copied', 'get deal']:
                    continue
                
                if re.match(r'^[A-Z0-9]{3,20}$', elem_text):
                    return elem_text
            
            # Method 3: Search all text for code pattern
            all_text = card.get_text()
            code_pattern = r'\b([A-Z0-9]{4,20})\b'
            matches = re.findall(code_pattern, all_text)
            
            for match in matches:
                if match.upper() not in ['SHOW', 'CODE', 'GET', 'DEAL', 'TOP', 'PICK', 'COPY', 'COPIED', 'MORE']:
                    return match
            
            return ''
            
        except Exception as e:
            return ''
    
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
            
            # Pattern 4: "Limited time"
            if 'limited time' in text_content.lower():
                expiry_date = datetime.now() + timedelta(days=30)
                return expiry_date.strftime('%Y-%m-%d')
            
            return ''
            
        except Exception as e:
            return ''