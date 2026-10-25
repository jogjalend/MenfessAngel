import os, io, json, requests
from flask import Flask, request
from PIL import Image
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"
ADMIN_ID = int(os.getenv("ADMIN_ID") or "8584319568")

HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))

# --- PRELOAD LOGO & SESSION (BIAR NGEBUT) ---
SESSION = requests.Session()
LOGO_CACHE = None
for p in ["logo.png","api/logo.png","api/logo.jpg"]:
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
    if not LOGO_CACHE:
        return b
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        w, h = base.size
        # Resize logo 14% dari lebar, gak pake loop pixel
        lw = int(w * 0.14)
        logo = LOGO_CACHE.copy()
        logo.thumbnail((lw, lw), Image.LANCZOS)
        # Bikin putih transparan super cepat
        white_logo = Image.new("RGBA", logo.size, (255,255,255,0))
        # paste logo sebagai mask biar putih
        r, g, b_, a = logo.split()
        white_layer = Image.new("RGBA", logo.size, (255,255,255,210))
        white_layer.putalpha(a)
        # tempel
        base.paste(white_layer, (w - logo.width - 25, h - logo.height - 25), white_layer)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=90, optimize=True)
        return out.getvalue()
    except:
        return b

@app.route("/", methods=['GET'])
def home():
    return "Bot Active - FAST MODE", 200

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
            msg_id = cq["message"]["message_id"]
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
            if cb_data == "profil":
                quotas = load_quota()
                q = quotas.get(get_today_key(chat_id), {"text":0,"media":0})
                tag = f"@{cq['from'].get('username')}" if cq['from'].get('username') else cq['from'].get('first_name')
                txt = f"👤 {tag}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
            elif cb_data.startswith("delete|"):
                _, ch_msg_id = cb_data.split("|")
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":ch_msg_id})
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Deleted!"})
            return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        tag = f"@{msg['from'].get('username')}" if msg['from'].get('username') else msg['from'].get('first_name') or "Angel"

        if "text" in msg and msg["text"].startswith("/start"):
            caption = f"Welcome, {tag}.\nLimit: 5 texts & 5 media/day.\nSend menfess now."
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

        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)

        q = quotas[key]
        pesan = f"Sent! {tag}\nText:{q['text']}/{LIMIT_TEXT} Media:{q['media']}/{LIMIT_MEDIA}"
        kb = {"inline_keyboard": [[{"text":"➡️ See Message","url":curl}], [{"text":"🗑️ Delete","callback_data":f"delete|{cmid}"}]]}
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":pesan,"reply_markup":kb})

    except Exception as e:
        print(e)
    return "ok",200
