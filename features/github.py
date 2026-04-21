import os
import requests
import logging
from utils import create_rar_parts, create_inline_keyboard, download_file_with_headers, logger

GITHUB_TOKEN = os.environ.get("GH_TOKEN")

def _headers():
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers

def get_releases(repo_name):
    try:
        url = f"https://api.github.com/repos/{repo_name}/releases"
        r = requests.get(url, headers=_headers(), timeout=15)
        if r.status_code != 200:
            return None, f"❌ خطا در دریافت ریلیزها (کد {r.status_code})"
        releases = r.json()
        if not releases:
            return None, "⚠️ این ریپو هیچ ریلیزی ندارد."
        buttons = []
        for rel in releases[:10]:
            tag = rel["tag_name"]
            name = rel["name"] or tag
            published = rel["published_at"][:10] if rel["published_at"] else "نامشخص"
            assets_count = len(rel.get("assets", []))
            if rel.get("draft"):
                name = f"[DRAFT] {name}"
            if rel.get("prerelease"):
                name = f"[PRE] {name}"
            text = f"{name} ({tag}) - {published} - {assets_count} فایل"
            callback_data = f"github_release_assets_{repo_name}|{tag}"
            buttons.append({"text": text, "callback_data": callback_data})
        buttons.append({"text": "🔙 برگشت", "callback_data": "back_to_menu"})
        return create_inline_keyboard(buttons, columns=1), None
    except Exception as e:
        logger.error(f"get_releases error: {e}")
        return None, f"❌ خطا: {str(e)[:100]}"

def get_release_assets(repo_name, tag_name):
    try:
        url = f"https://api.github.com/repos/{repo_name}/releases/tags/{tag_name}"
        r = requests.get(url, headers=_headers(), timeout=15)
        if r.status_code == 404:
            # fallback: جستجو در لیست ریلیزها
            list_url = f"https://api.github.com/repos/{repo_name}/releases"
            r2 = requests.get(list_url, headers=_headers(), timeout=15)
            if r2.status_code == 200:
                for rel in r2.json():
                    if rel["tag_name"] == tag_name:
                        assets = rel.get("assets", [])
                        break
                else:
                    return None, f"❌ ریلیز با تگ {tag_name} پیدا نشد."
            else:
                return None, f"❌ خطا در دریافت اطلاعات ریلیز (کد {r.status_code})"
        else:
            assets = r.json().get("assets", [])
        
        if not assets:
            return None, "⚠️ این ریلیز هیچ فایل ضمیمه‌ای ندارد."
        
        buttons = []
        for asset in assets:
            name = asset["name"]
            size_mb = asset["size"] / (1024*1024)
            downloads = asset.get("download_count", 0)
            text = f"📎 {name} - {size_mb:.1f}MB - {downloads} دانلود"
            callback_data = f"github_download_asset_{repo_name}|{tag_name}|{name}"
            buttons.append({"text": text, "callback_data": callback_data})
        buttons.append({"text": "🔙 برگشت به ریلیزها", "callback_data": f"releases_repo_{repo_name}"})
        buttons.append({"text": "🔙 برگشت به منو", "callback_data": "back_to_menu"})
        return create_inline_keyboard(buttons, columns=1), None
    except Exception as e:
        logger.error(f"get_release_assets error: {e}")
        return None, f"❌ خطا: {str(e)[:100]}"

# توابع دیگر (search_repo, download_repo, download_release_asset) مانند قبل
