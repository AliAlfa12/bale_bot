import yt_dlp
import os
import time
import subprocess
import json
from utils import ensure_ffmpeg, logger

ensure_ffmpeg()

COOKIES_FILE = "cookies.txt"

def check_cookies_file():
    """بررسی وجود فایل کوکی‌ها"""
    if os.path.exists(COOKIES_FILE):
        file_size = os.path.getsize(COOKIES_FILE)
        logger.info(f"✅ Cookies file found: {COOKIES_FILE} ({file_size} bytes)")
        return True
    else:
        logger.warning(f"⚠️ Cookies file not found")
        return False

def get_po_token():
    """✅ سعی برای دریافت PO Token"""
    logger.info("🔑 Trying to get PO Token...")
    try:
        # دستور برای دریافت PO Token
        result = subprocess.run(
            ['yt-dlp', '--extractor-args', 'youtube:po_token=', '--list-formats', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'],
            capture_output=True,
            timeout=10,
            text=True
        )
        logger.info("✅ PO Token extraction attempted")
        return True
    except Exception as e:
        logger.warning(f"⚠️ PO Token extraction failed: {e}")
        return False

def download_youtube_video(url, chat_id, send_message_func):
    """دانلود ویدیو یوتیوب - با تمام راه‌حل‌ها"""
    send_message_func(chat_id, "🎬 در حال پردازش ویدیو...")
    
    try:
        logger.info("=" * 70)
        logger.info(f"🎬 YouTube Video Download Started")
        logger.info(f"URL: {url}")
        logger.info("=" * 70)
        
        cookies_available = check_cookies_file()
        
        if not cookies_available:
            logger.error("❌ Cookies not found")
            return None, "❌ کوکی‌های یوتیوب لازم است.\n\nدستور ایجاد کوکی:\n```\npython -m yt_dlp --cookies-from-browser firefox https://www.youtube.com\n```"
        
        # ✅ تلاش 1: تنظیمات استاندارد
        logger.info("🔄 Attempt 1: Standard settings with cookies")
        result = try_download_video(url, chat_id, send_message_func, method='standard')
        if result[0]:
            return result
        
        # ✅ تلاش 2: بدون mweb client
        logger.info("🔄 Attempt 2: Without mweb client")
        result = try_download_video(url, chat_id, send_message_func, method='web_only')
        if result[0]:
            return result
        
        # ✅ تلاش 3: فقط audio
        logger.info("🔄 Attempt 3: Audio only (workaround)")
        result = try_download_video(url, chat_id, send_message_func, method='audio_only')
        if result[0]:
            return result
        
        # اگر هیچ کدام کار نکرد
        logger.error("❌ All download attempts failed")
        return None, "❌ متأسفانه این ویدیو با تنظیمات فعلی قابل دانلود نیست.\n\n**حل‌های ممکن:**\n1️⃣ کوکی‌های خود را refresh کنید\n2️⃣ از Firefox استفاده کنید\n3️⃣ بعداً دوباره تلاش کنید"
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return None, f"❌ خطا: {str(e)[:150]}"

def try_download_video(url, chat_id, send_message_func, method='standard'):
    """سعی برای دانلود با روش‌های مختلف"""
    try:
        logger.info(f"Using method: {method}")
        
        if method == 'standard':
            ydl_opts = {
                'format': 'b/best',
                'merge_output_format': 'mp4',
                'cookiefile': COOKIES_FILE,
                'outtmpl': '%(title)s [%(id)s].%(ext)s',
                'quiet': False,
                'socket_timeout': 30,
                'retries': 3,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web', 'mweb'],
                    }
                }
            }
        
        elif method == 'web_only':
            ydl_opts = {
                'format': 'b/best',
                'merge_output_format': 'mp4',
                'cookiefile': COOKIES_FILE,
                'outtmpl': '%(title)s [%(id)s].%(ext)s',
                'quiet': False,
                'socket_timeout': 30,
                'retries': 3,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],  # فقط web
                    }
                }
            }
        
        elif method == 'audio_only':
            # اگر ویدیو دانلود نشود، حداقل صدا بگیریم
            ydl_opts = {
                'format': 'best[ext=m4a]/best[ext=webm]/best[ext=mp3]/best',
                'cookiefile': COOKIES_FILE,
                'outtmpl': '%(title)s [%(id)s].%(ext)s',
                'quiet': False,
                'socket_timeout': 30,
                'retries': 3,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                    }
                }
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"📥 Extracting video info ({method})...")
            info = ydl.extract_info(url, download=False)
            
            video_title = info.get('title', 'video')
            video_duration = info.get('duration', 0)
            
            logger.info(f"✅ Got info: {video_title}")
            send_message_func(chat_id, f"📹 **{video_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ دانلود...")
            
            logger.info(f"⬇️ Downloading...")
            ydl.download([url])
            
            logger.info(f"🔍 Looking for file...")
            downloaded_file = find_downloaded_file(video_title, 'video')
            
            if downloaded_file:
                logger.info(f"✅ Downloaded: {downloaded_file}")
                file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                logger.info(f"📊 Size: {file_size_mb:.2f}MB")
                return (downloaded_file, video_title)
            else:
                logger.warning(f"⚠️ File not found ({method})")
                return (None, None)
    
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"⚠️ {method} failed: {error_msg[:100]}")
        return (None, None)

