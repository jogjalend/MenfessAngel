import os, io, requests, traceback
from flask import Flask, request
from PIL import Image
import tweepy
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"

def add_watermark(b):
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        for p in ["logo.png","api/logo.png","logo_pro_white.png"]:
            if os.path.exists(p):
                logo = Image.open(p).convert("RGBA")
                w,h = base.size
                size = int(w*0.12)  # 12% aja, jangan 18%
                logo.thumbnail((size,size))
                # Transparansi 35% biar estetik
                alpha = logo.split()[-1]
                alpha = alpha.point(lambda p: int(p*0.65))
                logo.putalpha(alpha)
                
                margin = 24
                px = w - logo.width - margin
                py = h - logo.height - margin
                base.paste(logo, (px, py), logo)
                
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=92)
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
                uname = cq["from"].get("username","-")
                txt = f"👤 Profile\n\nID: {chat_id}\nUsername: @{uname}\n\nFree Daily Quota: Text 5, Media 5"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
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
            txt = f"""Halo, {first_name}! 👋

@{username}

Buat menfess mu di sini
Auto post to Channel & X

📩 Support: @jogja_lend"""
            kb_start = {"inline_keyboard": [[{"text":"👤 Profile","callback_data":"profil"}], [{"text":"📋 Bot Information","callback_data":"info_bot"}]]}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt,"reply_markup":kb_start})
            return "ok",200

        caption = msg.get("caption") or msg.get("text") or ""
        if not caption and "photo" not in msg: return "ok",200

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
            with open("/tmp/post.jpg","wb") as f: f.write(fb)
            media = api.media_upload("/tmp/post.jpg")
            resp = client.create_tweet(text=caption, media_ids=[media.media_id])
        else:
            resp = client.create_tweet(text=caption)

        tid = resp.data['id']
        xurl = f"https://x.com/i/web/status/{tid}"
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb}) if fb else requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}" if cmid!="0" else f"https://t.me/{CHANNEL_USERNAME}"

        pesan = f"""✅ Menfess Sent Successfully!

Free Daily Quota
Text: 0/5
Media: 1/5

Need help? -> @jogja_lend"""
        kb = {"inline_keyboard":[[{"text":"➡️ See on X","url":xurl}], [{"text":"➡️ See on Channel","url":curl}], [{"text":"🗑️ Delete Post","callback_data":f"delete|{tid}|{cmid}"}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":pesan,"reply_markup":kb})

    except Exception as e:
        print(traceback.format_exc())
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Error: {e}"})
        except: pass
    return "ok",200