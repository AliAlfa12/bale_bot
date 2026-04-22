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
    # حذف کاراکترهای نامجاز در zip
    filename = filename.replace('\x00', '').replace('<', '_').replace('>', '_').replace(':', '_').replace('"', '_').replace('|', '_').replace('?', '_').replace('*', '_').replace('\\', '_').replace('/', '_')
    # محدود کردن طول
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
        asset_mapping = {}  # url -> zip_path
        
        # ✅ IMPROVED: جمع‌آوری بهتر منابع (تصاویر، کتاب‌خانه‌ها و غیره)
        assets = []
        
        # ✅ استخراج CSS
        for link in soup.find_all('link', rel='stylesheet', href=True):
            assets.append(('css', urljoin(url, link['href']), link))
        
        # ✅ استخراج JavaScript
        for script in soup.find_all('script', src=True):
            assets.append(('js', urljoin(url, script['src']), script))
        
        # ✅ IMPROVED: استخراج تصاویر (با data-src برای lazy loading)
        for img in soup.find_all('img'):
            img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if img_src:
                assets.append(('image', urljoin(url, img_src), img))
        
        # ✅ استخراج تصاویر پس‌زمینه از style attribute
        for elem in soup.find_all(style=re.compile(r'background.*url')):
            style = elem.get('style', '')
            urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
            for img_url in urls:
                if img_url and not img_url.startswith('data:'):
                    assets.append(('image', urljoin(url, img_url), elem))
        
        # ✅ استخراج ویدیوها
        for video in soup.find_all('video'):
            if video.get('src'):
                assets.append(('video', urljoin(url, video['src']), video))
            for source in video.find_all('source', src=True):
                assets.append(('video', urljoin(url, source['src']), source))
        
        # ✅ استخراج صوت‌ها
        for audio in soup.find_all('audio'):
            if audio.get('src'):
                assets.append(('audio', urljoin(url, audio['src']), audio))
            for source in audio.find_all('source', src=True):
                assets.append(('audio', urljoin(url, source['src']), source))
        
        # حذف تکراری‌ها بر اساس URL
        unique_assets = {}
        for asset_type, asset_url, tag in assets:
            if asset_url not in unique_assets:
                unique_assets[asset_url] = (asset_type, tag)
        
        logger.info(f"Found {len(unique_assets)} unique assets to download")
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            downloaded_count = 0
            
            for asset_url, (asset_type, tag) in unique_assets.items():
                try:
                    asset_url, _ = urldefrag(asset_url)
                    
                    # ✅ skip data URLs
                    if asset_url.startswith('data:'):
                        continue
                    
                    parsed = urlparse(asset_url)
                    path = parsed.path
                    
                    if not path or path == '/':
                        continue
                    
                    # حذف leading slash
                    if path.startswith('/'):
                        path = path[1:]
                    
                    # ایجاد مسیر در zip
                    if asset_type == 'css':
                        zip_path = f"assets/css/{path}"
                    elif asset_type == 'js':
                        zip_path = f"assets/js/{path}"
                    elif asset_type == 'image':
                        zip_path = f"assets/images/{path}"
                    elif asset_type == 'video':
                        zip_path = f"assets/videos/{path}"
                    elif asset_type == 'audio':
                        zip_path = f"assets/audios/{path}"
                    else:
                        zip_path = f"assets/other/{path}"
                    
                    # پاکسازی کاراکترهای نامجاز
                    zip_path = sanitize_filename(zip_path)
                    
                    # اگر مسیر تکراری بود، شماره اضافه کن
                    if zip_path in asset_mapping.values():
                        base, ext = os.path.splitext(zip_path)
                        counter = 1
                        while f"{base}_{counter}{ext}" in asset_mapping.values():
                            counter += 1
                        zip_path = f"{base}_{counter}{ext}"
                    
                    # ✅ IMPROVED: دانلود با retry و timeout بهتر
                    time.sleep(random.uniform(0.1, 0.3))
                    asset_resp = requests.get(
                        asset_url, 
                        headers=DEFAULT_HEADERS.copy(),
                        timeout=15,
                        allow_redirects=True
                    )
                    
                    if asset_resp.status_code == 200:
                        # ✅ بررسی اندازه (حداکثر 50MB به ازای هر فایل)
                        if len(asset_resp.content) > 50 * 1024 * 1024:
                            logger.warning(f"File too large, skipping: {asset_url}")
                            continue
                        
                        zf.writestr(zip_path, asset_resp.content)
                        asset_mapping[asset_url] = zip_path
                        downloaded_count += 1
                        
                        # اصلاح لینک در HTML
                        if tag and hasattr(tag, 'name'):
                            relative_path = os.path.join('..', zip_path) if zip_path.startswith('assets/') else zip_path
                            if tag.name == 'link':
                                tag['href'] = relative_path
                            elif tag.name == 'script':
                                tag['src'] = relative_path
                            elif tag.name == 'img':
                                tag['src'] = relative_path
                                # حذف data-src برای lazy loading
                                if 'data-src' in tag.attrs:
                                    del tag['data-src']
                                if 'data-lazy-src' in tag.attrs:
                                    del tag['data-lazy-src']
                            elif tag.name in ('source', 'video', 'audio'):
                                tag['src'] = relative_path
                    else:
                        logger.warning(f"Failed to download {asset_url}: {asset_resp.status_code}")
                        
                except Exception as e:
                    logger.warning(f"Error downloading {asset_url}: {e}")
                    continue
            
            logger.info(f"Successfully downloaded {downloaded_count}/{len(unique_assets)} assets")
            
            # ✅ IMPROVED: اصلاح CSS files
            for file_info in zf.filelist:
                if file_info.filename.startswith('assets/css/'):
                    try:
                        css_content = zf.read(file_info.filename).decode('utf-8', errors='ignore')
                        pattern = r'url\([\'"]?(.*?)[\'"]?\)'
                        
                        def replacer(m):
                            orig = m.group(1)
                            if orig.startswith(('http', 'data:')) or orig.startswith('/'):
                                # اگر URL خارجی یا data URL است
                                if orig.startswith('data:'):
                                    return m.group(0)
                                # اگر absolute path است
                                if orig.startswith('/'):
                                    abs_url = urljoin(url, orig)
                                else:
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
            
            # ✅ ذخیره HTML اصلاح شده
            zf.writestr('index.html', str(soup).encode('utf-8'))
            zf.writestr('info.txt', f"تعداد منابع دانلود شده: {downloaded_count}\nآدرس: {url}")
        
        logger.info(f"Website download completed: {len(zip_buffer.getvalue())} bytes")
        return zip_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"download_website error: {e}")
        return f"❌ خطا: {str(e)[:200]}"
