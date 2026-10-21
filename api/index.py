import os
import io
import requests
from flask import Flask, request
from PIL import Image
import tweepy

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "-100392893142"
CHANNEL_USERNAME = "menfessangel"

START_TEXT = "halo @{username} Bot aktif!"

def add_watermark(img_bytes):
    try:
        base = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        for logo_path in ["logo.png", "api/logo.png"]:
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")
                w, h = base.size
                logo.thumbnail((int(w * 0.18), int(w * 0.18)))
                # INI YANG DIGANTI KE KIRI ATAS
                pos = (15, 15)
                base.paste(logo, pos, logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=90)
                return out.getvalue()
    except Exception as e:
        print(f"Watermark error: {e}")
    return img_bytes

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST'])
def main(path):
    if request.method == 'GET':
        return "Bot Aktif - Watermark Kiri Atas", 200
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "ok", 200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        if "text" in msg and msg["text"].startswith("/start"):
            username = msg["from"].get("username", "user")
            text = START_TEXT.format(username=username)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text})
            return "ok", 200
        caption = msg.get("caption") or msg.get("text") or ""
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        file_bytes = None
        if "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            file_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_content = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}").content
            file_bytes = add_watermark(file_content)
        if file_bytes:
            with open("/tmp/post.jpg", "wb") as f:
                f.write(file_bytes)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)
        tweet_id = resp.data['id']
        x_url = f"https://x.com/i/web/status/{tweet_id}"
        channel_msg_id = None
        try:
            if file_bytes:
                r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": caption}, files={"photo": file_bytes}, timeout=20)
            else:
                r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption}, timeout=20)
            if r.ok:
                channel_msg_id = r.json()["result"]["message_id"]
        except Exception as e:
            print(f"Channel error: {e}")
        if channel_msg_id:
            channel_url = f"https://t.me/{CHANNEL_USERNAME}/{channel_msg_id}"
        else:
            channel_url = f"https://t.me/{CHANNEL_USERNAME}"
        keyboard = {"