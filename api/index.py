import os, requests, io
from flask import Flask, request
from PIL import Image
import tweepy

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET")
CHANNEL_ID =
os.getenv("CHANNEL_ID") or "-100392893142"
CHANNEL_USERNAME = "menfessangel"

START_TEXT = """halo @{username} ✨

UPDATE SUKSES JAM 23:18!

ini bot promote Lend Angel.
kirim foto + caption yaa"""

SUCCESS_TEXT = """✅ BERHASIL POST!

Link ada di bawah ini yaa 👇"""

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
    except: pass
    return b

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET','POST'])
def main(path):
    if request.method == 'GET': return "Bot Aktif Bos! 23:18", 200
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        username = msg["from"].get("username","user")
        text_in = msg.get("text","")
        if text_in.startswith("/start"):
            txt = START_TEXT.format(username=username)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
            return "ok",200
        caption = msg.get("caption") or msg.get("text") or "menfess"
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        tweet_id = None
        if "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            wm = add_watermark(fb)
            with open("/tmp/post.jpg","wb") as f: f.write(wm)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
            tweet_id = resp.data['id']
        elif "text" in msg:
            resp = client.create_tweet(text=caption)
            tweet_id = resp.data['id']
        x_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else "https://x.com/jogjalend"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":SUCCESS_TEXT})
    except Exception as e: print(e)
    return "ok",200
# ===============================
# EDIT BALASAN BOT DISINI AJA BOS!
# ===============================

START_TEXT = """halo, @{username} ! ✨

ini adalah bot promote Lend Angel.
kamu bisa mengirimkan text beserta foto diri
kalian disini, let's go!

Ketik menfess kamu disini 👇"""

SUCCESS_TEXT = """✅ Berhasil mengirim menfess!

Free Daily Quota
Text: 0/50
Media: 1/10

Butuh bantuan? -> @jogja_lend"""

# ===============================

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png", "api/logo.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w,h = base.size
                # logo max 16% dari lebar foto
                logo.thumbnail((int(w*0.16), int(w*0.16)))
                base.paste(logo, (w-logo.width-15, h-logo.height-15), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=92)
                return out.getvalue()
    except Exception as e:
        print(f"watermark error: {e}")
    return b

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET','POST'])
def main(path):
    if request.method == 'GET': 
        return "Bot Aktif Bos!", 200
    try:
        data = request.get_json()
        if not data or "message" not in data: 
            return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        username = msg["from"].get("username","user")
        text_in = msg.get("text","")

        if text_in.startswith("/start"):
            txt = START_TEXT.format(username=username)
            kb = {"inline_keyboard": [[{"text":"👤 Profile","callback_data":"profile"}], [{"text":"📋 Rules","callback_data":"rules"}]]}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt,"reply_markup":kb})
            return "ok",200

        caption = msg.get("caption") or msg.get("text") or "menfess"
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)

        tweet_id = None
        if "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            wm = add_watermark(fb)
            with open("/tmp/post.jpg","wb") as f: f.write(wm)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
            tweet_id = resp.data['id']
            try: 
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":wm})
            except: pass
        elif "text" in msg:
            resp = client.create_tweet(text=caption)
            tweet_id = resp.data['id']
            try: 
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
            except: pass

        x_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else "https://x.com/jogjalend"
        ch_url = f"https://t.me/jogja_lend"

        kb_ok = {"inline_keyboard": [[{"text":"➡️ See on X","url":x_url}], [{"text":"➡️ See on Channel","url":ch_url}], [{"text":"🗑️ Delete Post","callback_data":f"delete_{tweet_id}"}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":SUCCESS_TEXT,"reply_markup":kb_ok})

    except Exception as e:
        print(e)
    return "ok",200