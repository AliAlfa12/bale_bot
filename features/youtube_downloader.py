import yt_dlp
import os
import time
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
    """دانلود ویدیو یوتیوب - بهبور شده"""
    send_message_func(chat_id, "🎬 در حال پردازش ویدیو...")
    
    try:
        logger.info("=" * 60)
        logger.info(f"🎬 YouTube Video Download Started")
        logger.info(f"URL: {url}")
        logger.info("=" * 60)
        
        # ✅ روش 1: بدون کوکی (OAuth2) - سعی کنید
        logger.info("🔄 Attempt 1: Using OAuth2 (no cookies)")
        
        ydl_opts_oauth = {
            'format': 'bestvideo+bestaudio/best/worstvideo+worstaudio/worst',
            'merge_output_format': 'mp4',
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
                    'player_client': ['web'],  # ✅ فقط web
                }
            },
            'socket_timeout': 30,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts_oauth) as ydl:
                # اطلاعات ویدیو
                logger.info(f"📥 Extracting video info (OAuth2)...")
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')
                video_duration = info.get('duration', 0)
                video_size_mb = info.get('filesize', 0) / (1024 * 1024) if info.get('filesize') else 'نامشخص'
                
                logger.info(f"✅ Video info extracted: {video_title}")
                send_message_func(chat_id, f"📹 **{video_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n📦 حجم: {video_size_mb if isinstance(video_size_mb, str) else f'{video_size_mb:.1f}MB'}\n\n⬇️ دانلود...")
                
                # دانلود ویدیو
                logger.info(f"⬇️ Starting download (OAuth2)...")
                ydl.download([url])
                
                # پیدا کردن فایل
                logger.info(f"🔍 Looking for downloaded file...")
                downloaded_file = find_downloaded_file(video_title, video_duration, 'video')
                
                if downloaded_file:
                    logger.info(f"✅ Video file downloaded: {downloaded_file}")
                    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                    logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                    logger.info("=" * 60)
                    return downloaded_file, video_title
                else:
                    logger.warning(f"⚠️ File not found with OAuth2, trying with cookies...")
        
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.warning(f"⚠️ OAuth2 failed: {error_msg[:100]}")
            logger.info("🔄 Attempt 2: Using cookies...")
        
        # ✅ روش 2: استفاده از کوکی‌ها - اگر OAuth2 نشد
        cookies_available = check_cookies_file()
        
        if cookies_available:
            logger.info("📝 Using cookies for retry...")
            
            ydl_opts_cookies = {
                'format': 'bestvideo+bestaudio/best/worstvideo+worstaudio/worst',
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
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                'extractor_args': {
                    'youtube': {
                        'player_client': ['web'],
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_cookies) as ydl:
                # اطلاعات ویدیو
                logger.info(f"📥 Extracting video info (with cookies)...")
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')
                video_duration = info.get('duration', 0)
                video_size_mb = info.get('filesize', 0) / (1024 * 1024) if info.get('filesize') else 'نامشخص'
                
                logger.info(f"✅ Video info extracted: {video_title}")
                send_message_func(chat_id, f"📹 **{video_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n📦 حجم: {video_size_mb if isinstance(video_size_mb, str) else f'{video_size_mb:.1f}MB'}\n\n⬇️ دانلود...")
                
                # دانلود ویدیو
                logger.info(f"⬇️ Starting download (with cookies)...")
                ydl.download([url])
                
                # پیدا کردن فایل
                logger.info(f"🔍 Looking for downloaded file...")
                downloaded_file = find_downloaded_file(video_title, video_duration, 'video')
                
                if downloaded_file:
                    logger.info(f"✅ Video file downloaded: {downloaded_file}")
                    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                    logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                    logger.info("=" * 60)
                    return downloaded_file, video_title
        
        # اگر هیچ روش کار نکرد
        logger.error(f"❌ Downloaded file not found")
        logger.info("=" * 60)
        return None, "❌ فایل دانلود شده پیدا نشد"
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"❌ Download error: {error_msg[:300]}")
        logger.info("=" * 60)
        
        # بهتر شده: error messages
        if "The page needs to be reloaded" in error_msg:
            return None, "❌ کوکی‌های شما نیاز به refresh دارند.\n\nحل:\n• کوکی‌های خود را دوباره export کنید:\npython -m yt_dlp --cookies-from-browser firefox --cookies cookies.txt https://www.youtube.com"
        elif "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            return None, "❌ یوتیوب درخواست ورود دارد.\n\nحل: کوکی‌های خود را دوباره ذخیره کنید"
        elif "Requested format is not available" in error_msg:
            return None, "❌ فرمت درخواست شده موجود نیست"
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
        
        # ✅ روش 1: بدون کوکی
        logger.info("🔄 Attempt 1: Using OAuth2 (no cookies)")
        
        ydl_opts_oauth = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
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
                    'player_client': ['web'],
                }
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts_oauth) as ydl:
                logger.info(f"📥 Extracting audio info (OAuth2)...")
                info = ydl.extract_info(url, download=False)
                audio_title = info.get('title', 'audio')
                video_duration = info.get('duration', 0)
                
                logger.info(f"✅ Audio info extracted: {audio_title}")
                send_message_func(chat_id, f"🎵 **{audio_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ استخراج صدا...")
                
                logger.info(f"⬇️ Starting audio download (OAuth2)...")
                ydl.download([url])
                
                logger.info(f"🔍 Looking for downloaded audio file...")
                downloaded_file = find_downloaded_file(audio_title, video_duration, 'audio')
                
                if downloaded_file:
                    logger.info(f"✅ Audio file downloaded: {downloaded_file}")
                    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                    logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                    logger.info("=" * 60)
                    return downloaded_file, audio_title
                else:
                    logger.warning(f"⚠️ File not found with OAuth2, trying with cookies...")
        
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.warning(f"⚠️ OAuth2 failed: {error_msg[:100]}")
            logger.info("🔄 Attempt 2: Using cookies...")
        
        # ✅ روش 2: استفاده از کوکی‌ها
        cookies_available = check_cookies_file()
        
        if cookies_available:
            logger.info("📝 Using cookies for retry...")
            
            ydl_opts_cookies = {
                'format': 'bestaudio/best',
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
                        'player_client': ['web'],
                    }
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_cookies) as ydl:
                logger.info(f"📥 Extracting audio info (with cookies)...")
                info = ydl.extract_info(url, download=False)
                audio_title = info.get('title', 'audio')
                video_duration = info.get('duration', 0)
                
                logger.info(f"✅ Audio info extracted: {audio_title}")
                send_message_func(chat_id, f"🎵 **{audio_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ استخراج صدا...")
                
                logger.info(f"⬇️ Starting audio download (with cookies)...")
                ydl.download([url])
                
                logger.info(f"🔍 Looking for downloaded audio file...")
                downloaded_file = find_downloaded_file(audio_title, video_duration, 'audio')
                
                if downloaded_file:
                    logger.info(f"✅ Audio file downloaded: {downloaded_file}")
                    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                    logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                    logger.info("=" * 60)
                    return downloaded_file, audio_title
        
        logger.error(f"❌ Downloaded audio file not found")
        logger.info("=" * 60)
        return None, "❌ فایل صوتی دانلود شده پیدا نشد"
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"❌ Download error: {error_msg[:300]}")
        logger.info("=" * 60)
        
        if "The page needs to be reloaded" in error_msg:
            return None, "❌ کوکی‌های شما نیاز به refresh دارند"
        elif "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            return None, "❌ یوتیوب درخواست ورود دارد"
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

def find_downloaded_file(title, duration, file_type):
    """✅ NEW: کمک برای یافتن فایل دانلود شده"""
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
    
    # اگر تنها یک فایل است، آن را بگیرید
    if len(found_files) == 1:
        logger.info(f"Found single file: {found_files[0]}")
        return found_files[0]
    
    # اگر چندتا است، جدیدترین را بگیرید
    latest_file = max(found_files, key=lambda x: os.path.getmtime(x))
    logger.info(f"Found multiple files, using latest: {latest_file}")
    return latest_file
