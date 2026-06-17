import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright
from scaning_web import checking_website, load_websites
from config.settings import INPUT_IMEI_FILE, BATCH_SIZE
from utils.helpers import chunk_list, load_checkpoint
from core.checker import check_imei_with_retry

def process_website(page, site, batches, checkpoint):
    site_name, url = site["name"], site["url"]
    print(f"\n{'='*20} WEBSITE: {site_name} {'='*20}")
    
    for batch in batches:
        print(f"\n  > BATCH {batch['batch_id']} ({len(batch['imeis'])} IMEIs)")
        for imei in batch['imeis']:
            if _is_already_processed(checkpoint, site_name, imei): continue
            print(f"[{imei}] Đang check...")
            check_imei_with_retry(page, url, site_name, imei, checkpoint)
            time.sleep(random.uniform(2, 5))

def _is_already_processed(checkpoint, site_name, imei):
    if site_name in checkpoint and imei in checkpoint[site_name]:
        print(f"[{imei}] Đã xử lý trước đó. Bỏ qua.")
        return True
    return False

def load_imeis_from_file() -> list:
    df = pd.read_csv(INPUT_IMEI_FILE) if INPUT_IMEI_FILE.endswith('.csv') else pd.read_excel(INPUT_IMEI_FILE)
    imei_col = next((col for col in df.columns if col.lower() in ['imei', 'serial', 'esn']), None)
    if not imei_col:
        raise ValueError(f"Không tìm thấy cột IMEI. Các cột hiện có: {df.columns.tolist()}")
    return df[imei_col].astype(str).tolist()

def run_automation():
    websites = load_websites()
    tracking_result = checking_website()
    accessible_websites = _filter_accessible_websites(websites, tracking_result)
    
    if not accessible_websites:
        print("Không có website nào truy cập được. Kết thúc.")
        return
        
    imeis = load_imeis_from_file()
    print(f"Đã load {len(imeis)} IMEI.")
    
    checkpoint = load_checkpoint()
    batches = list(chunk_list(imeis, BATCH_SIZE))
    
    with sync_playwright() as p:
        browser, page = _setup_browser(p)
        for site in accessible_websites:
            process_website(page, site, batches, checkpoint)
            time.sleep(random.uniform(5, 10))
        browser.close()
    print("\n🎉 HOÀN THÀNH!")

def _filter_accessible_websites(websites, tracking_result):
    accessible = []
    for site in websites:
        scan_res = next((r for r in tracking_result["results"] if r["website"] == site["name"]), None)
        if scan_res and scan_res["success"]:
            accessible.append(site)
        else:
            print(f" {site['name']}")
    print(f"\n Có {len(accessible)}/{len(websites)} websites truy cập được")
    return accessible

def _setup_browser(p):
    browser = p.chromium.launch(headless=False, slow_mo=300)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}, locale="vi-VN",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    return browser, context.new_page()

def main():
    print("\n" + "="*70)
    print("PHASE 1: SCAN WEBSITES")
    print("="*70)
    checking_website()

    print("\n" + "="*70)
    print("PHASE 2 & 3: LỌC WEBSITES & CHECK IMEI")
    print("="*70)
    run_automation()

if __name__ == "__main__":
    main()