import os
import json
import requests
from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@menfessangel"
LIMIT_TEXT = 3
LIMIT_MEDIA = 3
QUOTA_FILE = "/tmp/quota.json"

try:
    from PIL import Image, ImageDraw, ImageFont
    import io
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False

def load_quota():
    try:
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, "r") as f:
                return json.load(f)
    except: pass
    return {}

def save_quota(data):
    try:
        with open(QUOTA_FILE, "w") as f:
            json.dump(data, f)
    except: pass

def get_today_key(chat_id):
    return f"{chat_id}_{datetime.now().strftime('%Y-%m-%d')}"

def check_limit(chat_id, type_media=False):
    quotas = load_quota()
    key = get_today_key(chat_id)
    if key not in quotas:
        quotas[key] = {"text": 0, "media": 0}
    limit = LIMIT_MEDIA if type_media else LIMIT_TEXT
    field = "media" if type_media else "text"
    if quotas[key][field] >= limit:
        return False
    quotas[key][field] += 1
    save_quota(quotas)
    return True

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

def add_watermark(image_bytes):
    if not PIL_AVAILABLE:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
        
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            w, h = img.size
            logo_w = int(w * 0.18)
            logo_h = int(logo_w * logo.size[1] / logo.size[0])
            logo = logo.resize((logo_w, logo_h))
            img.paste(logo, (w - logo_w - 15, h - logo_h - 15), logo)
        else:
            txt_layer = Image.new("RGBA", img.size, (255,255,255,0))
            draw = ImageDraw.Draw(txt_layer)
            draw.text((img.size[0]*0.02, img.size[1]*0.92), "@menfessangel", fill=(255,255,255,180))
            img = Image.alpha_composite(img, txt_layer)

        out = io.BytesIO()
        img.convert("RGB").save(out, format="JPEG", quality=90)
        return out.getvalue()
    except:
        return image_bytes

@app.route("/", methods=["GET"])
def index():
    return "MenfessAngel Bot Jalan!", 200

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "ok", 200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        if msg["chat"]["type"] != "private":
            return "ok", 200

        is_media = "photo" in msg
        if not check_limit(chat_id, is_media):
            send_message(chat_id, "Limit harian habis (3x/hari), coba besok ya!")
            return "ok", 200

        caption = msg.get("caption", "") or msg.get("text", "")

        if "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            file_bytes = requests.get(file_url).content
            file_bytes = add_watermark(file_bytes)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            requests.post(url, files={"photo": file_bytes}, data={"chat_id": CHANNEL_ID, "caption": caption})
        elif "text" in msg:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHANNEL_ID, "text": caption})

        send_message(chat_id, "✅ Menfess terkirim ke @menfessangel")
        return "ok", 200
    except Exception as e:
        print(e)
        return "ok", 200
