"""Debug script to inspect the HTML structure of the bus route page"""
import requests
from bs4 import BeautifulSoup

url = 'http://buyttphcm.com.vn/en-us/RouteDetail'
params = {'rId': 1, 'sP': 'Route'}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

response = requests.get(url, params=params, headers=headers, timeout=10)
print(f"Status Code: {response.status_code}")
print(f"URL: {response.url}")
print("\n" + "="*80)

soup = BeautifulSoup(response.text, 'html.parser')

# Save the HTML to a file for inspection
with open('debug_page.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())
print("HTML saved to debug_page.html")

# Look for all divs that might contain timetable
print("\nLooking for potential timetable containers...")
print("="*80)

# Check for tables
tables = soup.find_all('table')
print(f"\nFound {len(tables)} tables")
for i, table in enumerate(tables):
    print(f"\nTable {i+1}:")
    print(f"  Class: {table.get('class', 'None')}")
    print(f"  ID: {table.get('id', 'None')}")
    rows = table.find_all('tr')
    print(f"  Rows: {len(rows)}")
    if rows:
        print(f"  First row: {rows[0].get_text(strip=True)[:100]}")

# Check for divs with class containing 'timetable', 'schedule', 'time'
print("\n" + "="*80)
print("Looking for divs with timetable-related classes...")
potential_divs = soup.find_all('div', class_=lambda x: x and any(keyword in str(x).lower() for keyword in ['time', 'schedule', 'table']))
print(f"Found {len(potential_divs)} potential divs")
for div in potential_divs[:5]:  # Show first 5
    print(f"  Class: {div.get('class')}")
    print(f"  Text preview: {div.get_text(strip=True)[:100]}")
    print()

# Look for any elements with time-like patterns
print("\n" + "="*80)
print("Looking for elements with time patterns...")
import re
time_pattern = re.compile(r'\d{1,2}:\d{2}')
elements_with_time = soup.find_all(string=time_pattern)
print(f"Found {len(elements_with_time)} elements with time patterns")
for elem in elements_with_time[:10]:  # Show first 10
    parent = elem.parent
    print(f"  Tag: {parent.name}, Class: {parent.get('class', 'None')}, Text: {elem.strip()[:50]}")
