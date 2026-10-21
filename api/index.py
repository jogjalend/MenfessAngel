import os
import requests
import io
from flask import Flask, request
from PIL import Image
import tweepy

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET")

def add_watermark(base_bytes):
    try:
        base = Image.open(io.BytesIO(base_bytes)).convert("RGBA")
        logo_path = None
        for p in ["logo.png", "api/logo.png", "MenfessAngel/logo.png"]:
            if os.path.exists(p):
                logo_path = p
                break
        if not logo_path:
            return base_bytes
        logo = Image.open(logo_path).convert("RGBA")
        w, h = base.size
        logo.thumbnail((int(w*0.16), int(w*0.16)))
        base.paste(logo, (w - logo.width - 15, h - logo.height - 15), logo)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=92)
        return out.getvalue()
    except:
        return base_bytes

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST'])
def main(path):
    if request.method == 'GET':
        return "Bot Menfess Angel Aktif Bos!", 200

    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "ok", 200

        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "photo" not in msg:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": "Kirim FOTO + caption bos! 📸"})
            return "ok", 200

        caption = msg.get("caption", "menfess") or "menfess"
        file_id = msg["photo"][-1]["file_id"]

        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_path = r["result"]["file_path"]
        file_bytes = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}").content

        wm = add_watermark(file_bytes)

        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
                                access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)

        with open("/tmp/post.jpg", "wb") as f:
            f.write(wm)

        media = api.media_upload("/tmp/post.jpg")
        client.create_tweet(text=caption, media_ids=[media.media_id])

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": f"✅ BERHASIL POST KE X!\n\n{caption}"})

    except Exception as e:
        print(f"ERROR: {e}")
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"❌ Gagal: {e}"})
        except:
            pass

    return "ok", 200
