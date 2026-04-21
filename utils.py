import os
import requests
import zipfile
import io
import time
import random
import logging
import subprocess
import shlex
from urllib.parse import urlparse

# ========== تنظیمات لاگ ==========
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== متغیرهای محیطی ==========
BALE_TOKEN = os.environ.get("BALE_TOKEN")
BASE_URL = f"https://tapi.bale.ai/bot{BALE_TOKEN}/"
GROUP_CHAT_ID = os.environ.get("CHAT_ID_GROUP")
ARCHIVE_PASSWORD = os.environ.get("ARCHIVE_PASSWORD")

# ========== هدرهای پیشرفته ==========
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# ========== توابع اصلی ==========
def send_message(chat_id, text, reply_markup=None):
    url = BASE_URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        logger.info(f"Sending message to {chat_id}: {text[:50]}...")
        requests.post(url, json=payload, timeout=30)
    except Exception as e:
        logger.error(f"sendMessage error: {e}")

def send_document(chat_id, file_path, caption=""):
    url = BASE_URL + "sendDocument"
    with open(file_path, 'rb') as f:
        files = {"document": (os.path.basename(file_path), f, "application/octet-stream")}
        data = {"chat_id": chat_id, "caption": caption}
        try:
            response = requests.post(url, data=data, files=files, timeout=60)
            response_data = response.json()
            if response.status_code == 200 and response_data.get("ok") and GROUP_CHAT_ID:
                try:
                    sent_message_id = response_data["result"]["message_id"]
                    forward_url = BASE_URL + "forwardMessage"
                    forward_data = {
                        "chat_id": GROUP_CHAT_ID,
                        "from_chat_id": chat_id,
                        "message_id": sent_message_id
                    }
                    requests.post(forward_url, json=forward_data, timeout=30)
                    logger.info(f"Forwarded to group: {sent_message_id}")
                except Exception as e:
                    logger.error(f"Forward error: {e}")
        except Exception as e:
            logger.error(f"sendDocument error: {e}")

def send_bytes_as_document(chat_id, file_bytes, filename, caption=""):
    url = BASE_URL + "sendDocument"
    files = {"document": (filename, file_bytes, "application/octet-stream")}
    data = {"chat_id": chat_id, "caption": caption}
    try:
        response = requests.post(url, data=data, files=files, timeout=60)
        response_data = response.json()
        if response.status_code == 200 and response_data.get("ok") and GROUP_CHAT_ID:
            try:
                sent_message_id = response_data["result"]["message_id"]
                forward_url = BASE_URL + "forwardMessage"
                forward_data = {
                    "chat_id": GROUP_CHAT_ID,
                    "from_chat_id": chat_id,
                    "message_id": sent_message_id
                }
                requests.post(forward_url, json=forward_data, timeout=30)
            except Exception as e:
                logger.error(f"Forward error: {e}")
    except Exception as e:
        logger.error(f"sendBytes error: {e}")

# ========== توابع RAR ==========
def create_rar_parts(file_path, base_name, part_size_mb=19):
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []
    part_size = f"{part_size_mb}m"
    password_part = f"-p{ARCHIVE_PASSWORD}" if ARCHIVE_PASSWORD else ""
    cmd = f'rar a -v{part_size} {password_part} "{base_name}.rar" "{file_path}"'
    try:
        subprocess.run(shlex.split(cmd), check=True, capture_output=True, text=True, timeout=120)
        parts = []
        for f in os.listdir('.'):
            if f.startswith(base_name) and (f.endswith('.rar') or '.part' in f):
                parts.append(f)
        parts.sort()
        logger.info(f"Created RAR parts: {parts}")
        return parts
    except subprocess.CalledProcessError as e:
        logger.error(f"RAR part error: {e.stderr}")
        return []

def create_single_rar(file_path, output_name=None):
    if not output_name:
        output_name = os.path.basename(file_path) + '.rar'
    password_part = f"-p{ARCHIVE_PASSWORD}" if ARCHIVE_PASSWORD else ""
    cmd = f'rar a {password_part} "{output_name}" "{file_path}"'
    try:
        subprocess.run(shlex.split(cmd), check=True, capture_output=True, text=True, timeout=60)
        return output_name
    except subprocess.CalledProcessError as e:
        logger.error(f"RAR single error: {e.stderr}")
        return None

# ========== توابع کمکی ==========
def ensure_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except:
        try:
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'ffmpeg'], check=True)
            return True
        except:
            return False

def create_inline_keyboard(buttons, columns=1):
    keyboard = []
    row = []
    for i, btn in enumerate(buttons):
        row.append({"text": btn["text"], "callback_data": btn["callback_data"]})
        if (i+1) % columns == 0 or i == len(buttons)-1:
            keyboard.append(row)
            row = []
    return {"inline_keyboard": keyboard}

def remove_reply_keyboard():
    return {"remove_keyboard": True}

def download_file_with_headers(url, timeout=50, retries=2):
    headers = DEFAULT_HEADERS.copy()
    headers['Referer'] = url
    for attempt in range(retries):
        try:
            logger.info(f"Download attempt {attempt+1}: {url}")
            time.sleep(random.uniform(1, 3))
            r = requests.get(url, headers=headers, timeout=timeout, stream=True)
            if r.status_code == 200:
                return r
            elif r.status_code == 403:
                logger.warning(f"403 Forbidden for {url}")
                headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            else:
                logger.warning(f"Status {r.status_code} for {url}")
        except Exception as e:
            logger.error(f"Download error: {e}")
    return None
