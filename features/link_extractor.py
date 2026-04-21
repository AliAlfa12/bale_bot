import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

def extract_links_from_webpage(url):
    """
    استخراج تمام لینک‌های یک صفحه وب
    """
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return None, f"❌ خطا: وضعیت {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set()
        
        # استخراج تمام تگ‌های a
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith(('http://', 'https://')):
                links.add(href)
            elif href.startswith('/') or href.startswith('./') or href.startswith('../'):
                full_url = urljoin(url, href)
                links.add(full_url)
        
        # دسته‌بندی لینک‌ها
        internal_links = []
        external_links = []
        file_links = []
        
        domain = urlparse(url).netloc
        
        for link in links:
            parsed = urlparse(link)
            if parsed.netloc == domain:
                internal_links.append(link)
            else:
                external_links.append(link)
            
            # شناسایی لینک‌های فایل
            if any(ext in parsed.path.lower() for ext in ['.pdf', '.zip', '.rar', '.mp4', '.mp3', '.jpg', '.png']):
                file_links.append(link)
        
        # ذخیره لینک‌ها در فایل موقت
        temp_file = "extracted_links.txt"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(f"🔗 **لینک‌های استخراج شده از {url}**\n\n")
            f.write(f"📊 **آمار:**\n")
            f.write(f"- مجموع لینک‌ها: {len(links)}\n")
            f.write(f"- لینک‌های داخلی: {len(internal_links)}\n")
            f.write(f"- لینک‌های خارجی: {len(external_links)}\n")
            f.write(f"- لینک‌های فایل: {len(file_links)}\n\n")
            
            f.write("🔗 **لینک‌های داخلی:**\n")
            for link in internal_links[:50]:
                f.write(f"{link}\n")
            
            f.write("\n🌐 **لینک‌های خارجی:**\n")
            for link in external_links[:50]:
                f.write(f"{link}\n")
            
            f.write("\n📁 **لینک‌های فایل:**\n")
            for link in file_links[:50]:
                f.write(f"{link}\n")
            
            if len(links) > 150:
                f.write(f"\n... و {len(links) - 150} لینک دیگر")
        
        return temp_file, None
        
    except Exception as e:
        return None, f"❌ خطا در استخراج لینک‌ها: {str(e)[:100]}"
