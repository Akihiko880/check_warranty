import os

INPUT_IMEI_FILE = "imei.xlsx" 
INPUT_WEB_FILE = "link_web.json"
RESULTS_CSV = "results.csv"
CHECKPOINT_FILE = "checkpoint.json"
TRACKING_LOG_FILE = "tracking_log.json"
SCREENSHOT_DIR = "screenshots"

MAX_RETRIES_PER_IMEI = 3
POST_SUCCESS_DELAY = 15
BATCH_SIZE = 5
PAGE_LOAD_TIMEOUT = 30000
WAIT_AFTER_LOAD = 2000

os.makedirs(SCREENSHOT_DIR, exist_ok=True)