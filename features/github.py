import os
import requests
import logging
from utils import create_rar_parts, create_inline_keyboard, download_file_with_headers, logger

GITHUB_TOKEN = os.environ.get("GH_TOKEN")

def _headers():
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'BaleBot/1.0 (https://github.com/yourbot)'
    }
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers

def _log_response(resp, context):
    logger.info(f"{context}: status={resp.status_code}, url={resp.url}")
    if resp.status_code != 200:
        try:
            logger.error(f"{context} error body: {resp.text[:200]}")
        except:
            pass

def search_github(query):
    """
    جستجوی کلی در گیت‌هاب:
    - اگر query شامل '/' باشد → ریپوی دقیق
    - در غیر این صورت: جستجو در ریپوها و کاربران
    باز می‌گرداند: (keyboard, error_message)
    """
    if '/' in query:
        # جستجوی دقیق ریپو
        try:
            url = f"https://api.github.com/repos/{query}"
            r = requests.get(url, headers=_headers(), timeout=10)
            _log_response(r, "search_exact_repo")
            if r.status_code != 200:
                return None, "❌ ریپو مورد نظر یافت نشد."
            repo = r.json()
            full_name = repo["full_name"]
            stars = repo["stargazers_count"]
            # ساخت یک دکمه برای همین ریپو
            buttons = [{"text": f"⭐ {stars} - {full_name}", "callback_data": f"github_repo_{full_name}"}]
            buttons.append({"text": "🔙 برگشت", "callback_data": "back_to_menu"})
            return create_inline_keyboard(buttons, columns=1), None
        except Exception as e:
            logger.error(f"exact repo search error: {e}")
            return None, "❌ خطا در جستجوی ریپو"
    else:
        # جستجوی عمومی در ریپوها و کاربران
        repos = []
        users = []
        try:
            # جستجوی ریپوها (بر اساس نام)
            repo_url = f"https://api.github.com/search/repositories?q={query}+in:name&per_page=5"
            r_repo = requests.get(repo_url, headers=_headers(), timeout=10)
            _log_response(r_repo, "search_repos_general")
            if r_repo.status_code == 200:
                repos = r_repo.json().get("items", [])
        except Exception as e:
            logger.error(f"repo search error: {e}")
        
        try:
            # جستجوی کاربران (بر اساس نام کاربری)
            user_url = f"https://api.github.com/search/users?q={query}+in:login&per_page=5"
            r_user = requests.get(user_url, headers=_headers(), timeout=10)
            _log_response(r_user, "search_users_general")
            if r_user.status_code == 200:
                users = r_user.json().get("items", [])
        except Exception as e:
            logger.error(f"user search error: {e}")
        
        if not repos and not users:
            return None, "❌ هیچ نتیجه‌ای برای جستجوی شما یافت نشد."
        
        buttons = []
        for repo in repos[:5]:
            full_name = repo["full_name"]
            stars = repo["stargazers_count"]
            buttons.append({"text": f"📁 {full_name} ⭐ {stars}", "callback_data": f"github_repo_{full_name}"})
        for user in users[:5]:
            login = user["login"]
            buttons.append({"text": f"👤 {login}", "callback_data": f"github_user_{login}"})
        buttons.append({"text": "🔙 برگشت", "callback_data": "back_to_menu"})
        return create_inline_keyboard(buttons, columns=1), None

def get_user_repos(username):
    """دریافت لیست ریپوهای یک کاربر (حداکثر ۱۰ عدد)"""
    try:
        url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10"
        r = requests.get(url, headers=_headers(), timeout=10)
        _log_response(r, f"user_repos_{username}")
        if r.status_code != 200:
            return None, "❌ خطا در دریافت ریپوهای کاربر"
        repos = r.json()
        if not repos:
            return None, "⚠️ این کاربر هیچ ریپوی عمومی ندارد."
        buttons = []
        for repo in repos:
            full_name = repo["full_name"]
            stars = repo["stargazers_count"]
            buttons.append({"text": f"📁 {full_name} ⭐ {stars}", "callback_data": f"github_repo_{full_name}"})
        buttons.append({"text": "🔙 برگشت به جستجو", "callback_data": "back_to_menu"})
        return create_inline_keyboard(buttons, columns=1), None
    except Exception as e:
        logger.error(f"get_user_repos error: {e}")
        return None, "❌ خطا در دریافت اطلاعات کاربر"

# توابع قبلی (download_repo, get_releases, get_release_assets, download_release_asset) بدون تغییر
def download_repo(repo_name):
    try:
        url = f"https://api.github.com/repos/{repo_name}/zipball"
        r = requests.get(url, headers=_headers(), timeout=50)
        _log_response(r, "download_repo")
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
        _log_response(r, "get_releases")
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
        url_list = f"https://api.github.com/repos/{repo_name}/releases"
        r_list = requests.get(url_list, headers=_headers(), timeout=15)
        _log_response(r_list, "get_release_assets_list")
        if r_list.status_code != 200:
            return None, f"❌ خطا در دریافت لیست ریلیزها (کد {r_list.status_code})"
        releases = r_list.json()
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
            text = f"📎 {name} - {size_mb:.1f}MB"
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
        url_list = f"https://api.github.com/repos/{repo_name}/releases"
        r = requests.get(url_list, headers=_headers(), timeout=15)
        _log_response(r, "download_release_asset_list")
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
