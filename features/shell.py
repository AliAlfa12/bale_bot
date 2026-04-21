import subprocess
import shlex
from utils import send_message

ALLOWED_COMMANDS = [
    "ls", "pwd", "whoami", "uptime", "df", "free", "ps", "top", "cat", "echo",
    "python", "pip", "git", "grep", "find", "du", "uname", "date",
    "cal", "hostname", "id", "env", "which", "stat", "head", "tail", "sort", "uniq",
    "nslookup", "dig", "ping", "curl", "wget"
]

def is_command_safe(command):
    dangerous = ["rm -rf", "shutdown", "reboot", "mkfs", "dd if=", "> /dev/sda", ":(){ :|:& };:"]
    cmd_lower = command.lower()
    for d in dangerous:
        if d in cmd_lower:
            return False
    base = command.split()[0].lower()
    if base in ["ping", "curl", "wget"]:
        return True
    if base not in ALLOWED_COMMANDS:
        return False
    return True

def run_command(command, chat_id=None):
    if not is_command_safe(command):
        output = "❌ دستور غیرمجاز یا خطرناک است."
        if chat_id:
            send_message(chat_id, f"```\n{output}```")
        return output
    # اگر ping بدون -c بود اضافه کن
    if command.strip().startswith("ping") and "-c" not in command:
        command = command.replace("ping", "ping -c 4", 1)
    try:
        args = shlex.split(command)
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if not output.strip():
            output = "✅ دستور اجرا شد اما خروجی نداشت."
        if len(output) > 3000:
            output = output[:3000] + "\n... (خروجی بیش از حد طولانی)"
        if chat_id:
            send_message(chat_id, f"```\n{output}```")
        return output
    except subprocess.TimeoutExpired:
        output = "⏰ دستور بیش از 30 ثانیه طول کشید و متوقف شد."
        if chat_id:
            send_message(chat_id, f"```\n{output}```")
        return output
    except Exception as e:
        output = f"❌ خطا در اجرا: {str(e)}"
        if chat_id:
            send_message(chat_id, f"```\n{output}```")
        return output
