from playwright.sync_api import Page, Locator
from config.selectors import (
    IMEI_INPUT_SELECTORS, SUBMIT_BUTTON_SELECTORS, 
    RESULT_SELECTORS, RESULT_KEYWORDS, INPUT_CONTEXT_JS, NEARBY_BUTTON_JS
)
from browser.ad_handler import close_ads, is_ad_element

def find_imei_input(page: Page) -> Locator | None:
    close_ads(page)
    return _find_input_by_selectors(page) or _find_input_by_context(page)

def _find_input_by_selectors(page: Page) -> Locator | None:
    for sel in IMEI_INPUT_SELECTORS:
        try:
            for i in range(page.locator(sel).count()):
                elem = page.locator(sel).nth(i)
                if elem.is_visible() and not is_ad_element(elem):
                    if elem.evaluate("el => el.tagName.toLowerCase()") == 'input':
                        return elem
        except Exception:
            pass
    return None

def _find_input_by_context(page: Page) -> Locator | None:
    try:
        all_inputs = page.locator("input[type='text'], input:not([type])")
        for i in range(all_inputs.count()):
            elem = all_inputs.nth(i)
            if elem.is_visible() and not is_ad_element(elem) and elem.evaluate(INPUT_CONTEXT_JS):
                return elem
        
        # Fallback: Trả về input visible đầu tiên không phải ad
        for i in range(all_inputs.count()):
            elem = all_inputs.nth(i)
            if elem.is_visible() and not is_ad_element(elem):
                return elem
    except Exception:
        pass
    return None

def find_submit_button(page: Page) -> Locator | None:
    return _find_button_by_selectors(page) or _find_button_by_proximity(page)

def _find_button_by_selectors(page: Page) -> Locator | None:
    for sel in SUBMIT_BUTTON_SELECTORS:
        try:
            for i in range(page.locator(sel).count()):
                elem = page.locator(sel).nth(i)
                if elem.is_visible() and not is_ad_element(elem):
                    if elem.evaluate("el => el.tagName.toLowerCase()") in ['button', 'input']:
                        return elem
        except Exception:
            pass
    return None

def _find_button_by_proximity(page: Page) -> Locator | None:
    try:
        imei_input = find_imei_input(page)
        if not imei_input: return None
        
        nearby_html = imei_input.evaluate(NEARBY_BUTTON_JS)
        if not nearby_html: return None
        
        if 'checkImeiBtn' in nearby_html:
            return page.locator(".checkImeiBtn").first
        if 'type="submit"' in nearby_html:
            return page.locator("button[type='submit'], input[type='submit']").first
    except Exception:
        pass
    return None

def extract_result(page: Page) -> str:
    try: page.wait_for_load_state("networkidle", timeout=5000)
    except Exception: pass
    page.wait_for_timeout(2000)
    
    return _extract_from_selectors(page) or _extract_from_body(page)

def _extract_from_selectors(page: Page) -> str:
    for sel in RESULT_SELECTORS:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                text = loc.first.inner_text()
                if len(text) > 20: return _filter_relevant_text(text)
        except Exception: pass
    return ""

def _filter_relevant_text(text: str) -> str:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    relevant = [line for line in lines if any(kw in line.lower() for kw in RESULT_KEYWORDS)]
    return " | ".join(relevant[:5]) if relevant else " ".join(lines[:10])

def _extract_from_body(page: Page) -> str:
    try:
        lines = [l.strip() for l in page.locator("body").inner_text().split('\n') if l.strip()]
        return " ".join(lines[:15])
    except Exception:
        return ""