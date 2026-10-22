import os, io, json, requests, traceback
from flask import Flask, request
from PIL import Image
import tweepy
from datetime import datetime
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"

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

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png","api/logo.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w,h = base.size
                size = int(w*0.15)
                logo.thumbnail((size,size), Image.LANCZOS)
                data = []
                for r,g,bl,a in logo.getdata():
                    if a > 20: data.append((255,255,255,230))
                    else: data.append((255,255,255,0))
                logo.putdata(data)
                px = w - logo.width - 35
                py = h - logo.height - 55
                base.paste(logo, (px, py), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=95)
                return out.getvalue()
    except: pass
    return b

@app.route("/")
@app.route("/<path:path>", methods=['GET','POST'])
def handler(path=None):
    if request.method == 'GET': return "Bot Active @jogja_lend", 200
    try:
        data = request.get_json()
        if not data: return "ok",200

        if "callback_query" in data:
    cq = data["callback_query"]
    cb_data = cq["data"]
    chat_id = cq["message"]["chat"]["id"]
    msg_id = cq["message"]["message_id"]

    if cb_data == "profil":
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
        quotas = load_quota()
        key = get_today_key(chat_id)
        q = quotas.get(key, {"text":0,"media":0})
        txt = f"👤 Profile\n\nID: {chat_id}\nToday Usage\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
        return "ok",200

    if cb_data == "info_bot":
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"📋 Angel Menfess Bot\nFree Daily Quota: Text 5, Media 5\nQuestions & Support: @Jogja_Lend"})
        return "ok",200

    if cb_data.startswith("delete|"):
        try:
            _, tweet_id, ch_msg_id = cb_data.split("|")

            try:
                client = tweepy.Client(
                    consumer_key=X_API_KEY,
                    consumer_secret=X_API_SECRET,
                    access_token=X_ACCESS_TOKEN,
                    access_token_secret=X_ACCESS_SECRET
                )
                client.delete_tweet(tweet_id)
            except Exception:
                pass

            try:
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
                    json={"chat_id": CHANNEL_ID, "message_id": ch_msg_id}
                )
            except Exception:
                pass

            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": cq["id"], "text": "✅ Post deleted!"}
            )
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                json={"chat_id": chat_id, "message_id": msg_id, "text": "🗑️ Post successfully deleted!"}
            )
        except Exception:
            pass
        return "ok",200

    return "ok",200
            if cb_data == "info_bot":
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"📋 Angel Menfess Bot\nFree Daily Quota: Text 5, Media 5\nQuestions & Support: @Jogja_Lend"})
                return "ok",200
            if cb_data.startswith("delete|"):
                _, tweet_id, ch_msg_id = cb_data.split("|")
                try:
                    client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
                    client.delete_tweet(tweet_id)
                except: pass
                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":ch_msg_id})
                except: pass
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"],"text":"✅ Post deleted!"})
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"🗑️ Post successfully deleted!"})
            return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg and msg["text"].startswith("/start"):
            from_user = msg.get("from", {})
            first_name = from_user.get("first_name", "you")
            username = from_user.get("username", "jogja_lend")
            txt = f"Halo, {first_name}! 👋\n\n@{username}\n\nBuat menfess mu di sini\nAuto post to Channel & X\n\n📩 Support: @jogja_lend"
            kb_start = {"inline_keyboard": [[{"text":"👤 Profile","callback_data":"profil"}], [{"text":"📋 Bot Information","callback_data":"info_bot"}]]}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt,"reply_markup":kb_start})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200

        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        if is_media:
            if quotas[key]["media"] >= LIMIT_MEDIA:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Media quota habis! {LIMIT_MEDIA}/{LIMIT_MEDIA} hari ini. Coba lagi besok."})
                return "ok",200
        else:
            if quotas[key]["text"] >= LIMIT_TEXT:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Text quota habis! {LIMIT_TEXT}/{LIMIT_TEXT} hari ini. Coba lagi besok."})
                return "ok",200

        caption = add_hashtag(raw_caption)

        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
        api = tweepy.API(auth)
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        fb = None
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark(fb)

        if fb:
            with open("/tmp/post.jpg","wb") as f: f.write(fb)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)

        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)

        tid = resp.data['id']
        xurl = f"https://x.com/i/web/status/{tid}"

        # ===== AUTO REACT AKUN 2 LIKE + RETWEET =====
        try:
            if os.getenv("X2_API_KEY"):
                client2 = tweepy.Client(
                    consumer_key=os.getenv("X2_API_KEY"),
                    consumer_secret=os.getenv("X2_API_SECRET"),
                    access_token=os.getenv("X2_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("X2_ACCESS_SECRET")
                )
                client2.like(tid)
                client2.retweet(tid)
                print(f"Akun 2 sukses LIKE+RETWEET {tid}")
        except Exception as e:
            print(f"Auto react akun 2 gagal: {e}")
        # ===== END AUTO REACT =====

        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb}) if fb else requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}" if cmid!="0" else f"https://t.me/{CHANNEL_USERNAME}"

        pesan = f"👑 Menfess Sent Successfully!\n\nFree Daily Quota\nText: 0/5\nMedia: 1/5\n\nNeed help? -> @jogja_lend"
kb = {"inline_keyboard": [
    [
        {"text": "➡️ See on X", "url": f"https://x.com/jogja_lend/status/{tid}"},
        {"text": "➡️ See on Channel", "url": curl}
    ],
    [
        {"text": "🗑️ Delete Post", "callback_data": f"delete_{tid}"}
    ]
]}
requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": pesan, "reply_markup": kb})
    except Exception as e:
        print(traceback.format_exc())
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Error: {e}"})
        except: pass
    return "ok",200
