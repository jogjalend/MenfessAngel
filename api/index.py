import os, io, json, requests, re
from flask import Flask, request
from PIL import Image
from datetime import datetime, timezone, timedelta
import time

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")

HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
SETTINGS_FILE = "/tmp/settings.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()

BAD_WORDS = ["kontol","memek","ngentot","anjing","babi","tolol","goblok"]
LOGO_CACHE = None
for p in ["logo.png","api/logo.png"]:
    if os.path.exists(p):
        try: LOGO_CACHE = Image.open(p).convert("RGBA"); break
        except: pass

def load_quota():
    try:
        if os.path.exists(QUOTA_FILE):
            with open(QUOTA_FILE,"r") as f: return json.load(f)
    except: pass
    return {}
def save_quota(d):
    try: 
        with open(QUOTA_FILE,"w") as f: json.dump(d,f)
    except: pass
def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE,"r") as f: return json.load(f)
    except: pass
    return {}
def save_settings(d):
    try:
        with open(SETTINGS_FILE,"w") as f: json.dump(d,f)
    except: pass
def is_threads_enabled(chat_id): return load_settings().get(str(chat_id),{}).get("threads", False)
def set_threads_enabled(chat_id, v):
    s = load_settings()
    if str(chat_id) not in s: s[str(chat_id)] = {}
    s[str(chat_id)]["threads"] = v
    save_settings(s)
def get_today_key(chat_id): return f"{chat_id}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(text):
    if not text: return HASHTAG.strip()
    if "#jogjalend" in text.lower(): return text
    return text.strip() + HASHTAG
def censor_text(text):
    c = text
    for w in BAD_WORDS:
        c = re.sub(re.escape(w), "***", c, flags=re.IGNORECASE)
    return c
def add_watermark_fast(b):
    if not LOGO_CACHE: return b
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        w,h = base.size
        logo = LOGO_CACHE.copy()
        logo.thumbnail((int(w*0.15), int(w*0.15)), Image.LANCZOS)
        base.paste(logo, (w-logo.width-35, h-logo.height-55), logo)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
        return out.getvalue()
    except: return b

def post_to_threads(text):
    if not THREADS_TOKEN or not THREADS_USER_ID: return None
    if len(text) > 500: text = text[:497] + "..."
    try:
        if any(w in text.lower() for w in BAD_WORDS):
            text = censor_text(text)
        r1 = SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data={"media_type":"TEXT","text":text,"access_token":THREADS_TOKEN}, timeout=15)
        if not r1.ok: return None
        cid = r1.json().get("id")
        if not cid: return None
        for i in range(6):
            time.sleep(5)
            rs = SESSION.get(f"https://graph.threads.net/v1.0/{cid}", params={"fields":"status,error_message","access_token":THREADS_TOKEN}, timeout=15)
            if rs.ok:
                st = rs.json().get("status")
                if st == "FINISHED": break
                if st in ["ERROR","EXPIRED"]: return None
        r2 = SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish", data={"creation_id":cid,"access_token":THREADS_TOKEN}, timeout=15)
        if r2.ok: return r2.json().get("id")
        return None
    except Exception as e:
        print(e); return None

# ====== FIX TERBARU OPSI B - TANPA WELCOME ======
def get_start_text(chat_id):
    threads_on = is_threads_enabled(chat_id)
    threads_txt = "ON ✅" if threads_on else "OFF ❌"
    return (
        f"Menfess Angel • Official\n\n"
        f"Your post will be published to:\n\n"
        f"  Channel → @menfessangel\n"
        f"  Threads → @jogjalend [optional]\n"
        f"  X → @jogjalendpm [maintenance]\n\n"
        f"Threads mode: {threads_txt}\n"
        f"Daily reset: 00:00 WIB\n"
        f"Limit: 5 texts & 5 media"
    )

def get_main_menu_text():
    return (
        f"Menfess Angel • Official\n\n"
        f"Your post will be published to:\n\n"
        f"  Channel → @menfessangel\n"
        f"  Threads → @jogjalend [optional]\n"
        f"  X → @jogjalendpm [maintenance]"
    )

# TOMBOL GEDE FULL-WIDTH
def get_main_menu():
    return {"inline_keyboard": [
        [{"text":"📝 Post Menfess","callback_data":"menu_post"}],
        [{"text":"👤 Profile","callback_data":"profil"}],
        [{"text":"🧵 Threads Setting","callback_data":"menu_threads"}],
        [{"text":"📊 Stats","callback_data":"menu_stats"}],
        [{"text":"📜 Rules","callback_data":"menu_rules"}],
        [{"text":"ℹ️ Help","callback_data":"menu_help"}],
        [{"text":"📢 Channel","url":"https://t.me/menfessangel"}]
    ]}

