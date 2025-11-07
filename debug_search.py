from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument('--start-maximized')

driver = webdriver.Chrome(options=options)
driver.get("https://www.retailmenot.com")

print("Page loaded. Waiting 5 seconds...")
time.sleep(5)

# Find all input elements
inputs = driver.find_elements(By.TAG_NAME, 'input')
print(f"\nFound {len(inputs)} input elements:")

for i, inp in enumerate(inputs):
    try:
        print(f"\n{i+1}. Type: {inp.get_attribute('type')}")
        print(f"   Placeholder: {inp.get_attribute('placeholder')}")
        print(f"   Class: {inp.get_attribute('class')}")
        print(f"   Name: {inp.get_attribute('name')}")
    except:
        pass

input("\nPress Enter to close...")
driver.quit()
