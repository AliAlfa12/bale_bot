import os
import requests
import logging
from utils import create_rar_parts, create_inline_keyboard, download_file_with_headers, logger

GITHUB_TOKEN = os.environ.get("GH_TOKEN")

def _headers():
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'BaleBot/1.0'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers

def search_repo(query):
    try:
        r = requests.get(f"https://api.github.com/search/repositories?q={query}&per_page=5", headers=_headers(), timeout=10)
        if r.status_code != 200:
            return None, "❌ خطا در ارتباط با گیت‌هاب"
        items = r.json().get("items", [])
        if not items:
            return None, "❌ هیچ ریپویی یافت نشد."
        buttons = []
        for item in items:
            name = item["full_name"]
            stars = item["stargazers_count"]
            text = f"⭐ {stars} - {name}"
            callback_data = f"github_repo_{name}"
            buttons.append({"text": text, "callback_data": callback_data})
        buttons.append({"text": "🔙 برگشت", "callback_data": "back_to_menu"})
        return create_inline_keyboard(buttons, columns=1), None
    except Exception as e:
        logger.error(f"search_repo error: {e}")
        return None, f"❌ خطا: {str(e)[:100]}"

def download_repo(repo_name):
    try:
        url = f"https://api.github.com/repos/{repo_name}/zipball"
        r = requests.get(url, headers=_headers(), timeout=50)
        if r.status_code != 200:
            return f"❌ خطا (کد {r.status_code})"
        temp_filename = f"{repo_name.replace('/', '-')}.zip"
        with open(temp_filename, 'wb') as f:
            f.write(r.content)
        base_name = repo_name.replace('/', '-')
        parts = create_rar_parts(temp_filename, base_name, part_size_mb=19)
        os.remove(temp_filename)
        if not parts:
            return "❌ خطا در ایجاد پارت‌های RAR"
        return {"type": "download", "parts": parts, "repo": repo_name}
    except Exception as e:
        logger.error(f"download_repo error: {e}")
        return f"❌ خطا: {str(e)[:100]}"

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
        # همیشه لیست releases را می‌گیریم (بدون استفاده از endpoint /tags/)
        list_url = f"https://api.github.com/repos/{repo_name}/releases"
        r = requests.get(list_url, headers=_headers(), timeout=15)
        if r.status_code != 200:
            return None, f"❌ خطا در دریافت لیست ریلیزها (کد {r.status_code})"
        releases = r.json()
        target_release = None
        for rel in releases:
            if rel["tag_name"] == tag_name:
                target_release = rel
                break
        if not target_release:
            return None, f"❌ ریلیز با تگ {tag_name} پیدا نشد."
        assets = target_release.get("assets", [])
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

def download_release_asset(repo_name, tag_name, asset_name):
    try:
        # ابتدا لیست releases را بگیریم
        list_url = f"https://api.github.com/repos/{repo_name}/releases"
        r = requests.get(list_url, headers=_headers(), timeout=15)
        if r.status_code != 200:
            return f"❌ خطا در دریافت لیست ریلیزها (کد {r.status_code})"
        releases = r.json()
        target_release = None
        for rel in releases:
            if rel["tag_name"] == tag_name:
                target_release = rel
                break
        if not target_release:
            return f"❌ ریلیز با تگ {tag_name} پیدا نشد."
        assets = target_release.get("assets", [])
        target_asset = None
        for asset in assets:
            if asset["name"] == asset_name:
                target_asset = asset
                break
        if not target_asset:
            return f"❌ Asset '{asset_name}' یافت نشد"
        download_url = target_asset["browser_download_url"]
        response = download_file_with_headers(download_url, timeout=60)
        if not response or response.status_code != 200:
            return f"❌ خطا در دانلود (کد {response.status_code if response else 'No response'})"
        temp_filename = asset_name
        with open(temp_filename, 'wb') as f:
            f.write(response.content)
        base_name = os.path.splitext(asset_name)[0]
        parts = create_rar_parts(temp_filename, base_name, part_size_mb=19)
        os.remove(temp_filename)
        if not parts:
            return "❌ خطا در ایجاد پارت‌های RAR"
        return {"type": "download", "parts": parts, "repo": f"{repo_name} - {tag_name} - {asset_name}"}
    except Exception as e:
        logger.error(f"download_release_asset error: {e}")
        return f"❌ خطا: {str(e)[:100]}"
