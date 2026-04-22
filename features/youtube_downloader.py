import yt_dlp
import os
from utils import ensure_ffmpeg, logger

ensure_ffmpeg()

def find_downloaded_file(target_title, extensions):
    """
    ✅ NEW: تابع بهتر برای پیدا کردن فایل دانلود شده
    حتی اگر کاراکترهای خاص در عنوان باشند
    """
    for file in os.listdir('.'):
        if file.endswith(extensions):
            try:
                # مقایسه بدون وابستگی کاملی به عنوان دقیق
                file_name_no_ext = os.path.splitext(file)[0]
                # بررسی شباهت اولیه (حداقل ۵ کاراکتر اول)
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
        ydl_opts = {
            'username': 'oauth2',
            'password': '',
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
            # ✅ استفاده از تابع بهتر
            downloaded_file = find_downloaded_file(video_title, ('.mp4', '.mkv', '.webm'))
            if downloaded_file:
                return downloaded_file, video_title
            else:
                return None, "❌ فایل پیدا نشد"
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg:
            return None, "❌ یوتیوب درخواست ورود دارد. لطفاً ابتدا با دستور زیر لاگین کنید: python -m yt_dlp --username oauth2 --password '' http[...]"
        return None, f"❌ خطا: {error_msg[:100]}"

def download_youtube_audio(url, chat_id, send_message_func):
    send_message_func(chat_id, "🎵 در حال دریافت اطلاعات...")
    try:
        ydl_opts = {
            'username': 'oauth2',
            'password': '',
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
            'verbose': True,
            'quiet': False,
            'no_warnings': False,
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
            # ✅ استفاده از تابع بهتر
            downloaded_file = find_downloaded_file(audio_title, ('.mp3',))
            if downloaded_file:
                return downloaded_file, audio_title
            else:
                return None, "❌ فایل صوتی پیدا نشد"
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg:
            return None, "❌ یوتیوب درخواست ورود دارد. لطفاً ابتدا با دستور زیر لاگین کنید: python -m yt_dlp --username oauth2 --password '' http[...]"
        return None, f"❌ خطا: {error_msg[:100]}"
