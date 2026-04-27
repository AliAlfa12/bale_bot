import os
import time
import requests
from urllib.parse import urlparse
from utils import (
    send_message, edit_message_text, send_document, send_bytes_as_document,
    create_inline_keyboard, remove_reply_keyboard, logger, 
    download_file_with_headers, create_rar_parts, clean_files_safe,
    sanitize_website_name
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
        else:
            logger.error(f"getUpdates failed with status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"getUpdates error: {e}", exc_info=True)
    return []

def handle_rar_download(chat_id, file_path, description, cleanup=True):
    """
    ✅ تابع یکپارچه برای دانلود و فشرده‌سازی RAR
    """
    try:
        logger.info(f"Starting RAR compression for: {file_path}")
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        parts = create_rar_parts(file_path, base_name, 19)
        
        if cleanup:
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
            except FileNotFoundError:
                logger.warning(f"File not found for cleanup: {file_path}")
            except Exception as e:
                logger.error(f"Cleanup error for {file_path}: {e}")
        
        if parts:
            logger.info(f"RAR compression successful: {len(parts)} parts created")
            if len(parts) == 1:
                send_document(chat_id, parts[0], f"✅ {description}")
            else:
                send_message(chat_id, f"📦 فایل به {len(parts)} پارت RAR تقسیم شد")
                for part_file in parts:
                    send_document(chat_id, part_file, f"📎 {part_file}")
                clean_files_safe(parts)
        else:
            logger.error("RAR compression failed - no parts created")
            send_message(chat_id, "❌ خطا در فشرده‌سازی - لطفا دوباره تلاش کنید")
        
        return bool(parts)
    except Exception as e:
        logger.error(f"handle_rar_download error: {e}", exc_info=True)
        send_message(chat_id, f"❌ خطا در پردازش فایل: {str(e)[:150]}")
        return False

def process_callback(chat_id, message_id, data):
    logger.info(f"Callback received - Chat: {chat_id}, Data: {data}")
    
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
            logger.info(f"Downloading repo: {repo}")
            edit_message_text(chat_id, message_id, f"⬇️ شروع دانلود {repo} ...", None)
            result = download_repo(repo)
            if isinstance(result, dict) and result.get("type") == "download":
                parts = result["parts"]
                logger.info(f"Repository downloaded successfully: {len(parts)} parts")
                if len(parts) == 1:
                    send_document(chat_id, parts[0], f"✅ {repo} دانلود شد")
                else:
                    send_message(chat_id, f"📦 ریپو به {len(parts)} پارت RAR تقسیم شد")
                    for part_file in parts:
                        send_document(chat_id, part_file, f"📎 {part_file}")
                    clean_files_safe(parts)
            else:
                logger.error(f"Repository download failed: {result}")
                send_message(chat_id, result)
            show_main_menu(chat_id)
        
        # ========== ریلیزها ==========
        elif data.startswith("releases_repo_"):
            repo = data[14:]
            logger.info(f"Fetching releases for: {repo}")
            edit_message_text(chat_id, message_id, f"🔍 در حال دریافت ریلیزهای {repo} ...", None)
            keyboard, error = get_releases(repo)
            if error:
                logger.error(f"Release fetch error for {repo}: {error}")
                send_message(chat_id, error)
                show_main_menu(chat_id)
            else:
                edit_message_text(chat_id, message_id, f"🏷️ ریلیزهای {repo}:", keyboard)
        
        elif data.startswith("github_release_assets_"):
            rest = data[len("github_release_assets_"):]
            parts = rest.split("|")
            if len(parts) == 2:
                repo, tag = parts
                logger.info(f"Fetching assets for: {repo} - {tag}")
                edit_message_text(chat_id, message_id, f"🔍 در حال دریافت فایل‌های ریلیز {tag} ...", None)
                keyboard, error = get_release_assets(repo, tag)
                if error:
                    logger.error(f"Asset fetch error: {error}")
                    send_message(chat_id, error)
                    show_main_menu(chat_id)
                else:
                    edit_message_text(chat_id, message_id, f"📦 فایل‌های موجود در ریلیز {tag}:", keyboard)
        
        elif data.startswith("github_download_asset_"):
            rest = data[len("github_download_asset_"):]
            parts = rest.split("|")
            if len(parts) == 3:
                repo, tag, asset_name = parts
                logger.info(f"Downloading asset: {asset_name} from {repo}")
                edit_message_text(chat_id, message_id, f"⬇️ شروع دانلود {asset_name} ...", None)
                result = download_release_asset(repo, tag, asset_name)
                if isinstance(result, dict) and result.get("type") == "download":
                    plist = result["parts"]
                    logger.info(f"Asset downloaded: {len(plist)} parts")
                    if len(plist) == 1:
                        send_document(chat_id, plist[0], f"✅ {asset_name} دانلود شد")
                    else:
                        send_message(chat_id, f"📦 فایل به {len(plist)} پارت RAR تقسیم شد")
                        for pfile in plist:
                            send_document(chat_id, pfile, f"📎 {pfile}")
                        clean_files_safe(plist)
                else:
                    logger.error(f"Asset download failed: {result}")
                    send_message(chat_id, result)
                show_main_menu(chat_id)
        
        # ========== یوتیوب ==========
        elif data.startswith("youtube_video_"):
            url = data[14:]
            logger.info(f"Downloading YouTube video: {url}")
            edit_message_text(chat_id, message_id, "🎬 شروع دانلود ویدیو...", None)
            file_path, result = download_youtube_video(url, chat_id, send_message)
            if file_path:
                logger.info(f"YouTube video downloaded: {file_path}")
                handle_rar_download(chat_id, file_path, "🎬 ویدیو دانلود شد")
            else:
                logger.error(f"YouTube video download failed: {result}")
                send_message(chat_id, result)
            show_main_menu(chat_id)
        
        elif data.startswith("youtube_audio_"):
            url = data[15:]
            logger.info(f"Downloading YouTube audio: {url}")
            edit_message_text(chat_id, message_id, "🎵 شروع دانلود صدا...", None)
            file_path, result = download_youtube_audio(url, chat_id, send_message)
            if file_path:
                logger.info(f"YouTube audio downloaded: {file_path}")
                handle_rar_download(chat_id, file_path, "🎵 فایل صوتی دانلود شد")
            else:
                logger.error(f"YouTube audio download failed: {result}")
                send_message(chat_id, result)
            show_main_menu(chat_id)
    
    except Exception as e:
        logger.error(f"process_callback error: {e}", exc_info=True)
        send_message(chat_id, f"❌ خطای غیرمنتظره: {str(e)[:150]}")
        show_main_menu(chat_id)

def process_message(chat_id, text):
    try:
        if chat_id in user_states:
            state = user_states[chat_id]
            action = state.get("action")
            logger.info(f"Processing message - Chat: {chat_id}, Action: {action}, Text: {text[:50]}")
            
            if action == "waiting_for_repo":
                repo = text.strip()
                ctx = state.get("context", "search")
                del user_states[chat_id]
                
                if ctx == "search":
                    logger.info(f"Searching GitHub for: {repo}")
                    send_message(chat_id, f"🔍 در حال جستجوی {repo} ...")
                    keyboard, err = search_github(repo)
                    if err:
                        logger.error(f"GitHub search error: {err}")
                        send_message(chat_id, err)
                        show_main_menu(chat_id)
                    else:
                        send_message(chat_id, "نتایج جستجو:", reply_markup=keyboard)
                elif ctx == "download":
                    logger.info(f"Downloading repository: {repo}")
                    send_message(chat_id, f"⬇️ شروع دانلود {repo} ...")
                    result = download_repo(repo)
                    if isinstance(result, dict) and result.get("type") == "download":
                        parts = result["parts"]
                        logger.info(f"Repo downloaded: {len(parts)} parts")
                        if len(parts) == 1:
                            send_document(chat_id, parts[0], f"✅ {repo} دانلود شد")
                        else:
                            send_message(chat_id, f"📦 ریپو به {len(parts)} پارت RAR تقسیم شد")
                            for p in parts:
                                send_document(chat_id, p, f"📎 {p}")
                            clean_files_safe(parts)
                    else:
                        logger.error(f"Repo download error: {result}")
                        send_message(chat_id, result)
                    show_main_menu(chat_id)
                elif ctx == "releases":
                    logger.info(f"Fetching releases: {repo}")
                    send_message(chat_id, f"🔍 دریافت ریلیزهای {repo} ...")
                    keyboard, err = get_releases(repo)
                    if err:
                        logger.error(f"Releases fetch error: {err}")
                        send_message(chat_id, err)
                        show_main_menu(chat_id)
                    else:
                        send_message(chat_id, f"🏷️ ریلیزهای {repo}:", reply_markup=keyboard)
            
            elif action == "waiting_for_command":
                cmd = text.strip()
                del user_states[chat_id]
                logger.info(f"Executing command: {cmd}")
                send_message(chat_id, f"💻 در حال اجرا: `{cmd}` ...")
                run_command(cmd, chat_id)
                show_main_menu(chat_id)
            
            elif action == "waiting_for_ai":
                q = text.strip()
                del user_states[chat_id]
                logger.info(f"AI question: {q[:50]}")
                send_message(chat_id, "🤖 در حال فکر کردن...")
                ask_gemini(q, chat_id)
                show_main_menu(chat_id)
            
            elif action == "waiting_for_download_link":
                url = text.strip()
                del user_states[chat_id]
                logger.info(f"Downloading file from link: {url}")
                send_message(chat_id, "⬇️ در حال دانلود فایل...")
                try:
                    logger.info(f"Sending HTTP request to: {url}")
                    r = download_file_with_headers(url, timeout=60)
                    if r and r.status_code == 200:
                        content = r.content
                        size_mb = len(content)/(1024*1024)
                        fname = urlparse(url).path.split("/")[-1] or "downloaded_file"
                        logger.info(f"File downloaded successfully - Size: {size_mb:.2f}MB, Name: {fname}")
                        temp_file = fname
                        with open(temp_file, 'wb') as f:
                            f.write(content)
                        handle_rar_download(chat_id, temp_file, f"📁 {size_mb:.1f}MB - {fname}")
                    else:
                        status_code = r.status_code if r else "No Response"
                        logger.error(f"Download failed - Status: {status_code}")
                        send_message(chat_id, f"❌ خطا در دانلود - وضعیت: {status_code}\n\nممکن است لینک نامعتبر باشد یا سرور دسترسی را رد کرده است.")
                except Exception as e:
                    logger.error(f"Download link error: {e}", exc_info=True)
                    send_message(chat_id, f"❌ خطا در دانلود:\n{str(e)[:200]}")
                show_main_menu(chat_id)
            
            elif action == "waiting_for_website_url":
                url = text.strip()
                del user_states[chat_id]
                logger.info(f"Downloading website: {url}")
                send_message(chat_id, "⏳ در حال دانلود وب‌سایت (ممکن است چند دقیقه طول بکشد)...")
                result = download_website(url, chat_id)
                if isinstance(result, bytes):
                    logger.info(f"Website downloaded - Size: {len(result)/(1024*1024):.2f}MB")
                    website_name = sanitize_website_name(url)
                    filename = f"{website_name}.zip"
                    send_bytes_as_document(chat_id, result, filename, f"🌐 وب‌سایت دانلود شده: {url}")
                else:
                    logger.error(f"Website download error: {result}")
                    send_message(chat_id, f"❌ {result}")
                show_main_menu(chat_id)
            
            elif action == "waiting_for_extract_links":
                url = text.strip()
                del user_states[chat_id]
                logger.info(f"Extracting links from: {url}")
                send_message(chat_id, f"🔗 در حال استخراج لینک‌های {url}...")
                file_path, error = extract_links_from_webpage(url)
                if error:
                    logger.error(f"Link extraction error: {error}")
                    send_message(chat_id, error)
                else:
                    logger.info(f"Links extracted successfully: {file_path}")
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
                logger.info(f"YouTube URL received: {url}")
                btns = [
                    {"text": "🎬 دانلود ویدیو (حداکثر 720p)", "callback_data": f"youtube_video_{url}"},
                    {"text": "🎵 دانلود صدا (MP3)", "callback_data": f"youtube_audio_{url}"},
                    {"text": "🔙 برگشت به منو", "callback_data": "back_to_menu"}
                ]
                reply_markup = create_inline_keyboard(btns, columns=1)
                send_message(chat_id, "🎬 چه نوع دانلودی انجام شود؟", reply_markup)
            return
        
        if text == "/start":
            logger.info(f"Start command - Chat: {chat_id}")
            show_main_menu(chat_id)
        elif text == "/help":
            logger.info(f"Help command - Chat: {chat_id}")
            show_help(chat_id)
            show_main_menu(chat_id)
        else:
            logger.warning(f"Unknown message - Chat: {chat_id}, Text: {text}")
            send_message(chat_id, "❓ لطفاً از منوی اصلی استفاده کنید.")
            show_main_menu(chat_id)
    
    except Exception as e:
        logger.error(f"process_message error: {e}", exc_info=True)
        send_message(chat_id, f"❌ خطای غیرمنتظره: {str(e)[:150]}")
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
    MAX_RUNTIME = 5 * 3600 + 55 * 60  # ✅ GitHub Actions max 6 hours
    
    logger.info("=" * 60)
    logger.info("🤖 BOT STARTED")
    logger.info(f"Initial offset: {offset}")
    logger.info(f"Max runtime: {MAX_RUNTIME // 60} minutes")
    logger.info("=" * 60)
    
    update_count = 0
    error_count = 0
    
    while time.time() - start_time < MAX_RUNTIME:
        try:
            updates = get_updates(offset)
            
            if not updates:
                # No updates, wait a bit
                time.sleep(2)
                continue
            
            logger.info(f"📨 Received {len(updates)} updates")
            
            for upd in updates:
                update_count += 1
                update_id = upd.get("update_id")
                
                if update_id is not None and update_id >= offset:
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
                            except Exception as e:
                                logger.warning(f"answerCallbackQuery error: {e}")
                            
                            process_callback(chat_id, message_id, data)
                        
                        elif "message" in upd:
                            msg = upd["message"]
                            chat_id = msg["chat"]["id"]
                            text = msg.get("text", "")
                            process_message(chat_id, text)
                    
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error processing update: {e}", exc_info=True)
            
            # Save offset
            with open(offset_file, "w") as f:
                f.write(str(offset))
        
        except Exception as e:
            error_count += 1
            logger.error(f"Main loop error: {e}", exc_info=True)
            time.sleep(5)
    
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("🤖 BOT SHUTDOWN")
    logger.info(f"Runtime: {elapsed // 60:.0f} minutes")
    logger.info(f"Updates processed: {update_count}")
    logger.info(f"Errors: {error_count}")
    logger.info(f"Final offset: {offset}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
