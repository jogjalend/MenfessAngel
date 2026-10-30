from flask import Flask, request
import os, requests

app = Flask(__name__)
BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
LOG_CHANNEL = os.getenv("LOG_CHANNEL") or ADMIN_ID

def get_welcome(name):
    return (
        f"👋🏻 Halo {name}! Selamat datang di dukungan @menfessangel!\n"
        f"Kebijakan Privasi\n\n"
        f"Aturan dukungan:\n"
        f"• Tolong sampaikan permintaan Anda langsung tanpa sapaan\n"
        f"• Jangan mengirim tautan tanpa izin\n"
        f"• Jangan mengirim media (misalnya foto dan video) tanpa izin\n"
        f"Melanggar aturan ini dapat mengakibatkan Anda diblokir oleh bot.\n\n"
        f"⬇️ Ketik permintaan Anda dan tim dukungan akan merespon secepatnya."
    )

def send_message(chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except:
        pass

def forward_to_admin(user_id, name, username, text):
    if not LOG_CHANNEL:
        return
    log_text = f"📩 Support baru\nDari: {name} (@{username}) ID: {user_id}\n\nPesan:\n{text}"
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": LOG_CHANNEL, "text": log_text},
            timeout=10
        )
    except:
        pass

@app.route("/", methods=["GET", "POST"])
@app.route("/api/support", methods=["GET", "POST"])
def main():
    if request.method == "GET":
        return "Support Bot @joglendsupportBot OK", 200

    data = request.get_json(force=True, silent=True) or {}
    if "message" not in data:
        return "ok", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")
    from_user = msg.get("from", {})
    name = from_user.get("first_name", "User")
    username = from_user.get("username", "-")

    if text.startswith("/start"):
        send_message(chat_id, get_welcome(name))
    elif len(text) >= 2:
        forward_to_admin(chat_id, name, username, text)
        send_message(chat_id, "✅ Pesan Anda telah diteruskan ke tim dukungan. Mohon tunggu respon.")

    return "ok", 200
