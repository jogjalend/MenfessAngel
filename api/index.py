from flask import Flask
app = Flask(__name__)

import os, io, json, requests, traceback
from PIL import Image
import tweepy
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"

HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5

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
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{chat_id}_{today}"

def add_hashtag(text):
    if not text: return HASHTAG.strip()
    if "#jogjalend" in text.lower(): return text
    return text.strip() + HASHTAG

def tg(m,p):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{m}", json=p, timeout=10)
    except: return None

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET','POST'])
def handler(path=None):
    if request.method == 'GET': return "Bot Active @jogja_lend", 200
    chat_id=None
    try:
        data = request.get_json(silent=True)
        if not data: return "ok",200
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq.get("data","")
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            if cb_data == "profil":
                tg("answerCallbackQuery", {"callback_query_id":cq["id"]})
                quotas = load_quota()
                key = get_today_key(chat_id)
                q = quotas.get(key, {"text":0,"media":0})
                txt = f"Profile\nID: {chat_id}\nToday\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}"
                tg("sendMessage", {"chat_id":chat_id,"text":txt})
                return "ok",200
            if cb_data == "info_bot":
                tg("answerCallbackQuery", {"callback_query_id":cq["id"]})
                tg("sendMessage", {"chat_id":chat_id,"text":"Angel Menfess Bot\nQuota Text 5 Media 5\nSupport @jogja_lend"})
                return "ok",200
            if cb_data.startswith("delete|"):
                _, tid, cmid = cb_data.split("|")
                try:
                    client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
                    client.delete_tweet(tid)
                except: pass
                try: tg("deleteMessage", {"chat_id":CHANNEL_ID,"message_id":int(cmid)})
                except: pass
                tg("answerCallbackQuery", {"callback_query_id":cq["id"],"text":"Deleted!"})
                tg("editMessageText", {"chat_id":chat_id,"message_id":msg_id,"text":"Post deleted!"})
                return "ok",200
        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        if msg.get("text","").startswith("/start"):
            txt = f"Halo! Buat menfess mu disini\nAuto post to Channel & X"
            kb = {"inline_keyboard": [[{"text":"Profile","callback_data":"profil"}], [{"text":"Bot Info","callback_data":"info_bot"}]]}
            tg("sendMessage", {"chat_id":chat_id,"text":txt,"reply_markup":kb})
            return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        if is_media and quotas[key]["media"]>=LIMIT_MEDIA:
            tg("sendMessage", {"chat_id":chat_id,"text":f"Media quota habis {LIMIT_MEDIA}/{LIMIT_MEDIA}"}); return "ok",200
        if not is_media and quotas[key]["text"]>=LIMIT_TEXT:
            tg("sendMessage", {"chat_id":chat_id,"text":f"Text quota habis {LIMIT_TEXT}/{LIMIT_TEXT}"}); return "ok",200
        caption = add_hashtag(raw_caption)
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        fb = None
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=10).json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=15).content
        if fb:
            open("/tmp/post.jpg","wb").write(fb)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)
        if is_media: quotas[key]["media"]+=1
        else: quotas[key]["text"]+=1
        save_quota(quotas)
        tid = resp.data['id']
        xurl = f"https://x.com/i/web/status/{tid}"
        if fb:
            rr = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb}, timeout=15)
            cmid = rr.json()["result"]["message_id"] if rr.ok else "0"
        else:
            rr = tg("sendMessage", {"chat_id":CHANNEL_ID,"text":caption})
            cmid = rr.json()["result"]["message_id"] if rr and rr.ok else "0"
        pesan = f"Sent! Text:{quotas[key]['text']}/{LIMIT_TEXT} Media:{quotas[key]['media']}/{LIMIT_MEDIA}"
        kb = {"inline_keyboard":[[{"text":"See on X","url":xurl}], [{"text":"Delete","callback_data":f"delete|{tid}|{cmid}"}]]}
        tg("sendMessage", {"chat_id":chat_id,"text":pesan,"reply_markup":kb})
    except Exception as e:
        if chat_id: tg("sendMessage", {"chat_id":chat_id,"text":f"Error: {e}"})
    return "ok",200
