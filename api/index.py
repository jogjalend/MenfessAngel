import os, io, json, requests, traceback
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
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    return f"{chat_id}_{today}"
def add_hashtag(text):
    if not text: return HASHTAG.strip()
    if "#jogjalend" in text.lower(): return text
    return text.strip() + HASHTAG
def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png","api/logo.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w,h = base.size
                size = int(w*0.15)
                logo.thumbnail((size,size), Image.LANCZOS)
                datas = []
                for r,g,bl,a in logo.getdata():
                    if a > 20: datas.append((255,255,255,230))
                    else: datas.append((255,255,255,0))
                logo.putdata(datas)
                base.paste(logo, (w - logo.width - 35, h - logo.height - 55), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=95)
                return out.getvalue()
    except: pass
    return b

@app.route("/", methods=['GET'])
def home():
    return "Bot Active - X OFF - TG ON", 200

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
            
            if cb_data == "profil":
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
                quotas = load_quota()
                key = get_today_key(chat_id)
                q = quotas.get(key, {"text":0,"media":0})
                first = cq["from"].get("first_name") or "Angel"
                uname = cq["from"].get("username")
                tag = f"@{uname}" if uname else first
                txt = f"""👤 Profile - {tag}

🆔 ID: {chat_id}
🏷️ Daily Quota (WIB)

📄 Text : {q['text']}/{LIMIT_TEXT}
📪 Media: {q['media']}/{LIMIT_MEDIA}

🔹 Status X (@jogja_lend): OFF - Maintenance
🔹 Telegram Channel: @menfessangel - ON

Your quota resets every 00:00 WIB."""
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
                return "ok",200

            if cb_data == "info_bot":
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
                info_txt = """ℹ️ About JogjaLend Bot Angel

Welcome to the anonymous menfess bot for Jogja area!

📢 Channel: @menfessangel
🐦 X (Twitter): @jogjalendpm - Under Maintenance

HOW TO USE:
Just send your text, photo, or video directly to this bot. It will be posted anonymously to the channel with #jogjalend hashtag.

RULES:
- No SARA, spam, or personal data
- Keep it anonymous & respectful
- Media will get a small watermark

LIMIT:
5 texts & 5 media per day. Reset at 00:00 WIB.

Enjoy, Angel! 🤍"""
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":info_txt})
                return "ok",200

            if cb_data.startswith("delete|"):
                _, ch_msg_id = cb_data.split("|")
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":ch_msg_id})
                except: pass
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"],"text":"Deleted!"})
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Post deleted!"})
            return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg and msg["text"].startswith("/start"):
            first = msg["from"].get("first_name") or "Angel"
            uname = msg["from"].get("username")
            tag = f"@{uname}" if uname else first
            caption = f"""Welcome, {tag}.

X @jogja_lend is under maintenance, posts will only go to @menfessangel for now.

Limit: 5 texts & 5 media/day.

Please send your menfess now."""
            kb = {"inline_keyboard": [[{"text":"📢 Channel","url":"https://t.me/menfessangel"}],[{"text":"👤 Profile","callback_data":"profil"},{"text":"ℹ️ Info","callback_data":"info_bot"}]]}
            try:
                if os.path.exists("api/logo.png"):
                    with open("api/logo.png","rb") as f:
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":chat_id,"caption":caption,"reply_markup":json.dumps(kb)}, files={"photo":f})
                else:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":kb})
            except:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":kb})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        
        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)
        fb = None
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark(fb)

        if fb:
            res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb})
        else:
            res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}"

        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)

        q = quotas[key]
        pesan = f"""🏷️Free daily kuota
📄Text : {q['text']}/{LIMIT_TEXT}
📪Media : {q['media']}/{LIMIT_MEDIA}
@{msg['from'].get('username') or msg['from'].get('first_name')} berhasil mengirim menfess!

Join Channel : @menfessangel"""

        kb = {"inline_keyboard": [[{"text":"➡️ See Message","url":curl}], [{"text":"🗑️ Delete Post","callback_data":f"delete|{cmid}"}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":pesan,"reply_markup":kb})

    except Exception as e:
        print(traceback.format_exc())
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Error: {e}"})
        except: pass
    return "ok",200
