from flask import Flask, request
app = Flask(__name__)

import os, requests, tweepy, json
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_SECRET") or os.getenv("X_ACCESS_SECRET")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
QUOTA_FILE = "/tmp/quota.json"

def tg(m,p):
    try: return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{m}", json=p, timeout=15)
    except: return None

def load_q():
    try:
        if os.path.exists(QUOTA_FILE):
            return json.load(open(QUOTA_FILE))
    except: pass
    return {}

def save_q(d):
    try: json.dump(d, open(QUOTA_FILE,"w"))
    except: pass

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET','POST'])
def main(path):
    if request.method == 'GET':
        return "Bot Active", 200
    
    data = request.get_json(silent=True)
    if not data: return "ok",200

    # Tombol Profile & Rules
    if "callback_query" in data:
        cq = data["callback_query"]
        cid = cq["message"]["chat"]["id"]
        d = cq.get("data","")
        if d == "profile":
            q = load_q()
            key = f"{cid}_{datetime.now().strftime('%Y-%m-%d')}"
            u = q.get(key, {"text":0,"media":0})
            txt = f"👤 Profile\nID: {cid}\nDaily Kuota\nMedia : {u['media']}/5\nText : {u['text']}/5"
            tg("answerCallbackQuery", {"callback_query_id": cq["id"]})
            tg("sendMessage", {"chat_id": cid, "text": txt})
            return "ok",200
        if d == "rules":
            txt = "📜 Rules @jogja_lend\n\n1. No porn/SARA/spam\n2. No doxxing\n3. Sopan\nLanggar = banned"
            tg("answerCallbackQuery", {"callback_query_id": cq["id"]})
            tg("sendMessage", {"chat_id": cid, "text": txt})
            return "ok",200

    if "message" not in data: return "ok",200
    msg = data["message"]
    chat_id = msg["chat"]["id"]
    raw = msg.get("text") or msg.get("caption") or ""

    # ===== 1. PESAN /START =====
    if raw.startswith("/start"):
        start_text = """halo, semuanyaa!

Selamat datang di Bot Menfess Angel JogjaLend 🤖

Ini adalah bot auto menfess @jogja_lend
Anda bisa mengirimkan text beserta foto diri kalian disini ya!

Jangan lupa join channel @menfessangel & follow @jogja_lend untuk liat menfess kamu

Kirim menfess terbaikmu sekarang! ✨"""
        kb = {"inline_keyboard": [[{"text": "👤 Profile", "callback_data": "profile"}], [{"text": "📜 Rules", "callback_data": "rules"}]]}
        tg("sendMessage", {"chat_id": chat_id, "text": start_text, "reply_markup": kb})
        return "ok",200

    # ===== 2. PESAN MENFESS TERKIRIM =====
    try:
        quotas = load_q()
        key = f"{chat_id}_{datetime.now().strftime('%Y-%m-%d')}"
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg

        if is_media and quotas[key]["media"] >= 5:
            tg("sendMessage", {"chat_id": chat_id, "text": "❌ Kuota media habis (5/5) besok lagi ya"})
            return "ok",200
        if not is_media and quotas[key]["text"] >= 5:
            tg("sendMessage", {"chat_id": chat_id, "text": "❌ Kuota text habis (5/5) besok lagi ya"})
            return "ok",200

        text = raw if "#jogjalend" in raw.lower() else raw + "\n\n#jogjalend"
        client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_SECRET)
        x_id = None; cmid = "0"

        if is_media:
            fid = msg["photo"][-1]["file_id"]
            f = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f['result']['file_path']}").content
            open("/tmp/a.jpg","wb").write(fb)
            auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET)
            api = tweepy.API(auth)
            m = api.media_upload("/tmp/a.jpg")
            resp = client.create_tweet(text=text, media_ids=[m.media_id])
            x_id = resp.data['id']
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":text}, files={"photo":fb}).json()
            cmid = r["result"]["message_id"]
            quotas[key]["media"]+=1
        else:
            resp = client.create_tweet(text=text)
            x_id = resp.data['id']
            r = tg("sendMessage", {"chat_id": CHANNEL_ID, "text": text})
            cmid = r.json()["result"]["message_id"] if r and r.ok else "0"
            quotas[key]["text"]+=1
        
        save_q(quotas)

        # FIX USERNAME
        username = msg.get("from", {}).get("username")
        user_display = f"@{username}" if username else f"ID {chat_id}"
        
        x_url = f"https://x.com/jogjalend/status/{x_id}"
        channel_url = f"https://t.me/menfessangel/{cmid}" if "@" in str(CHANNEL_ID) else f"https://t.me/c/{str(CHANNEL_ID).replace('-100','')}/{cmid}"

        ok_text = f"""Menfess Terkirim
username {user_display}
Daily Kuota
Media : {quotas[key]['media']}/5
Text : {quotas[key]['text']}/5

📢 Channel Menfess Angel :
@menfessangel"""

        kb2 = {
            "inline_keyboard": [
                [{"text": "See On X", "url": x_url}, {"text": "See On Channel", "url": channel_url}],
                [{"text": "Help", "url": "https://t.me/jogja_lend"}]
            ]
        }
        tg("sendMessage", {"chat_id": chat_id, "text": ok_text, "reply_markup": kb2})

    except Exception as e:
        tg("sendMessage", {"chat_id": chat_id, "text": f"❌ Gagal: {e}"})
    
    return "ok",200