import os, io, json, requests, traceback
from flask import Flask, request
from PIL import Image
import tweepy
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID") or "8584319568")
except:
    ADMIN_ID = 8584319568

HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))

BROADCAST_TEXT = """👼 HALO ANGEL!

Jangan lupa follow & join ya 🤍

FOLLOW:
• Channel: @menfessangel
• Grup: @jogjalend
• X: x.com/jogjalendpm

Kirim menfess kalian disini, auto-post 24 jam!"""

BROADCAST_KB = {
    "inline_keyboard": [
        [{"text": "📢 Channel", "url": "https://t.me/menfessangel"}, {"text": "💬 Grup", "url": "https://t.me/jogjalend"}],
        [{"text": "🐦 X / Twitter", "url": "https://x.com/jogjalendpm"}]
    ]
}

def load_quota():
    try:
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_quota(data):
    try:
        with open(QUOTA_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass

def get_today_key(chat_id):
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    return f"{chat_id}_{today}"

def add_hashtag(text):
    if not text:
        return HASHTAG.strip()
    if "#jogjalend" in text.lower():
        return text
    return text.strip() + HASHTAG

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png", "api/logo.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w, h = base.size
                size = int(w * 0.15)
                logo.thumbnail((size, size), Image.LANCZOS)
                datas = []
                for r, g, bl, a in logo.getdata():
                    if a > 20:
                        datas.append((255, 255, 255, 230))
                    else:
                        datas.append((255, 255, 255, 0))
                logo.putdata(datas)
                px = w - logo.width - 35
                py = h - logo.height - 55
                base.paste(logo, (px, py), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=95)
                return out.getvalue()
    except:
        pass
    return b

@app.route("/")
@app.route("/<path:path>", methods=['GET', 'POST'])
def handler(path=None):
    if request.method == 'GET':
        return "Bot Active @jogja_lend - OK", 200
    try:
        data = request.get_json()
        if not data:
            return "ok", 200

        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq["data"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]

            if cb_data == "profil":
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
                quotas = load_quota()
                key = get_today_key(chat_id)
                q = quotas.get(key, {"text": 0, "media": 0})
                txt = f"👤 Profile\nID: {chat_id}\n\nToday Usage\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": txt})
                return "ok", 200

            if cb_data == "info_bot":
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
                info_txt = """Menfess Angel Bot - @jogja_lend

CARA PAKAI:
Kirim langsung text / foto + caption kesini.
Auto posting ke X & Channel.

KUOTA HARIAN:
- Text: 5 / hari
- Media: 5 / hari
Reset jam 00:00 WIB

RULES:
1. Dilarang Spam Link Judol
2. Dilarang doxxing / spill data pribadi
3. Dilarang spam link Grup Bodong
4. Wajib pakai #jogjalend
5. follow x : x.com/jogjalendpm
Langgar = banned permanen.

Support: @Jogja_Lend"""
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": info_txt})
                return "ok", 200

            if cb_data.startswith("delete|"):
                _, tweet_id, ch_msg_id = cb_data.split("|")
                try:
                    client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
                    client.delete_tweet(tweet_id)
                except:
                    pass
                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": ch_msg_id})
                except:
                    pass
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"], "text": "Deleted!"})
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": "Post deleted!"})
            return "ok", 200

        if "message" not in data:
            return "ok", 200

        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg and msg["text"].startswith("/start"):
            txt = """Welcome to Menfess Angel Bot

Auto-post to:
- X: @jogja_lend
- Channel: @menfessangel

Free Daily Quota:
Text  : 5
Media : 5

Silakan kirim menfess kamu sekarang.
Support: @Jogja_Lend"""
            kb_start = {"inline_keyboard": [[{"text": "Profile", "callback_data": "profil"}], [{"text": "Bot Information", "callback_data": "info_bot"}]]}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": txt, "reply_markup": kb_start})
            return "ok", 200

        if "text" in msg and msg["text"].startswith("/broadcast"):
            if chat_id != ADMIN_ID:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "Khusus admin su!"})
                return "ok", 200
            custom_text = msg["text"].replace("/broadcast", "").strip()
            final_text = custom_text if custom_text else BROADCAST_TEXT
            quotas = load_quota()
            all_ids = set([k.split("_")[0] for k in quotas.keys()])
            all_ids.add(str(chat_id))
            sent = 0
            for uid in all_ids:
                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": uid, "text": final_text, "reply_markup": BROADCAST_KB})
                    sent += 1
                except:
                    pass
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"✅ Broadcast terkirim ke {sent} user!"})
            return "ok", 200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg:
            return "ok", 200

        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas:
            quotas[key] = {"text": 0, "media": 0}

        is_media = "photo" in msg
        if is_media:
            if quotas[key]["media"] >= LIMIT_MEDIA:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"Media quota habis! {LIMIT_MEDIA}/{LIMIT_MEDIA} hari ini."})
                return "ok", 200
        else:
            if quotas[key]["text"] >= LIMIT_TEXT:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"Text quota habis! {LIMIT_TEXT}/{LIMIT_TEXT} hari ini."})
                return "ok", 200

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
            with open("/tmp/post.jpg", "wb") as f:
                f.write(fb)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)

        if is_media:
            quotas[key]["media"] += 1
        else:
            quotas[key]["text"] += 1
        save_quota(quotas)

        tid = resp.data['id']
        xurl = f"https://x.com/i/web/status/{tid}"
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": caption}, files={"photo": fb}) if fb else requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption})
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}" if cmid != "0" else f"https://t.me/{CHANNEL_USERNAME}"

        # INI YANG 2 TAB ATAS - SUDAH FIX
        pesan = f"""✅ Menfess Berhasil Terkirim!

Makasih ya angel, menfess kamu udah tayang 💌

📊 Sisa kuota hari ini:
Text: {LIMIT_TEXT - quotas[key]['text']}/{LIMIT_TEXT} | Media: {LIMIT_MEDIA - quotas[key]['media']}/{LIMIT_MEDIA}

Butuh bantuan? @Jogja_Lend"""
        
        kb = {
            "inline_keyboard": [
                [{"text": "🐦 Lihat di X", "url": xurl}, {"text": "📢 Lihat di Channel", "url": curl}],
                [{"text": "🗑️ Hapus Post", "callback_data": f"delete|{tid}|{cmid}"}]
            ]
        }
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": pesan, "reply_markup": kb})

    except Exception as e:
        print(traceback.format_exc())
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": f"Error: {e}"})
        except:
            pass
    return "ok", 200
