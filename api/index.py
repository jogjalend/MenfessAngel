import os, io, json, requests, traceback
from flask import Flask, request
from PIL import Image
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
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

def load_quota():
    try:
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE, "r") as f: return json.load(f)
    except: pass
    return {}
def save_quota(data):
    try:
        with open(QUOTA_FILE, "w") as f: json.dump(data, f)
    except: pass
def get_today_key(chat_id):
    today = datetime.now(WIB).strftime("%Y-%m-%d")
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
                datas = []
                for r,g,bl,a in logo.getdata():
                    if a > 20: datas.append((255,255,255,230))
                    else: datas.append((255,255,255,0))
                logo.putdata(datas)
                base.paste(logo, (w - logo.width - 35, h - logo.height - 55), logo)
                out = io.BytesIO()
                base.convert("RGB").save(out, format="JPEG", quality=95)
                return out.getvalue()
    except: pass
    return b

@app.route("/")
@app.route("/<path:path>", methods=['GET','POST'])
def handler(path=None):
    if request.method == 'GET': return "Bot Active - X OFF (Suspended) - TG ON", 200
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
                txt = f"👤 Profile\nID: {chat_id}\n\nToday Usage\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}\n\nStatus X: SUSPENDED (maintenance)"
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt})
                return "ok",200
            if cb_data == "info_bot":
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
                info_txt = """Menfess Angel Bot - @jogja_lend

INFO: X @jogja_lend sedang ditangguhkan, jadi postingan hanya ke Channel @menfessangel dulu ya angel 🙏

CARA PAKAI: Kirim text / foto + caption kesini.

KUOTA:
Text 5/hari | Media 5/hari
Reset 00:00 WIB

RULES:
1. No Judol/Spam Link
2. No Doxxing
3. No link grup bodong
4. Wajib #jogjalend
Support: @Jogja_Lend"""
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":info_txt})
                return "ok",200
            if cb_data.startswith("delete|"):
                _, ch_msg_id = cb_data.split("|")
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":ch_msg_id})
                except: pass
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"],"text":"Deleted!"})
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Post deleted from Channel!"})
            return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg and msg["text"].startswith("/start"):
            txt = """Welcome to Menfess Angel Bot 🤍

⚠️ INFO: X @jogja_lend lagi ditangguhkan, jadi menfess kamu akan tayang di Channel @menfessangel dulu ya.

Auto-post to:
- Channel: @menfessangel (AKTIF)
- X: @jogja_lend (Maintenance)

Free Daily Quota:
Text  : 5 | Media : 5

Silakan kirim menfess kamu sekarang.
Support: @Jogja_Lend"""
            kb_start = {"inline_keyboard": [[{"text":"Profile","callback_data":"profil"}], [{"text":"Bot Information","callback_data":"info_bot"}]]}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt,"reply_markup":kb_start})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        
        # FILTER KATA BIAR GAK KE SUSPEND LAGI
        banned_words = ["free ch", "open bo", "link tele", "t.me/+", "judol", "slot gacor"]
        lower = raw_caption.lower()
        for bw in banned_words:
            if bw in lower:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Menfess kamu mengandung kata terlarang ({bw}) dan ditolak demi keamanan akun. Mohon edit ya angel 🙏"})
                return "ok",200

        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        if is_media:
            if quotas[key]["media"] >= LIMIT_MEDIA:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Media quota habis! {LIMIT_MEDIA}/{LIMIT_MEDIA}"})
                return "ok",200
        else:
            if quotas[key]["text"] >= LIMIT_TEXT:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Text quota habis! {LIMIT_TEXT}/{LIMIT_TEXT}"})
                return "ok",200

        caption = add_hashtag(raw_caption)
        fb = None
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark(fb)

        # HANYA POST KE TELEGRAM
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":fb}) if fb else requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}" if cmid!="0" else f"https://t.me/{CHANNEL_USERNAME}"

        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)

        pesan = f"""✅ Menfess Berhasil Terkirim!

Makasih ya angel, menfess kamu udah tayang di Channel 💌

⚠️ X lagi maintenance (akun ditangguhkan), jadi cuma tayang di Channel dulu ya.

📊 Sisa kuota:
Text: {LIMIT_TEXT - quotas[key]['text']}/{LIMIT_TEXT} | Media: {LIMIT_MEDIA - quotas[key]['media']}/{LIMIT_MEDIA}

@Jogja_Lend"""
        kb = {"inline_keyboard": [[{"text":"📢 Lihat di Channel","url":curl}], [{"text":"🗑️ Hapus Post","callback_data":f"delete|{cmid}"}]]}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":pesan,"reply_markup":kb})

    except Exception as e:
        print(traceback.format_exc())
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Error: {e}"})
        except: pass
    return "ok",200
