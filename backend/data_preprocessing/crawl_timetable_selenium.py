"""
Improved script to crawl bus timetable data using Selenium for JavaScript-rendered content
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
from pathlib import Path
import re


class BusTimetableCrawler:
    def __init__(self, base_dir='Bus_route_data/HCMC_bus_routes', headless=True):
        self.base_url = 'http://buyttphcm.com.vn/en-us/RouteDetail'
        self.base_dir = Path(base_dir)
        self.headless = headless
        self.driver = None
    
    def init_driver(self):
        """Initialize Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            print("Chrome WebDriver initialized successfully")
        except Exception as e:
            print(f"Error initializing Chrome WebDriver: {e}")
            print("Please make sure Chrome and ChromeDriver are installed")
            raise
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def get_route_page(self, route_id):
        """Navigate to route page and wait for timetable to load"""
        url = f"{self.base_url}?rId={route_id}&sP=Route"
        
        try:
            print(f"Loading page: {url}")
            self.driver.get(url)
            
            # Wait for the timetable tab to be clickable
            wait = WebDriverWait(self.driver, 15)
            
            # Click on the Timetables tab
            timetable_tab = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[@href='#tabs-2' and contains(text(), 'Timetables')]"))
            )
            timetable_tab.click()
            print("Clicked on Timetables tab")
            
            # Wait for timetable content to load (wait for loading spinner to disappear)
            time.sleep(3)  # Give it a moment for JavaScript to execute
            
            # Wait for timetable content
            wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "timetableInfo"))
            )
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            return True
        except Exception as e:
            print(f"Error loading route {route_id}: {e}")
            return False
    
    def extract_timetable_data(self):
        """Extract timetable data from the loaded page"""
        timetables = {'outbound': [], 'inbound': []}
        
        try:
            # Find the timetable container
            timetable_div = self.driver.find_element(By.ID, "accTimetable")
            
            # Look for all accordion sections (each direction has its own section)
            sections = timetable_div.find_elements(By.CSS_SELECTOR, "h3, .ui-accordion-header")
            
            if not sections:
                # Try alternative structure
                sections = timetable_div.find_elements(By.XPATH, ".//*[contains(@class, 'ui-accordion-header') or contains(@class, 'accordion-header')]")
            
            print(f"Found {len(sections)} timetable sections")
            
            for idx, section in enumerate(sections):
                # Get the direction from section header
                section_text = section.text.lower()
                print(f"Section {idx}: {section_text[:50]}")
                
                # Determine direction
                direction = None
                if any(keyword in section_text for keyword in ['outbound', 'chiều đi', 'lượt đi', 'to']):
                    # Check if it's the first "to" (outbound)
                    if timetables['outbound'] == []:
                        direction = 'outbound'
                elif any(keyword in section_text for keyword in ['inbound', 'chiều về', 'lượt về', 'return']):
                    direction = 'inbound'
                
                # If still no direction, assign based on order
                if direction is None:
                    if idx == 0:
                        direction = 'outbound'
                    elif idx == 1:
                        direction = 'inbound'
                
                if direction:
                    # Click to expand the section if collapsed
                    try:
                        if 'ui-accordion-header-collapsed' in section.get_attribute('class'):
                            section.click()
                            time.sleep(1)
                    except:
                        pass
                    
                    # Find the content panel
                    content = None
                    try:
                        # Try to find the next sibling div
                        content = section.find_element(By.XPATH, "./following-sibling::div[1]")
                    except:
                        try:
                            # Alternative: find by class
                            parent = section.find_element(By.XPATH, "..")
                            content = parent.find_element(By.CSS_SELECTOR, ".ui-accordion-content")
                        except:
                            pass
                    
                    if content:
                        # Extract table data
                        tables = content.find_elements(By.TAG_NAME, "table")
                        for table in tables:
                            data = self.parse_table_element(table)
                            if data:
                                timetables[direction].extend(data)
                    
                    print(f"  Direction: {direction}, Rows extracted: {len(timetables[direction])}")
            
            return timetables
            
        except Exception as e:
            print(f"Error extracting timetable: {e}")
            import traceback
            traceback.print_exc()
            return timetables
    
    def parse_table_element(self, table):
        """Parse a Selenium WebElement table"""
        try:
            rows = table.find_elements(By.TAG_NAME, "tr")
            if len(rows) < 2:
                return None
            
            # Extract headers
            header_row = rows[0]
            headers = []
            for cell in header_row.find_elements(By.CSS_SELECTOR, "th, td"):
                text = cell.text.strip()
                headers.append(text if text else f'Column_{len(headers)}')
            
            if not headers:
                return None
            
            # Extract data rows
            data = []
            for row in rows[1:]:
                cells = row.find_elements(By.CSS_SELECTOR, "td, th")
                if cells:
                    row_data = {}
                    for idx, cell in enumerate(cells):
                        if idx < len(headers):
                            row_data[headers[idx]] = cell.text.strip()
                    if row_data:
                        data.append(row_data)
            
            return data if data else None
        except Exception as e:
            print(f"Error parsing table: {e}")
            return None
    
    def save_timetable(self, route_id, direction, data):
        """Save timetable data to CSV"""
        if not data or len(data) == 0:
            print(f"No data to save for route {route_id} {direction}")
            return False
        
        route_dir = self.base_dir / str(route_id)
        route_dir.mkdir(parents=True, exist_ok=True)
        
        filename = route_dir / f'timetable_{direction}.csv'
        
        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"✓ Saved {filename} ({len(data)} rows)")
            return True
        except Exception as e:
            print(f"Error saving {filename}: {e}")
            return False
    
    def crawl_route(self, route_id):
        """Crawl timetable for a single route"""
        print(f"\n{'='*60}")
        print(f"Crawling route {route_id}...")
        print(f"{'='*60}")
        
        if not self.get_route_page(route_id):
            return False
        
        timetables = self.extract_timetable_data()
        
        success = False
        for direction, data in timetables.items():
            if data:
                if self.save_timetable(route_id, direction, data):
                    success = True
            else:
                print(f"No {direction} timetable found for route {route_id}")
        
        return success
    
    def get_existing_routes(self):
        """Get list of route IDs from existing directory structure"""
        routes = []
        if self.base_dir.exists():
            for item in self.base_dir.iterdir():
                if item.is_dir():
                    try:
                        route_id = int(item.name)
                        routes.append(route_id)
                    except ValueError:
                        pass
        return sorted(routes)
    
    def crawl_all_routes(self, route_ids=None, delay=2):
        """Crawl timetables for all routes"""
        if route_ids is None:
            route_ids = self.get_existing_routes()
        
        if not route_ids:
            print("No routes found. Please provide route IDs.")
            return
        
        print(f"Found {len(route_ids)} routes to crawl: {route_ids}")
        
        try:
            self.init_driver()
            
            success_count = 0
            failed_routes = []
            
            for route_id in route_ids:
                try:
                    if self.crawl_route(route_id):
                        success_count += 1
                    else:
                        failed_routes.append(route_id)
                    
                    # Be polite to the server
                    time.sleep(delay)
                except Exception as e:
                    print(f"Unexpected error crawling route {route_id}: {e}")
                    failed_routes.append(route_id)
            
            print(f"\n{'='*60}")
            print(f"Crawling complete!")
            print(f"Success: {success_count}/{len(route_ids)}")
            if failed_routes:
                print(f"Failed routes: {failed_routes}")
            print(f"{'='*60}")
            
        finally:
            self.close_driver()


def main():
    # Create crawler
    crawler = BusTimetableCrawler(headless=False)  # Set to True for headless mode
    
    # Option 1: Test with a single route first
    try:
        crawler.init_driver()
        crawler.crawl_route(1)
    finally:
        crawler.close_driver()
    
    # Option 2: Crawl all existing routes (uncomment to use)
    # crawler.crawl_all_routes()
    
    # Option 3: Crawl specific routes
    # crawler.crawl_all_routes(route_ids=[1, 4, 6, 9, 20])


if __name__ == '__main__':
    main()
