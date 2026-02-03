#!/usr/bin/env python3
"""
Hang Seng Bank HIBOR Monitor - Simplified Version
只存儲1個月HIBOR，格式與HSBC腳本統一
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
import json
import re
import time
import os

# 數據存儲文件（與HSBC不同以避免衝突）
DATA_FILE = "api/hase_hibor.json"

def format_datetime(dt=None):
    """格式化時間為 YYYYMMDD HH:MM:SS"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y%m%d %H:%M:%S')

def fetch_hangseng_hibor():
    """獲取恆生銀行1個月HIBOR數據"""
    url = "https://www.hangseng.com/en-hk/personal/banking/rates/hibor/"
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    driver = None
    try:
        print("🚀 Starting browser for Hang Seng HIBOR page...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"🌐 Accessing: {url}")
        driver.get(url)
        
        # 等待頁面加載
        print("⏳ Waiting for page to load...")
        time.sleep(6)
        
        # 獲取頁面文本內容
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # 提取1個月HIBOR數據和日期
        result = extract_hangseng_1m_data(page_text)
        
        if result["success"]:
            # 創建網站更新時間（使用頁面中的日期 + 固定時間11:00）
            data_date = result["data_date"]
            website_update_time = data_date.strftime('%Y%m%d') + " 11:00:00"
            
            print(f"✅ Successfully extracted 1-month HIBOR")
            print(f"   Page date: {data_date.strftime('%Y-%m-%d')}")
            print(f"   1-month HIBOR: {result['hibor_value']}%")
            
            driver.quit()
            
            return {
                "success": True,
                "hibor_value": result["hibor_value"],
                "website_update_time": website_update_time,
                "fetch_time": format_datetime(),
                "url": url
            }
        else:
            print(f"❌ Data extraction failed: {result.get('error', 'Unknown error')}")
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

def extract_hangseng_1m_data(page_text):
    """從恆生頁面提取1個月HIBOR數據"""
    # Step 1: 提取頁面中的日期
    data_date = None
    
    # 查找"As at"後面的日期（格式: DD/MM/YYYY）
    date_pattern = r'As at\s+(\d{2}/\d{2}/\d{4})\s+'
    match = re.search(date_pattern, page_text)
    
    if match:
        date_str = match.group(1)
        print(f"✅ Found date string: {date_str}")
        
        # 解析日期 (格式: DD/MM/YYYY)
        try:
            day, month, year = map(int, date_str.split('/'))
            data_date = datetime(year, month, day)
            print(f"✅ Parsed date: {data_date.strftime('%Y-%m-%d')}")
        except:
            print(f"⚠️  Could not parse date: {date_str}")
    
    if not data_date:
        print("⚠️  Using current date as fallback")
        data_date = datetime.now()
    
    # Step 2: 提取1個月HIBOR數據
    hibor_value = None
    
    # 方法1: 從主表格查找 "1 Month"
    lines = page_text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 查找包含"1 Month"的行
        if "1 Month" in line:
            # 提取百分比數值
            rate_pattern = r'(\d+\.\d+)%'
            rate_match = re.search(rate_pattern, line)
            
            if rate_match:
                hibor_value = float(rate_match.group(1))
                print(f"✅ Found 1-month HIBOR in main table: {hibor_value}%")
                break
    
    # 方法2: 如果主表格沒有，從歷史表格查找
    if hibor_value is None:
        hist_pattern = r'(\d{2}/\d{2}/\d{4})\s*\|\s*(\d+\.\d+)%'
        hist_matches = re.findall(hist_pattern, page_text)
        
        if hist_matches:
            # 取最新的一條記錄
            latest_date_str, latest_rate = hist_matches[-1]
            hibor_value = float(latest_rate)
            print(f"✅ Found 1-month HIBOR in historical table: {hibor_value}%")
    
    if hibor_value is not None:
        return {
            "success": True,
            "data_date": data_date,
            "hibor_value": hibor_value
        }
    else:
        return {
            "success": False,
            "error": "1-month HIBOR data not found on page"
        }

def load_history():
    """加載歷史數據"""
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
    """保存歷史數據"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Failed to save history file: {e}")
        return False

def get_last_record():
    """獲取最後一條記錄"""
    history = load_history()
    if history["records"]:
        return history["records"][-1]
    return None

def should_record_new_data(new_website_update_time, new_hibor_value):
    """檢查是否需要記錄新數據"""
    last_record = get_last_record()
    
    if last_record is None:
        return True
    
    # 檢查網站更新時間是否不同
    if last_record["website_update_time"] != new_website_update_time:
        return True
    
    # 即使更新時間相同，檢查HIBOR值是否變化
    if abs(last_record["hibor_value"] - new_hibor_value) > 0.00001:
        print(f"⚠️  Same update time but HIBOR changed: {last_record['hibor_value']}% -> {new_hibor_value}%")
        return True
    
    return False

def main():
    """主函數"""
    print("=" * 70)
    print(f"Hang Seng Bank 1-Month HIBOR Monitor")
    print(f"Start time: {format_datetime()}")
    print("=" * 70)
    
    # 獲取數據
    result = fetch_hangseng_hibor()
    
    if not result["success"]:
        print(f"\n❌ Fetch failed: {result.get('error', 'Unknown error')}")
        return
    
    # 檢查是否需要記錄新數據
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
            # 提取日期部分進行比較
            new_date = result["website_update_time"][:8]
            last_date = last_record["website_update_time"][:8]
            
            if new_date != last_date:
                print(f"   New data date: {new_date} (previous: {last_date})")
            
            change = result["hibor_value"] - last_record["hibor_value"]
            change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
            print(f"   HIBOR change: {change_symbol}{abs(change):.5f}%")
        
        # 加載歷史記錄並添加新記錄
        history = load_history()
        
        new_record = {
            "website_update_time": result["website_update_time"],
            "fetch_time": result["fetch_time"],
            "hibor_value": result["hibor_value"]
        }
        
        history["records"].append(new_record)
        
        # 只保留最近200條記錄
        if len(history["records"]) > 200:
            history["records"] = history["records"][-200:]
        
        # 保存歷史記錄
        if save_history(history):
            print(f"📝 Saved to {DATA_FILE}")
            print(f"   Total records: {len(history['records'])}")
        
        # 輸出當前記錄
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

def show_history(limit=10):
    """顯示歷史記錄"""
    history = load_history()
    
    print("=" * 70)
    print(f"Hang Seng 1-Month HIBOR History (Last {min(limit, len(history['records']))} records)")
    print("=" * 70)
    
    if not history["records"]:
        print("No records found")
        return
    
    records_to_show = history["records"][-limit:] if limit > 0 else history["records"]
    
    print(f"{'Website Update':20} {'Fetch Time':20} {'HIBOR':>10}")
    print("-" * 70)
    
    for record in reversed(records_to_show):
        print(f"{record['website_update_time']:20} {record['fetch_time']:20} {record['hibor_value']:>9.5f}%")

def show_summary():
    """顯示數據摘要"""
    history = load_history()
    
    if not history["records"]:
        print("No data available")
        return
    
    print("=" * 60)
    print("HANG SENG HIBOR DATA SUMMARY")
    print("=" * 60)
    
    records = history["records"]
    
    # 按日期分組
    dates = {}
    for record in records:
        date_key = record["website_update_time"][:8]  # YYYYMMDD
        if date_key not in dates:
            dates[date_key] = []
        dates[date_key].append(record["hibor_value"])
    
    # 計算統計數據
    values = [r["hibor_value"] for r in records]
    
    print(f"Date range: {min(dates.keys())} to {max(dates.keys())}")
    print(f"Unique dates: {len(dates)}")
    print(f"Total records: {len(records)}")
    print(f"\nLatest HIBOR: {records[-1]['hibor_value']:.5f}% on {records[-1]['website_update_time'][:8]}")
    print(f"Average: {sum(values)/len(values):.5f}%")
    print(f"Minimum: {min(values):.5f}%")
    print(f"Maximum: {max(values):.5f}%")
    
    # 每日變化
    if len(dates) >= 2:
        sorted_dates = sorted(dates.keys())
        latest_date = sorted_dates[-1]
        prev_date = sorted_dates[-2]
        
        latest_avg = sum(dates[latest_date]) / len(dates[latest_date])
        prev_avg = sum(dates[prev_date]) / len(dates[prev_date])
        daily_change = latest_avg - prev_avg
        
        change_symbol = "↑" if daily_change > 0 else "↓" if daily_change < 0 else "→"
        print(f"Daily change: {change_symbol}{abs(daily_change):.5f}% ({prev_date} → {latest_date})")
    
    print("=" * 60)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "history":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            show_history(limit)
        elif command == "summary":
            show_summary()
        elif command == "test":
            print("🧪 Test mode - Fetch only")
            result = fetch_hangseng_hibor()
            if result["success"]:
                print(f"\n✅ Test successful!")
                print(json.dumps({
                    "website_update_time": result["website_update_time"],
                    "fetch_time": result["fetch_time"],
                    "hibor_value": result["hibor_value"]
                }, ensure_ascii=False, indent=2))
            else:
                print(f"\n❌ Test failed: {result.get('error', 'Unknown error')}")
        elif command == "latest":
            history = load_history()
            if history["records"]:
                print(json.dumps(history["records"][-1], ensure_ascii=False, indent=2))
            else:
                print("No records found")
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  (no command)        # Run monitoring")
            print("  history [N]         # Show last N records")
            print("  summary             # Show summary")
            print("  test                # Test fetch")
            print("  latest              # Show latest record")
    else:
        main()