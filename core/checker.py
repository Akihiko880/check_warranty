import time
import random
import os
from playwright.sync_api import Page
from config.settings import MAX_RETRIES_PER_IMEI, POST_SUCCESS_DELAY, SCREENSHOT_DIR
from utils.helpers import get_timestamp, save_to_csv, save_checkpoint
from browser.form_handler import find_imei_input, find_submit_button, extract_result

def check_imei_with_retry(page: Page, url: str, site_name: str, imei: str, checkpoint: dict):
    for attempt in range(1, MAX_RETRIES_PER_IMEI + 1):
        print(f"Lần thử {attempt}/{MAX_RETRIES_PER_IMEI}...")
        success, result_text, status, reason = _attempt_check_imei(page, url, imei)
        if success:
            _handle_success(page, site_name, imei, checkpoint, attempt, result_text)
            return True, result_text
            
        if attempt == MAX_RETRIES_PER_IMEI:
            _handle_failure(site_name, imei, checkpoint, attempt, status, reason, result_text)
            return False, result_text
            
        print(f"Failed: {reason}. Thử lại...")
        time.sleep(random.uniform(2, 4))
    return False, ""

def _attempt_check_imei(page: Page, url: str, imei: str):
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        imei_input, submit_btn = find_imei_input(page), find_submit_button(page)
        if not imei_input or not submit_btn:
            return False, "", "failed", "input_or_button_not_found"
            
        imei_input.click()
        imei_input.fill(imei)
        submit_btn.click()
        
        result_text = extract_result(page)
        status, reason = _evaluate_result(result_text)
        return status == "success", result_text, status, reason
    except Exception as e:
        return False, "", "error", str(e)[:150]

def _evaluate_result(result_text: str):
    if not result_text or len(result_text) < 20:
        return "failed", "no_result_found"
    lower_text = result_text.lower()
    if "captcha" in lower_text or "invalid" in lower_text or "không khớp" in lower_text:
        return "failed", "captcha_or_invalid_input"
    return "success", ""

def _handle_success(page: Page, site_name: str, imei: str, checkpoint: dict, attempt: int, result_text: str):
    save_to_csv({
        "timestamp": get_timestamp(), "website": site_name, "imei": imei,
        "status": "success", "reason": "", "result_snippet": result_text[:500]
    })
    _update_checkpoint(checkpoint, site_name, imei, "success", attempt)
    print(f"SUCCESS (sau {attempt} lần thử)")
    _save_screenshot(page, site_name, imei)
    
    print(f"Đang chờ {POST_SUCCESS_DELAY}s trước khi chuyển sang IMEI tiếp theo...")
    time.sleep(POST_SUCCESS_DELAY)

def _handle_failure(site_name: str, imei: str, checkpoint: dict, attempt: int, status: str, reason: str, result_text: str):
    save_to_csv({
        "timestamp": get_timestamp(), "website": site_name, "imei": imei,
        "status": status, "reason": f"{reason} (sau {MAX_RETRIES_PER_IMEI} lần thử)",
        "result_snippet": result_text[:500] if result_text else ""
    })
    _update_checkpoint(checkpoint, site_name, imei, status, attempt)
    print(f"FAILED sau {MAX_RETRIES_PER_IMEI} lần thử")

def _update_checkpoint(checkpoint: dict, site_name: str, imei: str, status: str, attempts: int):
    if site_name not in checkpoint: checkpoint[site_name] = {}
    checkpoint[site_name][imei] = {"status": status, "timestamp": get_timestamp(), "attempts": attempts}
    save_checkpoint(checkpoint)

def _save_screenshot(page: Page, site_name: str, imei: str):
    try:
        filename = f"{site_name.replace(' ', '_').lower()}_{imei}.png"
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, filename), full_page=True)
    except Exception as e:
        print(f"Lỗi khi chụp ảnh màn hình: {e}")