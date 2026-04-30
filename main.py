import os
import time
import requests
import signal
from urllib.parse import urlparse

from utils import (
    send_message, edit_message_text, send_document, send_bytes_as_document,
    create_inline_keyboard, remove_reply_keyboard, logger, 
    download_file_with_headers, create_rar_parts, clean_files_safe,
    sanitize_website_name
)
from features.user_settings import (
    get_user_settings, set_download_type, set_google_drive_folder,
    upload_to_google_drive, DOWNLOAD_TYPES
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

# ✅ Global flag for graceful shutdown
SHUTDOWN_REQUESTED = False

def signal_handler(signum, frame):
    """✅ Handle shutdown signals gracefully"""
    global SHUTDOWN_REQUESTED
    logger.info(f"📢 Received signal {signum}, preparing to shutdown...")
    SHUTDOWN_REQUESTED = True

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def get_updates(offset):
    """✅ بهبور شده: better error handling"""
    url = f"https://tapi.bale.ai/bot{os.environ['BALE_TOKEN']}/getUpdates"
    params = {"offset": offset, "timeout": 25, "allowed_updates": ["message", "callback_query"]}
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
            else:
                logger.warning(f"API error: {data.get('description', 'Unknown')}")
        
        elif resp.status_code in (502, 503):
            logger.warning(f"⚠️ Server {resp.status_code} - will retry")
            time.sleep(2)
            return []
        
        elif resp.status_code == 429:
            logger.warning("⚠️ Rate limited - waiting...")
            time.sleep(10)
            return []
        
        else:
            logger.error(f"HTTP {resp.status_code}")
    
    except requests.Timeout:
        logger.warning("⚠️ Timeout")
    except requests.ConnectionError:
        logger.warning("⚠️ Connection error")
    except Exception as e:
        logger.error(f"Error: {e}")
    
    return []

def handle_rar_download(chat_id, file_path, description, cleanup=True):
    """✅ RAR download - with Google Drive support"""
    try:
        user_settings = get_user_settings(chat_id)
        download_type = user_settings.get('download_type', 'direct')
        
        logger.info(f"Download type: {download_type}")
        
        # ✅ نوع 1: دانلود مستقیم (پارت‌بندی)
        if download_type == 'direct':
            logger.info(f"Direct download: {file_path}")
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            parts = create_rar_parts(file_path, base_name, 19)
            
            if cleanup:
                try:
                    os.remove(file_path)
                except:
                    pass
            
            if parts:
                if len(parts) == 1:
                    send_document(chat_id, parts[0], f"✅ {description}")
                else:
                    send_message(chat_id, f"📦 {len(parts)} پارت RAR")
                    for part_file in parts:
                        send_document(chat_id, part_file, f"📎 {part_file}")
                    clean_files_safe(parts)
            else:
                send_message(chat_id, "❌ خطا در فشرده‌سازی")
            
            return True
        
        # ✅ نوع 2: آپلود به Google Drive
        elif download_type == 'google_drive':
            logger.info(f"Google Drive upload: {file_path}")
            
            folder_id = user_settings.get('google_drive_folder_id')
            if not folder_id:
                send_message(chat_id, "❌ Folder ID تنظیم نشده است\n\nلطفاً تنظیمات را بررسی کنید")
                return False
            
            deploy_url = os.environ.get('GOOGLE_DRIVE_DEPLOY_URL')
            if not deploy_url:
                send_message(chat_id, "❌ Deploy URL تنظیم نشده است")
                logger.error("GOOGLE_DRIVE_DEPLOY_URL not set")
                return False
            
            send_message(chat_id, "⏳ در حال آپلود به Google Drive...")
            
            # فشرده‌سازی بدون پارت‌بندی
            try:
                rar_file = os.path.splitext(file_path)[0] + '.rar'
                cmd = f'rar a "{rar_file}" "{file_path}"'
                subprocess.run(shlex.split(cmd), check=True, capture_output=True, timeout=300)
                logger.info(f"RAR created: {rar_file}")
            except Exception as e:
                logger.error(f"RAR creation error: {e}")
                send_message(chat_id, f"❌ خطا در فشرده‌سازی: {str(e)[:100]}")
                return False
            
            # آپلود
            success, message = upload_to_google_drive(rar_file, folder_id, deploy_url)
            
            # پاک‌سازی
            if cleanup:
                try:
                    os.remove(file_path)
                    os.remove(rar_file)
                except:
                    pass
            
            send_message(chat_id, message)
            return success
    
    except Exception as e:
        logger.error(f"handle_rar_download error: {e}")
        send_message(chat_id, f"❌ خطا: {str(e)[:150]}")
        return False

def process_callback(chat_id, message_id, data):
    """✅ بهبور شده callback handler"""
    logger.info(f"Callback: {data[:50]}")
    
    try:
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

        elif data == "menu_settings":
            from features.menu import show_settings_menu
            show_settings_menu(chat_id)
        elif data == "settings_menu":
            from features.menu import show_settings_menu
            show_settings_menu(chat_id)
        elif data == "settings_download_direct":
            set_download_type(chat_id, 'direct')
            send_message(chat_id, "✅ نوع دانلود: دانلود مستقیم (پارت‌بندی)")
            from features.menu import show_settings_menu
            show_settings_menu(chat_id)
        elif data == "settings_download_gdrive":
            set_download_type(chat_id, 'google_drive')
            send_message(chat_id, "✅ نوع دانلود: آپلود به Google Drive")
            from features.menu import show_gdrive_settings
            show_gdrive_settings(chat_id)
            user_states[chat_id] = {"action": "waiting_for_gdrive_folder_id"}
        
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
        
        # ========== GitHub ==========
        elif data.startswith("github_repo_"):
            repo = data[12:]
            btns = [
                {"text": "📥 دانلود ریپو", "callback_data": f"download_repo_{repo}"},
                {"text": "🏷️ ریلیزها", "callback_data": f"releases_repo_{repo}"},
                {"text": "🔙 منو", "callback_data": "back_to_menu"}
            ]
            reply_markup = create_inline_keyboard(btns, columns=1)
            edit_message_text(chat_id, message_id, f"📦 **{repo}**", reply_markup)
        
        elif data.startswith("github_user_"):
            username = data[12:]
            keyboard, error = get_user_repos(username)
            if error:
                send_message(chat_id, error)
            else:
                edit_message_text(chat_id, message_id, f"📁 ریپوهای {username}:", keyboard)
        
        elif data.startswith("download_repo_"):
            repo = data[14:]
            edit_message_text(chat_id, message_id, f"⬇️ دانلود {repo}...", None)
            result = download_repo(repo)
            if isinstance(result, dict) and result.get("type") == "download":
                parts = result["parts"]
                if len(parts) == 1:
                    send_document(chat_id, parts[0], f"✅ {repo}")
                else:
                    send_message(chat_id, f"📦 {len(parts)} پارت")
                    for p in parts:
                        send_document(chat_id, p, f"📎 {p}")
                    clean_files_safe(parts)
            else:
                send_message(chat_id, result)
            show_main_menu(chat_id)
        
        elif data.startswith("releases_repo_"):
            repo = data[14:]
            keyboard, error = get_releases(repo)
            if error:
                send_message(chat_id, error)
            else:
                edit_message_text(chat_id, message_id, f"🏷️ ریلیزهای {repo}:", keyboard)
        
        elif data.startswith("github_release_assets_"):
            rest = data[len("github_release_assets_"):]
            parts = rest.split("|")
            if len(parts) == 2:
                repo, tag = parts
                keyboard, error = get_release_assets(repo, tag)
                if error:
                    send_message(chat_id, error)
                else:
                    edit_message_text(chat_id, message_id, f"📦 فایل‌های {tag}:", keyboard)
        
        elif data.startswith("github_download_asset_"):
            rest = data[len("github_download_asset_"):]
            parts = rest.split("|")
            if len(parts) == 3:
                repo, tag, asset_name = parts
                result = download_release_asset(repo, tag, asset_name)
                if isinstance(result, dict) and result.get("type") == "download":
                    plist = result["parts"]
                    if len(plist) == 1:
                        send_document(chat_id, plist[0], f"✅ {asset_name}")
                    else:
                        send_message(chat_id, f"📦 {len(plist)} پارت")
                        for pf in plist:
                            send_document(chat_id, pf, f"📎 {pf}")
                        clean_files_safe(plist)
                else:
                    send_message(chat_id, result)
                show_main_menu(chat_id)
        
        # ========== YouTube ==========
        elif data.startswith("youtube_video_"):
            url = data[14:]
            file_path, result = download_youtube_video(url, chat_id, send_message)
            if file_path:
                handle_rar_download(chat_id, file_path, "🎬 ویدیو")
            else:
                send_message(chat_id, result)
            show_main_menu(chat_id)
        
        elif data.startswith("youtube_audio_"):
            url = data[15:]
            file_path, result = download_youtube_audio(url, chat_id, send_message)
            if file_path:
                handle_rar_download(chat_id, file_path, "🎵 صدا")
            else:
                send_message(chat_id, result)
            show_main_menu(chat_id)
    
    except Exception as e:
        logger.error(f"Callback error: {e}")
        send_message(chat_id, f"❌ خطا: {str(e)[:150]}")

def process_message(chat_id, text):
    """✅ بهبور شده message handler"""
    try:
        if chat_id in user_states:
            state = user_states[chat_id]
            action = state.get("action")
            
            if action == "waiting_for_repo":
                repo = text.strip()
                ctx = state.get("context", "search")
                del user_states[chat_id]
                
                if ctx == "search":
                    keyboard, err = search_github(repo)
                    if err:
                        send_message(chat_id, err)
                    else:
                        send_message(chat_id, "نتایج:", reply_markup=keyboard)
                elif ctx == "download":
                    result = download_repo(repo)
                    if isinstance(result, dict) and result.get("type") == "download":
                        parts = result["parts"]
                        if len(parts) == 1:
                            send_document(chat_id, parts[0], f"✅ {repo}")
                        else:
                            for p in parts:
                                send_document(chat_id, p, f"📎 {p}")
                            clean_files_safe(parts)
                    else:
                        send_message(chat_id, result)
                    show_main_menu(chat_id)
            
            elif action == "waiting_for_command":
                cmd = text.strip()
                del user_states[chat_id]
                run_command(cmd, chat_id)
                show_main_menu(chat_id)
            
            elif action == "waiting_for_ai":
                q = text.strip()
                del user_states[chat_id]
                ask_gemini(q, chat_id)
                show_main_menu(chat_id)
            
            elif action == "waiting_for_download_link":
                url = text.strip()
                del user_states[chat_id]
                try:
                    r = download_file_with_headers(url, timeout=60)
                    if r and r.status_code == 200:
                        content = r.content
                        size_mb = len(content)/(1024*1024)
                        fname = urlparse(url).path.split("/")[-1] or "file"
                        with open(fname, 'wb') as f:
                            f.write(content)
                        handle_rar_download(chat_id, fname, f"📁 {size_mb:.1f}MB")
                    else:
                        send_message(chat_id, "❌ دانلود ناموفق")
                except Exception as e:
                    send_message(chat_id, f"❌ خطا: {str(e)[:150]}")
                show_main_menu(chat_id)
            
            elif action == "waiting_for_website_url":
                url = text.strip()
                del user_states[chat_id]
                result = download_website(url, chat_id)
                if isinstance(result, bytes):
                    website_name = sanitize_website_name(url)
                    filename = f"{website_name}.zip"
                    send_bytes_as_document(chat_id, result, filename, f"🌐 {url}")
                else:
                    send_message(chat_id, f"❌ {result}")
                show_main_menu(chat_id)
            
            elif action == "waiting_for_extract_links":
                url = text.strip()
                del user_states[chat_id]
                file_path, error = extract_links_from_webpage(url)
                if error:
                    send_message(chat_id, error)
                else:
                    send_document(chat_id, file_path, "🔗 لینک‌ها")
                    try:
                        os.remove(file_path)
                    except:
                        pass
                show_main_menu(chat_id)

            elif action == "waiting_for_gdrive_folder_id":
                folder_id = text.strip()
                del user_states[chat_id]
                
                if set_google_drive_folder(chat_id, folder_id):
                    send_message(chat_id, f"✅ Folder ID ذخیره شد: `{folder_id}`")
                    from features.menu import show_settings_menu
                    show_settings_menu(chat_id)
                else:
                    send_message(chat_id, "❌ خطا در ذخیره Folder ID")
                    show_main_menu(chat_id)
            
            elif action == "waiting_for_youtube":
                url = text.strip()
                del user_states[chat_id]
                btns = [
                    {"text": "🎬 ویدیو", "callback_data": f"youtube_video_{url}"},
                    {"text": "🎵 صدا", "callback_data": f"youtube_audio_{url}"},
                    {"text": "🔙 منو", "callback_data": "back_to_menu"}
                ]
                send_message(chat_id, "انتخاب کنید:", reply_markup=create_inline_keyboard(btns, columns=1))
            
            return
        
        if text == "/start":
            show_main_menu(chat_id)
        elif text == "/help":
            show_help(chat_id)
            show_main_menu(chat_id)
        else:
            send_message(chat_id, "❓ از منو استفاده کنید")
            show_main_menu(chat_id)
    
    except Exception as e:
        logger.error(f"Message error: {e}")
        send_message(chat_id, f"❌ خطا: {str(e)[:150]}")

def main():
    """✅ Main bot loop with graceful shutdown"""
    global SHUTDOWN_REQUESTED
    
    offset_file = "offset.txt"
    offset = 0
    if os.path.exists(offset_file):
        try:
            offset = int(open(offset_file).read().strip())
        except:
            offset = 0
    
    start_time = time.time()
    MAX_RUNTIME = 330 * 60  # 330 دقیقه = 5.5 ساعت
    
    logger.info("=" * 60)
    logger.info("🤖 BOT STARTED")
    logger.info(f"Offset: {offset}")
    logger.info("=" * 60)
    
    try:
        while (time.time() - start_time) < MAX_RUNTIME and not SHUTDOWN_REQUESTED:
            try:
                updates = get_updates(offset)
                
                if not updates:
                    time.sleep(1)
                    continue
                
                for upd in updates:
                    if SHUTDOWN_REQUESTED:
                        break
                    
                    update_id = upd.get("update_id")
                    if update_id and update_id >= offset:
                        offset = update_id + 1
                        
                        try:
                            if "callback_query" in upd:
                                cb = upd["callback_query"]
                                chat_id = cb["message"]["chat"]["id"]
                                message_id = cb["message"]["message_id"]
                                data = cb["data"]
                                
                                try:
                                    requests.post(
                                        f"https://tapi.bale.ai/bot{os.environ['BALE_TOKEN']}/answerCallbackQuery",
                                        json={"callback_query_id": cb["id"]},
                                        timeout=5
                                    )
                                except:
                                    pass
                                
                                process_callback(chat_id, message_id, data)
                            
                            elif "message" in upd:
                                msg = upd["message"]
                                chat_id = msg["chat"]["id"]
                                text = msg.get("text", "")
                                process_message(chat_id, text)
                        
                        except Exception as e:
                            logger.error(f"Update error: {e}")
                
                with open(offset_file, "w") as f:
                    f.write(str(offset))
            
            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(5)
    
    except KeyboardInterrupt:
        logger.info("💤 Interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        elapsed = (time.time() - start_time) / 60
        logger.info("=" * 60)
        logger.info(f"🤖 BOT STOPPED")
        logger.info(f"Runtime: {elapsed:.0f} minutes")
        logger.info(f"Offset: {offset}")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()
