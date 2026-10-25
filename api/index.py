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
        return False, quotas
    
    quotas[key][field] += 1
    save_quota(quotas)
    return True, quotas

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def add_watermark(image_bytes):
    if not PIL_AVAILABLE:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        txt_layer = Image.new("RGBA", img.size, (255,255,255,0))
        draw = ImageDraw.Draw(txt_layer)
        
        watermark_text = "@menfessangel"
        w, h = img.size
        
        # Font size proporsional
        try:
            font = ImageFont.truetype("arial.ttf", int(w*0.05))
        except:
            font = ImageFont.load_default()
        
        # Posisi pojok kanan bawah
        draw.text((w*0.02, h*0.92), watermark_text, font=font, fill=(255,255,255,180))
        
        combined = Image.alpha_composite(img, txt_layer)
        out = io.BytesIO()
        combined.convert("RGB").save(out, format="JPEG")
        return out.getvalue()
    except Exception as e:
        print(f"Watermark error: {e}")
        return image_bytes

@app.route("/", methods=["GET"])
def index():
    return "MenfessAngel Bot Jalan! @menfessangel", 200

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "ok", 200
            
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        chat_type = msg["chat"]["type"]

        # Hanya proses chat private
        if chat_type != "private":
            return "ok", 200

        # Cek ada foto / media
        is_media = "photo" in msg or "video" in msg or "document" in msg
        
        ok, _ = check_limit(chat_id, is_media)
        if not ok:
            send_message(chat_id, f"😭 Limit harian kamu habis ({LIMIT_MEDIA if is_media else LIMIT_TEXT}x/hari). Coba lagi besok ya!")
            return "ok", 200

        caption = msg.get("caption", "") or msg.get("text", "")
        
        # Jika ada foto
        if "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            file_bytes = requests.get(file_url).content
            
            # Kasih watermark
            file_bytes = add_watermark(file_bytes)
            
            # Kirim ke channel
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            files = {"photo": file_bytes}
            data_send = {"chat_id": CHANNEL_ID, "caption": caption}
            requests.post(url, files=files, data=data_send)
        
        elif "text" in msg:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHANNEL_ID, "text": caption})

        send_message(chat_id, "✅ Menfess kamu berhasil dikirim ke @menfessangel")
        return "ok", 200

    except Exception as e:
        print(f"Error: {e}")
        return "ok", 200
