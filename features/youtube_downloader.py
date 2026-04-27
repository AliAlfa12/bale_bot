import yt_dlp
import os
from utils import ensure_ffmpeg, logger

ensure_ffmpeg()

# ✅ YouTube Cookies setup
COOKIES_FILE = "cookies.txt"

def check_cookies_file():
    """
    ✅ بررسی دقیق وجود فایل کوکی‌ها
    """
    logger.info(f"🔍 Checking for cookies file: {COOKIES_FILE}")
    
    if os.path.exists(COOKIES_FILE):
        file_size = os.path.getsize(COOKIES_FILE)
        logger.info(f"✅ Cookies file found: {COOKIES_FILE}")
        logger.info(f"   Size: {file_size} bytes")
        
        # بررسی محتوا
        try:
            with open(COOKIES_FILE, 'r') as f:
                first_line = f.readline().strip()
                logger.info(f"   Header: {first_line[:80]}")
        except:
            pass
        
        return True
    else:
        logger.warning(f"⚠️ Cookies file NOT found: {COOKIES_FILE}")
        logger.info(f"   Current directory: {os.getcwd()}")
        logger.info(f"   Files in directory: {os.listdir('.')[:10]}")
        logger.info(f"ℹ️ Will use OAuth2 instead")
        return False

def download_youtube_video(url, chat_id, send_message_func):
    """دانلود ویدیو یوتیوب"""
    send_message_func(chat_id, "🎬 در حال پردازش ویدیو...")
    
    try:
        logger.info("=" * 60)
        logger.info(f"🎬 YouTube Video Download Started")
        logger.info(f"URL: {url}")
        logger.info("=" * 60)
        
        # بررسی کوکی‌ها
        cookies_available = check_cookies_file()
        
        # ✅ بهبور شده: Format options
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best/worstvideo+worstaudio/worst',  # ✅ بسیار flexible
            'merge_output_format': 'mp4',
            'postprocessors': [],
            'outtmpl': '%(title)s [%(id)s].%(ext)s',  # ✅ شامل ID برای تمایز
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'retries': 5,  # ✅ بیشتر
            'retry_sleep': 2,
            'no_check_certificate': True,
            'prefer_insecure': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'ios', 'mweb'],  # ✅ کلاینت‌های بیشتر
                    'player_skip': ['js', 'configs'],
                }
            }
        }
        
        # ✅ اضافه کردن کوکی‌ها اگر موجود باشند
        if cookies_available:
            logger.info(f"📝 Using cookies from: {COOKIES_FILE}")
            ydl_opts['cookiefile'] = COOKIES_FILE
        else:
            logger.warning(f"⚠️ No cookies, using OAuth2")
        
        logger.info(f"📥 Extracting video info...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # اطلاعات ویدیو
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'video')
                video_duration = info.get('duration', 0)
                video_size_mb = info.get('filesize', 0) / (1024 * 1024) if info.get('filesize') else 'نامشخص'
                
                logger.info(f"✅ Video info extracted:")
                logger.info(f"   Title: {video_title}")
                logger.info(f"   Duration: {video_duration // 60}:{video_duration % 60:02d}")
                logger.info(f"   Size: {video_size_mb}")
                
                send_message_func(chat_id, f"📹 **{video_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n📦 حجم: {video_size_mb if isinstance(video_size_mb, str) else f'{video_size_mb:.1f}MB'}\n\n⬇️ دانلود...")
                
                # ✅ دانلود ویدیو
                logger.info(f"⬇️ Starting download...")
                ydl.download([url])
                
                # پیدا کردن فایل
                logger.info(f"🔍 Looking for downloaded file...")
                downloaded_file = None
                for file in os.listdir('.'):
                    if file.endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi')):
                        logger.debug(f"   Found video file: {file}")
                        if video_title in file or 'nGIg40xs9e4' in file:  # ✅ با ID هم چک کنید
                            downloaded_file = file
                            logger.info(f"   ✅ Matched: {file}")
                            break
                
                # اگر نشد، اخرین ویدیو فایل را بگیرید
                if not downloaded_file:
                    video_files = [f for f in os.listdir('.') if f.endswith(('.mp4', '.mkv', '.webm', '.mov', '.avi'))]
                    if video_files:
                        downloaded_file = sorted(video_files, key=lambda x: os.path.getmtime(x))[-1]
                        logger.info(f"   ✅ Using latest video file: {downloaded_file}")
                
                if downloaded_file:
                    logger.info(f"✅ Video file downloaded: {downloaded_file}")
                    file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
                    logger.info(f"📊 File size: {file_size_mb:.2f}MB")
                    logger.info("=" * 60)
                    return downloaded_file, video_title
                else:
                    logger.error(f"❌ Downloaded file not found")
                    logger.info(f"   Files in directory: {os.listdir('.')[:20]}")
                    logger.info("=" * 60)
                    return None, "❌ فایل دانلود شده پیدا نشد"
            
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                logger.error(f"❌ Download error: {error_msg[:300]}")
                logger.info("=" * 60)
                
                # ✅ بهتر شده: error messages
                if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
                    return None, "❌ یوتیوب درخواست ورود دارد.\n\nحل:\n• کوکی‌های شما اکسپایر شده‌اند\n• مجدد کوکی‌های جدید را ذخیره کنید"
                elif "Requested format is not available" in error_msg:
                    return None, "❌ فرمت درخواست شده موجود نیست"
                elif "age restricted" in error_msg.lower():
                    return None, "❌ این ویدیو برای افراد ۱۸+ است"
                elif "is no longer available" in error_msg or "has been removed" in error_msg:
                    return None, "❌ این ویدیو حذف شده یا در دسترس نیست"
                elif "HTTP Error" in error_msg:
                    return None, f"❌ خطای شبکه: {error_msg[:100]}"
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
                    'player_client': ['web', 'ios', 'mweb'],
                    'player_skip': ['js', 'configs'],
                }
            }
        }
        
        # ✅ اضافه کردن کوکی‌ها
        if cookies_available:
            logger.info(f"📝 Using cookies from: {COOKIES_FILE}")
            ydl_opts['cookiefile'] = COOKIES_FILE
        
        logger.info(f"📥 Extracting audio info...")
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
                        logger.debug(f"   Found audio file: {file}")
                        if audio_title in file or '[' in file:  # ✅ با ID هم چک کنید
                            downloaded_file = file
                            logger.info(f"   ✅ Matched: {file}")
                            break
                
                # اگر نشد، اخرین MP3 فایل را بگیرید
                if not downloaded_file:
                    mp3_files = [f for f in os.listdir('.') if f.endswith('.mp3')]
                    if mp3_files:
                        downloaded_file = sorted(mp3_files, key=lambda x: os.path.getmtime(x))[-1]
                        logger.info(f"   ✅ Using latest MP3 file: {downloaded_file}")
                
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
                
                if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
                    return None, "❌ یوتیوب درخواست ورود دارد.\n\nحل: کوکی‌های خود را دوباره ذخیره کنید"
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
