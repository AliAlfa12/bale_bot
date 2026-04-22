import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from utils import logger

def extract_links_from_webpage(url):
    """
    ✅ IMPROVED: استخراج لینک‌های یک صفحه وب همراه با متن نمایشی
    - هر لینک با متن نمایشی (link text) ذخیره می‌شود
    - اگر متن نمایشی نباشد، خود URL نمایش داده می‌شود
    """
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return None, f"❌ خطا: وضعیت {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ✅ تغییر: استفاده از dictionary برای ذخیره متن + لینک
        links_data = {
            'internal': [],    # لیست اینرنال لینک‌ها
            'external': [],    # لیست خارجی لینک‌ها
            'file': []         # لیست فایل لینک‌ها
        }
        
        domain = urlparse(url).netloc
        
        # استخراج تمام تگ‌های a
        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href']
            # متن نمایشی لینک
            link_text = link_tag.get_text(strip=True) or href
            
            # تبدیل به URL کامل
            if href.startswith(('http://', 'https://')):
                full_url = href
            elif href.startswith('/') or href.startswith('./') or href.startswith('../'):
                full_url = urljoin(url, href)
            else:
                continue
            
            # دسته‌بندی لینک
            parsed = urlparse(full_url)
            link_entry = (link_text, full_url)  # ✅ tuple (متن, لینک)
            
            # شناسایی نوع لینک
            is_internal = parsed.netloc == domain
            is_file = any(ext in parsed.path.lower() for ext in 
                         ['.pdf', '.zip', '.rar', '.mp4', '.mp3', '.jpg', '.png', 
                          '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.exe', '.iso'])
            
            if is_file:
                links_data['file'].append(link_entry)
            elif is_internal:
                links_data['internal'].append(link_entry)
            else:
                links_data['external'].append(link_entry)
        
        # حذف تکراری‌ها (بر اساس URL)
        for category in links_data:
            unique_links = {}
            for text, link in links_data[category]:
                if link not in unique_links:
                    unique_links[link] = text
            links_data[category] = list(unique_links.items())
        
        # محاسبه کل لینک‌ها
        total_links = sum(len(links_data[cat]) for cat in links_data)
        
        # ذخیره لینک‌ها در فایل موقت
        temp_file = "extracted_links.txt"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(f"🔗 **لینک‌های استخراج شده از {url}**\n")
            f.write(f"{'=' * 60}\n\n")
            
            f.write(f"📊 **آمار:**\n")
            f.write(f"- مجموع لینک‌ها: {total_links}\n")
            f.write(f"- لینک‌های داخلی: {len(links_data['internal'])}\n")
            f.write(f"- لینک‌های خارجی: {len(links_data['external'])}\n")
            f.write(f"- لینک‌های فایل: {len(links_data['file'])}\n\n")
            
            # ✅ نمایش لینک‌های داخلی با متن
            if links_data['internal']:
                f.write("🔗 **لینک‌های داخلی:**\n")
                f.write("-" * 60 + "\n")
                for i, (link_text, link_url) in enumerate(links_data['internal'][:50], 1):
                    f.write(f"{i}. [{link_text}]\n   {link_url}\n\n")
            
            # ✅ نمایش لینک‌های خارجی با متن
            if links_data['external']:
                f.write("\n🌐 **لینک‌های خارجی:**\n")
                f.write("-" * 60 + "\n")
                for i, (link_text, link_url) in enumerate(links_data['external'][:50], 1):
                    f.write(f"{i}. [{link_text}]\n   {link_url}\n\n")
            
            # ✅ نمایش لینک‌های فایل با متن
            if links_data['file']:
                f.write("\n📁 **لینک‌های فایل:**\n")
                f.write("-" * 60 + "\n")
                for i, (link_text, link_url) in enumerate(links_data['file'][:50], 1):
                    f.write(f"{i}. [{link_text}]\n   {link_url}\n\n")
            
            # اگر بیشتر از ۱۵۰ لینک باشد
            remaining = total_links - 150
            if remaining > 0:
                f.write(f"\n... و {remaining} لینک دیگر\n")
        
        return temp_file, None
        
    except Exception as e:
        logger.error(f"Link extraction error: {e}")
        return None, f"❌ خطا در استخراج لینک‌ها: {str(e)[:100]}"
