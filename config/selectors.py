# --- AD HANDLING ---
AD_CLOSE_SELECTORS = [
    "button:has-text('close' i)", "button:has-text('đóng' i)",
    ".modal-close", ".popup-close", ".close-btn",
    "[aria-label='Close']", "[aria-label='Đóng']",
    ".fc-cta-consent", ".fc-button-background",
    "#onetrust-accept-btn-handler", ".css-47sehv",
]
AD_INDICATORS = ["ad", "ads", "advert", "advertisement", "banner", "sponsor", "promo", "popup", "modal", "overlay"]
AD_SIZES = [(300, 250), (728, 90), (160, 600), (320, 50), (300, 600)]
AD_SIZE_TOLERANCE = 50

# --- FORM HANDLING ---
IMEI_INPUT_SELECTORS = [
    "#imeiFld", "#imei", "#serial", "#serial-number-input", "#imei-input", "#serial-input",
    "input.imeiFld", "input.imei-input", "input.serial-input",
    "input[class*='imei' i]", "input[class*='serial' i]",
    "input[name*='imei' i]", "input[name*='serial' i]", "input[name*='esn' i]", "input[name*='meid' i]",
    "input[placeholder*='imei' i]", "input[placeholder*='serial' i]",
    "input[type='text'][maxlength='15']", "input[type='text'][maxlength='14']",
]

SUBMIT_BUTTON_SELECTORS = [
    ".checkImeiBtn", ".btn-check", ".check-btn", ".imei-check-btn",
    "button:has-text('Check IMEI' i)", "button:has-text('Check Serial' i)",
    "button:has-text('Kiểm tra' i)", "button:has-text('Gửi' i)",
    "button:has-text('check' i)", "button:has-text('submit' i)", "button:has-text('search' i)",
    "input[type='submit']", "button[type='submit']",
    "input[type='button'][value*='check' i]", "input[type='button'][value*='submit' i]",
]

RESULT_SELECTORS = [
    ".result", ".check-result", ".status", ".info", ".response",
    "#result", "#status", ".alert", ".success", ".error", "main", ".container"
]
RESULT_KEYWORDS = [
    "warranty", "status", "model", "capacity", "color", "purchase", "expired", 
    "valid", "invalid", "bảo hành", "trạng thái", "mô hình", "hết hạn", "hợp lệ", "imei", "serial", "apple"
]

# --- JAVASCRIPT SNIPPETS ---
IS_AD_ELEMENT_JS = """
    el => {
        let parent = el; let classes = []; let ids = [];
        for (let i = 0; i < 5 && parent; i++) {
            if (parent.className) classes.push(parent.className.toLowerCase());
            if (parent.id) ids.push(parent.id.toLowerCase());
            parent = parent.parentElement;
        }
        return { classes: classes.join(' '), ids: ids.join(' '), width: el.offsetWidth, height: el.offsetHeight };
    }
"""

INPUT_CONTEXT_JS = """
    el => {
        let parent = el.closest('.inputGroupField, .form-group, .form-field, .check-form, .imei-form');
        if (parent && /imei|serial|check/.test(parent.textContent.toLowerCase())) return true;
        let prev = el.previousElementSibling, next = el.nextElementSibling;
        let parentText = el.parentElement ? el.parentElement.textContent.toLowerCase() : '';
        let allText = (prev ? prev.textContent : '') + ' ' + (next ? next.textContent : '') + ' ' + parentText;
        return /imei|serial/.test(allText);
    }
"""

NEARBY_BUTTON_JS = """
    el => {
        let container = el.closest('.row, .inputGroupField, .form-group, .form-field');
        if (container) {
            let btn = container.querySelector('button, input[type="submit"], input[type="button"]');
            if (btn) return btn.outerHTML;
        }
        let parent = el.parentElement;
        for (let i = 0; i < 3 && parent; i++) {
            let btn = parent.querySelector('button, input[type="submit"]');
            if (btn && btn.offsetParent !== null) return btn.outerHTML;
            parent = parent.parentElement;
        }
        return null;
    }
"""