@app.route("/", methods=['GET'])
def home(): return "Bot Active - V9 Opsi B No Welcome",200

@app.route("/", methods=['POST'])
@app.route("/api/index.py", methods=['POST'])
def handler():
    try:
        data = request.get_json()
        if not data: return "ok",200
        
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq["data"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})

            if cb_data in ["menu_main", "back_to_start"]:
                text = get_start_text(chat_id)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":text,"reply_markup":get_main_menu()})
                return "ok",200

            elif cb_data in ["menu_post","menu_stats","menu_rules","menu_help"]:
                texts = {
                    "menu_post": "📝 POST MENFESS\n\nSend text or photo directly to this bot.\nDaily limit: 5 texts & 5 media.\nHashtag #jogjalend will be added automatically.",
                    "menu_stats": f"📊 STATISTICS\n\nYour usage today: {load_quota().get(get_today_key(chat_id), {'text':0,'media':0})}\nLimit: {LIMIT_TEXT} Text & {LIMIT_MEDIA} Media",
                    "menu_rules": "📜 COMMUNITY GUIDELINES\n\n1. No Spam & Scam Links\n2. No SARA & Hate Speech\n3. No Doxxing & Personal Data\n4. Stay Professional\n\nViolation = Permanent Ban",
                    "menu_help": "ℹ️ HELP CENTER\n\n/start - Show main menu\nSimply send your menfess (text/photo) to post\nThreads is OFF by default. Enable it via Profile"
                }
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":texts[cb_data],"reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"menu_main"}]]}})
                return "ok",200

            elif cb_data in ["profil","menu_threads","toggle_threads"]:
                if cb_data == "toggle_threads":
                    set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                quotas = load_quota()
                q = quotas.get(get_today_key(chat_id), {"text":0,"media":0})
                on = is_threads_enabled(chat_id)
                tag = f"@{cq['from'].get('username')}" if cq["from"].get("username") else cq["from"].get("first_name")
                txt = f"👤 PROFILE - {tag}\n🆔 ID: {chat_id}\n📄 Text: {q['text']}/{LIMIT_TEXT}\n📦 Media: {q['media']}/{LIMIT_MEDIA}\n🔹 Telegram: ON\n🔹 Threads: {'ON ✅' if on else 'OFF ❌'}"
                kb = {"inline_keyboard": [[{"text": f"🧵 Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"🔙 Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200

            elif cb_data.startswith("delete|"):
                _, ch_msg_id = cb_data.split("|")
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":ch_msg_id})
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Post has been deleted! 🗑️"})
                return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        tag = f"@{msg['from'].get('username')}" if msg["from"].get("username") else msg["from"].get("first_name") or "Angel"

        if "text" in msg and msg["text"].startswith(("/start","/menu")):
            text = get_start_text(chat_id)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text,"reply_markup":get_main_menu()})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        
        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)

        if is_media and quotas[key]["media"] >= LIMIT_MEDIA:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"❌ Media quota exceeded!"})
            return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"❌ Text quota exceeded!"})
            return "ok",200

        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark_fast(fb)
            files = {"photo": ("menfess.jpg", fb, "image/jpeg")}
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30)
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}"

        threads_id = None
        if is_threads_enabled(chat_id):
            threads_id = post_to_threads(caption)

        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)
        q = quotas[key]

        status_msg = "Posted to Telegram & Threads" if threads_id else ("Posted to Telegram only" if not is_threads_enabled(chat_id) else "Posted to Telegram. Threads failed")

        pesan = f"🏷️ QUOTA STATUS\n📄 Text: {q['text']}/{LIMIT_TEXT}\n📦 Media: {q['media']}/{LIMIT_MEDIA}\n{status_msg}"

        buttons = [[{"text":"➡️ View on Telegram","url":curl}]]
        if threads_id: buttons.append([{"text":"🧵 View on Threads","url":f"https://www.threads.net/@{CHANNEL_USERNAME}"}])
        buttons.append([{"text":"📋 Menu","callback_data":"menu_main"}, {"text":"🗑️ Delete","callback_data":f"delete|{cmid}"}])
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":pesan,"reply_markup":{"inline_keyboard":buttons}})

    except Exception as e:
        print(e)
        import traceback; traceback.print_exc()
    return "ok",200
