import time
from playwright.sync_api import Page, Locator
from config.selectors import (
    AD_CLOSE_SELECTORS, AD_INDICATORS, AD_SIZES, 
    AD_SIZE_TOLERANCE, IS_AD_ELEMENT_JS
)

def close_ads(page: Page):
    """Đóng các popup quảng cáo và overlay"""
    for selector in AD_CLOSE_SELECTORS:
        _try_close_selector(page, selector)
    time.sleep(1)

def _try_close_selector(page: Page, selector: str):
    try:
        elements = page.locator(selector)
        for i in range(min(elements.count(), 3)):
            try:
                if elements.nth(i).is_visible():
                    elements.nth(i).click(timeout=1000)
                    time.sleep(0.5)
            except Exception:
                pass
    except Exception:
        pass

def is_ad_element(element: Locator) -> bool:
    """Kiểm tra xem element có nằm trong container quảng cáo không"""
    try:
        info = element.evaluate(IS_AD_ELEMENT_JS)
        return _contains_ad_keyword(info) or _matches_ad_size(info)
    except Exception:
        return False

def _contains_ad_keyword(info: dict) -> bool:
    text_to_check = (info['classes'] + ' ' + info['ids']).lower()
    return any(indicator in text_to_check for indicator in AD_INDICATORS)

def _matches_ad_size(info: dict) -> bool:
    width, height = info['width'], info['height']
    return any(abs(width - w) < AD_SIZE_TOLERANCE and abs(height - h) < AD_SIZE_TOLERANCE for w, h in AD_SIZES)