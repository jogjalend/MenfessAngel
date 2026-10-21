import os, requests, io
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

START_TEXT = "halo @{username} UPDATE SUKSES 23:18!"

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png","api/logo.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w,h = base.size
                logo.thumbnail((int(w*0.16), int(w*0.16)))
                base.paste(logo, (w-logo.width-15, h-logo.height-15), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=92)
                return out.getvalue()
    except:
        pass
    return b

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET','POST'])
def main(path):
    if request.method == 'GET':
        return "Bot Aktif 23:37", 200
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        if "text" in msg and msg["text"].startswith("/start"):
            username = msg["from"].get("username","user")
            txt = START_TEXT.format(username=username)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
            return "ok",200
        caption = msg.get("caption") or msg.get("text") or ""
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        file_bytes = None
        if "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            file_bytes = add_watermark(fb)
        if file_bytes:
            open("/tmp/post.jpg","wb").write(file_bytes)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)
        tweet_id = resp.data['id']
        x_url = f"https://x.com/i/web/status/{tweet_id}"
        channel_msg_id = None
        try:
            if file_bytes:
                res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": caption}, files={"photo": file_bytes})
            else:
                res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption})
            if res.ok:
                channel_msg_id = res.json()["result"]["message_id"]
        except Exception as e:
            print(e)
        if channel_msg_id:
            channel_url = f"https://t.me/{CHANNEL_USERNAME}/{channel_msg_id}"
        else:
            channel_url = f"https://t.me/{CHANNEL_USERNAME}"
        keyboard = {"inline_keyboard": [[{"text": "See on X", "url": x_url}], [{"text": "See on Channel", "url": channel_url}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "Berhasil POST!", "reply_markup": keyboard})
    except Exception as e:
        print(e)
    return "ok",200