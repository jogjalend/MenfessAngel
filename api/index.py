import os, io, json, requests
from flask import Flask, request
from PIL import Image
from datetime import datetime, timezone, timedelta
import time

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")

HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))

SESSION = requests.Session()
LOGO_CACHE = None
for p in ["logo.png","api/logo.png"]:
    if os.path.exists(p):
        try:
            LOGO_CACHE = Image.open(p).convert("RGBA")
            break
        except: pass

def load_quota():
    try:
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, "r") as f: return json.load(f)
    except: pass
    return {}
def save_quota(data):
    try:
        with open(QUOTA_FILE, "w") as f: json.dump(data, f)
    except: pass
def get_today_key(chat_id):
    return f"{chat_id}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(text):
    if not text: return HASHTAG.strip()
    if "#jogjalend" in text.lower(): return text
    return text.strip() + HASHTAG

def add_watermark_fast(b):
    if not LOGO_CACHE: return b
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        w,h = base.size
        lw = int(w*0.15)
        logo = LOGO_CACHE.copy()
        logo.thumbnail((lw,lw), Image.LANCZOS)
        alpha = logo.split()[-1]
        white = Image.new("RGBA", logo.size, (255,255,255,200))
        white.putalpha(alpha)
        base.paste(white, (w-logo.width-35, h-logo.height-55), white)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
        return out.getvalue()
    except:
        return b

def post_to_threads(text):
    if not THREADS_TOKEN or not THREADS_USER_ID:
        print("THREADS env not set")
        return None
    try:
        # 1. Create container
        url_create = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        r1 = SESSION.post(url_create, data={
            "media_type": "TEXT",
            "text": text,
            "access_token": THREADS_TOKEN
        }, timeout=15)
        print(f"Threads create: {r1.text}")
        if not r1.ok:
            return None
        creation_id = r1.json().get("id")
        if not creation_id:
            return None
        
        time.sleep(3)
        
        # 2. Publish
        url_pub = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
        r2 = SESSION.post(url_pub, data={
            "creation_id": creation_id,
            "access_token": THREADS_TOKEN
        }, timeout=15)
        print(f"Threads publish: {r2.text}")
        if r2.ok:
            return r2.json().get("id")
        return None
    except Exception as e:
        print(f"Threads error: {e}")
        return None

@app.route("/", methods=['GET'])
def home():
    return "Bot Active - FAST & THREADS", 200

@app.route("/", methods=['POST'])
@app.route("/api/index.py", methods=['POST'])
def handler():
    try:
        data = request.get_json()
        if not data: return "ok",200
        
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq["data"]
            chat_id = cq["message"]["chat"]["id"]
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
            if cb_data == "profil":
                quotas = load_quota()
                key = get_today_key(chat_id)
                q = quotas.get(key, {"text":0,"media":0})
                uname = cq["from"].get("username")
                tag = f"@{uname}" if uname else cq["from"].get("first_name")
                txt = f"""👤 Profile - {tag}

🆔 ID: {chat_id}
🏷️ Daily Quota (WIB)

📄 Text : {q['text']}/{LIMIT_TEXT}
📪 Media: {q['media']}/{LIMIT_MEDIA}

🔹 Telegram Channel: @menfessangel - ON
🔹 Threads: ON

Quota reset 00:00 WIB."""
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
            elif cb_data.startswith("delete|"):
                _, ch_msg_id = cb_data.split("|")
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":ch_msg_id})
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cq["message"]["chat"]["id"],"message_id":cq["message"]["message_id"],"text":"Post deleted! 🗑️"})
            return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        first = msg["from"].get("first_name") or "Angel"
        uname = msg["from"].get("username")
        tag = f"@{uname}" if uname else first

        if "text" in msg and msg["text"].startswith("/start"):
            caption = f"""Welcome, {tag}.

X @jogjalendpm is under maintenance, posts will now go to @menfessangel + Threads.

Limit: 5 texts & 5 media/day.

Please send your menfess now."""
            kb = {"inline_keyboard": [[{"text":"📢 Channel","url":"https://t.me/menfessangel"}],[{"text":"👤 Profile","callback_data":"profil"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":kb})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        
        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)

        # Cek quota
        if is_media and quotas[key]["media"] >= LIMIT_MEDIA:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"❌ Media quota habis hari ini!"})
            return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"❌ Text quota habis hari ini!"})
            return "ok",200

        # 1. POST KE TELEGRAM CHANNEL
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark_fast(fb)
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb})
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}"

        # 2. POST KE THREADS (text only, karena threads butuh URL publik buat image)
        threads_id = post_to_threads(caption)
        threads_url = f"https://www.threads.net/@menfessangel" if threads_id else ""

        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)

        q = quotas[key]
        pesan = f"""🏷️ Free daily quota
📄 Text : {q['text']}/{LIMIT_TEXT}
📪 Media : {q['media']}/{LIMIT_MEDIA}
Successfully sent, {tag}!

{'✅ Posted to Threads' if threads_id else '⚠️ Telegram OK, Threads failed (cek token)'}

Join Channel : @menfessangel"""

        buttons = [[{"text":"➡️ See Telegram","url":curl}]]
        if threads_id:
            # kalo mau link threads, gak bisa direct post id, pake profile dulu
            buttons.append([{"text":"🧵 See Threads","url":f"https://www.threads.net/@{CHANNEL_USERNAME}"}])
        buttons.append([{"text":"🗑️ Delete Post","callback_data":f"delete|{cmid}"}])

        kb = {"inline_keyboard": buttons}
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":pesan,"reply_markup":kb})

    except Exception as e:
        print(e)
    return "ok",200
