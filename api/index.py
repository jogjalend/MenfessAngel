import os
import time
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") # ex: -100xxxxxxxxxx
ADMIN_ID = os.getenv("ADMIN_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")

SESSION = requests.Session()
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg(method, data=None, files=None):
    try:
        return SESSION.post(f"{TG_API}/{method}", data=data, files=files, timeout=30).json()
    except Exception as e:
        print(e)
        return {}

def upload_catbox(file_bytes, filename="img.jpg"):
    try:
        r = SESSION.post("https://catbox.moe/user/api.php",
                         data={"reqtype": "fileupload"},
                         files={"fileToUpload": (filename, file_bytes)},
                         timeout=40)
        if r.ok and r.text.startswith("http"):
            return r.text.strip()
    except Exception as e:
        print("catbox err", e)
    return None

def post_to_threads(text, file_bytes=None):
    if not THREADS_TOKEN or not THREADS_USER_ID or not text:
        return
    try:
        text = text[:440]  # limit Threads
        if file_bytes:
            image_url = upload_catbox(file_bytes)
            if not image_url:
                print("Gagal upload catbox")
                return
            payload = {
                "media_type": "IMAGE",
                "image_url": image_url,
                "text": text,
                "access_token": THREADS_TOKEN
            }
        else:
            payload = {
                "media_type": "TEXT",
                "text": text,
                "access_token": THREADS_TOKEN
            }
        
        # Step 1: Create container
        r1 = SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data=payload, timeout=30)
        j1 = r1.json()
        print("Threads container:", j1)
        container_id = j1.get("id")
        if not container_id:
            return

        # Step 2: Wait & Publish
        time.sleep(7)
        r2 = SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish",
                          data={"creation_id": container_id, "access_token": THREADS_TOKEN}, timeout=30)
        print("Threads publish:", r2.json())
    except Exception as e:
        print("Threads error:", e)

@app.route("/", methods=["GET"])
def home():
    return "Menfess Angel + Threads Active!"

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data: return "ok", 200
    
    msg = data.get("message") or data.get("channel_post")
    if not msg: return "ok", 200
    
    chat_id = msg["chat"]["id"]
    text = msg.get("text") or msg.get("caption") or ""
    
    # /start
    if text.startswith("/start"):
        tg("sendMessage", {"chat_id": chat_id, "text": "Kirim menfess kamu di sini ya!\n\nTeks / foto / video bakal gue post ke @menfessangel (Telegram) + Threads @jogjalend\n\nKetik aja langsung tanpa /"})
        return "ok", 200

    # Ambil file kalau ada foto
    file_bytes = None
    if "photo" in msg:
        try:
            file_id = msg["photo"][-1]["file_id"]
            f = tg("getFile", {"file_id": file_id})
            fp = f["result"]["file_path"]
            fr = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=30)
            file_bytes = fr.content
        except: pass

    # Format menfess
    menfess_text = text.strip()
    if not menfess_text:
        menfess_text = "💌 Menfess"

    # 1. Kirim ke Telegram Channel
    try:
        if file_bytes:
            tg("sendPhoto", {"chat_id": CHANNEL_ID, "caption": menfess_text, "parse_mode": "HTML"}, files={"photo": file_bytes})
        else:
            tg("sendMessage", {"chat_id": CHANNEL_ID, "text": menfess_text, "parse_mode": "HTML"})
    except Exception as e:
        print("TG channel err", e)

    # 2. Kirim ke Threads
    post_to_threads(menfess_text, file_bytes)

    # 3. Balas ke pengirim
    tg("sendMessage", {"chat_id": chat_id, "text": "✅ Menfess terkirim ke Telegram & Threads! Makasih ya 💖"})
    return "ok", 200
