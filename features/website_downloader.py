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
    
    logger.info(f"Starting website download: {url}")
    
    if chat_id:
        from utils import send_message
        send_message(chat_id, f"🌐 شروع دانلود وب‌سایت: {url}")
    
    try:
        logger.info(f"Fetching website HTML from: {url}")
        headers = DEFAULT_HEADERS.copy()
        r = requests.get(url, headers=headers, timeout=20)
        
        if r.status_code != 200:
            error_msg = f"❌ خطا: وضعیت {r.status_code}\n\nجزئیات: سرور پاسخ داده ولی بدون موفقیت"
            logger.error(f"Website fetch failed - Status: {r.status_code}, URL: {url}")
            return error_msg
        
        logger.info(f"HTML fetched successfully ({len(r.content)} bytes)")
        soup = BeautifulSoup(r.text, 'html.parser')
        zip_buffer = io.BytesIO()
        asset_mapping = {}
        
        assets = []
        
        # استخراج CSS
        logger.info("Extracting CSS files...")
        for link in soup.find_all('link', rel='stylesheet', href=True):
            assets.append(('css', urljoin(url, link['href']), link))
        logger.info(f"Found {len([a for a in assets if a[0] == 'css'])} CSS files")
        
        # استخراج JavaScript
        logger.info("Extracting JavaScript files...")
        for script in soup.find_all('script', src=True):
            assets.append(('js', urljoin(url, script['src']), script))
        logger.info(f"Found {len([a for a in assets if a[0] == 'js'])} JS files")
        
        # استخراج تصاویر
        logger.info("Extracting images...")
        for img in soup.find_all('img'):
            img_src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if img_src:
                assets.append(('image', urljoin(url, img_src), img))
        logger.info(f"Found {len([a for a in assets if a[0] == 'image'])} images")
        
        # استخراج تصاویر پس‌زمینه
        logger.info("Extracting background images...")
        for elem in soup.find_all(style=re.compile(r'background.*url')):
            style = elem.get('style', '')
            urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
            for img_url in urls:
                if img_url and not img_url.startswith('data:'):
                    assets.append(('image', urljoin(url, img_url), elem))
        
        # استخراج ویدیوها
        logger.info("Extracting videos...")
        for video in soup.find_all('video'):
            if video.get('src'):
                assets.append(('video', urljoin(url, video['src']), video))
            for source in video.find_all('source', src=True):
                assets.append(('video', urljoin(url, source['src']), source))
        logger.info(f"Found {len([a for a in assets if a[0] == 'video'])} videos")
        
        # استخراج صوت‌ها
        logger.info("Extracting audio files...")
        for audio in soup.find_all('audio'):
            if audio.get('src'):
                assets.append(('audio', urljoin(url, audio['src']), audio))
            for source in audio.find_all('source', src=True):
                assets.append(('audio', urljoin(url, source['src']), source))
        logger.info(f"Found {len([a for a in assets if a[0] == 'audio'])} audio files")
        
        # حذف تکراری‌ها
        unique_assets = {}
        for asset_type, asset_url, tag in assets:
            if asset_url not in unique_assets:
                unique_assets[asset_url] = (asset_type, tag)
        
        logger.info(f"Total unique assets: {len(unique_assets)}")
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            downloaded_count = 0
            failed_count = 0
            
            for idx, (asset_url, (asset_type, tag)) in enumerate(unique_assets.items(), 1):
                try:
                    asset_url, _ = urldefrag(asset_url)
                    
                    if asset_url.startswith('data:'):
                        logger.debug(f"Skipping data URL: {asset_url[:50]}")
                        continue
                    
                    parsed = urlparse(asset_url)
                    path = parsed.path
                    
                    if not path or path == '/':
                        logger.warning(f"Invalid path for: {asset_url}")
                        continue
                    
                    if path.startswith('/'):
                        path = path[1:]
                    
                    # تعیین نوع پوشه
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
                    
                    zip_path = sanitize_filename(zip_path)
                    
                    # تکرار چک
                    if zip_path in asset_mapping.values():
                        base, ext = os.path.splitext(zip_path)
                        counter = 1
                        while f"{base}_{counter}{ext}" in asset_mapping.values():
                            counter += 1
                        zip_path = f"{base}_{counter}{ext}"
                    
                    # دانلود
                    time.sleep(random.uniform(0.1, 0.3))
                    logger.debug(f"[{idx}/{len(unique_assets)}] Downloading: {asset_url[:80]}")
                    
                    asset_resp = requests.get(
                        asset_url, 
                        headers=DEFAULT_HEADERS.copy(),
                        timeout=15,
                        allow_redirects=True
                    )
                    
                    if asset_resp.status_code == 200:
                        content_size_mb = len(asset_resp.content) / (1024 * 1024)
                        
                        if content_size_mb > 50:
                            logger.warning(f"File too large ({content_size_mb:.2f}MB), skipping: {asset_url}")
                            failed_count += 1
                            continue
                        
                        zf.writestr(zip_path, asset_resp.content)
                        asset_mapping[asset_url] = zip_path
                        downloaded_count += 1
                        logger.debug(f"Downloaded: {asset_url} ({content_size_mb:.2f}MB)")
                        
                        # تصحیح در HTML
                        if tag and hasattr(tag, 'name'):
                            if tag.name == 'link':
                                tag['href'] = zip_path
                            elif tag.name == 'script':
                                tag['src'] = zip_path
                            elif tag.name == 'img':
                                tag['src'] = zip_path
                                if 'data-src' in tag.attrs:
                                    del tag['data-src']
                                if 'data-lazy-src' in tag.attrs:
                                    del tag['data-lazy-src']
                            elif tag.name in ('source', 'video', 'audio'):
                                tag['src'] = zip_path
                    else:
                        logger.warning(f"Failed to download {asset_url} - Status: {asset_resp.status_code}")
                        failed_count += 1
                
                except requests.Timeout:
                    logger.warning(f"Timeout downloading: {asset_url}")
                    failed_count += 1
                except requests.ConnectionError as e:
                    logger.warning(f"Connection error for {asset_url}: {e}")
                    failed_count += 1
                except Exception as e:
                    logger.warning(f"Error downloading {asset_url}: {e}")
                    failed_count += 1
                    continue
            
            logger.info(f"Asset download summary - Success: {downloaded_count}, Failed: {failed_count}, Total: {len(unique_assets)}")
            
            # تصحیح CSS
            logger.info("Processing CSS files...")
            for file_info in zf.filelist:
                if file_info.filename.startswith('assets/css/'):
                    try:
                        css_content = zf.read(file_info.filename).decode('utf-8', errors='ignore')
                        pattern = r'url\([\'"]?(.*?)[\'"]?\)'
                        
                        def replacer(m):
                            orig = m.group(1)
                            if orig.startswith(('http', 'data:')) or orig.startswith('/'):
                                if orig.startswith('data:'):
                                    return m.group(0)
                                if orig.startswith('/'):
                                    abs_url = urljoin(url, orig)
                                else:
                                    abs_url = orig
                            else:
                                abs_url = urljoin(url, orig)
                            
                            abs_url, _ = urldefrag(abs_url)
                            
                            if abs_url in asset_mapping:
                                return f"url('{asset_mapping[abs_url]}')"
                            return m.group(0)
                        
                        new_css = re.sub(pattern, replacer, css_content)
                        zf.writestr(file_info.filename, new_css.encode('utf-8'))
                    except Exception as e:
                        logger.warning(f"Error processing CSS {file_info.filename}: {e}")
            
            # ذخیره HTML
            logger.info("Saving HTML file...")
            zf.writestr('index.html', str(soup).encode('utf-8'))
            zf.writestr('info.txt', f"""تعداد منابع دانلود شده: {downloaded_count}/{len(unique_assets)}
تعداد ناموفق: {failed_count}
آدرس: {url}

نکات:
- تمام عکس‌ها، فایل‌های CSS و JavaScript در پوشه assets موجود است
- فایل index.html نقطه شروع است
- اگر برخی عکس‌ها لود نشد، ممکن است به دلیل CORS یا سرور باشد
- برای باز کردن: index.html را در مرورگر باز کنید""")
        
        result_size_mb = len(zip_buffer.getvalue()) / (1024 * 1024)
        logger.info(f"Website download completed - Size: {result_size_mb:.2f}MB, Assets: {downloaded_count}")
        return zip_buffer.getvalue()
    
    except requests.Timeout:
        error_msg = "❌ خطا: زمان مجاز برای دانلود وب‌سایت تمام شد\n\nلطفا دوباره تلاش کنید یا یک وب‌سایت کوچک‌تر را انتخاب کنید"
        logger.error(f"Website download timeout: {url}")
        return error_msg
    except requests.ConnectionError as e:
        error_msg = f"❌ خطا در اتصال به وب‌سایت:\n{str(e)[:100]}\n\nلطفا آدرس را بررسی کنید"
        logger.error(f"Website download connection error: {e}")
        return error_msg
    except Exception as e:
        error_msg = f"❌ خطا در دانلود وب‌سایت:\n{str(e)[:150]}"
        logger.error(f"download_website error: {e}", exc_info=True)
        return error_msg
