"""
✅ مدیریت تنظیمات کاربر
- نوع دانلود (مستقیم یا Google Drive)
- ذخیره تنظیمات در فایل JSON
"""

import os
import json
import requests
from utils import logger

SETTINGS_FILE = "user_settings.json"

# ✅ نوع‌های دانلود
DOWNLOAD_TYPES = {
    'direct': 'دانلود مستقیم (پارت‌بندی)',
    'google_drive': 'آپلود به Google Drive'
}

def load_settings():
    """بارگذاری تمام تنظیمات کاربران"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    return {}

def save_settings(settings):
    """ذخیره تمام تنظیمات کاربران"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        logger.info(f"Settings saved")
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

def get_user_settings(chat_id):
    """دریافت تنظیمات کاربر"""
    settings = load_settings()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in settings:
        # تنظیمات پیش‌فرض
        settings[chat_id_str] = {
            'download_type': 'direct',  # پیش‌فرض: مستقیم
            'google_drive_folder_id': None,
            'created_at': str(__import__('datetime').datetime.now())
        }
        save_settings(settings)
    
    return settings[chat_id_str]

def set_download_type(chat_id, download_type):
    """تنظیم نوع دانلود کاربر"""
    if download_type not in DOWNLOAD_TYPES:
        return False
    
    settings = load_settings()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in settings:
        settings[chat_id_str] = {
            'download_type': 'direct',
            'google_drive_folder_id': None,
            'created_at': str(__import__('datetime').datetime.now())
        }
    
    settings[chat_id_str]['download_type'] = download_type
    save_settings(settings)
    logger.info(f"User {chat_id} set download type to: {download_type}")
    return True

def set_google_drive_folder(chat_id, folder_id):
    """تنظیم folder ID گوگل درایو"""
    settings = load_settings()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in settings:
        settings[chat_id_str] = {
            'download_type': 'direct',
            'google_drive_folder_id': None,
            'created_at': str(__import__('datetime').datetime.now())
        }
    
    settings[chat_id_str]['google_drive_folder_id'] = folder_id
    save_settings(settings)
    logger.info(f"User {chat_id} set Google Drive folder: {folder_id}")
    return True

def upload_to_google_drive(file_path, folder_id, deploy_url):
    """
    ✅ آپلود فایل به Google Drive
    
    Args:
        file_path: مسیر فایل محلی
        folder_id: شناسه پوشه درایو
        deploy_url: آدرس Google Apps Script Deploy
    """
    try:
        logger.info(f"📤 Uploading to Google Drive: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False, "فایل پیدا نشد"
        
        # خواندن فایل
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # تبدیل به Base64
        import base64
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        
        # تعیین MIME type
        file_ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.rar': 'application/x-rar-compressed',
            '.zip': 'application/zip',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.pdf': 'application/pdf',
        }
        mime_type = mime_types.get(file_ext, 'application/octet-stream')
        
        # تهیه داده‌ها برای ارسال
        payload = {
            'fileData': file_base64,
            'fileName': os.path.basename(file_path),
            'mimeType': mime_type,
            'folderId': folder_id
        }
        
        # ارسال درخواست به Google Apps Script
        logger.info(f"📡 Sending to: {deploy_url}")
        response = requests.post(deploy_url, json=payload, timeout=300)
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                logger.info(f"✅ Uploaded successfully: {result.get('fileId')}")
                file_url = result.get('fileUrl')
                return True, f"✅ آپلود موفق\n[دریافت فایل]({file_url})"
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.error(f"Upload failed: {error_msg}")
                return False, f"❌ خطا: {error_msg}"
        else:
            logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
            return False, f"❌ خطای سرور ({response.status_code})"
    
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        return False, f"❌ خطا: {str(e)[:150]}"
