import io
import zipfile
import requests
import os
import time
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from utils import DEFAULT_HEADERS, logger

def sanitize_filename(filename):
    filename = filename.replace('\x00', '').replace('<', '_').replace('>', '_').replace(':', '_').replace('"', '_').replace('|', '_').replace('?', '_').replace('*', '_').replace('\\', '_').replace('/', '_')
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:190] + ext
    return filename

def download_website(url, chat_id=None):
    if not url.startswith(('http://','https://')):
        url = 'http://' + url
    if chat_id:
        from utils import send_message
        send_message(chat_id, f"🌐 شروع دانلود وب‌سایت: {url}")
    
    try:
        headers = DEFAULT_HEADERS.copy()
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            return f"❌ خطا: وضعیت {r.status_code}"
        
        soup = BeautifulSoup(r.text, 'html.parser')
        base_domain = urlparse(url).netloc
        zip_buffer = io.BytesIO()
        downloaded_files = set()
        asset_mapping = {}
        
        # جمع‌آوری منابع
        assets = []
        for link in soup.find_all('link', rel='stylesheet', href=True):
            assets.append(('css', urljoin(url, link['href']), link))
        for script in soup.find_all('script', src=True):
            assets.append(('js', urljoin(url, script['src']), script))
        for img in soup.find_all('img', src=True):
            assets.append(('image', urljoin(url, img['src']), img))
        for video in soup.find_all('video'):
            if video.get('src'):
                assets.append(('video', urljoin(url, video['src']), video))
            for source in video.find_all('source', src=True):
                assets.append(('video', urljoin(url, source['src']), source))
        for audio in soup.find_all('audio'):
            if audio.get('src'):
                assets.append(('audio', urljoin(url, audio['src']), audio))
            for source in audio.find_all('source', src=True):
                assets.append(('audio', urljoin(url, source['src']), source))
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # دانلود assets و اصلاح لینک‌ها
            for asset_type, asset_url, tag in assets:
                asset_url, _ = urldefrag(asset_url)
                if asset_url in asset_mapping:
                    new_path = asset_mapping[asset_url]
                else:
                    parsed = urlparse(asset_url)
                    path = parsed.path
                    if not path or path == '/':
                        continue
                    filename = os.path.basename(path)
                    if not filename or '.' not in filename:
                        filename = f"asset_{hash(asset_url)}.bin"
                    filename = sanitize_filename(filename)
                    if asset_type == 'css':
                        save_path = f"assets/css/{filename}"
                    elif asset_type == 'js':
                        save_path = f"assets/js/{filename}"
                    elif asset_type == 'image':
                        save_path = f"assets/images/{filename}"
                    elif asset_type == 'video':
                        save_path = f"assets/videos/{filename}"
                    elif asset_type == 'audio':
                        save_path = f"assets/audios/{filename}"
                    else:
                        save_path = f"assets/other/{filename}"
                    
                    # جلوگیری از duplicate
                    if save_path in downloaded_files:
                        base, ext = os.path.splitext(save_path)
                        counter = 1
                        while f"{base}_{counter}{ext}" in downloaded_files:
                            counter += 1
                        save_path = f"{base}_{counter}{ext}"
                    
                    # دانلود
                    try:
                        time.sleep(random.uniform(0.3, 0.8))
                        asset_resp = requests.get(asset_url, headers=headers, timeout=10)
                        if asset_resp.status_code == 200:
                            zf.writestr(save_path, asset_resp.content)
                            downloaded_files.add(save_path)
                            asset_mapping[asset_url] = save_path
                        else:
                            continue
                    except:
                        continue
                    new_path = save_path
                
                # اصلاح لینک در HTML
                if new_path:
                    relative_path = os.path.join('..', new_path) if new_path.startswith('assets/') else new_path
                    if tag.name == 'link':
                        tag['href'] = relative_path
                    elif tag.name == 'script':
                        tag['src'] = relative_path
                    elif tag.name == 'img':
                        tag['src'] = relative_path
                    elif tag.name in ('source', 'video', 'audio'):
                        tag['src'] = relative_path
            
            # اصلاح CSS files (تصاویر پس‌زمینه و فونت‌ها)
            for file_info in zf.filelist:
                if file_info.filename.startswith('assets/css/'):
                    css_content = zf.read(file_info.filename).decode('utf-8', errors='ignore')
                    pattern = r'url\([\'"]?(.*?)[\'"]?\)'
                    def replacer(m):
                        orig = m.group(1)
                        if orig.startswith('http'):
                            abs_url = orig
                        else:
                            abs_url = urljoin(url, orig)
                        abs_url, _ = urldefrag(abs_url)
                        if abs_url in asset_mapping:
                            return f"url('../{asset_mapping[abs_url]}')"
                        return m.group(0)
                    new_css = re.sub(pattern, replacer, css_content)
                    zf.writestr(file_info.filename, new_css.encode('utf-8'))
            
            # ذخیره HTML اصلاح شده
            zf.writestr('index.html', str(soup).encode('utf-8'))
            zf.writestr('info.txt', f"تعداد assets: {len(downloaded_files)}\nآدرس: {url}")
        
        return zip_buffer.getvalue()
    except Exception as e:
        logger.error(f"download_website error: {e}")
        return f"❌ خطا: {str(e)[:200]}"
