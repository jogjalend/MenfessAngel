import os
import json
import requests
import io
from flask import Flask, request
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@menfessangel"
LIMIT_TEXT = 3
LIMIT_MEDIA = 3
QUOTA_FILE = "/tmp/quota.json"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo.png")

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

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def add_watermark(image_bytes):
    try:
        base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        w, h = base.size
        
        # Jika ada file logo.png pakai logo, kalau gak ada pakai teks
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            # resize logo jadi 20% lebar foto
            logo_w = int(w * 0.20)
            ratio = logo_w / logo.size[0]
            logo_h = int(logo.size[1] * ratio)
            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
            
            # posisi kanan bawah
            x = w - logo_w - 20
            y = h - logo_h - 20
            base.paste(logo, (x, y), logo)
        else:
            # Watermark teks fallback
            txt_layer = Image.new("RGBA", base.size, (255,255,255,0))
            draw = ImageDraw.Draw(txt_layer)
            font_size = int(w * 0.055)
            try: font = ImageFont.truetype("arial.ttf", font_size)
            except: font = ImageFont.load_default()
            text = "@Jogja_Lend"
            bbox = draw.textbbox((0,0), text, font=font)
            text_w = bbox[2]-bbox[0]
            text_h = bbox[3]-bbox[1]
            x = w - text_w - 20
            y = h - text_h - 20
            # outline
            for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
                draw.text((x+dx, y+dy), text, font=font, fill="black")
            draw.text((x, y), text, font=font, fill="white")
            base = Image.alpha_composite(base, txt_layer)

        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=95)
        out.seek(0)
        return out
    except Exception as e:
        print(f"Watermark fail: {e}")
        return io.BytesIO(image_bytes)

@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":
        return "Jogja Lend Bot Active - No Filter + Watermark", 200

    data = request.get_json()
    if not data or "message" not in data:
        return "ok", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    raw_caption = msg.get("caption") or msg.get("text") or ""
    if not raw_caption and "photo" not in msg and "video" not in msg:
        return "ok", 200

    quotas = load_quota()
    key = get_today_key(chat_id)
    if key not in quotas:
        quotas[key] = {"text": 0, "media": 0}
    
    is_media = "photo" in msg or "video" in msg
    quota_type = "media" if is_media else "text"
    limit = LIMIT_MEDIA if is_media else LIMIT_TEXT

    if quotas[key][quota_type] >= limit:
        send_message(chat_id, f"⚠️ Kuota {quota_type} habis ({limit}/{limit}) besok lagi ya angel!")
        return "ok", 200

    try:
        if is_media and "photo" in msg:
            # Download foto resolusi tertinggi
            file_id = msg["photo"][-1]["file_id"]
            file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            img_bytes = requests.get(file_url).content
            
            # Tambah watermark
            watermarked = add_watermark(img_bytes)
            
            # Kirim ke channel
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                data={"chat_id": CHANNEL_ID, "caption": raw_caption},
                files={"photo": watermarked}
            )
        elif is_media and "video" in msg:
            # Untuk video pakai copy dulu (watermark video butuh ffmpeg, skip dulu)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage", json={
                "chat_id": CHANNEL_ID, "from_chat_id": chat_id, "message_id": msg["message_id"]
            })
        else:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": CHANNEL_ID, "text": raw_caption
            })

        quotas[key][quota_type] += 1
        save_quota(quotas)

        pesan_sukses = f"""✅ Menfess Berhasil Terkirim

💌 Menfess kamu berhasil tayang di Channel @menfessangel

⚠️ System Notice: X @jogja_lend is currently under maintenance.

📊 Sisa Kuota Hari Ini:
- Text: {LIMIT_TEXT - quotas[key]['text']}/{LIMIT_TEXT}
- Media: {LIMIT_MEDIA - quotas[key]['media']}/{LIMIT_MEDIA}

Thank you angel!
@Jogja_Lend"""
        send_message(chat_id, pesan_sukses)

    except Exception as e:
        print(e)
        send_message(chat_id, "❌ Gagal kirim, coba lagi.")

    return "ok", 200
