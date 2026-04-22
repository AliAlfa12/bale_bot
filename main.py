import os
import time
import requests
from urllib.parse import urlparse
from utils import (
    send_message, edit_message_text, send_document, send_bytes_as_document,
    create_inline_keyboard, remove_reply_keyboard, logger, 
    download_file_with_headers, create_rar_parts, clean_files_safe
)
from features.menu import (
    show_main_menu, show_help, ask_for_repo_name, ask_for_command, 
    ask_for_ai_question, ask_for_download_link, ask_for_website_url, 
    ask_for_extract_links_url, ask_for_youtube_url
)
from features.github import search_github, get_user_repos, download_repo, get_releases, get_release_assets, download_release_asset
from features.shell import run_command
from features.ai import ask_gemini
from features.network_test import test_site_accessibility
from features.website_downloader import download_website
from features.link_extractor import extract_links_from_webpage
from features.youtube_downloader import download_youtube_video, download_youtube_audio

user_states = {}

def get_updates(offset):
    url = f"https://tapi.bale.ai/bot{os.environ['BALE_TOKEN']}/getUpdates"
    params = {"offset": offset, "timeout": 30, "allowed_updates": ["message", "callback_query"]}
    try:
        resp = requests.get(url, params=params, timeout=35)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
    except Exception as e:
        logger.error(f"getUpdates error: {e}")
    return []

