import math
import random
import time
import os
import base64
import pandas as pd
from playwright.sync_api import sync_playwright, expect
import ddddocr
from openpyxl import load_workbook

ocr = ddddocr.DdddOcr()
results = []
os.makedirs("captchas", exist_ok=True)

def human_delay(min_ms=100, max_ms=500):
    """Tạo delay ngẫu nhiên như con người (tính bằng giây)"""
    time.sleep(random.uniform(min_ms, max_ms) / 1000)

def bezier_curve(start, end, steps=20):
    """
    Tạo đường cong Bezier bậc 3 từ điểm start đến end
    Trả về list các điểm (x, y) để chuột đi theo
    """
    x1, y1 = start
    x2, y2 = end
    
    # Tạo 2 điểm control ngẫu nhiên (làm đường cong tự nhiên)
    distance = math.hypot(x2 - x1, y2 - y1)
    offset = distance * 0.3  # Độ lệch 30% khoảng cách
    
    cx1 = x1 + (x2 - x1) * random.uniform(0.2, 0.4) + random.uniform(-offset, offset)
    cy1 = y1 + (y2 - y1) * random.uniform(0.2, 0.4) + random.uniform(-offset, offset)
    cx2 = x1 + (x2 - x1) * random.uniform(0.6, 0.8) + random.uniform(-offset, offset)
    cy2 = y1 + (y2 - y1) * random.uniform(0.6, 0.8) + random.uniform(-offset, offset)
    
    points = []
    for i in range(steps + 1):
        t = i / steps
        # Công thức Bezier bậc 3
        x = (1-t)**3 * x1 + 3*(1-t)**2*t * cx1 + 3*(1-t)*t**2 * cx2 + t**3 * x2
        y = (1-t)**3 * y1 + 3*(1-t)**2*t * cy1 + 3*(1-t)*t**2 * cy2 + t**3 * y2
        points.append((x, y))
    return points

def human_like_mouse_move(page, target_locator):
    box = target_locator.bounding_box()
    if not box:
        target_locator.scroll_into_view_if_needed()
        human_delay(200, 400)
        box = target_locator.bounding_box()
    
    if not box:
        print("Không lấy được vị trí target")
        return
    
    target_x = box['x'] + box['width'] / 2 + random.uniform(-3, 3)
    target_y = box['y'] + box['height'] / 2 + random.uniform(-3, 3)
    
    # Vị trí bắt đầu ngẫu nhiên (từ giữa màn hình hoặc vị trí ngẫu nhiên)
    viewport = page.viewport_size
    start_x = random.uniform(viewport['width'] * 0.3, viewport['width'] * 0.7)
    start_y = random.uniform(viewport['height'] * 0.3, viewport['height'] * 0.7)

    points = bezier_curve((start_x, start_y), (target_x, target_y), steps=random.randint(15, 25))
    
    for px, py in points:
        page.mouse.move(px, py)
        # Tốc độ di chuyển không đều (nhanh ở giữa, chậm ở đầu/cuối)
        human_delay(5, 20)

def human_like_click(page, target_locator):
    """Click như con người: di chuột đến → hover → click"""
    human_like_mouse_move(page, target_locator)
    human_delay(100, 300)  # Hover một chút
    
    # Click với lực nhấn ngẫu nhiên (thời gian giữ chuột)
    page.mouse.down()
    human_delay(50, 150)
    page.mouse.up()

def human_like_type(page, target_locator, text):
    """
    Gõ từng ký tự như con người:
    - Di chuột đến ô input
    - Click vào ô
    - Gõ từng ký tự với delay ngẫu nhiên
    - Thỉnh thoảng "nhầm" rồi xóa (tùy chọn)
    """
    # 1. Di chuột đến ô input
    human_like_mouse_move(page, target_locator)
    human_delay(150, 350)
    
    # 2. Click vào ô (có thể click 1-2 lần như con người)
    human_like_click(page, target_locator)
    if random.random() < 0.3:  # 30% khả năng click thêm lần nữa
        human_delay(100, 250)
        human_like_click(page, target_locator)
    
    human_delay(200, 500)  # Chờ ô input được focus
    
    # 3. Gõ từng ký tự
    for char in text:
        page.keyboard.type(char, delay=0)  # Không dùng delay built-in
        human_delay(80, 250)  # Delay ngẫu nhiên giữa các phím
        
        # 5% khả năng "gõ nhầm" rồi xóa (rất giống người)
        if random.random() < 0.05 and char.isalpha():
            wrong_char = chr(ord(char) + random.choice([-1, 1]))
            page.keyboard.type(wrong_char)
            human_delay(150, 300)
            page.keyboard.press("Backspace")
            human_delay(100, 250)
            page.keyboard.type(char)
            human_delay(80, 200)

