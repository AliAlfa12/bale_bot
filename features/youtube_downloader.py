import yt_dlp
import os
import base64
import re
from utils import ensure_ffmpeg, logger

ensure_ffmpeg()

# متد جستجوی فایل (بدون تغییر، اما بازنویسی شد)
def find_downloaded_file(target_title, extensions):
    try:
        safe_title = re.sub(r'[\\/*?:"<>|]', "", target_title)[:50]
        for file in os.listdir('.'):
            if file.endswith(extensions):
                if safe_title in file or any(
                    ext in file for ext in extensions
                ):
                    return file
    except Exception as e:
        logger.warning(f"Error finding file: {e}")
    return None


def download_youtube_video(url, chat_id, send_message_func):
    send_message_func(chat_id, "🎬 در حال پردازش ویدیو...")

    # کوکی‌ها
    cookies_file = None
    youtube_cookies_b64 = os.environ.get("YOUTUBE_COOKIES")
    if youtube_cookies_b64:
        cookies_file = '/tmp/youtube_cookies.txt'
        with open(cookies_file, 'wb') as f:
            f.write(base64.b64decode(youtube_cookies_b64))
        logger.info("✅ YouTube cookies loaded.")
    else:
        logger.warning("⚠️ YOUTUBE_COOKIES not found.")

    # گزینه‌های گسترده برای پایداری بیشتر
    ydl_opts = {
        'cookiefile': cookies_file,
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'merge_output_format': 'mp4',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web'],  # استفاده از کلاینت‌های مختلف
                'skip': ['hls', 'dash', 'webpage']
            }
        },
        'no_check_certificate': True,
        'prefer_insecure': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')
            video_duration = info.get('duration', 0)
            
            # پیدا کردن کیفیت واقعی فایل دانلودی
            formats = info.get('formats', [])
            selected_format = next(
                (f for f in formats if f.get('height') and f.get('height') <= 720 and f.get('vcodec') != 'none'), 
                formats[0] if formats else None
            )
            final_height = selected_format.get('height', 'N/A') if selected_format else 'N/A'
            final_size_mb = selected_format.get('filesize', 0) if selected_format else 0
            size_mb = final_size_mb / (1024 * 1024)

            send_message_func(
                chat_id,
                f"📹 **{video_title}**\n"
                f"⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n"
                f"📊 کیفیت: {final_height}p\n"
                f"📦 حجم تقریبی: {size_mb:.1f}MB\n\n⬇️ شروع دانلود..."
            )
            
            # دانلود واقعی
            ydl.download([url])
            downloaded_file = find_downloaded_file(video_title, ('.mp4', '.mkv', '.webm'))
            
            if downloaded_file:
                return downloaded_file, video_title
            else:
                logger.error("Downloaded file not found after download.")
                return None, "❌ فایل پیدا نشد"

    except Exception as e:
        error_msg = str(e)
        logger.error(f"YouTube video download failed: {error_msg}")
        if "Sign in to confirm" in error_msg:
            return None, "❌ نیاز به احراز هویت. لطفاً کوکی YOUTUBE_COOKIES را به‌روز کنید."
        return None, f"❌ خطا: {error_msg[:100]}"
