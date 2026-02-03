#!/usr/bin/env python3
"""
HKAB HIBOR Official Rate Fetcher
直接從香港銀行公會官方頁面獲取1個月期HIBOR數據
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
import os

# 數據存儲文件
DATA_FILE = "api/hkab_hibor.json"

def format_datetime(dt=None):
    """格式化時間為 YYYYMMDD HH:MM:SS"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y%m%d %H:%M:%S')

def fetch_hkab_hibor():
    """從HKAB官方頁面獲取1個月HIBOR數據"""
    url = "https://www.hkab.org.hk/en/rates/hibor"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        print("🌐 Fetching HKAB official HIBOR page...")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # 檢測編碼
        response.encoding = 'utf-8'
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取數據
        result = extract_hkab_data(soup, url)
        
        if result["success"]:
            print(f"✅ Successfully extracted official HIBOR data")
            print(f"   Data date: {result['data_date']}")
            print(f"   1-month HIBOR: {result['hibor_value']}%")
            
            return {
                "success": True,
                "hibor_value": result["hibor_value"],
                "website_update_time": result["website_update_time"],
                "fetch_time": format_datetime(),
                "url": url
            }
        else:
            print(f"❌ Data extraction failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": result.get("error", "Data extraction failed"),
                "fetch_time": format_datetime()
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        return {
            "success": False,
            "error": f"Network error: {str(e)}",
            "fetch_time": format_datetime()
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "fetch_time": format_datetime()
        }

def extract_hkab_data(soup, url):
    """從HKAB頁面提取1個月HIBOR數據"""
    # 保存頁面內容用於調試
    #debug_file = f"hkab_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    #with open(debug_file, 'w', encoding='utf-8') as f:
    #    f.write(str(soup))
    #print(f"📄 Debug file saved: {debug_file}")
    
    # 提取頁面中的所有文本
    page_text = soup.get_text()
    
    # Step 1: 提取數據日期
    data_date = None
    
    # 查找日期模式 (格式: "Hong Kong Time on 2026-2-3.")
    date_patterns = [
        r'Hong Kong Time on (\d{4}-\d{1,2}-\d{1,2})',
        r'(\d{4}-\d{1,2}-\d{1,2})\s*Hong Kong Time',
        r'as at.*?(\d{4}-\d{1,2}-\d{1,2})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            print(f"✅ Found date string: {date_str}")
            
            # 解析日期 (格式: 2026-2-3)
            try:
                # 標準化日期格式
                parts = date_str.split('-')
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                
                data_date = datetime(year, month, day)
                print(f"✅ Parsed date: {data_date.strftime('%Y-%m-%d')}")
                break
            except Exception as e:
                print(f"⚠️  Could not parse date '{date_str}': {e}")
    
    if not data_date:
        print("⚠️  Using current date as fallback")
        data_date = datetime.now()
    
    # Step 2: 提取1個月HIBOR值
    hibor_value = None
    
    # 方法1: 查找表格中的"1 Month"行
    # HKAB頁面表格格式簡單，可以直接查找文本
    lines = page_text.split('\n')
    
    found_1_month = False
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 查找"1 Month"文本
        if "1 Month" in line:
            found_1_month = True
            print(f"✅ Found '1 Month' at line {i}: {line}")
            
            # 在接下來的幾行中查找數值
            for j in range(i+1, min(i+5, len(lines))):
                next_line = lines[j].strip()
                # 嘗試提取浮點數
                rate_match = re.search(r'(\d+\.\d+)', next_line)
                if rate_match:
                    hibor_value = float(rate_match.group(1))
                    print(f"✅ Found HIBOR value: {hibor_value}")
                    break
            
            if hibor_value:
                break
    
    # 方法2: 使用正則表達式直接匹配
    if hibor_value is None:
        # 匹配 "1 Month" 後面的數值
        pattern = r'1 Month\s*[\s\S]*?(\d+\.\d+)'
        match = re.search(pattern, page_text, re.IGNORECASE)
        
        if match:
            hibor_value = float(match.group(1))
            print(f"✅ Found HIBOR via regex: {hibor_value}")
    
    # 方法3: 查找所有數值，然後根據上下文確定
    if hibor_value is None:
        # 查找所有看起來像利率的數值
        all_numbers = re.findall(r'\b\d+\.\d{5}\b', page_text)
        if all_numbers:
            print(f"Found potential rates: {all_numbers}")
            # 通常1個月HIBOR在這些數值中有特定位置
            # 根據頁面結構，1個月利率通常在列表的特定位置
            if len(all_numbers) >= 4:  # 至少有隔夜、1周、2周、1個月
                hibor_value = float(all_numbers[3])  # 第4個通常是1個月
                print(f"✅ Assumed 1-month HIBOR (4th value): {hibor_value}")
    
    if hibor_value is not None:
        # 創建網站更新時間（數據日期 + 固定時間11:15）
        website_update_time = data_date.strftime('%Y%m%d') + " 11:15:00"
        
        return {
            "success": True,
            "data_date": data_date,
            "hibor_value": hibor_value,
            "website_update_time": website_update_time
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
    print(f"HKAB Official HIBOR Monitor")
    print(f"Start time: {format_datetime()}")
    print("=" * 70)
    
    # 獲取數據
    result = fetch_hkab_hibor()
    
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
    print(f"HKAB Official HIBOR History (Last {min(limit, len(history['records']))} records)")
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
    print("HKAB OFFICIAL HIBOR DATA SUMMARY")
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
            result = fetch_hkab_hibor()
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