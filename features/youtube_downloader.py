import yt_dlp
import os
import time
import subprocess
from utils import ensure_ffmpeg, logger

ensure_ffmpeg()

# ✅ YouTube Cookies setup
COOKIES_FILE = "cookies.txt"

def check_cookies_file():
    """بررسی وجود فایل کوکی‌ها"""
    if os.path.exists(COOKIES_FILE):
        file_size = os.path.getsize(COOKIES_FILE)
        logger.info(f"✅ Cookies file found: {COOKIES_FILE} ({file_size} bytes)")
        return True
    else:
        logger.warning(f"⚠️ Cookies file not found: {COOKIES_FILE}")
        return False

def setup_challenge_solver():
    """✅ نصب JavaScript challenge solver"""
    logger.info("🔧 Setting up challenge solver...")
    try:
        # Check if node-based solver exists
        result = subprocess.run(
            ['npm', 'list', '-g', 'yt-dlp-js-challenge-solver'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info("✅ Challenge solver already installed")
            return True
    except:
        pass
    
    logger.info("ℹ️ Challenge solver not found (optional)")
    return False

def download_youtube_video(url, chat_id, send_message_func):
    """دانلود ویدیو یوتیوب - حل شده"""
    send_message_func(chat_id, "🎬 در حال پردازش ویدیو...")
    
    try:
        logger.info("=" * 60)
        logger.info(f"🎬 YouTube Video Download Started")
        logger.info(f"URL: {url}")
        logger.info("=" * 60)
        
        # ✅ فقط با کوکی‌ها (OAuth2 کار نمی‌کند برای این ویدیو)
        cookies_available = check_cookies_file()
        
        if not cookies_available:
            logger.error("❌ Cookies not found and OAuth2 won't work")
            return None, "❌ کوکی‌های یوتیوب لازم است.\n\nدستور ایجاد کوکی:\n```\npython -m yt_dlp --cookies-from-browser firefox --cookies cookies.txt https://www.youtube.com\n```"
        
        logger.info("📝 Using cookies...")
        
        # ✅ تنظیمات بهبور شده برای challenge solving
        ydl_opts = {
            'format': 'b',  # ✅ بهترین فرمت موجود
            'merge_output_format': 'mp4',
            'cookiefile': COOKIES_FILE,
            'outtmpl': '%(title)s [%(id)s].%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'retries': 5,
            'retry_sleep': 2,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'mweb'],
                    'player_skip': [],  # ✅ Don't skip anything
                }
            },
            # ✅ Challenge solving options
            'youtube_include_dash_manifest': True,
            'youtube_include_hls_manifest': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # اطلاعات ویدیو
            logger.info(f"📥 Extracting video info...")
            info = ydl.extract_info(url, download=False)
            
            video_title = info.get('title', 'video')
            video_duration = info.get('duration', 0)
            video_size_mb = info.get('filesize', 0) / (1024 * 1024) if info.get('filesize') else 'نامشخص'
            
            logger.info(f"✅ Video info extracted: {video_title}")
            logger.info(f"   Formats available: {len(info.get('formats', []))}")
            
            # نمایش فرمت‌های موجود
            if info.get('formats'):
                logger.info(f"   Available formats:")
                for fmt in info['formats'][:3]:
                    logger.info(f"     - {fmt.get('format_id')}: {fmt.get('format')}")
            
            send_message_func(chat_id, f"📹 **{video_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n📦 حجم: {video_size_mb if isinstance(video_size_mb, str) else f'{video_size_mb:.1f}MB'}\n\n⬇️ دانلود...")
            
            # دانلود وی��یو
            logger.info(f"⬇️ Starting download...")
            ydl.download([url])
            
            # پیدا کردن فایل
            logger.info(f"🔍 Looking for downloaded file...")
            downloaded_file = find_downloaded_file(video_title, 'video')
            
            if downloaded_file:
                logger.info(f"✅ Video file downloaded: {downloaded_file}")
                file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                logger.info("=" * 60)
                return downloaded_file, video_title
            else:
                logger.error(f"❌ Downloaded file not found")
                logger.info("=" * 60)
                return None, "❌ فایل دانلود شده پیدا نشد"
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"❌ Download error: {error_msg[:300]}")
        logger.info("=" * 60)
        
        if "challenge solving failed" in error_msg.lower():
            return None, "❌ یوتیوب درخواست تایید دارد.\n\nحل:\n• کوکی‌های جدید را export کنید\n• اطمینان داشته باشید Firefox/Chrome را استفاده می‌کنید"
        elif "Requested format is not available" in error_msg or "Only images are available" in error_msg:
            return None, "❌ این ویدیو فقط صورت‌بندی محدودی دارد.\n\nحل: بعداً دوباره تلاش کنید"
        elif "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            return None, "❌ یوتیوب درخواست ورود دارد.\n\nحل: کوکی‌های خود را دوباره export کنید"
        elif "age restricted" in error_msg.lower():
            return None, "❌ این ویدیو برای افراد ۱۸+ است"
        elif "is no longer available" in error_msg or "has been removed" in error_msg:
            return None, "❌ این ویدیو حذف شده یا در دسترس نیست"
        else:
            return None, f"❌ خطا: {error_msg[:150]}"
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        logger.info("=" * 60)
        error_msg = str(e)
        
        if "No such file or directory" in error_msg and "ffmpeg" in error_msg:
            return None, "❌ ffmpeg نصب نشده است"
        else:
            return None, f"❌ خطا: {error_msg[:150]}"

