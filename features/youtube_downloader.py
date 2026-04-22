import yt_dlp
import os
import time
import subprocess
from utils import ensure_ffmpeg, logger

ensure_ffmpeg()

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
            downloaded_file = None
            for file in os.listdir('.'):
                if file.endswith(('.mp4', '.mkv', '.webm')):
                    if video_title in file or file.startswith(video_title):
                        downloaded_file = file
                        break
            if downloaded_file:
                return downloaded_file, video_title
            else:
                return None, "❌ فایل پیدا نشد"
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg:
            return None, "❌ یوتیوب درخواست ورود دارد. لطفاً ابتدا با دستور زیر لاگین کنید: python -m yt_dlp --username oauth2 --password '' https://www.youtube.com/watch?v=test"
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
                'verbose': True,     # برای دیدن لاگ‌های دقیق و عیب‌یابی
            'quiet': False,      # خاموش نبودن خروجی
            'no_warnings': False, # نشان دادن تمام هشدارها
            'extractor_args': {'youtube': {'player_client': ['ios', 'web']}}, # استفاده از کلاینت‌های مختلف برای دور زدن محدودی
            'no_check_certificate': True,
            'prefer_insecure': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_title = info.get('title', 'audio')
            video_duration = info.get('duration', 0)
            send_message_func(chat_id, f"🎵 **{audio_title}**\n⏱️ مدت: {video_duration // 60}:{video_duration % 60:02d}\n\n⬇️ استخراج صدا...")
            ydl.download([url])
            downloaded_file = None
            for file in os.listdir('.'):
                if file.endswith('.mp3'):
                    if audio_title in file or file.startswith(audio_title):
                        downloaded_file = file
                        break
            if downloaded_file:
                return downloaded_file, audio_title
            else:
                return None, "❌ فایل صوتی پیدا نشد"
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg:
            return None, "❌ یوتیوب درخواست ورود دارد. لطفاً ابتدا با دستور زیر لاگین کنید: python -m yt_dlp --username oauth2 --password '' https://www.youtube.com/watch?v=test"
        return None, f"❌ خطا: {error_msg[:100]}"
