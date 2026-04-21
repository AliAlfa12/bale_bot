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
        zip_buffer = io.BytesIO()
        downloaded_files = set()
        asset_mapping = {}
        
        # جمع‌آوری منابع بدون تکرار (استفاده از دیکشنری)
        assets_dict = {}
        for link in soup.find_all('link', rel='stylesheet', href=True):
            abs_url = urljoin(url, link['href'])
            assets_dict[abs_url] = ('css', link)
        for script in soup.find_all('script', src=True):
            abs_url = urljoin(url, script['src'])
            assets_dict[abs_url] = ('js', script)
        for img in soup.find_all('img', src=True):
            abs_url = urljoin(url, img['src'])
            assets_dict[abs_url] = ('image', img)
        for video in soup.find_all('video'):
            if video.get('src'):
                abs_url = urljoin(url, video['src'])
                assets_dict[abs_url] = ('video', video)
            for source in video.find_all('source', src=True):
                abs_url = urljoin(url, source['src'])
                assets_dict[abs_url] = ('video', source)
        for audio in soup.find_all('audio'):
            if audio.get('src'):
                abs_url = urljoin(url, audio['src'])
                assets_dict[abs_url] = ('audio', audio)
            for source in audio.find_all('source', src=True):
                abs_url = urljoin(url, source['src'])
                assets_dict[abs_url] = ('audio', source)
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for asset_url, (asset_type, tag) in assets_dict.items():
                asset_url, _ = urldefrag(asset_url)
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
                
                # جلوگیری از duplicate name در zip
                if save_path in downloaded_files:
                    base, ext = os.path.splitext(save_path)
                    counter = 1
                    while f"{base}_{counter}{ext}" in downloaded_files:
                        counter += 1
                    save_path = f"{base}_{counter}{ext}"
                
                try:
                    time.sleep(random.uniform(0.3, 0.8))
                    asset_resp = requests.get(asset_url, headers=headers, timeout=10)
                    if asset_resp.status_code == 200:
                        zf.writestr(save_path, asset_resp.content)
                        downloaded_files.add(save_path)
                        asset_mapping[asset_url] = save_path
                        # اصلاح لینک در HTML
                        relative_path = os.path.join('..', save_path) if save_path.startswith('assets/') else save_path
                        if tag.name == 'link':
                            tag['href'] = relative_path
                        elif tag.name == 'script':
                            tag['src'] = relative_path
                        elif tag.name == 'img':
                            tag['src'] = relative_path
                        elif tag.name in ('source', 'video', 'audio'):
                            tag['src'] = relative_path
                except Exception as e:
                    logger.warning(f"Failed to download {asset_url}: {e}")
                    continue
            
            # اصلاح CSS files (urlهای داخلی)
            for file_info in zf.filelist:
                if file_info.filename.startswith('assets/css/'):
                    try:
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
                    except Exception as e:
                        logger.warning(f"Error processing CSS {file_info.filename}: {e}")
            
            # ذخیره HTML اصلاح شده
            zf.writestr('index.html', str(soup).encode('utf-8'))
            zf.writestr('info.txt', f"تعداد assets: {len(downloaded_files)}\nآدرس: {url}")
        
        return zip_buffer.getvalue()
    except Exception as e:
        logger.error(f"download_website error: {e}")
        return f"❌ خطا: {str(e)[:200]}"