def download_youtube_audio(url, chat_id, send_message_func):
    """دانلود صدای یوتیوب (MP3)"""
    send_message_func(chat_id, "🎵 در حال پردازش صدا...")
    
    try:
        logger.info("=" * 60)
        logger.info(f"🎵 YouTube Audio Download Started")
        logger.info(f"URL: {url}")
        logger.info("=" * 60)
        
        cookies_available = check_cookies_file()
        
        if not cookies_available:
            logger.error("❌ Cookies not found")
            return None, "❌ کوکی‌های یوتیوب لازم است"
        
        logger.info("📝 Using cookies...")
        
        ydl_opts = {
            'format': 'b',  # ✅ بهترین صوت موجود
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'cookiefile': COOKIES_FILE,
            'outtmpl': '%(title)s [%(id)s].%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'retries': 5,
            'retry_sleep': 2,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'mweb'],
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"📥 Extracting audio info...")
            info = ydl.extract_info(url, download=False)
            audio_title = info.get('title', 'audio')
            video_duration = info.get('duration', 0)
            
            logger.info(f"✅ Audio info extracted: {audio_title}")
            send_message_func(chat_id, f"🎵 **{audio_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ استخراج صدا...")
            
            logger.info(f"⬇️ Starting audio download...")
            ydl.download([url])
            
            logger.info(f"🔍 Looking for downloaded audio file...")
            downloaded_file = find_downloaded_file(audio_title, 'audio')
            
            if downloaded_file:
                logger.info(f"✅ Audio file downloaded: {downloaded_file}")
                file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                logger.info("=" * 60)
                return downloaded_file, audio_title
            else:
                logger.error(f"❌ Downloaded audio file not found")
                logger.info("=" * 60)
                return None, "❌ فایل صوتی دانلود شده پیدا نشد"
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"❌ Download error: {error_msg[:300]}")
        logger.info("=" * 60)
        
        if "challenge solving failed" in error_msg.lower() or "Only images" in error_msg:
            return None, "❌ این ویدیو نیاز به تایید دارد یا فرمت محدود است"
        else:
            return None, f"❌ خطا: {error_msg[:150]}"
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        logger.info("=" * 60)
        return None, f"❌ خطا: {str(e)[:150]}"

def find_downloaded_file(title, file_type):
    """کمک برای یافتن فایل دانلود شده"""
    logger.debug(f"Looking for {file_type} file: {title}")
    
    if file_type == 'video':
        extensions = ('.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv')
    else:  # audio
        extensions = ('.mp3',)
    
    found_files = []
    for file in os.listdir('.'):
        if file.endswith(extensions):
            logger.debug(f"   Found: {file}")
            found_files.append(file)
    
    if not found_files:
        logger.warning(f"No {file_type} files found")
        return None
    
    # اگر تنها یک فایل است
    if len(found_files) == 1:
        return found_files[0]
    
    # جدیدترین فایل
    latest_file = max(found_files, key=lambda x: os.path.getmtime(x))
    return latest_file
