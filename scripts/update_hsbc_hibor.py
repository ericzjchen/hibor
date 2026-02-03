#!/usr/bin/env python3
"""
HSBC HIBOR Monitor - English Version Only
Accurate date extraction from page content
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
import json
import re
import time
import os

# Data storage files
DATA_FILE = "api/hsbc_hibor.json"

def format_datetime(dt=None):
    """Format datetime to YYYYMMDD HH:MM:SS"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y%m%d %H:%M:%S')

def fetch_hibor_data():
    """Fetch HSBC HIBOR data using Selenium - English only"""
    url = "https://www.hsbc.com.hk/mortgages/tools/hibor-rate/"
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.add_argument('--accept-language=en-US,en;q=0.9')
    
    driver = None
    try:
        print("🚀 Starting browser for English page...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"🌐 Accessing: {url}")
        driver.get(url)
        
        # Wait for page load
        print("⏳ Waiting for page to load...")
        time.sleep(8)
        
        # Get page text content
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Extract HIBOR value and date
        result = extract_hibor_and_date(page_text)
        
        if result["success"]:
            # Create website_update_time from extracted date + fixed time
            data_date = result["data_date"]
            website_update_time = data_date.strftime('%Y%m%d') + " 11:00:00"
            
            print(f"✅ Successfully extracted data")
            print(f"   Page date: {data_date.strftime('%Y-%m-%d')}")
            print(f"   HIBOR value: {result['hibor_value']}%")
            
            driver.quit()
            
            return {
                "success": True,
                "hibor_value": result["hibor_value"],
                "website_update_time": website_update_time,
                "fetch_time": format_datetime(),
                "url": url
            }
        else:
            print(f"❌ Failed to extract data: {result.get('error', 'Unknown error')}")
            driver.quit()
            return {
                "success": False,
                "error": result.get("error", "Data extraction failed"),
                "fetch_time": format_datetime()
            }
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        if driver:
            driver.quit()
        return {
            "success": False,
            "error": f"Selenium error: {str(e)}",
            "fetch_time": format_datetime()
        }

def extract_hibor_and_date(page_text):
    """Extract HIBOR value and date from English page text"""
    lines = page_text.split('\n')
    
    # Save page content for debugging
    #debug_file = f"page_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    #with open(debug_file, 'w', encoding='utf-8') as f:
    #    f.write("=== PAGE CONTENT ===\n")
    #    for i, line in enumerate(lines):
    #        f.write(f"{i:3d}: {line}\n")
    #print(f"📄 Debug file saved: {debug_file}")
    
    # Step 1: Find the year from page (e.g., "2026 HIBOR for the interest period...")
    year = None
    year_patterns = [
        r'(\d{4})\s+HIBOR',
        r'HIBOR\s+(\d{4})',
        r'Year\s+(\d{4})',
        r'(\d{4})\s+HK\$',
    ]
    
    for line in lines:
        for pattern in year_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                year = int(match.group(1))
                print(f"✅ Found year: {year}")
                break
        if year:
            break
    
    if not year:
        year = datetime.now().year
        print(f"⚠️  Year not found, using current year: {year}")
    
    # Step 2: Find the first data line (latest HIBOR)
    # Expected format: "2 February 2.40000%" or "2 Feb 2.40000%"
    first_data_line = None
    hibor_value = None
    
    month_map = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    for line in lines:
        line = line.strip()
        
        # Match format: "2 February 2.40000%" or "30 January 2.62000%"
        pattern = r'^(\d{1,2})\s+([A-Za-z]+)\s+(\d+\.\d+)%$'
        match = re.match(pattern, line)
        
        if match:
            day_str = match.group(1)
            month_str = match.group(2).lower()
            hibor_str = match.group(3)
            
            # Get month number
            month_key = month_str[:3]  # Take first 3 chars
            month_num = month_map.get(month_key)
            
            if month_num and hibor_str:
                day = int(day_str)
                hibor_value = float(hibor_str)
                first_data_line = line
                
                print(f"✅ Found first data line: {line}")
                print(f"   Parsed: {year}-{month_num:02d}-{day:02d}, HIBOR: {hibor_value}%")
                
                # Create datetime object
                data_date = datetime(year, month_num, day)
                
                # Verify this is not a future date
                if data_date > datetime.now():
                    print(f"⚠️  Date {data_date.strftime('%Y-%m-%d')} is in future, adjusting year...")
                    # Probably wrong year, use previous year
                    data_date = datetime(year - 1, month_num, day)
                
                return {
                    "success": True,
                    "data_date": data_date,
                    "hibor_value": hibor_value
                }
    
    # Alternative pattern: date and HIBOR might be in separate elements
    if not first_data_line:
        # Look for any HIBOR value
        hibor_patterns = [
            r'(\d+\.\d{5})%',
            r'(\d+\.\d{4})%',
            r'(\d+\.\d{3})%',
            r'(\d+\.\d{2})%',
            r'(\d+\.\d)%',
        ]
        
        for pattern in hibor_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                plausible_values = [float(x) for x in matches if 0.1 < float(x) < 20]
                if plausible_values:
                    hibor_value = max(plausible_values)
                    print(f"✅ Found HIBOR value: {hibor_value}%")
                    
                    # Try to find date near the HIBOR
                    # Look for date patterns near where HIBOR appears
                    date_pattern = r'(\d{1,2})\s+([A-Za-z]+)'
                    date_match = re.search(date_pattern, page_text)
                    
                    if date_match:
                        day_str = date_match.group(1)
                        month_str = date_match.group(2).lower()
                        month_key = month_str[:3]
                        month_num = month_map.get(month_key)
                        
                        if month_num:
                            data_date = datetime(year, month_num, int(day_str))
                            return {
                                "success": True,
                                "data_date": data_date,
                                "hibor_value": hibor_value
                            }
    
    print("❌ Could not extract HIBOR and date from page")
    return {
        "success": False,
        "error": "No valid HIBOR data found in page"
    }

def load_history():
    """Load historical data"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "records" not in data:
                    data["records"] = []
                return data
        except Exception as e:
            print(f"⚠️  Failed to load history file: {e}")
    
    return {"records": []}

def save_history(history_data):
    """Save historical data"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Failed to save history file: {e}")
        return False

