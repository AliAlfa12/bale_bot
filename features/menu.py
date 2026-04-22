from utils import send_message, create_inline_keyboard, remove_reply_keyboard

def show_main_menu(chat_id):
    buttons = [
        {"text": "🔍 جستجو در گیت‌هاب", "callback_data": "menu_search"},  # تغییر نام
        {"text": "📦 دانلود ریپو", "callback_data": "menu_download"},
        {"text": "🏷️ مشاهده ریلیزها", "callback_data": "menu_releases"},
        {"text": "💻 اجرای دستور لینوکسی", "callback_data": "menu_cli"},
        {"text": "🤖 سوال از هوش مصنوعی", "callback_data": "menu_ai"},
        {"text": "📥 دانلود فایل از لینک", "callback_data": "menu_download_link"},
        {"text": "🌐 دانلود کامل وب‌سایت", "callback_data": "menu_download_website"},
        {"text": "🔗 استخراج لینک‌های وب‌سایت", "callback_data": "menu_extract_links"},
        {"text": "🎬 دانلود از یوتیوب", "callback_data": "menu_youtube"},
        {"text": "📡 تست دسترسی به سایت‌ها", "callback_data": "menu_network_test"},
        {"text": "❓ راهنما", "callback_data": "menu_help"}
    ]
    reply_markup = create_inline_keyboard(buttons, columns=1)
    send_message(chat_id, "🤖 **ربات دانلودر پیشرفته**\nلطفاً یکی از گزینه‌ها را انتخاب کنید:", reply_markup)

def show_help(chat_id):
    text = (
        "📚 **راهنمای ربات**\n\n"
        "🔍 جستجو در گیت‌هاب (با نام ریپو یا نام کاربری)\n"
        "📦 دانلود ریپو (با فرمت owner/repo)\n"
        "🏷️ مشاهده ریلیزها و دانلود نسخه خاص\n"
        "💻 اجرای دستورات لینوکسی (ls, ping -c 4, curl, ...)\n"
        "🤖 سوال از هوش مصنوعی (Gemini)\n"
        "📥 دانلود فایل از لینک مستقیم\n"
        "🌐 دانلود کامل وب‌سایت (HTML + assets)\n"
        "🔗 استخراج تمام لینک‌های یک وب‌سایت\n"
        "🎬 دانلود ویدیو و صدا از یوتیوب\n"
        "📡 تست دسترسی به سایت‌های معروف\n\n"
        "⚠️ فایل‌های بزرگتر از 20MB به چند پارت RAR تقسیم می‌شوند\n"
        "⚠️ فایل‌های دانلود شده با رمز عبور (در صورت تنظیم) محافظت می‌شوند"
    )
    send_message(chat_id, text)

# توابع ask_for_* (بدون تغییر)
def ask_for_repo_name(chat_id):
    msg = "لطفاً عبارت جستجو را وارد کنید:\n- برای ریپوی دقیق: `owner/repo`\n- برای جستجوی کلی: یک کلمه (مثل `deltachat`)"
    send_message(chat_id, msg, reply_markup=remove_reply_keyboard())

def ask_for_command(chat_id):
    msg = "💻 لطفاً دستور لینوکسی خود را وارد کنید:\nمثال: `ls -la` یا `ping -c 4 google.com`\n⚠️ دستورات خطرناک مجاز نیستند."
    send_message(chat_id, msg, reply_markup=remove_reply_keyboard())

def ask_for_ai_question(chat_id):
    msg = "🤖 لطفاً سوال خود را از هوش مصنوعی بپرسید:"
    send_message(chat_id, msg, reply_markup=remove_reply_keyboard())

def ask_for_download_link(chat_id):
    msg = "📥 لطفاً لینک مستقیم فایل را وارد کنید:"
    send_message(chat_id, msg, reply_markup=remove_reply_keyboard())

def ask_for_website_url(chat_id):
    msg = "🌐 لطفاً آدرس وب‌سایت (مثال: https://example.com) را وارد کنید:"
    send_message(chat_id, msg, reply_markup=remove_reply_keyboard())

def ask_for_extract_links_url(chat_id):
    msg = "🔗 لطفاً آدرس وب‌سایت برای استخراج لینک‌ها را وارد کنید:"
    send_message(chat_id, msg, reply_markup=remove_reply_keyboard())

def ask_for_youtube_url(chat_id):
    msg = "🎬 لطفاً آدرس ویدیوی یوتیوب را وارد کنید:"
    send_message(chat_id, msg, reply_markup=remove_reply_keyboard())