def random_scroll_and_hover(page):
    """Thêm hành vi phụ: scroll nhẹ, hover ngẫu nhiên trước khi làm việc chính"""
    # Scroll nhẹ xuống rồi lên lại
    scroll_amount = random.randint(50, 150)
    page.mouse.wheel(0, scroll_amount)
    human_delay(200, 400)
    page.mouse.wheel(0, -scroll_amount)
    human_delay(150, 300)
    
    # Hover vào một vị trí ngẫu nhiên trên trang
    viewport = page.viewport_size
    random_x = random.uniform(100, viewport['width'] - 100)
    random_y = random.uniform(100, viewport['height'] - 100)
    page.mouse.move(random_x, random_y)
    human_delay(300, 600)

def save_results_to_excel(df, filename="ket_qua_bao_hanh.xlsx"):
    """Lưu kết quả vào file Excel, giữ nguyên định dạng cũ nếu file đã tồn tại"""
    temp_path = filename.replace('.xlsx', '_temp.xlsx')
    try:
        with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        if os.path.exists(filename):
            os.remove(filename)
        os.rename(temp_path, filename)
        return True
    except PermissionError:
        print("File Excel đang mở! Đóng file rồi thử lại.")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False
    except Exception as e:
        print(f"Lỗi lưu Excel: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False                                                                                                                                                                                                                     

input_file = "imei.xlsx"
output_file = "ket_qua_bao_hanh.xlsx"

if os.path.exists(output_file):
    print(f"📂 Phát hiện file kết quả cũ: {output_file}")
    df = pd.read_excel(output_file)
    print(f"✅ Đã load {len(df)} dòng từ file output")
    
    # Kiểm tra cột KetQuaKiemTra có tồn tại không
    if 'KetQuaKiemTra' not in df.columns:
        print("⚠️ Cột 'KetQuaKiemTra' không tồn tại, tạo mới...")
        df['KetQuaKiemTra'] = "Chưa kiểm tra / Lỗi hệ thống"
    else:
        # Đếm thống kê
        total = len(df)
        pending = df[df['KetQuaKiemTra'] == "Chưa kiểm tra / Lỗi hệ thống"].shape[0]
        error = df[df['KetQuaKiemTra'].astype(str).str.startswith("Lỗi") | df['KetQuaKiemTra'].astype(str).str.startswith("CAPTCHA sai")].shape[0]
        success = total - pending - error
        
        # print(f"📊 Thống kê:")
        print(f"   ✅ Thành công: {success}")
        print(f"   ❌ Lỗi (sẽ check lại): {error}")
        print(f"   ⏳ Chưa kiểm tra: {pending}")
        print(f"   🔄 Tổng cần xử lý: {pending + error}")
else:
    print(f"📂 Không tìm thấy file output, tạo mới từ {input_file}")
    df = pd.read_excel(input_file)
    df['KetQuaKiemTra'] = "Chưa kiểm tra / Lỗi hệ thống"
    print(f"Đã tạo file Excel với {len(df)} dòng")
    print(f"✅ Đã load {len(df)} dòng từ file input")

imeis = df["IMEI"].astype(str).tolist()
print(f"Loaded {len(imeis)} IMEI")

retry_count_total = 0
max_retries = 3
total_time = 0
success_count = 0

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=300)
    page = browser.new_page() 
    
    for idx, imei in enumerate(imeis):
        current_status = df.at[idx, 'KetQuaKiemTra'] 
        if not (current_status.startswith("Lỗi") or current_status.startswith("CAPTCHA sai") or current_status == "Chưa kiểm tra / Lỗi load trang" or current_status == "Lỗi load trang"):   
            print(f"⏭️  [{idx+1}/{len(imeis)}] BỎ QUA IMEI {imei} (đã thành công)")
            print (f"current_status: {current_status}")
            continue
        print(f"\n--- Đang xử lý IMEI: {imei} ---")
        print(f"current_status: {current_status}")
        try:
            page.goto("https://checkcoverage.apple.com/?locale=vi_VN", timeout=30000)
            page.wait_for_selector("#serial-number-input", timeout=30000)
            page.fill("#serial-number-input", imei)
        except Exception as e:
            print(f"Không thể load trang: {e}")
            df.at[idx, 'KetQuaKiemTra'] = f"Lỗi load trang: {str(e)[:100]}"
            save_results_to_excel(df)
            continue
    
        retry_count = 0
        success = False
        while retry_count < max_retries and not success:
            if retry_count > 0:
                print(f"\n Thử lại lần {retry_count}/{max_retries}...")
                retry_count_total += 1
                try:
                    print("Đang click nút 'Mã mới' để lấy CAPTCHA mới...")
                    refresh_btn = page.locator("#captcha-refresh-btn")
                    refresh_btn.click()
                    time.sleep(2)  # Chờ CAPTCHA mới load
                    print("Đã lấy CAPTCHA mới")
                except Exception as e:
                    print(f"❌ Không thể click nút 'Mã mới': {e}")
                    # Fallback: reload trang nếu không tìm thấy nút
                    print("Fallback: Reload trang...")
                    page.reload()
                    time.sleep(2)
                    try:
                        page.wait_for_selector("#serial-number-input")
                        page.fill("#serial-number-input", imei)
                    except Exception as e:
                        print(f"❌ Lỗi sau khi reload: {e}")
                        # save_results_to_excel(df)
                        break  
            try:
                page.wait_for_selector("img.captcha-image", timeout=15000) 
            except Exception:
                print("Không tìm đc capcha, skip")
                df.at[idx, 'KetQuaKiemTra'] = "Lỗi không có CAPTCHA"
                # save_results_to_excel(df)
                break

            captcha_img = page.locator("img.captcha-image").first
            src_data = captcha_img.get_attribute("src")
            file_path = f"captchas/{imei}.jpg" 
        
            if src_data and src_data.startswith("data:image"):
                base64_data = src_data.split(",")[1]
                img_bytes = base64.b64decode(base64_data)
                
                start = time.time()
                captcha_text = ocr.classification(img_bytes).upper()
                ocr_time = time.time() - start
                total_time += ocr_time
                success_count += 1
                print(f"OCR nhận diện: '{captcha_text}' trong {ocr_time:.3f}s")
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(base64_data))
                print(f"Đã lưu CAPTCHA vào: {file_path}")
                # save_results_to_excel(df)
                try: 
                    captcha_input = page.locator('input[aria-label="Nhập CAPTCHA"]').first
                    if not captcha_input.count():
                        captcha_input = page.locator('input[type="text"]').nth(1)
                    
                    human_delay(500, 1500)
                    human_like_type(page, captcha_input, captcha_text)
                    print(f"✅ Đã tự động điền CAPTCHA: {captcha_text}")
                    
                except Exception as e:
                    print(f"❌ Không thể fill CAPTCHA: {e}")
            else:
                captcha_img.screenshot(path=file_path)
                print(f"Đã lưu CAPTCHA vào: {file_path}")
            
            submit_button = page.locator("div.serial-button button[type='submit']")
           
            try:
                print("Đang kiểm tra trạng thái nút Gửi...")
                submit_button.wait_for(state="attached", timeout=60000)
                print("Đang chờ nút Gửi được kích hoạt (hết disabled)...")
                expect(submit_button).to_be_enabled(timeout=10000)
                print("Nút Gửi đã sẵn sàng, đang bấm...")
                
                submit_button.click()
                print("Đang đợi trang load kết quả...")
                page.wait_for_load_state("networkidle")
                time.sleep(3) 
                
                page_content = page.locator("main").inner_text()
                page_content = page_content.replace('\n', ' ').replace('\r', ' ')
                page_content = ' '.join(page_content.split())
                print(f"Kết quả ({len(page_content)} ký tự): {page_content[:100]}...")
                print("nội dung đầy đủ:", page_content)
                if "không khớp" in page_content or "invalid" in page_content.lower() or "Làm mới mã" in page_content:
                    print("❌ Submit xong nhưng Apple báo CAPTCHA không khớp. Sẽ thử lại...")
                    retry_count += 1
                    continue
                df.at[idx, 'KetQuaKiemTra'] = page_content
                print("Xuất được kết quả bảo hành")
                success = True
                if save_results_to_excel(df):
                    print(f"💾 Đã lưu kết quả IMEI {imei} vào Excel (dòng {idx+1})")
                else:
                    print("⚠️ Không thể lưu Excel, nhưng kết quả vẫn trong RAM")
            except Exception as e:
                print(f"Lỗi roài {imei}: {e}")
                retry_count += 1
                continue
                
        if not success and retry_count >= max_retries:
            print(f"⚠️ Đã thử {max_retries} lần nhưng CAPTCHA vẫn sai. Bỏ qua IMEI này.")
            df.at[idx, 'KetQuaKiemTra'] = f"CAPTCHA sai sau {max_retries} lần thử"
        
        time.sleep(2)
    browser.close()

print("\n Đã xuất kết quả ra file ket_qua_bao_hanh.xlsx")
print(f"Thời gian OCR tổng cộng: {total_time:.3f}s")
print(f"Số lần OCR thành công: {success_count}")

# class WebsiteUser(HttpUser):
#     wait_time = between(2, 5)

#     @task
#     def homepage(self):
#         response = self.client.get("/", name="homepage")
#         elapsed_time = response.elapsed.total_seconds()

#         if elapsed_time > 2: print(f"Slow response: {elapsed_time:.3f}s")
#         if response.status_code != 200: print(f"Error {response.status_code}")

#         results["requests"].append(
#             {
#                 "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
#                 "url": "/", "status_code": response.status_code, "elapsed_time": elapsed_time
#             }
#         )

# @events.quitting.add_listener
# def save_results(environment, **kwargs):
#     results["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
#     results["total_requests"] = len(results["requests"])

#     with open("results.json","w",encoding="utf-8") as f:
#         json.dump(results, f, indent=4, ensure_ascii=False)

#     print("Saved results.json")