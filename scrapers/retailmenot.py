import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import random
from base_scraper import BaseScraper

class RetailMeNotScraper(BaseScraper):
    """Scraper for RetailMeNot coupon website"""
    
    def __init__(self, headless=True, debug=False, config=None):
        """Initialize the scraper"""
        super().__init__(headless, debug, config)
        self.base_url = "https://www.retailmenot.com"
        self.codes_revealed_globally = False
        self.codes_checked_once = False
        self.no_valid_codes_detected = False  # NEW FLAG
        
    def _try_close_popup(self, timeout=2, context="general"):
        """Try to close popup with short timeout - ALSO CHECK FOR 'NO VALID CODES' MESSAGE"""
        
        # FIRST: Check if popup contains "no valid codes" message
        try:
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Look for the error message in popup
            error_phrases = [
                'no more valid codes',
                'no valid codes left',
                'there are no more valid codes left',
                'code has expired',
                'no longer available'
            ]
            
            # Check for error div with x-show="error"
            error_divs = soup.find_all(attrs={'x-show': re.compile(r'error', re.I)})
            for div in error_divs:
                error_text = div.get_text(strip=True).lower()
                if any(phrase in error_text for phrase in error_phrases):
                    print(f"\n⚠️  DETECTED: Store has no valid codes left!")
                    print(f"   Message: '{div.get_text(strip=True)}'")
                    self.no_valid_codes_detected = True
                    # Still close the popup and continue
                    break
            
            # Also check for specific error paragraph
            error_elem = soup.find('p', class_='text-xl font-semibold')
            if error_elem:
                error_text = error_elem.get_text(strip=True).lower()
                if any(phrase in error_text for phrase in error_phrases):
                    print(f"\n⚠️  DETECTED: Store has no valid codes left!")
                    print(f"   Message: '{error_elem.get_text(strip=True)}'")
                    self.no_valid_codes_detected = True
        
        except Exception:
            pass  # If checking fails, just continue with closing popup
        
        # SECOND: Close the popup as usual
        popup_selectors = [
            'button[aria-label*="close" i]',
            'button[title*="close" i]',
            'button.close',
            'button[class*="close"]',
            '[class*="close-button"]',
            'button[class*="ml-auto"]',
            'div[role="dialog"] button',
        ]
        
        for selector in popup_selectors:
            try:
                close_button = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                
                if close_button.is_displayed():
                    close_button.click()
                    print(f"  SUCCESS: Closed popup ({context})")
                    time.sleep(0.5)
                    return True
                    
            except (TimeoutException, NoSuchElementException):
                continue
            except Exception:
                continue
        
        return False
    
    def search_store(self, store_name):
        """Search for a store using the search bar"""
        try:
            print(f"Searching for: {store_name}")
            
            self.driver.get(self.base_url)
            print("  -> Loaded homepage")
            
            self._try_close_popup(timeout=2, context="homepage")
            
            self._random_delay(2, 3)
            
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[aria-label*="Search"]',
                'input.z-20',
                'input[x-model="term"]'
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
                print("  WARNING: Search input not found, trying direct URL...")
                return self._try_direct_url(store_name)
            
            self.driver.execute_script("arguments[0].scrollIntoView(true);", search_input)
            time.sleep(0.3)
            
            try:
                search_input.click()
            except:
                self.driver.execute_script("arguments[0].click();", search_input)
            
            time.sleep(0.3)
            search_input.clear()
            time.sleep(0.2)
            
            print(f"  -> Typing '{store_name}'...")
            for char in store_name:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.12))
            
            self._random_delay(0.5, 1)
            search_input.send_keys(Keys.RETURN)
            
            print("  -> Waiting for results...")
            self._random_delay(4, 6)
            
            self._try_close_popup(timeout=2, context="after search")
            
            current_url = self.driver.current_url
            print(f"  -> Current URL: {current_url}")
            
            if '/view/' in current_url:
                print(f"SUCCESS: Successfully navigated to store page")
                return True
            else:
                print(f"WARNING: Not on store page, trying direct URL...")
                return self._try_direct_url(store_name)
                
        except Exception as e:
            print(f"ERROR: Error during search: {str(e)}")
            return self._try_direct_url(store_name)
    
    def _try_direct_url(self, store_name):
        """Fallback: Try to navigate directly to store page"""
        try:
            print(f"  -> Attempting direct URL for {store_name}")
            
            clean_name = store_name.lower().strip()
            if not clean_name.endswith('.com'):
                clean_name += '.com'
            
            direct_url = f"{self.base_url}/view/{clean_name}"
            
            print(f"  -> Navigating to: {direct_url}")
            self.driver.get(direct_url)
            self._random_delay(3, 5)
            
            self._try_close_popup(timeout=2, context="direct URL")
            
            page_source = self.driver.page_source.lower()
            
            if '404' in page_source or 'not found' in page_source:
                print(f"  ERROR: Store page not found (404)")
                return False
            
            print(f"  SUCCESS: Direct URL successful")
            return True
            
        except Exception as e:
            print(f"  ERROR: Direct URL failed: {str(e)}")
            return False
    
    def scrape_store(self, store_name):
        """Scrape all coupons and deals for a specific store"""
        # Reset flags for new store
        self.no_valid_codes_detected = False
        self.codes_revealed_globally = False
        self.codes_checked_once = False
        self.coupons_data = []  # Clear previous data
        
        try:
            if not self.driver:
                self.setup_driver()
            
            if not self.search_store(store_name):
                print(f"ERROR: Could not access store page for {store_name}")
                return []
            
            print("\nWaiting for page to fully load...")
            time.sleep(2)
            
            print("\nScrolling to load all offers...")
            self._scroll_page()
            
            print("\nParsing page content...")
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')
            
            if self.debug:
                debug_file = f'debug_page_{store_name.replace(".com", "")}.html'
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"  -> Saved page HTML to: {debug_file}")
            
            print("\nLooking for offers...")
            
            offers_container = soup.find('div', {'data-component-name': 'top_offers'})
            
            if not offers_container:
                print("  WARNING: 'top_offers' container not found")
                return []
            
            print("  SUCCESS: Found offers container")
            
            all_children = offers_container.find_all('div', recursive=False)
            
            offer_divs = []
            for div in all_children:
                classes = div.get('class', [])
                if 'border' in classes and 'rounded-lg' in classes:
                    offer_divs.append(div)
            
            if len(offer_divs) == 0:
                print("  -> Trying fallback: finding by titles...")
                h3_elements = offers_container.find_all('h3', class_='font-sans')
                
                for h3 in h3_elements:
                    parent = h3.find_parent('div', class_=re.compile(r'border'))
                    if parent and parent not in offer_divs:
                        offer_divs.append(parent)
            
            print(f"  -> Found {len(offer_divs)} total offers\n")
            
            if len(offer_divs) == 0:
                print("ERROR: No offers to scrape")
                return []
            
            scraped_count = 0
            for index, offer_div in enumerate(offer_divs, 1):
                try:
                    offer_data = self._extract_offer_data(offer_div, store_name, index)
                    
                    if offer_data and offer_data.get('title'):
                        self.coupons_data.append(offer_data)
                        scraped_count += 1
                        print(f"SUCCESS [{scraped_count}/{len(offer_divs)}] {offer_data['deal_type'].upper()}: {offer_data['title'][:55]}...")
                    
                    self._random_delay(0.2, 0.5)
                    
                except Exception as e:
                    print(f"WARNING: Error extracting offer {index}: {str(e)}")
                    continue
            
            print(f"\nSUCCESS: Successfully extracted {scraped_count} offers")
            
            # NEW LOGIC: Check for codes, but skip if "no valid codes" detected
            codes_to_reveal = [c for c in self.coupons_data if c['deal_type'] == 'code' and c['uuid']]
            
            if len(codes_to_reveal) > 0:
                print(f"\nAttempting to reveal coupon codes...")
                self._smart_reveal_codes(store_name)
                
                # If no valid codes detected, mark all code coupons
                if self.no_valid_codes_detected:
                    print(f"\n⚠️  Marking all codes as 'NO VALID CODES LEFT' for this store")
                    for coupon in self.coupons_data:
                        if coupon['deal_type'] == 'code' and not coupon.get('coupon_code'):
                            coupon['coupon_code'] = 'NO VALID CODES LEFT'
            else:
                print(f"\nNo codes to reveal (only deals)")
            
            return self.coupons_data
            
        except Exception as e:
            print(f"\nERROR: FATAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if self.debug:
                input("   Press Enter to close browser...")
            
            return []
    
    def _scroll_page(self):
        """Scroll page smoothly to load all dynamic content"""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_attempts = 3
            
            while scroll_attempts < max_attempts:
                for i in range(2):
                    scroll_position = (i + 1) * (last_height // 2)
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                    time.sleep(random.uniform(0.3, 0.6))
                
                time.sleep(1)
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scroll_attempts += 1
            
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.5)
            print("  SUCCESS: Scrolling complete")
            
        except Exception as e:
            print(f"  WARNING: Scroll error: {str(e)}")
    
    def _extract_offer_data(self, offer_div, store_name, position):
        """Extract all fields from a single offer div"""
        data = {
            'source': 'RetailMeNot',
            'store_name': store_name.replace('.com', '').strip().title(),
            'title': '',
            'description': '',
            'coupon_code': '',
            'deal_type': '',
            'expiry_date': '',
            'coupon_url': '',
            'category': '',
            'uuid': '',
            'button_text': ''
        }
        
        # Extract Title from discount div (25% Off)
        discount_div = offer_div.find('div', class_='text-purple-700')
        if discount_div:
            discount_parts = discount_div.find_all('p', class_='leading-none')
            if discount_parts:
                title_parts = [p.get_text(strip=True) for p in discount_parts]
                data['title'] = ' '.join(title_parts)
            else:
                data['title'] = discount_div.get_text(strip=True)
        
        # Extract Description from h3 tag
        h3_elem = offer_div.find('h3', class_='font-sans')
        if not h3_elem:
            h3_elem = offer_div.find('h3')
        if h3_elem:
            data['description'] = h3_elem.get_text(strip=True)
        
        if not data['title'] and data['description']:
            data['title'] = data['description']
        
        # Extract button text to detect tap/click to apply
        button_div = offer_div.find('div', class_='bg-gray-100')
        if button_div:
            data['button_text'] = button_div.get_text(strip=True)
        
        # Extract Deal Type
        deal_type_elem = offer_div.find('span', class_='bg-gray-200')
        if deal_type_elem:
            deal_type_text = deal_type_elem.get_text(strip=True).lower()
            if 'code' in deal_type_text:
                data['deal_type'] = 'code'
            elif 'sale' in deal_type_text:
                data['deal_type'] = 'deal'
            else:
                data['deal_type'] = 'deal'
        else:
            if discount_div and 'sale' in discount_div.get_text().lower():
                data['deal_type'] = 'deal'
            else:
                data['deal_type'] = 'code'
        
        # Extract additional description
        prose_div = offer_div.find('div', class_='prose')
        if prose_div:
            paragraphs = prose_div.find_all('p')
            prose_parts = [p.get_text(strip=True) for p in paragraphs]
            if prose_parts:
                data['description'] += ' ' + ' '.join(prose_parts)
        
        # Extract URL and UUID
        link_elem = offer_div.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('/'):
                data['coupon_url'] = f"https://www.retailmenot.com{href}"
            else:
                data['coupon_url'] = href
            
            uuid_attr = link_elem.get('data-content-uuid')
            if uuid_attr:
                data['uuid'] = uuid_attr
        
        # Extract Expiry Date
        data['expiry_date'] = self._extract_expiry_date(offer_div)
        
        # Extract Category
        category_tags = []
        tag_divs = offer_div.find_all('div', class_='rounded-[4px]')
        for tag in tag_divs:
            tag_text = tag.get_text(strip=True)
            exclude_keywords = ['verified', 'code', 'deal', 'sale', 'user', 'saved', 'interested', 'cash back', '%', 'limited time']
            if tag_text and not any(keyword in tag_text.lower() for keyword in exclude_keywords):
                category_tags.append(tag_text)
        
        data['category'] = ', '.join(category_tags[:3]) if category_tags else 'General'
        
        return data
    
    def _extract_expiry_date(self, offer_div):
        """Extract and parse expiry date"""
        text_content = offer_div.get_text()
        
        pattern1 = r'(?:Expires?|Ends?)\s+(\d{1,2})/(\d{1,2})/(\d{4})'
        match1 = re.search(pattern1, text_content, re.IGNORECASE)
        if match1:
            month, day, year = match1.groups()
            try:
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
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
        
        pattern3 = r'(?:Expires? in|Ends? in)\s+(\d+)\s+days?'
        match3 = re.search(pattern3, text_content, re.IGNORECASE)
        if match3:
            days = int(match3.group(1))
            expiry_date = datetime.now() + timedelta(days=days)
            return expiry_date.strftime('%Y-%m-%d')
        
        if 'limited time' in text_content.lower():
            expiry_date = datetime.now() + timedelta(days=30)
            return expiry_date.strftime('%Y-%m-%d')
        
        return ''
    
    def _is_non_code_text(self, text):
        """Check if text is a non-code message (not an actual coupon code)"""
        if not text:
            return False, ''
        
        text_lower = text.lower().strip()
        
        non_code_patterns = {
            'code provided at checkout': 'CODE AT CHECKOUT',
            'provided at checkout': 'CODE AT CHECKOUT',
            'no code required': 'NO CODE REQUIRED',
            'no code needed': 'NO CODE REQUIRED',
            'automatic discount': 'AUTO DISCOUNT',
            'auto applied': 'AUTO APPLIED',
            'applied at checkout': 'AUTO APPLIED',
            'discount applied automatically': 'AUTO APPLIED',
            'automatically applied': 'AUTO APPLIED',
            'see site for details': 'SEE SITE',
            'visit site': 'SEE SITE',
            'shop now': 'NO CODE REQUIRED',
            'get deal': 'NO CODE REQUIRED',
            'tap to apply': 'TAP TO APPLY',
            'click to apply': 'CLICK TO APPLY',
            'copy': '',
            'copied': '',
            'show code': '',
            'get code': '',
        }
        
        for pattern, normalized in non_code_patterns.items():
            if pattern in text_lower:
                return True, normalized if normalized else ''
        
        if len(text) > 25:
            return True, 'SEE SITE'
        
        if ' ' in text and len(text) > 5:
            return True, 'SEE SITE'
        
        return False, ''
    
    def _smart_reveal_codes(self, store_name):
        """Smart code revelation - Filter tap/click to apply & code at checkout"""
        
        # EARLY EXIT: If "no valid codes" detected, skip all clicking
        if self.no_valid_codes_detected:
            print(f"\n⚠️  Skipping code revelation - store has no valid codes")
            return
        
        coupons_to_reveal = [c for c in self.coupons_data if c['deal_type'] == 'code' and c['uuid']]
        
        # Filter: Check button_text for exclusions
        filtered_coupons = []
        for coupon in coupons_to_reveal:
            combined_text = (
                coupon.get('title', '') + ' ' + 
                coupon.get('description', '') + ' ' + 
                coupon.get('button_text', '')
            ).lower()
            
            exclude_keywords = [
                'tap to apply',
                'click to apply',
                'tap offer',
                'click offer',
                'tap coupon',
                'click coupon',
                'code provided at checkout',
                'provided at checkout',
                'no code required',
                'no code needed',
                'automatic discount',
                'auto applied',
            ]
            
            is_non_code, message = self._is_non_code_text(coupon.get('button_text', ''))
            
            if any(keyword in combined_text for keyword in exclude_keywords) or is_non_code:
                if is_non_code and message:
                    coupon['coupon_code'] = message
                    print(f"INFO: Marked '{message}': {coupon['title'][:40]}...")
                else:
                    print(f"INFO: Skipping '{coupon.get('button_text', 'special')}' coupon: {coupon['title'][:40]}...")
                continue
            
            filtered_coupons.append(coupon)
        
        coupons_to_reveal = filtered_coupons
        
        if not coupons_to_reveal:
            print("INFO: No codes to reveal (filtered out special coupons)")
            return
        
        print(f"Found {len(coupons_to_reveal)} codes to reveal\n")
        
        revealed_count = 0
        
        for index, coupon in enumerate(coupons_to_reveal, 1):
            # EARLY EXIT: If "no valid codes" was detected during clicking, stop
            if self.no_valid_codes_detected:
                print(f"\n⚠️  Stopping code revelation - no valid codes detected")
                break
            
            try:
                if self.codes_revealed_globally and index > 1:
                    print(f"[{index}/{len(coupons_to_reveal)}] All codes revealed, extracting...")
                    code = self._extract_code_from_page(coupon['uuid'])
                    if code:
                        coupon['coupon_code'] = code
                        revealed_count += 1
                        print(f"  SUCCESS: Code: {code}")
                    else:
                        print(f"  INFO: Code not found")
                    continue
                
                print(f"[{index}/{len(coupons_to_reveal)}] Checking if code visible...")
                code = self._extract_code_from_page(coupon['uuid'])
                
                if code:
                    coupon['coupon_code'] = code
                    revealed_count += 1
                    print(f"  SUCCESS: Code already visible: {code}")
                else:
                    print(f"[{index}/{len(coupons_to_reveal)}] Code not visible, clicking...")
                    
                    success, code = self._click_show_code_safe(coupon['uuid'])
                    
                    if success and code:
                        coupon['coupon_code'] = code
                        revealed_count += 1
                        print(f"  SUCCESS: Code revealed: {code}")
                        
                        if not self.codes_checked_once:
                            self._check_if_all_codes_revealed()
                            self.codes_checked_once = True
                    else:
                        print(f"  WARNING: Could not reveal code")
                
                self._random_delay(1, 2)
                
            except Exception as e:
                print(f"  ERROR: Error: {str(e)}")
                continue
        
        print(f"\nSUCCESS: Revealed {revealed_count}/{len(coupons_to_reveal)} codes")
    
    def _click_show_code_safe(self, uuid):
        """Click Show Code, close OLD page, stay on NEW page"""
        original_window = self.driver.current_window_handle
        
        try:
            original_windows = set(self.driver.window_handles)
            
            show_code_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f'a[data-content-uuid="{uuid}"]'))
            )
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", show_code_link)
            time.sleep(0.3)
            
            if not self._safe_click_with_retry(show_code_link):
                return False, ''
            
            print("    -> Waiting for new page...")
            self._random_delay(2, 4)
            
            new_windows = set(self.driver.window_handles)
            
            if len(new_windows) > len(original_windows):
                new_window = (new_windows - original_windows).pop()
                
                print("    -> Switching to new page...")
                self.driver.switch_to.window(new_window)
                
                time.sleep(2)
                
                print("    -> Closing popup on new page (checking for 'no valid codes')...")
                self._try_close_popup(timeout=3, context="code reveal")
                
                # Check if "no valid codes" was detected
                if self.no_valid_codes_detected:
                    print("    ⚠️  'No valid codes' detected - closing old page and stopping")
                    try:
                        self.driver.switch_to.window(original_window)
                        self.driver.close()
                    except:
                        pass
                    self.driver.switch_to.window(new_window)
                    return True, 'NO VALID CODES LEFT'
                
                code = self._extract_code_from_current_page()
                
                if code == 'NO VALID CODES LEFT':
                    print("    WARNING: Code expired/invalid")
                    try:
                        self.driver.switch_to.window(original_window)
                        self.driver.close()
                        print("    SUCCESS: Old page closed")
                    except Exception as e:
                        print(f"    WARNING: Could not close old page: {str(e)}")
                    
                    self.driver.switch_to.window(new_window)
                    return True, 'NO VALID CODES LEFT'
                
                print("    -> Closing old page...")
                try:
                    self.driver.switch_to.window(original_window)
                    self.driver.close()
                    print("    SUCCESS: Old page closed")
                except Exception as e:
                    print(f"    WARNING: Could not close old page: {str(e)}")
                
                print("    -> Staying on new page...")
                self.driver.switch_to.window(new_window)
                
                return (True, code) if code else (False, '')
            else:
                print("    -> No new window, code revealed inline")
                code = self._extract_code_from_page(uuid)
                return (True, code) if code else (False, '')
                
        except Exception as e:
            print(f"    ERROR: Click error: {str(e)}")
            
            try:
                available_windows = self.driver.window_handles
                if available_windows:
                    self.driver.switch_to.window(available_windows[0])
                    print("    INFO: Recovered to available window")
            except:
                pass
            
            return False, ''
   
    def _extract_code_from_current_page(self):
        """Extract coupon code from current page - Handle non-code messages"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            # Check for error messages first
            error_keywords = [
                'no more valid codes',
                'no valid codes left',
                'code has expired',
                'code is no longer valid',
                'this offer has expired',
                'offer expired',
                'no longer available',
                'not available',
            ]
            
            error_elem = soup.find('p', class_='text-xl font-semibold')
            if error_elem:
                error_text = error_elem.get_text(strip=True).lower()
                if any(keyword in error_text for keyword in error_keywords):
                    print(f"    WARNING: Detected: {error_text}")
                    return 'NO VALID CODES LEFT'
            
            error_divs = soup.find_all(attrs={'x-show': re.compile(r'error', re.I)})
            for div in error_divs:
                error_text = div.get_text(strip=True).lower()
                if any(keyword in error_text for keyword in error_keywords):
                    print(f"    WARNING: Detected: {error_text}")
                    return 'NO VALID CODES LEFT'
            
            page_text = soup.get_text().lower()
            if any(keyword in page_text for keyword in error_keywords):
                for keyword in error_keywords:
                    if keyword in page_text:
                        elem = soup.find(string=re.compile(keyword, re.I))
                        if elem:
                            parent = elem.find_parent(['p', 'div', 'span'])
                            if parent and any(cls in parent.get('class', []) for cls in ['font-semibold', 'font-bold', 'text-xl']):
                                print(f"    WARNING: Code expired or invalid")
                                return 'NO VALID CODES LEFT'
            
            exclude_words = ['copy', 'copied', 'show code', 'get code', 'get deal']
            
            # Try all extraction methods
            revealed_divs = soup.find_all('div', class_='bg-gray-100')
            for div in revealed_divs:
                code_text = div.get_text(strip=True)
                
                is_non_code, message = self._is_non_code_text(code_text)
                if is_non_code:
                    if message:
                        print(f"    INFO: Found non-code text: {code_text}")
                        return message
                    continue
                
                if code_text and re.match(r'^[A-Z0-9]{3,20}$', code_text):
                    if code_text.lower() not in exclude_words:
                        return code_text
            
            elem_with_code = soup.find(attrs={'data-clipboard-text': True})
            if elem_with_code:
                code = elem_with_code.get('data-clipboard-text', '').strip()
                
                is_non_code, message = self._is_non_code_text(code)
                if is_non_code and message:
                    print(f"    INFO: Found non-code text in clipboard: {code}")
                    return message
                
                if code and re.match(r'^[A-Z0-9]{3,20}$', code) and code.lower() not in exclude_words:
                    return code
            
            code_selectors = [
                {'class': re.compile(r'.*code.*', re.I)},
                {'class': re.compile(r'.*coupon.*', re.I)},
            ]
            
            for selector in code_selectors:
                code_elem = soup.find(['div', 'span', 'code'], selector)
                if code_elem:
                    code_text = code_elem.get_text(strip=True)
                    
                    is_non_code, message = self._is_non_code_text(code_text)
                    if is_non_code and message:
                        print(f"    INFO: Found non-code text: {code_text}")
                        return message
                    
                    if re.match(r'^[A-Z0-9]{3,20}$', code_text) and code_text.lower() not in exclude_words:
                        return code_text
            
            buttons = soup.find_all('button', string=re.compile(r'^[A-Z0-9]{3,20}$'))
            for button in buttons:
                code_text = button.get_text(strip=True)
                
                is_non_code, message = self._is_non_code_text(code_text)
                if is_non_code:
                    continue
                
                if code_text.lower() not in exclude_words:
                    return code_text
            
            all_elements = soup.find_all(['div', 'span', 'p'])
            for elem in all_elements:
                text = elem.get_text(strip=True)
                
                is_non_code, message = self._is_non_code_text(text)
                if is_non_code:
                    continue
                
                if re.match(r'^[A-Z0-9]{3,20}$', text) and text.lower() not in exclude_words:
                    return text
            
            return ''
            
        except Exception as e:
            return ''
   
    def _extract_code_from_page(self, uuid):
        """Extract code from main page - Handle non-code messages"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            coupon_link = soup.find('a', {'data-content-uuid': uuid})
            if not coupon_link:
                return ''
            
            parent_div = coupon_link.find_parent('div', class_=re.compile(r'border'))
            if not parent_div:
                return ''
            
            exclude_words = ['copy', 'copied', 'show code', 'get code', 'get deal']
            
            revealed_code_div = parent_div.find('div', class_='bg-gray-100')
            if revealed_code_div:
                code_text = revealed_code_div.get_text(strip=True)
                
                is_non_code, message = self._is_non_code_text(code_text)
                if is_non_code and message:
                    return message
                
                if code_text and re.match(r'^[A-Z0-9]{3,20}$', code_text) and code_text.lower() not in exclude_words:
                    return code_text
            
            purple_div = parent_div.find('div', class_='bg-purple-700')
            if purple_div:
                code_text = purple_div.get_text(strip=True)
                
                is_non_code, message = self._is_non_code_text(code_text)
                if is_non_code and message:
                    return message
                
                if code_text and code_text.lower() not in exclude_words:
                    if re.match(r'^[A-Z0-9]{3,20}$', code_text):
                        return code_text
            
            code_elem = parent_div.find(string=re.compile(r'^[A-Z0-9]{3,20}$'))
            if code_elem:
                code_text = code_elem.strip()
                
                is_non_code, message = self._is_non_code_text(code_text)
                if is_non_code:
                    return message if message else ''
                
                if code_text.lower() not in exclude_words:
                    return code_text
            
            button = parent_div.find('button', string=re.compile(r'^[A-Z0-9]{3,20}$'))
            if button:
                code_text = button.get_text(strip=True)
                
                is_non_code, message = self._is_non_code_text(code_text)
                if is_non_code:
                    return ''
                
                if code_text.lower() not in exclude_words:
                    return code_text
            
            divs = parent_div.find_all('div')
            for div in divs:
                text = div.get_text(strip=True)
                
                is_non_code, message = self._is_non_code_text(text)
                if is_non_code:
                    continue
                
                if re.match(r'^[A-Z0-9]{3,20}$', text) and text.lower() not in exclude_words:
                    return text
            
            return ''
            
        except Exception as e:
            return ''
  
    def _check_if_all_codes_revealed(self):
        """Check if clicking one code revealed all codes"""
        try:
            print("\n  Checking if all codes revealed...")
            
            time.sleep(1)
            
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            
            code_buttons = soup.find_all('button', string=re.compile(r'^[A-Z0-9]{3,20}$'))
            code_divs = soup.find_all('div', string=re.compile(r'^[A-Z0-9]{3,20}$'))
            
            total_codes = len(code_buttons) + len(code_divs)
            
            if total_codes >= 2:
                self.codes_revealed_globally = True
                print(f"  SUCCESS: All codes revealed! Found {total_codes} visible codes\n")
            else:
                self.codes_revealed_globally = False
                print("  INFO: Codes need individual clicks\n")
                
        except Exception as e:
            self.codes_revealed_globally = False