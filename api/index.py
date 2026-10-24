from flask import Flask, request
app = Flask(__name__)

import os, json, requests, tweepy
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"

def tg(m,p):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{m}", json=p, timeout=10)
    except: return None

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET','POST'])
def main(path):
    if request.method == 'GET':
        return "Bot Active - No Upstash Version", 200
    
    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return "ok",200
        
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text") or msg.get("caption") or ""
    
    if text.startswith("/start"):
        tg("sendMessage", {"chat_id": chat_id, "text": "Halo! Kirim menfess mu\nAuto post to X & Channel"})
        return "ok",200

    try:
        # auto hashtag
        if "#jogjalend" not in text.lower():
            text = text + "\n\n#jogjalend"

        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        
        # check photo
        if "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            f = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f['result']['file_path']}").content
            open("/tmp/a.jpg","wb").write(fb)
            auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
            api = tweepy.API(auth)
            m = api.media_upload("/tmp/a.jpg")
            resp = client.create_tweet(text=text, media_ids=[m.media_id])
            # kirim ke channel
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":text}, files={"photo":fb})
        else:
            resp = client.create_tweet(text=text)
            tg("sendMessage", {"chat_id": CHANNEL_ID, "text": text})

        tg("sendMessage", {"chat_id": chat_id, "text": f"Posted! {resp.data['id']}"})
    except Exception as e:
        tg("sendMessage", {"chat_id": chat_id, "text": f"Error: {e}"})
    
    return "ok",200