def download_youtube_audio(url, chat_id, send_message_func):
    """دانلود صدای یوتیوب (MP3)"""
    send_message_func(chat_id, "🎵 در حال پردازش صدا...")
    
    try:
        logger.info("=" * 70)
        logger.info(f"🎵 YouTube Audio Download Started")
        logger.info(f"URL: {url}")
        logger.info("=" * 70)
        
        cookies_available = check_cookies_file()
        
        if not cookies_available:
            return None, "❌ کوکی‌های یوتیوب لازم است"
        
        logger.info("📝 Using cookies...")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'cookiefile': COOKIES_FILE,
            'outtmpl': '%(title)s [%(id)s].%(ext)s',
            'quiet': False,
            'socket_timeout': 30,
            'retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"📥 Extracting audio info...")
            info = ydl.extract_info(url, download=False)
            audio_title = info.get('title', 'audio')
            video_duration = info.get('duration', 0)
            
            logger.info(f"✅ Got info: {audio_title}")
            send_message_func(chat_id, f"🎵 **{audio_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ استخراج صدا...")
            
            logger.info(f"⬇️ Downloading...")
            ydl.download([url])
            
            logger.info(f"🔍 Looking for file...")
            downloaded_file = find_downloaded_file(audio_title, 'audio')
            
            if downloaded_file:
                logger.info(f"✅ Downloaded: {downloaded_file}")
                file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                logger.info(f"📊 Size: {file_size_mb:.2f}MB")
                logger.info("=" * 70)
                return downloaded_file, audio_title
            else:
                logger.error(f"❌ Audio file not found")
                logger.info("=" * 70)
                return None, "❌ فایل صوتی دانلود شده پیدا نشد"
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"❌ Download error: {error_msg[:300]}")
        logger.info("=" * 70)
        
        if "Only images are available" in error_msg or "challenge solving failed" in error_msg.lower():
            return None, "❌ این ویدیو محافظت شده است.\n\nحل:\n• کوکی‌های خود را refresh کنید\n• بعداً دوباره تلاش کنید"
        else:
            return None, f"❌ خطا: {error_msg[:150]}"
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        logger.info("=" * 70)
        return None, f"❌ خطا: {str(e)[:150]}"

def find_downloaded_file(title, file_type):
    """کمک برای یافتن فایل دانلود شده"""
    if file_type == 'video':
        extensions = ('.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.m4a', '.webm')
    else:
        extensions = ('.mp3', '.m4a', '.webm', '.wav')
    
    found_files = []
    for file in os.listdir('.'):
        if file.endswith(extensions):
            found_files.append(file)
    
    if not found_files:
        return None
    
    if len(found_files) == 1:
        return found_files[0]
    
    # جدیدترین فایل
    latest = max(found_files, key=lambda x: os.path.getmtime(x))
    return latest