def get_last_record():
    """Get last recorded data"""
    history = load_history()
    if history["records"]:
        return history["records"][-1]
    return None

def should_record_new_data(new_website_update_time, new_hibor_value):
    """Check if new data should be recorded"""
    last_record = get_last_record()
    
    if last_record is None:
        return True
    
    # Check if website update time is different
    if last_record["website_update_time"] != new_website_update_time:
        return True
    
    # Even if update time is same, check if HIBOR value changed
    if abs(last_record["hibor_value"] - new_hibor_value) > 0.00001:
        print(f"⚠️  Same update time but HIBOR changed: {last_record['hibor_value']}% -> {new_hibor_value}%")
        return True
    
    return False

def main():
    """Main function"""
    print("=" * 70)
    print(f"HSBC HIBOR Monitor - English Version")
    print(f"Start time: {format_datetime()}")
    print("=" * 70)
    
    # Fetch data
    result = fetch_hibor_data()
    
    if not result["success"]:
        print(f"\n❌ Fetch failed: {result.get('error', 'Unknown error')}")
        return
    
    # Check if new data should be recorded
    should_record = should_record_new_data(
        result["website_update_time"], 
        result["hibor_value"]
    )
    
    if should_record:
        print(f"\n✅ Recording new HIBOR data!")
        print(f"   Website update: {result['website_update_time']}")
        print(f"   HIBOR value: {result['hibor_value']}%")
        print(f"   Fetch time: {result['fetch_time']}")
        
        last_record = get_last_record()
        if last_record:
            # Extract date parts for comparison
            new_date = result["website_update_time"][:8]
            last_date = last_record["website_update_time"][:8]
            
            if new_date != last_date:
                print(f"   New data date: {new_date} (previous: {last_date})")
            
            change = result["hibor_value"] - last_record["hibor_value"]
            change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
            print(f"   HIBOR change: {change_symbol}{abs(change):.5f}%")
        
        # Load history and add new record
        history = load_history()
        
        new_record = {
            "website_update_time": result["website_update_time"],
            "fetch_time": result["fetch_time"],
            "hibor_value": result["hibor_value"]
        }
        
        history["records"].append(new_record)
        
        # Keep only recent 200 records
        if len(history["records"]) > 200:
            history["records"] = history["records"][-200:]
        
        # Save history
        if save_history(history):
            print(f"📝 Saved to {DATA_FILE}")
            print(f"   Total records: {len(history['records'])}")
        
        # Output current record
        print("\n📊 Record content:")
        print(json.dumps(new_record, ensure_ascii=False, indent=2))
        
    else:
        print(f"\n⏸️  Data already recorded")
        last_record = get_last_record()
        print(f"   Last update: {last_record['website_update_time']}")
        print(f"   HIBOR value: {result['hibor_value']}%")
        print(f"   Last fetch: {last_record['fetch_time']}")
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Monitoring completed")
    print("=" * 70)

if __name__ == "__main__":
    main()