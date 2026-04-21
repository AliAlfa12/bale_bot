import time
import requests
from utils import send_message

def test_site_accessibility(chat_id):
    sites = {
        "Cloudflare": "https://www.cloudflare.com",
        "YouTube": "https://www.youtube.com",
        "PyPI": "https://pypi.org",
        "GitHub": "https://github.com",
        "Google": "https://www.google.com",
        "Bale": "https://bale.ai"
    }
    send_message(chat_id, "🌐 در حال تست دسترسی به سایت‌های معروف...")
    results = []
    for name, url in sites.items():
        try:
            start = time.time()
            r = requests.get(url, timeout=5, allow_redirects=True)
            elapsed = int((time.time() - start) * 1000)
            if r.status_code == 200:
                results.append(f"✅ {name} - {elapsed}ms")
            else:
                results.append(f"⚠️ {name} - HTTP {r.status_code}")
        except requests.Timeout:
            results.append(f"❌ {name} - timeout (بیش از 5 ثانیه)")
        except Exception as e:
            results.append(f"❌ {name} - خطا: {str(e)[:30]}")
    output = "🌐 **نتایج تست دسترسی:**\n" + "\n".join(results)
    send_message(chat_id, output)
