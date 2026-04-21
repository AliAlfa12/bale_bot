import os
import requests
from utils import send_message

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def ask_gemini(question, chat_id=None):
    if not GEMINI_API_KEY:
        answer = "❌ کلید API هوش مصنوعی تنظیم نشده است."
        if chat_id:
            send_message(chat_id, answer)
        return answer
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": question}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800}
    }
    try:
        r = requests.post(url, headers=headers, json=data, timeout=30)
        if r.status_code == 200:
            result = r.json()
            try:
                answer = result['candidates'][0]['content']['parts'][0]['text']
                if chat_id:
                    send_message(chat_id, answer)
                return answer
            except:
                answer = "❌ پاسخ دریافت نشد."
                if chat_id:
                    send_message(chat_id, answer)
                return answer
        else:
            answer = f"❌ خطا در ارتباط با هوش مصنوعی: {r.status_code}"
            if chat_id:
                send_message(chat_id, answer)
            return answer
    except Exception as e:
        answer = f"❌ خطا: {str(e)[:100]}"
        if chat_id:
            send_message(chat_id, answer)
        return answer