def handle_rar_download(chat_id, file_path, description, cleanup=True):
    """
    ✅ NEW: یک تابع یکپارچه برای دانلود و فشرده‌سازی RAR
    حذف تکرار کد در ۴ مکان
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    parts = create_rar_parts(file_path, base_name, 19)
    
    if cleanup:
        try:
            os.remove(file_path)
        except FileNotFoundError:
            logger.warning(f"File not found for cleanup: {file_path}")
        except Exception as e:
            logger.error(f"Cleanup error for {file_path}: {e}")
    
    if parts:
        if len(parts) == 1:
            send_document(chat_id, parts[0], f"✅ {description}")
        else:
            send_message(chat_id, f"📦 فایل به {len(parts)} پارت RAR تقسیم شد")
            for part_file in parts:
                send_document(chat_id, part_file, f"📎 {part_file}")
            # Clean up parts after sending
            clean_files_safe(parts)
    else:
        send_message(chat_id, "❌ خطا در فشرده‌سازی")
    
    return bool(parts)

def process_callback(chat_id, message_id, data):
    logger.info(f"Callback: {data} from {chat_id}, message_id={message_id}")
    
    # ========== منوی اصلی ==========
    if data == "menu_search":
        user_states[chat_id] = {"action": "waiting_for_repo", "context": "search"}
        ask_for_repo_name(chat_id)
    elif data == "menu_download":
        user_states[chat_id] = {"action": "waiting_for_repo", "context": "download"}
        ask_for_repo_name(chat_id)
    elif data == "menu_releases":
        user_states[chat_id] = {"action": "waiting_for_repo", "context": "releases"}
        ask_for_repo_name(chat_id)
    elif data == "menu_cli":
        user_states[chat_id] = {"action": "waiting_for_command"}
        ask_for_command(chat_id)
    elif data == "menu_ai":
        user_states[chat_id] = {"action": "waiting_for_ai"}
        ask_for_ai_question(chat_id)
    elif data == "menu_download_link":
        user_states[chat_id] = {"action": "waiting_for_download_link"}
        ask_for_download_link(chat_id)
    elif data == "menu_download_website":
        user_states[chat_id] = {"action": "waiting_for_website_url"}
        ask_for_website_url(chat_id)
    elif data == "menu_extract_links":
        user_states[chat_id] = {"action": "waiting_for_extract_links"}
        ask_for_extract_links_url(chat_id)
    elif data == "menu_youtube":
        user_states[chat_id] = {"action": "waiting_for_youtube"}
        ask_for_youtube_url(chat_id)
    elif data == "menu_network_test":
        test_site_accessibility(chat_id)
        show_main_menu(chat_id)
    elif data == "menu_help":
        show_help(chat_id)
        show_main_menu(chat_id)
    elif data == "back_to_menu":
        if chat_id in user_states:
            del user_states[chat_id]
        show_main_menu(chat_id)
    
    # ========== جستجوی گیت‌هاب (ریپو یا کاربر) ==========
    elif data.startswith("github_repo_"):
        repo = data[12:]
        btns = [
            {"text": "📥 دانلود ریپو", "callback_data": f"download_repo_{repo}"},
            {"text": "🏷️ مشاهده ریلیزها", "callback_data": f"releases_repo_{repo}"},
            {"text": "🔙 برگشت به منو", "callback_data": "back_to_menu"}
        ]
        reply_markup = create_inline_keyboard(btns, columns=1)
        edit_message_text(chat_id, message_id, f"📦 **{repo}**\nچه کاری انجام دهم؟", reply_markup)
    
    elif data.startswith("github_user_"):
        username = data[12:]
        edit_message_text(chat_id, message_id, f"🔍 در حال دریافت ریپوهای کاربر {username}...", None)
        keyboard, error = get_user_repos(username)
        if error:
            send_message(chat_id, error)
            show_main_menu(chat_id)
        else:
            edit_message_text(chat_id, message_id, f"📁 ریپوهای {username}:", keyboard)
    
    # ========== دانلود مستقیم ریپو ==========
    elif data.startswith("download_repo_"):
        repo = data[14:]
        edit_message_text(chat_id, message_id, f"⬇️ شروع دانلود {repo} ...", None)
        result = download_repo(repo)
        if isinstance(result, dict) and result.get("type") == "download":
            parts = result["parts"]
            if len(parts) == 1:
                send_document(chat_id, parts[0], f"✅ {repo} دانلود شد")
            else:
                send_message(chat_id, f"📦 ریپو به {len(parts)} پارت RAR تقسیم شد")
                for part_file in parts:
                    send_document(chat_id, part_file, f"📎 {part_file}")
                clean_files_safe(parts)
        else:
            send_message(chat_id, result)
        show_main_menu(chat_id)
    
    # ========== ریلیزها ==========
    elif data.startswith("releases_repo_"):
        repo = data[14:]
        edit_message_text(chat_id, message_id, f"🔍 در حال دریافت ریلیزهای {repo} ...", None)
        keyboard, error = get_releases(repo)
        if error:
            send_message(chat_id, error)
            show_main_menu(chat_id)
        else:
            edit_message_text(chat_id, message_id, f"🏷️ ریلیزهای {repo}:", keyboard)
    
    elif data.startswith("github_release_assets_"):
        rest = data[len("github_release_assets_"):]
        parts = rest.split("|")
        if len(parts) == 2:
            repo, tag = parts
            edit_message_text(chat_id, message_id, f"🔍 در حال دریافت فایل‌های ریلیز {tag} ...", None)
            keyboard, error = get_release_assets(repo, tag)
            if error:
                send_message(chat_id, error)
                show_main_menu(chat_id)
            else:
                edit_message_text(chat_id, message_id, f"📦 فایل‌های موجود در ریلیز {tag}:", keyboard)
    
    elif data.startswith("github_download_asset_"):
        rest = data[len("github_download_asset_"):]
        parts = rest.split("|")
        if len(parts) == 3:
            repo, tag, asset_name = parts
            edit_message_text(chat_id, message_id, f"⬇️ شروع دانلود {asset_name} ...", None)
            result = download_release_asset(repo, tag, asset_name)
            if isinstance(result, dict) and result.get("type") == "download":
                plist = result["parts"]
                if len(plist) == 1:
                    send_document(chat_id, plist[0], f"✅ {asset_name} دانلود شد")
                else:
                    send_message(chat_id, f"📦 فایل به {len(plist)} پارت RAR تقسیم شد")
                    for pfile in plist:
                        send_document(chat_id, pfile, f"📎 {pfile}")
                    clean_files_safe(plist)
            else:
                send_message(chat_id, result)
            show_main_menu(chat_id)
    
    # ========== یوتیوب ==========
    elif data.startswith("youtube_video_"):
        url = data[14:]
        edit_message_text(chat_id, message_id, "🎬 شروع دانلود ویدیو...", None)
        file_path, result = download_youtube_video(url, chat_id, send_message)
        if file_path:
            handle_rar_download(chat_id, file_path, "🎬 ویدیو دانلود شد")
        else:
            send_message(chat_id, result)
        show_main_menu(chat_id)
    
    elif data.startswith("youtube_audio_"):
        # ✅ FIX: offset غلط بود (13)، حالا صحیح است (15)
        url = data[15:]
        edit_message_text(chat_id, message_id, "🎵 شروع دانلود صدا...", None)
        file_path, result = download_youtube_audio(url, chat_id, send_message)
        if file_path:
            handle_rar_download(chat_id, file_path, "🎵 فایل صوتی دانلود شد")
        else:
            send_message(chat_id, result)
        show_main_menu(chat_id)

def process_message(chat_id, text):
    if chat_id in user_states:
        state = user_states[chat_id]
        action = state.get("action")
        
        if action == "waiting_for_repo":
            repo = text.strip()
            ctx = state.get("context", "search")
            del user_states[chat_id]
            
            if ctx == "search":
                send_message(chat_id, f"🔍 در حال جستجوی {repo} ...")
                keyboard, err = search_github(repo)
                if err:
                    send_message(chat_id, err)
                    show_main_menu(chat_id)
                else:
                    send_message(chat_id, "نتایج جستجو:", reply_markup=keyboard)
            elif ctx == "download":
                send_message(chat_id, f"⬇️ شروع دانلود {repo} ...")
                result = download_repo(repo)
                if isinstance(result, dict) and result.get("type") == "download":
                    parts = result["parts"]
                    if len(parts) == 1:
                        send_document(chat_id, parts[0], f"✅ {repo} دانلود شد")
                    else:
                        send_message(chat_id, f"📦 ریپو به {len(parts)} پارت RAR تقسیم شد")
                        for p in parts:
                            send_document(chat_id, p, f"📎 {p}")
                        clean_files_safe(parts)
                else:
                    send_message(chat_id, result)
                show_main_menu(chat_id)
            elif ctx == "releases":
                send_message(chat_id, f"🔍 دریافت ریلیزهای {repo} ...")
                keyboard, err = get_releases(repo)
                if err:
                    send_message(chat_id, err)
                    show_main_menu(chat_id)
                else:
                    send_message(chat_id, f"🏷️ ریلیزهای {repo}:", reply_markup=keyboard)
        
        elif action == "waiting_for_command":
            cmd = text.strip()
            del user_states[chat_id]
            send_message(chat_id, f"💻 در حال اجرا: `{cmd}` ...")
            run_command(cmd, chat_id)
            show_main_menu(chat_id)
        
        elif action == "waiting_for_ai":
            q = text.strip()
            del user_states[chat_id]
            send_message(chat_id, "🤖 در حال فکر کردن...")
            ask_gemini(q, chat_id)
            show_main_menu(chat_id)
        
        elif action == "waiting_for_download_link":
            url = text.strip()
            del user_states[chat_id]
            send_message(chat_id, "⬇️ در حال دانلود فایل...")
            try:
                r = download_file_with_headers(url, timeout=60)
                if r and r.status_code == 200:
                    content = r.content
                    size_mb = len(content)/(1024*1024)
                    fname = urlparse(url).path.split("/")[-1] or "downloaded_file"
                    temp_file = fname
                    with open(temp_file, 'wb') as f:
                        f.write(content)
                    handle_rar_download(chat_id, temp_file, f"📁 {size_mb:.1f}MB - {fname}")
                else:
                    send_message(chat_id, "❌ خطا در دانلود فایل")
            except Exception as e:
                logger.error(f"Download link error: {e}")
                send_message(chat_id, f"❌ خطا: {str(e)[:100]}")
            show_main_menu(chat_id)
        
        elif action == "waiting_for_website_url":
            url = text.strip()
            del user_states[chat_id]
            result = download_website(url, chat_id)
            if isinstance(result, bytes):
                # ✅ NEW: استفاده از URL به عنوان اسم فایل
                website_name = urlparse(url).netloc.replace('www.', '').split('.')[0]
                filename = f"{website_name}.zip"
                send_bytes_as_document(chat_id, result, filename, f"🌐 وب‌سایت دانلود شده: {url}")
            else:
                send_message(chat_id, result)
            show_main_menu(chat_id)
        
        elif action == "waiting_for_extract_links":
            url = text.strip()
            del user_states[chat_id]
            send_message(chat_id, f"🔗 در حال استخراج لینک‌های {url}...")
            file_path, error = extract_links_from_webpage(url)
            if error:
                send_message(chat_id, error)
            else:
                send_document(chat_id, file_path, "🔗 لینک‌های استخراج شده")
                try:
                    os.remove(file_path)
                except FileNotFoundError:
                    pass
                except Exception as e:
                    logger.error(f"Error removing extracted links file: {e}")
            show_main_menu(chat_id)
        
        elif action == "waiting_for_youtube":
            url = text.strip()
            del user_states[chat_id]
            btns = [
                {"text": "🎬 دانلود ویدیو (حداکثر 720p)", "callback_data": f"youtube_video_{url}"},
                {"text": "🎵 دانلود صدا (MP3)", "callback_data": f"youtube_audio_{url}"},
                {"text": "🔙 برگشت به منو", "callback_data": "back_to_menu"}
            ]
            reply_markup = create_inline_keyboard(btns, columns=1)
            send_message(chat_id, "🎬 چه نوع دانلودی انجام شود؟", reply_markup)
        return
    
    if text == "/start":
        show_main_menu(chat_id)
    elif text == "/help":
        show_help(chat_id)
        show_main_menu(chat_id)
    else:
        send_message(chat_id, "❓ لطفاً از منوی اصلی استفاده کنید.")
        show_main_menu(chat_id)

def main():
    offset_file = "offset.txt"
    offset = 0
    if os.path.exists(offset_file):
        with open(offset_file, "r") as f:
            try:
                offset = int(f.read().strip())
            except ValueError:
                offset = 0
    
    start_time = time.time()
    MAX_RUNTIME = 5 * 3600 + 55 * 60
    
    logger.info("Bot started. Starting main loop...")
    
    while time.time() - start_time < MAX_RUNTIME:
        updates = get_updates(offset)
        if not updates:
            time.sleep(1)
            continue
        
        for upd in updates:
            update_id = upd.get("update_id")
            if update_id is not None and update_id >= offset:
                offset = update_id + 1
                if "callback_query" in upd:
                    cb = upd["callback_query"]
                    chat_id = cb["message"]["chat"]["id"]
                    message_id = cb["message"]["message_id"]
                    data = cb["data"]
                    try:
                        requests.post(f"https://tapi.bale.ai/bot{os.environ['BALE_TOKEN']}/answerCallbackQuery", json={"callback_query_id": cb["id"]})
                    except Exception as e:
                        logger.warning(f"answerCallbackQuery error: {e}")
                    process_callback(chat_id, message_id, data)
                elif "message" in upd:
                    msg = upd["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg.get("text", "")
                    process_message(chat_id, text)
        
        with open(offset_file, "w") as f:
            f.write(str(offset))
    
    logger.info("Max runtime reached, exiting...")

if __name__ == "__main__":
    main()
