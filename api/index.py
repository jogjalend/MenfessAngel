# app harus di baris paling atas biar Vercel detek
from flask import Flask
app = Flask(__name__)

import os, io, json, requests, logging, traceback
from PIL import Image
import tweepy
from datetime import datetime

# import redis setelah app
try:
    from upstash_redis import Redis
except:
    Redis = None

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

CHANNEL_USERNAME = "menfessangel"
HASHTAG = "\n\n#jogjalend"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5

# setup redis lazy
redis_client = None
if Redis and REDIS_URL and REDIS_TOKEN:
    try:
        redis_client = Redis(url=REDIS_URL, token=REDIS_TOKEN)
    except:
        redis_client = None

def get_today_key(chat_id):
    today = datetime.now().strftime("%Y-%m-%d")
    return f"quota:{chat_id}:{today}"

def load_quota(chat_id):
    if not redis_client: return {"text":0,"media":0}
    key = get_today_key(chat_id)
    try:
        data = redis_client.get(key)
        if data: return json.loads(data) if isinstance(data, str) else data
    except: pass
    return {"text":0,"media":0}

def save_quota(chat_id, data):
    if not redis_client: return
    key = get_today_key(chat_id)
    try: redis_client.set(key, json.dumps(data), ex=172800)
    except: pass

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
                datas = [(255,255,255,230) if a>20 else (255,255,255,0) for r,g,bl,a in logo.getdata()]
                logo.putdata(datas)
                base.paste(logo, (w-logo.width-35, h-logo.height-55), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=95)
                return out.getvalue()
    except: pass
    return b

def tg_post(method, payload):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}", json=payload, timeout=10)
    except: return None

@app.route("/")
@app.route("/<path:path>", methods=['GET','POST'])
def handler(path=None):
    if request.method == 'GET': return "Bot Active @jogja_lend - Redis ON", 200
    chat_id = None
    try:
        data = request.get_json(silent=True)
        if not data: return "ok",200
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq.get("data","")
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            if cb_data == "profil":
                tg_post("answerCallbackQuery", {"callback_query_id":cq["id"]})
                q = load_quota(chat_id)
                txt = f"Profile ID: {chat_id}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}"
                tg_post("sendMessage", {"chat_id":chat_id,"text":txt})
                return "ok",200
            if cb_data == "info_bot":
                tg_post("answerCallbackQuery", {"callback_query_id":cq["id"]})
                tg_post("sendMessage", {"chat_id":chat_id,"text":"Angel Menfess Bot - Free Daily Quota Text 5 Media 5"})
                return "ok",200
            if cb_data.startswith("delete|"):
                parts = cb_data.split("|")
                if len(parts)!=3: return "ok",200
                _, tweet_id, ch_msg_id = parts
                if not tweet_id.isdigit(): return "ok",200
                try:
                    client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
                    client.delete_tweet(tweet_id)
                except: pass
                try: tg_post("deleteMessage", {"chat_id":CHANNEL_ID,"message_id":int(ch_msg_id)})
                except: pass
                tg_post("answerCallbackQuery", {"callback_query_id":cq["id"],"text":"Deleted!"})
                tg_post("editMessageText", {"chat_id":chat_id,"message_id":msg_id,"text":"Post deleted!"})
                return "ok",200
        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        if "text" in msg and msg["text"].startswith("/start"):
            txt = f"Halo! Buat menfess mu disini\nAuto post to Channel & X"
            kb = {"inline_keyboard": [[{"text":"Profile","callback_data":"profil"}], [{"text":"Bot Info","callback_data":"info_bot"}]]}
            tg_post("sendMessage", {"chat_id":chat_id,"text":txt,"reply_markup":kb})
            return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota(chat_id)
        is_media = "photo" in msg
        if is_media and quotas["media"]>=LIMIT_MEDIA:
            tg_post("sendMessage", {"chat_id":chat_id,"text":f"Media quota habis {LIMIT_MEDIA}/{LIMIT_MEDIA}"})
            return "ok",200
        if not is_media and quotas["text"]>=LIMIT_TEXT:
            tg_post("sendMessage", {"chat_id":chat_id,"text":f"Text quota habis {LIMIT_TEXT}/{LIMIT_TEXT}"})
            return "ok",200
        caption = add_hashtag(raw_caption)
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        fb = None
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            try:
                r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
                fp = r["result"]["file_path"]
                fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=15).content
                fb = add_watermark(fb)
            except: pass
        if fb:
            with open("/tmp/post.jpg","wb") as f: f.write(fb)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)
        if is_media: quotas["media"]+=1
        else: quotas["text"]+=1
        save_quota(chat_id, quotas)
        tid = resp.data['id']
        xurl = f"https://x.com/i/web/status/{tid}"
        if fb:
            try:
                r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb}, timeout=15)
                cmid = r.json()["result"]["message_id"] if r.ok else "0"
            except: cmid="0"
        else:
            r = tg_post("sendMessage", {"chat_id":CHANNEL_ID,"text":caption})
            cmid = r.json()["result"]["message_id"] if r and r.ok else "0"
        pesan = f"✅ Sent! Text:{quotas['text']}/{LIMIT_TEXT} Media:{quotas['media']}/{LIMIT_MEDIA}"
        kb = {"inline_keyboard":[[{"text":"See on X","url":xurl}], [{"text":"See Channel","url":f"https://t.me/{CHANNEL_USERNAME}/{cmid}"}], [{"text":"Delete","callback_data":f"delete|{tid}|{cmid}"}]]}
        tg_post("sendMessage", {"chat_id":chat_id,"text":pesan,"reply_markup":kb})
    except Exception as e:
        if chat_id: tg_post("sendMessage", {"chat_id":chat_id,"text":f"Error: {e}"})
    return "ok",200
