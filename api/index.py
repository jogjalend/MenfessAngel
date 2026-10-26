import os, io, json, requests
from flask import Flask, request
from PIL import Image
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"
HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
SETTINGS_FILE = "/tmp/settings.json"
BLOCKED_FILE = "/tmp/blocked.json"
MEMBERS_FILE = "/tmp/members.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
ADMIN_IDS = [8584319568]

# PRELOAD CACHE - ANTI DELAY
QUOTA_CACHE = {}
SETTINGS_CACHE = {}
BLOCKED_CACHE = {}
MEMBERS_CACHE = {}
LOGO_CACHE = None

for p in ["logo.png","api/logo.png"]:
    if os.path.exists(p):
        try: 
            LOGO_CACHE = Image.open(p).convert("RGBA")
            LOGO_CACHE.thumbnail((120, 120), Image.NEAREST) # preload kecil
            break
        except: pass

def load_json_fast(path, cache):
    if cache: return cache
    try:
        if os.path.exists(path):
            with open(path,"r") as f: return json.load(f)
    except: pass
    return {}

def save_json_fast(path, d):
    try:
        with open(path,"w") as f: json.dump(d,f)
    except: pass

def get_quota(): 
    global QUOTA_CACHE
    if not QUOTA_CACHE: QUOTA_CACHE = load_json_fast(QUOTA_FILE, {})
    return QUOTA_CACHE

def get_blocked():
    global BLOCKED_CACHE
    if not BLOCKED_CACHE: BLOCKED_CACHE = load_json_fast(BLOCKED_FILE, {})
    return BLOCKED_CACHE

def get_members():
    global MEMBERS_CACHE
    if not MEMBERS_CACHE: MEMBERS_CACHE = load_json_fast(MEMBERS_FILE, {})
    return MEMBERS_CACHE

def get_settings():
    global SETTINGS_CACHE
    if not SETTINGS_CACHE: SETTINGS_CACHE = load_json_fast(SETTINGS_FILE, {})
    return SETTINGS_CACHE

def is_admin(chat_id): return int(chat_id) in ADMIN_IDS
def is_threads_enabled(chat_id): return get_settings().get(str(chat_id),{}).get("threads", False)
def get_today_key(chat_id): return f"{chat_id}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(text):
    if not text: return HASHTAG.strip()
    if "#jogjalend" in text.lower(): return text
    return text.strip() + HASHTAG

def add_watermark_ultra_fast(b):
    if not LOGO_CACHE: return b
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        w,h = base.size
        # JANGAN RESIZE GEDE - ANTI DELAY
        base.paste(LOGO_CACHE, (w-LOGO_CACHE.width-20, h-LOGO_CACHE.height-20), LOGO_CACHE)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=75, optimize=False) # quality 75 = super cepet
        return out.getvalue()
    except: return b

def get_start_text(chat_id):
    on = is_threads_enabled(chat_id)
    mode = "ON ✅" if on else "OFF ❌"
    return f"𝗠𝗲𝗻𝗳𝗲𝘀𝘀 𝗔𝗻𝗴𝗲𝗹\n\nChannel → @menfessangel\nThreads → {mode}\nLimit: 5 text & 5 media"

def get_main_menu(chat_id):
    if is_admin(chat_id):
        return {"inline_keyboard": [[{"text":"👤 Profile","callback_data":"profil"}],[{"text":"👑 Admin","callback_data":"admin_panel"}],[{"text":"🧵 Threads","callback_data":"menu_threads"}]]}
    else:
        return {"inline_keyboard": [[{"text":"👤 Profile","callback_data":"profil"}],[{"text":"🧵 Threads Setting","callback_data":"menu_threads"}]]}

@app.route("/", methods=['GET'])
def home(): return "Bot V22 Anti Delay",200

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
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]}, timeout=2)

            if cb_data.startswith("delete_post_"):
                try:
                    target_msg_id = cb_data.replace("delete_post_","")
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":int(target_msg_id)}, timeout=3)
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"🗑️ Post dihapus"}, timeout=2)
                except: pass
                return "ok",200

            if cb_data == "toggle_threads":
                s = get_settings()
                cur = s.get(str(chat_id),{}).get("threads", False)
                if str(chat_id) not in s: s[str(chat_id)] = {}
                s[str(chat_id)]["threads"] = not cur
                save_json_fast(SETTINGS_FILE, s)
                SETTINGS_CACHE.clear()
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"Threads: {'ON ✅' if not cur else 'OFF ❌'}","reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"menu_main"}]]}}, timeout=2)
                return "ok",200

            if cb_data in ["menu_main","admin_panel","profil","menu_threads"]:
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)}, timeout=2)
                return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text","")

        # ANTI DELAY - CEK BLOKIR CEPET
        if str(chat_id) in get_blocked() and not is_admin(chat_id):
            return "ok",200

        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)}, timeout=3)
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        
        # CEK QUOTA CEPET
        quotas = get_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        if is_media and quotas[key]["media"] >= LIMIT_MEDIA:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"❌ Limit media habis"}, timeout=2)
            return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"❌ Limit text habis"}, timeout=2)
            return "ok",200

        caption = add_hashtag(raw_caption)

        # POST LANGSUNG - GAK USAH SAVE DULU - INI KUNCI ANTI DELAY
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}", timeout=3).json()
            fp = r["result"]["file_path"]
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=5).content
            # WATERMARK CEPET - KALO MAU SUPER CEPET COMMENT LINE INI
            fb = add_watermark_ultra_fast(fb)
            files = {"photo": ("m.jpg", fb, "image/jpeg")}
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=6).json()
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}, timeout=4).json()

        if res.get("ok"):
            posted_msg_id = res["result"]["message_id"]
            quotas[key]["media" if is_media else "text"] += 1
            # SAVE BELAKANGAN - BIAR USER GAK NUNGGU
            save_json_fast(QUOTA_FILE, quotas)
            
            used_text = quotas[key]["text"]
            used_media = quotas[key]["media"]
            threads_on = is_threads_enabled(chat_id)
            
            if threads_on:
                success_text = f"Menfess terkirim! ✅\n\nSisa kuota :\nText : {used_text}/{LIMIT_TEXT}\nMedia : {used_media}/{LIMIT_MEDIA}\n\n✅ Posted to Telegram & Threads (Threads ON),\nJoin Channel : @{CHANNEL_USERNAME}\nThreads : @jogjalend"
            else:
                success_text = f"Menfess terkirim! ✅\n\nSisa kuota :\nText : {used_text}/{LIMIT_TEXT}\nMedia : {used_media}/{LIMIT_MEDIA}\n\n✅ Posted to Telegram only (Threads OFF),\nJoin Channel : @{CHANNEL_USERNAME}"
            
            telegram_link = f"https://t.me/{CHANNEL_USERNAME}/{posted_msg_id}"
            buttons = {"inline_keyboard": [[{"text":"➡️ See Telegram","url": telegram_link}],[{"text":"🗑️ Delete Post","callback_data": f"delete_post_{posted_msg_id}"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":success_text,"reply_markup":buttons}, timeout=3)

    except Exception as e:
        print(f"ERR {e}")
    return "ok",200
