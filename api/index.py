import os, io, requests, traceback
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

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png","api/logo.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w,h = base.size
                size = int(w*0.18)
                logo = logo.resize((size,size))
                base.paste(logo, (15, 15), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=90)
                return out.getvalue()
    except Exception as e:
        print(e)
    return b

# FIX: JANGAN PAKE defaults={'path':''} LAGI, INI YANG BIKIN CRASH
@app.route("/")
@app.route("/<path:path>", methods=['GET','POST'])
def handler(path=None):
    if request.method == 'GET':
        return "Bot Aktif - FIX Mapping - Kiri Atas", 200
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        if "text" in msg and msg["text"].startswith("/start"):
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"aktif bos - mapping fix"})
            return "ok",200
        caption = msg.get("caption") or msg.get("text") or ""
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"⏳ Proses: {caption[:20]}"})
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        fb = None
        if "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark(fb)
        if fb:
            open("/tmp/post.jpg","wb").write(fb)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)
        tid = resp.data['id']
        xurl = f"https://x.com/i/web/status/{tid}"
        cmid = None
        try:
            if fb:
                res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb})
            else:
                res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
            if res.ok:
                cmid = res.json()["result"]["message_id"]
        except Exception as e:
            print(f"Channel err {e}")
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}" if cmid else f"https://t.me/{CHANNEL_USERNAME}"
        kb = {"inline_keyboard":[[{"text":"See on X","url":xurl}],[{"text":"See on Channel","url":curl}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"✅ Berhasil POST! Kiri Atas","reply_markup":kb})
    except Exception as e:
        print(traceback.format_exc())
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Error: {e}"})
    return "ok",200