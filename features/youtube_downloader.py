import yt_dlp
import os
import base64
from utils import ensure_ffmpeg, logger

ensure_ffmpeg()

def find_downloaded_file(target_title, extensions):
    """
    پیدا کردن فایل دانلود شده با مقایسه تطبیقی
    """
    for file in os.listdir('.'):
        if file.endswith(extensions):
            try:
                file_name_no_ext = os.path.splitext(file)[0]
                if len(target_title) > 5:
                    if file_name_no_ext[:5] == target_title[:5]:
                        return file
                elif target_title in file_name_no_ext:
                    return file
            except Exception as e:
                logger.warning(f"Error comparing {file}: {e}")
    return None

def download_youtube_video(url, chat_id, send_message_func):
    send_message_func(chat_id, "🎬 در حال دریافت اطلاعات ویدیو...")
    try:
        # خواندن کوکی از متغیر محیطی و ذخیره در فایل موقت
        cookies_file = None
        youtube_cookies_b64 = os.environ.get('YOUTUBE_COOKIES')
        if youtube_cookies_b64:
            cookies_file = '/tmp/youtube_cookies.txt'
            with open(cookies_file, 'wb') as f:
                f.write(base64.b64decode(youtube_cookies_b64))
            logger.info("✅ YouTube cookies loaded from environment.")
        else:
            logger.warning("⚠️ YOUTUBE_COOKIES secret not found. Download may fail for restricted videos.")

        ydl_opts = {
            'cookiefile': cookies_file,  # استفاده از فایل کوکی
            'format': 'best[height<=720]',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'skip': ['webpage']}},
            'no_check_certificate': True,
            'prefer_insecure': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')
            video_duration = info.get('duration', 0)
            video_size_mb = info.get('filesize', 0) / (1024 * 1024)
            send_message_func(chat_id, f"📹 **{video_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n📦 حجم: {video_size_mb:.1f}MB\n\n⬇️ دانلود...")
            ydl.download([url])
            downloaded_file = find_downloaded_file(video_title, ('.mp4', '.mkv', '.webm'))
            if downloaded_file:
                return downloaded_file, video_title
            else:
                return None, "❌ فایل پیدا نشد"
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "cookies" in error_msg.lower():
            return None, "❌ خطا در احراز هویت. لطفاً کوکی یوتیوب را در Secrets تنظیم کنید."
        return None, f"❌ خطا: {error_msg[:100]}"

def download_youtube_audio(url, chat_id, send_message_func):
    send_message_func(chat_id, "🎵 در حال دریافت اطلاعات...")
    try:
        # خواندن کوکی از متغیر محیطی
        cookies_file = None
        youtube_cookies_b64 = os.environ.get('YOUTUBE_COOKIES')
        if youtube_cookies_b64:
            cookies_file = '/tmp/youtube_cookies.txt'
            with open(cookies_file, 'wb') as f:
                f.write(base64.b64decode(youtube_cookies_b64))
            logger.info("✅ YouTube cookies loaded for audio.")

        ydl_opts = {
            'cookiefile': cookies_file,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['ios', 'web']}},
            'no_check_certificate': True,
            'prefer_insecure': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_title = info.get('title', 'audio')
            video_duration = info.get('duration', 0)
            send_message_func(chat_id, f"🎵 **{audio_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ استخراج صدا...")
            ydl.download([url])
            downloaded_file = find_downloaded_file(audio_title, ('.mp3',))
            if downloaded_file:
                return downloaded_file, audio_title
            else:
                return None, "❌ فایل صوتی پیدا نشد"
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "cookies" in error_msg.lower():
            return None, "❌ خطا در احراز هویت. لطفاً کوکی یوتیوب را در Secrets تنظیم کنید."
        return None, f"❌ خطا: {error_msg[:100]}"
