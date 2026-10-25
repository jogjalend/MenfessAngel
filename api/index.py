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
    return "Bot Active - X OFF (Suspended) - TG ON", 200

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
                txt = f"Profile\nID: {chat_id}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}\nStatus X: OFF"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
                return "ok",200
            if cb_data == "info_bot":
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
                info_txt = "X @jogja_lend suspend, post hanya ke @menfessangel dulu ya"
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
            txt = "Welcome 🤍 X OFF, hanya ke @menfessangel\nKirim menfess kamu sekarang"
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
