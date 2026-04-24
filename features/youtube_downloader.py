import yt_dlp
import os
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
        logger.info(f"ℹ️ Will use OAuth2 instead")
        return False

def download_youtube_video(url, chat_id, send_message_func):
    """دانلود ویدیو یوتیوب"""
    send_message_func(chat_id, "🎬 در حال پردازش ویدیو...")
    
    try:
        logger.info(f"🎬 Starting YouTube video download: {url}")
        
        # بررسی کوکی‌ها
        cookies_available = check_cookies_file()
        
        # ✅ بهبور شده: Format options
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # ✅ بهتر از قبل
            'merge_output_format': 'mp4',
            'postprocessors': [],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'retries': 3,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'socket_timeout': 30,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'ios'],  # ✅ کلاینت‌های مختلف
                }
            }
        }
        
        # ✅ اضافه کردن کوکی‌ها اگر موجود باشند
        if cookies_available:
            logger.info(f"📝 Using cookies from: {COOKIES_FILE}")
            ydl_opts['cookiefile'] = COOKIES_FILE
        
        logger.info(f"📥 Extracting video info from: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # اطلاعات ویدیو
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')
                video_duration = info.get('duration', 0)
                video_size_mb = info.get('filesize', 0) / (1024 * 1024) if info.get('filesize') else 'نامشخص'
                
                logger.info(f"✅ Video info extracted: {video_title}")
                send_message_func(chat_id, f"📹 **{video_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n📦 حجم: {video_size_mb if isinstance(video_size_mb, str) else f'{video_size_mb:.1f}MB'}\n\n⬇️ دانلود...")
                
                # ✅ دانلود ویدیو
                logger.info(f"⬇️ Starting download...")
                ydl.download([url])
                
                # پیدا کردن فایل
                logger.info(f"🔍 Looking for downloaded file...")
                downloaded_file = None
                for file in os.listdir('.'):
                    if file.endswith(('.mp4', '.mkv', '.webm', '.mov')):
                        file_name_no_ext = os.path.splitext(file)[0]
                        if len(video_title) > 10:
                            if file_name_no_ext[:10] == video_title[:10]:
                                downloaded_file = file
                                break
                        elif video_title in file_name_no_ext:
                            downloaded_file = file
                            break
                
                if downloaded_file:
                    logger.info(f"✅ Video file downloaded: {downloaded_file}")
                    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                    logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                    return downloaded_file, video_title
                else:
                    logger.error(f"❌ Downloaded file not found")
                    return None, "❌ فایل دانلود شده پیدا نشد"
            
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                logger.error(f"❌ Download error: {error_msg[:200]}")
                
                # ✅ بهتر شده: error messages
                if "Requested format is not available" in error_msg:
                    return None, "❌ فرمت درخواست شده موجود نیست.\n\nحل:\n• کوکی‌های شما ممکن است اکسپایر شده باشند\n• یا ویدیو فقط برای مناطق خاص موجود است"
                elif "Sign in to confirm" in error_msg:
                    return None, "❌ یوتیوب درخواست ورود دارد.\n\nحل: کوکی‌های خود را دوباره ذخیره کنید"
                elif "age restricted" in error_msg.lower():
                    return None, "❌ این ویدیو برای افراد ۱۸+ است"
                elif "is no longer available" in error_msg or "has been removed" in error_msg:
                    return None, "❌ این ویدیو حذف شده یا در دسترس نیست"
                elif "ERROR" in error_msg:
                    return None, f"❌ خطا: {error_msg[:150]}"
                else:
                    return None, f"❌ خطا: {error_msg[:150]}"
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        error_msg = str(e)
        
        if "No such file or directory" in error_msg:
            return None, "❌ ffmpeg نصب نشده است"
        elif "Sign in to confirm" in error_msg:
            return None, "❌ یوتیوب درخواست ورود دارد"
        else:
            return None, f"❌ خطا: {error_msg[:150]}"

def download_youtube_audio(url, chat_id, send_message_func):
    """دانلود صدای یوتیوب (MP3)"""
    send_message_func(chat_id, "🎵 در حال پردازش صدا...")
    
    try:
        logger.info(f"🎵 Starting YouTube audio download: {url}")
        
        # بررسی کوکی‌ها
        cookies_available = check_cookies_file()
        
        # ✅ تنظیمات صوتی
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'retries': 3,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'ios'],
                }
            }
        }
        
        # ✅ اضافه کردن کوکی‌ها
        if cookies_available:
            logger.info(f"📝 Using cookies from: {COOKIES_FILE}")
            ydl_opts['cookiefile'] = COOKIES_FILE
        
        logger.info(f"📥 Extracting audio info from: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # اطلاعات
                info = ydl.extract_info(url, download=False)
                audio_title = info.get('title', 'audio')
                video_duration = info.get('duration', 0)
                
                logger.info(f"✅ Audio info extracted: {audio_title}")
                send_message_func(chat_id, f"🎵 **{audio_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ استخراج صدا...")
                
                # ✅ دانلود
                logger.info(f"⬇️ Starting audio download and conversion...")
                ydl.download([url])
                
                # پیدا کردن فایل
                logger.info(f"🔍 Looking for downloaded audio file...")
                downloaded_file = None
                for file in os.listdir('.'):
                    if file.endswith('.mp3'):
                        file_name_no_ext = os.path.splitext(file)[0]
                        if len(audio_title) > 10:
                            if file_name_no_ext[:10] == audio_title[:10]:
                                downloaded_file = file
                                break
                        elif audio_title in file_name_no_ext:
                            downloaded_file = file
                            break
                
                if downloaded_file:
                    logger.info(f"✅ Audio file downloaded: {downloaded_file}")
                    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                    logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                    return downloaded_file, audio_title
                else:
                    logger.error(f"❌ Downloaded audio file not found")
                    return None, "❌ فایل صوتی دانلود شده پیدا نشد"
            
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                logger.error(f"❌ Download error: {error_msg[:200]}")
                
                if "Requested format is not available" in error_msg:
                    return None, "❌ فرمت درخواست شده موجود نیست.\n\nحل: کوکی‌های خود را دوباره ذخیره کنید"
                elif "Sign in to confirm" in error_msg:
                    return None, "❌ یوتیوب درخواست ورود دارد"
                elif "age restricted" in error_msg.lower():
                    return None, "❌ این ویدیو برای ۱۸+ است"
                elif "is no longer available" in error_msg or "has been removed" in error_msg:
                    return None, "❌ این ویدیو حذف شده یا در دسترس نیست"
                else:
                    return None, f"❌ خطا: {error_msg[:150]}"
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        error_msg = str(e)
        
        if "No such file or directory" in error_msg:
            return None, "❌ ffmpeg نصب نشده است"
        else:
            return None, f"❌ خطا: {error_msg[:150]}"
