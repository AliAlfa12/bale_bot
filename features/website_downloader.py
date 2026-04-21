import io
import zipfile
import requests
import os
import time
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from utils import send_message, send_document, DEFAULT_HEADERS, logger

def sanitize_filename(filename):
    filename = filename.replace('\x00', '')
    invalid_chars = '<>:"|?*\\/'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def download_website(url, chat_id):
    if not url.startswith(('http://','https://')):
        url = 'http://' + url
    send_message(chat_id, f"🌐 شروع دانلود وب‌سایت: {url}")
    logger.info(f"Starting website download: {url}")
    
    try:
        headers = DEFAULT_HEADERS.copy()
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # تاخیر تصادفی برای جلوگیری از مسدود شدن
        time.sleep(random.uniform(1, 3))
        
        r = requests.get(url, headers=headers, timeout=20)
        logger.info(f"Website response: {r.status_code}")
        
        if r.status_code != 200:
            return f"❌ خطا: وضعیت {r.status_code}"
        
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('index.html', html)
            seen_paths = set()
            assets = []
            
            # استخراج منابع
            for link in soup.find_all('link', rel='stylesheet', href=True):
                assets.append(urljoin(url, link['href']))
            for script in soup.find_all('script', src=True):
                assets.append(urljoin(url, script['src']))
            for img in soup.find_all('img', src=True):
                assets.append(urljoin(url, img['src']))
            for video in soup.find_all('video'):
                for source in video.find_all('source', src=True):
                    assets.append(urljoin(url, source['src']))
                if video.get('src'):
                    assets.append(urljoin(url, video['src']))
            for audio in soup.find_all('audio'):
                for source in audio.find_all('source', src=True):
                    assets.append(urljoin(url, source['src']))
                if audio.get('src'):
                    assets.append(urljoin(url, audio['src']))
            
            downloaded = 0
            for asset_url in assets[:60]:
                try:
                    time.sleep(random.uniform(0.5, 1.5))
                    asset_response = requests.get(asset_url, headers=headers, timeout=10)
                    if asset_response.status_code == 200:
                        parsed = urlparse(asset_url)
                        path = parsed.path
                        if not path or path.endswith('/'):
                            continue
                        if path.startswith('/'):
                            path = path[1:]
                        path = sanitize_filename(path)
                        if path in seen_paths:
                            base, ext = os.path.splitext(path)
                            counter = 1
                            while f"{base}_{counter}{ext}" in seen_paths:
                                counter += 1
                            path = f"{base}_{counter}{ext}"
                        seen_paths.add(path)
                        zf.writestr(path, asset_response.content)
                        downloaded += 1
                        logger.info(f"Downloaded asset: {path}")
                except Exception as e:
                    logger.warning(f"Asset download failed: {asset_url} - {e}")
                    continue
            
            info = f"تعداد assets دانلود شده: {downloaded}\nآدرس اصلی: {url}"
            zf.writestr('info.txt', info)
        
        logger.info(f"Website download completed: {downloaded} assets")
        return zip_buffer.getvalue()
    except Exception as e:
        logger.error(f"download_website error: {e}")
        return f"❌ خطا در دانلود وب‌سایت: {str(e)[:200]}"
