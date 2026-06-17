import json
import os
import time
import random
import requests
from datetime import datetime

from playwright.sync_api import sync_playwright


INPUT_FILE = "link_web.json"
LOG_FILE = "tracking_log.json"
SCREENSHOT_DIR = "screenshots"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def chunk_list(items, size):
    for i in range(0, len(items), size):
        yield {
            "batch_id": i // size,
            "start_idx": i,
            "end_idx": min(i + size - 1, len(items) - 1),
            "imeis": items[i:i+size]
        }

def now():
    return datetime.now().isoformat()

def get_public_ip():
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=10)
        return r.json()["ip"]
    except Exception:
        return "UNKNOWN"

def load_websites():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["websites"]

def append_log(tracking_data):
    """Lưu toàn bộ tracking data vào file log"""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(tracking_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Lỗi khi lưu log: {e}")

def detect_security(page):
    security = {}
    security["cloudflare_challenge"] = (
        page.locator("#challenge-form").count() > 0
        or page.locator("#challenge-running").count() > 0
        or page.locator("text=Checking your browser").count() > 0
        or page.locator("text=Attention Required!").count() > 0
    )
    security["cloudflare_turnstile"] = (
        page.locator("iframe[src*='challenges.cloudflare.com']").count() > 0
    )
    security["recaptcha"] = (
        page.locator("iframe[src*='recaptcha'], .g-recaptcha").count() > 0
    )
    security["hcaptcha"] = (
        page.locator("iframe[src*='hcaptcha'], .h-captcha").count() > 0
    )
    security["image_captcha"] = (
        page.locator("""
            img[class*='captcha' i],
            img[id*='captcha' i],
            img[src*='captcha' i],
            canvas[id*='captcha' i]
        """).count() > 0
    )
    return security

# 🔥 HÀM MỚI: QUÉT CHI TIẾT INPUT VÀ BUTTON
def scan_form_elements(page):
    """Quét chi tiết tất cả input và button trên trang"""
    
    form_info = {
        "inputs": [],
        "buttons": [],
        "imei_related_inputs": [],
        "submit_related_buttons": []
    }
    
    try:
        # ========================================
        # QUÉT TẤT CẢ INPUT
        # ========================================
        all_inputs = page.locator("input, textarea, select")
        input_count = all_inputs.count()
        
        print(f"   📝 Tìm thấy {input_count} input/textarea/select")
        
        for i in range(min(input_count, 20)):  # Giới hạn 20 input để không quá dài
            try:
                element = all_inputs.nth(i)
                
                # Chỉ lấy element visible
                if not element.is_visible():
                    continue
                
                # Thu thập thông tin element
                info = element.evaluate("""
                    el => {
                        return {
                            tag: el.tagName.toLowerCase(),
                            type: el.type || 'text',
                            name: el.name || '',
                            id: el.id || '',
                            class: el.className || '',
                            placeholder: el.placeholder || '',
                            maxlength: el.maxLength || -1,
                            value: el.value || '',
                            required: el.required || false,
                            disabled: el.disabled || false,
                            readonly: el.readOnly || false,
                            // Vị trí trên trang
                            rect: el.getBoundingClientRect(),
                            // Selector đề xuất
                            selector: el.id ? `#${el.id}` : 
                                     el.name ? `input[name="${el.name}"]` :
                                     el.className ? `input.${el.className.split(' ')[0]}` : '',
                            // Text xung quanh
                            nearby_text: (() => {
                                let parent = el.parentElement;
                                let text = '';
                                for (let j = 0; j < 3 && parent; j++) {
                                    text += parent.textContent.substring(0, 100) + ' ';
                                    parent = parent.parentElement;
                                }
                                return text.trim();
                            })()
                        };
                    }
                """)
                
                form_info["inputs"].append(info)
                
                # Kiểm tra xem có liên quan đến IMEI/Serial không
                text_to_check = (
                    info['name'] + ' ' + 
                    info['id'] + ' ' + 
                    info['placeholder'] + ' ' + 
                    info['class'] + ' ' +
                    info['nearby_text']
                ).lower()
                
                imei_keywords = ['imei', 'serial', 'esn', 'meid', 'device', 'phone']
                if any(kw in text_to_check for kw in imei_keywords):
                    form_info["imei_related_inputs"].append({
                        "index": i,
                        "selector": info['selector'],
                        "type": info['type'],
                        "placeholder": info['placeholder'],
                        "name": info['name'],
                        "id": info['id'],
                        "reason": f"Chứa từ khóa IMEI/Serial trong: {text_to_check[:100]}"
                    })
                    
            except Exception as e:
                pass
        
        # ========================================
        # QUÉT TẤT CẢ BUTTON
        # ========================================
        all_buttons = page.locator("button, input[type='submit'], input[type='button'], [role='button']")
        button_count = all_buttons.count()
        
        print(f"   🔘 Tìm thấy {button_count} button")
        
        for i in range(min(button_count, 20)):  # Giới hạn 20 button
            try:
                element = all_buttons.nth(i)
                
                # Chỉ lấy element visible
                if not element.is_visible():
                    continue
                
                # Thu thập thông tin element
                info = element.evaluate("""
                    el => {
                        return {
                            tag: el.tagName.toLowerCase(),
                            type: el.type || 'button',
                            name: el.name || '',
                            id: el.id || '',
                            class: el.className || '',
                            text: el.textContent.trim().substring(0, 100) || el.value || '',
                            disabled: el.disabled || false,
                            // Vị trí trên trang
                            rect: el.getBoundingClientRect(),
                            // Selector đề xuất
                            selector: el.id ? `#${el.id}` :
                                     el.className ? `button.${el.className.split(' ')[0]}` : '',
                            // Text xung quanh
                            nearby_text: (() => {
                                let parent = el.parentElement;
                                let text = '';
                                for (let j = 0; j < 3 && parent; j++) {
                                    text += parent.textContent.substring(0, 100) + ' ';
                                    parent = parent.parentElement;
                                }
                                return text.trim();
                            })()
                        };
                    }
                """)
                
                form_info["buttons"].append(info)
                
                # Kiểm tra xem có liên quan đến submit/check không
                text_to_check = (
                    info['text'] + ' ' + 
                    info['name'] + ' ' + 
                    info['id'] + ' ' + 
                    info['class'] + ' ' +
                    info['nearby_text']
                ).lower()
                
                submit_keywords = ['check', 'submit', 'search', 'send', 'lookup', 'verify', 'kiểm tra', 'gửi', 'get info']
                if any(kw in text_to_check for kw in submit_keywords):
                    form_info["submit_related_buttons"].append({
                        "index": i,
                        "selector": info['selector'],
                        "text": info['text'],
                        "type": info['type'],
                        "name": info['name'],
                        "id": info['id'],
                        "reason": f"Chứa từ khóa submit trong: {text_to_check[:100]}"
                    })
                    
            except Exception as e:
                pass
        
        # ========================================
        # TÓM TẮT
        # ========================================
        form_info["summary"] = {
            "total_inputs": len(form_info["inputs"]),
            "total_buttons": len(form_info["buttons"]),
            "imei_related_inputs_count": len(form_info["imei_related_inputs"]),
            "submit_related_buttons_count": len(form_info["submit_related_buttons"]),
            "best_imei_input": form_info["imei_related_inputs"][0] if form_info["imei_related_inputs"] else None,
            "best_submit_button": form_info["submit_related_buttons"][0] if form_info["submit_related_buttons"] else None
        }
        
    except Exception as e:
        print(f"   ❌ Lỗi khi scan form elements: {e}")
    
    return form_info

def scan_website(page, site, current_ip):
    name = site["name"]
    url = site["url"]
    
    print(f"\nScanning {name}")
    
    result = {
        "website": name,
        "url": url,
        "public_ip": current_ip,
        "access_time": now(),
        "http_status": None,
        "load_time": None,
        "success": False,
        "error": None,
        "security": {},
        "form_elements": {},  # 🔥 THÊM: Thông tin chi tiết về input/button
        "behavior": {
            "has_input_box": False,
            "has_submit_button": False,
            "has_ajax_request": False,
            "has_rate_limit": False,
            "has_login_required": False,
            "has_api_call": False,
            "response_type": None
        },
        "benchmark": {
            "requests_sent": 0,
            "requests_succeeded": 0,
            "requests_failed": 0,
            "avg_response_time": None,
            "min_response_time": None,
            "max_response_time": None,
            "first_captcha_seen": None,
            "first_rate_limit_seen": None,
            "last_http_code": None
        },
        "response_sample": {
            "title": None,
            "page_length": None,
            "contains_error_text": False,
            "contains_result_text": False
        },
        "screenshot": None
    }
    
    start = time.time()
    
    try:
        response = page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        result["http_status"] = response.status if response else None
        result["load_time"] = round(time.time() - start, 2)
        result["security"] = detect_security(page)
        
        # 🔥 QUÉT CHI TIẾT FORM ELEMENTS
        print(f"   🔍 Đang quét form elements...")
        result["form_elements"] = scan_form_elements(page)
        
        # Cập nhật behavior dựa trên form_elements
        result["behavior"]["has_input_box"] = result["form_elements"]["summary"]["total_inputs"] > 0
        result["behavior"]["has_submit_button"] = result["form_elements"]["summary"]["total_buttons"] > 0
        
        # In tóm tắt
        summary = result["form_elements"]["summary"]
        print(f"   📊 Tóm tắt:")
        print(f"      • Tổng input: {summary['total_inputs']}")
        print(f"      • Tổng button: {summary['total_buttons']}")
        print(f"      • Input liên quan IMEI: {summary['imei_related_inputs_count']}")
        print(f"      • Button liên quan submit: {summary['submit_related_buttons_count']}")
        
        if summary['best_imei_input']:
            print(f"      • 🎯 IMEI input tốt nhất: {summary['best_imei_input']['selector']}")
            print(f"         - Placeholder: {summary['best_imei_input']['placeholder']}")
            print(f"         - Name: {summary['best_imei_input']['name']}")
            print(f"         - ID: {summary['best_imei_input']['id']}")
        
        if summary['best_submit_button']:
            print(f"      • 🎯 Submit button tốt nhất: {summary['best_submit_button']['selector']}")
            print(f"         - Text: {summary['best_submit_button']['text']}")
            print(f"         - ID: {summary['best_submit_button']['id']}")
        
        # Chụp ảnh màn hình
        filename = name.replace(" ", "_").lower() + ".png"
        screenshot_path = os.path.join(SCREENSHOT_DIR, filename)
        page.screenshot(path=screenshot_path, full_page=True)
        result["screenshot"] = screenshot_path
        
        result["success"] = True
        
    except Exception as e:
        result["load_time"] = round(time.time() - start, 2)
        result["error"] = str(e)
    
    return result

def checking_website():
    websites = load_websites()
    public_ip = get_public_ip()
    scan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    tracking = {
        "scan_id": scan_id,
        "public_ip": public_ip,
        "scan_start": now(),
        "scan_end": None,
        "results": []
    }
    
    print("=" * 70)
    print("SCAN START")
    print("Public IP:", public_ip)
    print("=" * 70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="vi-VN",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        for site in websites:
            result = scan_website(page, site, public_ip)
            tracking["results"].append(result)
            
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            append_log(tracking)
            time.sleep(random.uniform(3, 6))
        
        browser.close()
    
    tracking["scan_end"] = now()
    append_log(tracking)
    
    print("\nDONE")
    print("Log saved:", LOG_FILE)
    
    return tracking

if __name__ == "__main__":
    checking_website()