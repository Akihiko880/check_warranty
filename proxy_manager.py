import json
import random
import requests
import os
import time
from datetime import datetime

class ProxyManager:
    def __init__(self, api_url="https://proxy.me", token="", params=None, cache_file="proxy_cache.json"):
        self.api_url = api_url
        self.token = token
        self.params = params or {"country": "", "protocol": "http"}
        self.cache_file = cache_file
        self.available_proxies = []
        self.used_proxies = []
        self.failed_proxies = []
        self.last_fetch_time = None
        self.total_fetched = 0
        
    def _build_request(self):
        headers = {
            "token": self.token,
            "Content-Type": "application/json"
        }
        return headers, self.params
    
    def _parse_single_proxy_from_dict(self, data_dict):
        """Parse 1 proxy từ dict (khi API trả về 1 proxy duy nhất)"""
        if not isinstance(data_dict, dict):
            return None
        
        # Thử nhiều key khác nhau
        host = data_dict.get("ip") or data_dict.get("host") or data_dict.get("address") or ""
        port = data_dict.get("port") or ""
        protocol = data_dict.get("protocol") or data_dict.get("type") or "http"
        country = data_dict.get("country") or data_dict.get("country_code") or "unknown"
        reputation = data_dict.get("reputation") or data_dict.get("score") or 0
        username = data_dict.get("username") or data_dict.get("user") or ""
        password = data_dict.get("password") or data_dict.get("pass") or ""
        
        # Nếu có field "id" chứa URL đầy đủ
        if "id" in data_dict and isinstance(data_dict["id"], str):
            id_value = data_dict["id"]
            # Parse URL từ id
            if "://" in id_value:
                protocol, rest = id_value.split("://", 1)
                if "@" in rest:
                    auth, host_port = rest.split("@", 1)
                    if ":" in auth:
                        username, password = auth.split(":", 1)
                else:
                    host_port = rest
                
                if ":" in host_port:
                    host, port = host_port.rsplit(":", 1)
        
        if not host or not port:
            return None
        
        # Xây dựng proxy URL
        if username and password:
            proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
        else:
            proxy_url = f"{protocol}://{host}:{port}"
        
        return {
            "url": proxy_url,
            "host": str(host),
            "port": str(port),
            "protocol": protocol,
            "username": username,
            "password": password,
            "country": country,
            "reputation": reputation,
            "raw_data": data_dict
        }
    
    def _parse_json_response(self, data):
        """Parse response dạng JSON - xử lý cả list và dict"""
        proxies = []
        
        # Trường hợp 1: data là list (nhiều proxy)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str) and ":" in item:
                    parts = item.split(":")
                    host = parts[0]
                    port = parts[1]
                    username = parts[2] if len(parts) > 2 else ""
                    password = parts[3] if len(parts) > 3 else ""
                    protocol = "http"
                    
                    if username and password:
                        proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
                    else:
                        proxy_url = f"{protocol}://{host}:{port}"
                    
                    proxies.append({
                        "url": proxy_url,
                        "host": host,
                        "port": port,
                        "protocol": protocol,
                        "username": username,
                        "password": password,
                        "country": "unknown",
                        "reputation": 0
                    })
                elif isinstance(item, dict):
                    proxy = self._parse_single_proxy_from_dict(item)
                    if proxy:
                        proxies.append(proxy)
        
        # Trường hợp 2: data là dict với key chứa list proxy
        elif isinstance(data, dict):
            # Thử tìm list trong các key phổ biến
            proxy_list = data.get("data") or data.get("proxies") or data.get("results") or data.get("items")
            
            if isinstance(proxy_list, list):
                # data là list
                for item in proxy_list:
                    if isinstance(item, dict):
                        proxy = self._parse_single_proxy_from_dict(item)
                        if proxy:
                            proxies.append(proxy)
                    elif isinstance(item, str) and ":" in item:
                        # Parse string format
                        parts = item.split(":")
                        if len(parts) >= 2:
                            host = parts[0]
                            port = parts[1]
                            proxy_url = f"http://{host}:{port}"
                            proxies.append({
                                "url": proxy_url,
                                "host": host,
                                "port": port,
                                "protocol": "http",
                                "username": "",
                                "password": "",
                                "country": "unknown",
                                "reputation": 0
                            })
            
            elif isinstance(proxy_list, dict):
                # 🔥 TRƯỜNG HỢP CỦA BẠN: data là dict chứa 1 proxy
                proxy = self._parse_single_proxy_from_dict(proxy_list)
                if proxy:
                    proxies.append(proxy)
                    print(f"   📊 API trả về 1 proxy (single object)")
            
            else:
                # Thử parse chính data như là 1 proxy
                proxy = self._parse_single_proxy_from_dict(data)
                if proxy:
                    proxies.append(proxy)
                    print(f"   📊 API trả về 1 proxy (root object)")
        
        return proxies
    
    def _auto_detect_and_parse(self, response):
        """Tự động detect format và parse response"""
        content_type = response.headers.get("Content-Type", "")
        text = response.text.strip()
        
        # Thử parse JSON trước
        if "json" in content_type or text.startswith("{") or text.startswith("["):
            try:
                data = response.json()
                print(f"   🔍 Response JSON keys: {list(data.keys()) if isinstance(data, dict) else 'Array'}")
                proxies = self._parse_json_response(data)
                if proxies:
                    return proxies
            except Exception as e:
                print(f"   ⚠️  Lỗi parse JSON: {e}")
        
        # Fallback: parse text
        return self._parse_text_response(text)
    
    def _parse_text_response(self, text):
        """Parse response dạng text"""
        proxies = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            protocol = "http"
            if "://" in line:
                protocol, line = line.split("://", 1)
            
            if ":" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    host = parts[0]
                    port = parts[1]
                    username = parts[2] if len(parts) > 2 else ""
                    password = parts[3] if len(parts) > 3 else ""
                    
                    if username and password:
                        proxy_url = f"{protocol}://{username}:{password}@{host}:{port}"
                    else:
                        proxy_url = f"{protocol}://{host}:{port}"
                    
                    proxies.append({
                        "url": proxy_url,
                        "host": host,
                        "port": port,
                        "protocol": protocol,
                        "username": username,
                        "password": password,
                        "country": "unknown",
                        "reputation": 0,
                        "raw": line
                    })
        
        return proxies
    
    def _save_to_cache(self):
        try:
            cache_data = {
                "proxies": self.available_proxies,
                "last_fetch": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                "total": len(self.available_proxies)
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Đã lưu {len(self.available_proxies)} proxy vào cache")
        except Exception as e:
            print(f"⚠️  Lỗi khi lưu cache: {e}")
    
    def _load_from_cache(self):
        try:
            if not os.path.exists(self.cache_file):
                return False
            
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            proxies = cache_data.get("proxies", [])
            if proxies:
                self.available_proxies = proxies
                self.last_fetch_time = datetime.fromisoformat(cache_data.get("last_fetch"))
                print(f"📂 Đã load {len(proxies)} proxy từ cache")
                return True
        except Exception as e:
            print(f"⚠️  Lỗi khi load cache: {e}")
        
        return False
    
    def _fetch_single_request(self):
        """Gọi API 1 lần và trả về list proxy (có thể 0, 1 hoặc nhiều)"""
        headers, params = self._build_request()
        
        response = requests.get(
            self.api_url,
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"   ❌ API status {response.status_code}")
            return []
        
        proxies = self._auto_detect_and_parse(response)
        return proxies
    
    def get_alive_proxies(self, limit=None, use_cache=True, force_refresh=False, max_requests=50):
        """
        Lấy danh sách proxy - hỗ trợ gọi API nhiều lần nếu mỗi lần chỉ trả về 1 proxy
        
        Args:
            limit: Số lượng proxy cần lấy (None = lấy tất cả)
            use_cache: Sử dụng cache nếu có
            force_refresh: Bắt buộc gọi API mới
            max_requests: Số lần gọi API tối đa (tránh loop vô hạn)
        """
        # Kiểm tra cache
        if use_cache and not force_refresh and os.path.exists(self.cache_file):
            if self._load_from_cache():
                if limit and len(self.available_proxies) > limit:
                    self.available_proxies = self.available_proxies[:limit]
                return self.available_proxies
        
        try:
            print(f"\n🌐 Đang gọi API: {self.api_url}")
            print(f"   Params: {self.params}")
            if limit:
                print(f"   Mục tiêu: {limit} proxy")
            else:
                print(f"   Mục tiêu: KHÔNG GIỚI HẠN")
            
            all_proxies = []
            request_count = 0
            consecutive_empty = 0  # Đếm số lần liên tiếp không có proxy
            
            while True:
                request_count += 1
                
                # Kiểm tra điều kiện dừng
                if limit and len(all_proxies) >= limit:
                    print(f"   ✅ Đã đạt mục tiêu {limit} proxy")
                    break
                
                if request_count > max_requests:
                    print(f"   ⚠️  Đạt giới hạn {max_requests} lần gọi API")
                    break
                
                if consecutive_empty >= 3:
                    print(f"   ⚠️  API không trả về proxy sau 3 lần gọi liên tiếp")
                    break
                
                # Gọi API
                print(f"   🔄 Lần gọi {request_count}...", end=" ")
                proxies = self._fetch_single_request()
                
                if proxies:
                    # Kiểm tra proxy trùng
                    new_proxies = []
                    for proxy in proxies:
                        if proxy['url'] not in [p['url'] for p in all_proxies]:
                            new_proxies.append(proxy)
                    
                    if new_proxies:
                        all_proxies.extend(new_proxies)
                        print(f"→ {len(new_proxies)} proxy mới (tổng: {len(all_proxies)})")
                        consecutive_empty = 0
                    else:
                        print(f"→ Proxy trùng, bỏ qua")
                        consecutive_empty += 1
                else:
                    print(f"→ Không có proxy")
                    consecutive_empty += 1
                
                # Delay giữa các lần gọi (tránh bị rate limit)
                if not (limit and len(all_proxies) >= limit):
                    time.sleep(0.5)
            
            # Giới hạn số lượng nếu cần
            if limit and len(all_proxies) > limit:
                all_proxies = all_proxies[:limit]
            
            self.available_proxies = all_proxies
            self.last_fetch_time = datetime.now()
            self.total_fetched = len(all_proxies)
            
            # Lưu cache
            if all_proxies:
                self._save_to_cache()
            
            print(f"\n✅ Đã lấy {len(all_proxies)} proxy từ {request_count} lần gọi API")
            
            # In danh sách
            print(f"\n📋 Danh sách proxy (hiển thị tối đa 10):")
            for i, proxy in enumerate(all_proxies[:10], 1):
                auth_info = " | Auth: Yes" if proxy.get('username') else ""
                print(f"   {i}. {proxy['url']}{auth_info}")
            
            if len(all_proxies) > 10:
                print(f"   ... và {len(all_proxies) - 10} proxy khác")
            
            return all_proxies
            
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: dùng cache
            if use_cache and self._load_from_cache():
                print("✅ Dùng proxy từ cache")
                return self.available_proxies
            return []
    
    def get_random_proxy(self):
        usable_proxies = [p for p in self.available_proxies if p['url'] not in self.failed_proxies]
        
        if not usable_proxies:
            if self.failed_proxies:
                print("⚠️  Tất cả proxy đều fail, reset...")
                self.failed_proxies = []
                usable_proxies = self.available_proxies
            else:
                print("⚠️  Không có proxy available")
                return None
        
        proxy = random.choice(usable_proxies)
        self.used_proxies.append(proxy)
        print(f"🔄 Sử dụng proxy: {proxy['url']}")
        return proxy
    
    def get_proxy_for_imei(self, imei_index):
        usable_proxies = [p for p in self.available_proxies if p['url'] not in self.failed_proxies]
        
        if not usable_proxies:
            if self.failed_proxies:
                print("⚠️  Tất cả proxy đều fail, reset...")
                self.failed_proxies = []
                usable_proxies = self.available_proxies
            else:
                return None
        
        proxy_index = imei_index % len(usable_proxies)
        proxy = usable_proxies[proxy_index]
        print(f"🔄 IMEI #{imei_index} → Proxy: {proxy['url']}")
        return proxy
    
    def get_proxy_stats(self):
        stats = {
            "total_available": len(self.available_proxies),
            "total_used": len(self.used_proxies),
            "total_failed": len(self.failed_proxies),
            "remaining": len(self.available_proxies) - len(self.failed_proxies),
            "usage_percentage": (len(self.used_proxies) / len(self.available_proxies) * 100) if self.available_proxies else 0,
            "fail_percentage": (len(self.failed_proxies) / len(self.available_proxies) * 100) if self.available_proxies else 0,
            "last_fetch_time": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            "total_fetched": self.total_fetched
        }
        return stats
    
    def mark_proxy_as_failed(self, proxy_url, reason=""):
        if proxy_url not in self.failed_proxies:
            self.failed_proxies.append(proxy_url)
            print(f"🚫 Proxy {proxy_url} bị đánh dấu fail: {reason}")
    
    def refresh_proxies(self, limit=None):
        print("\n🔄 Đang làm mới danh sách proxy...")
        self.used_proxies = []
        self.failed_proxies = []
        return self.get_alive_proxies(limit=limit, use_cache=False, force_refresh=True)


def test_proxy_manager():
    """Test function"""
    API_URL = "https://proxy.thuanle.me"
    TOKEN = "zZxW3t9ggL5HZ8gcjPsySUb8cvwb4X96"
    PARAMS = {
        "country": "",  
        "protocol": "http"
    }
    
    manager = ProxyManager(
        api_url=API_URL,
        token=TOKEN,
        params=PARAMS,
        cache_file="proxy_cache.json"
    )
    
    print("=" * 70)
    print("TEST PROXY MANAGER - AUTO FETCH MULTIPLE")
    print("=" * 70)
    
    # Test: Lấy 10 proxy (sẽ gọi API nhiều lần nếu cần)
    print("\n📌 TEST: Lấy 10 proxy (auto gọi nhiều lần)")
    print("-" * 70)
    proxies = manager.get_alive_proxies(limit=10, force_refresh=True)
    
    if proxies:
        print(f"\n✅ Đã lấy {len(proxies)} proxy")
        
        # Thống kê
        stats = manager.get_proxy_stats()
        print(f"\n📊 Thống kê:")
        print(f"   • Tổng available: {stats['total_available']}")
        print(f"   • Còn lại: {stats['remaining']}")
        
        # Test lấy proxy
        print(f"\n🎲 Test lấy proxy:")
        for i in range(3):
            proxy = manager.get_random_proxy()
            if proxy:
                print(f"   Lần {i+1}: {proxy['url']}")
    else:
        print("\n❌ Không lấy được proxy nào!")
    
    print("\n✅ TEST HOÀN THÀNH!")


if __name__ == "__main__":
    test_proxy_manager()