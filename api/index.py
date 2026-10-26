import os, io, json, requests
from flask import Flask, request
from PIL import Image
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
SETTINGS_FILE = "/tmp/settings.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()

# ADMIN KHUSUS - ID LU UDAH DI SET
ADMIN_IDS = [8584319568]  # @jogja_lend

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
def is_admin(chat_id): return int(chat_id) in ADMIN_IDS
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

def get_start_text(chat_id):
    on = is_threads_enabled(chat_id)
    mode = "ON ✅" if on else "OFF ❌"
    title = "𝗠𝗲𝗻𝗳𝗲𝘀𝘀 𝗔𝗻𝗴𝗲𝗹 • 𝗼 𝗳 𝗳 𝗶 𝗰 𝗶 𝗮 𝗹"
    return (
        f"{title}\n\n"
        f"Your post will be published to:\n\n"
        f"  Channel → @menfessangel\n"
        f"  Threads → @jogjalend [optional]\n"
        f"  X → @jogjalendpm [maintenance]\n\n"
        f"Threads mode: {mode}\n"
        f"Daily reset: 00:00 WIB\n"
        f"Limit: 5 texts & 5 media"
    )

def get_main_menu(chat_id):
    if is_admin(chat_id):
        return {"inline_keyboard": [
            [{"text":"👤 Profile","callback_data":"profil"}],
            [{"text":"📜 Rules","callback_data":"menu_rules"}, {"text":"📝 Post Menfess","callback_data":"menu_post"}],
            [{"text":"🧵 Threads Setting","callback_data":"menu_threads"}],
            [{"text":"👑 Admin","callback_data":"admin_panel"}, {"text":"ℹ️ Help","callback_data":"menu_help"}]
        ]}
    else:
        return {"inline_keyboard": [
            [{"text":"👤 Profile","callback_data":"profil"}],
            [{"text":"📜 Rules","callback_data":"menu_rules"}, {"text":"📝 Post Menfess","callback_data":"menu_post"}],
            [{"text":"🧵 Threads Setting","callback_data":"menu_threads"}],
            [{"text":"📊 Stats","callback_data":"menu_stats"}, {"text":"ℹ️ Help","callback_data":"menu_help"}]
        ]}

@app.route("/", methods=['GET'])
def home(): return "Bot V16.1 Admin 8584319568",200

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
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)})
                return "ok",200

            elif cb_data == "admin_panel":
                if not is_admin(chat_id): return "ok",200
                q = load_quota()
                txt = f"👑 ADMIN PANEL\nKhusus @jogja_lend\nID: {chat_id}\n\nRecords: {len(q)}"
                kb = {"inline_keyboard": [
                    [{"text":"🔄 Reset Quota","callback_data":"admin_reset"}, {"text":"📊 Global Stats","callback_data":"admin_stats"}],
                    [{"text":"🔙 Back","callback_data":"menu_main"}]
                ]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200

            elif cb_data == "admin_reset" and is_admin(chat_id):
                save_quota({})
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"✅ Quota reset!","reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"admin_panel"}]]}})
                return "ok",200

            elif cb_data in ["menu_post","menu_stats","menu_rules","menu_help","admin_stats"]:
                texts = {
                    "menu_post": "📝 POST MENFESS\nKirim text / foto langsung.",
                    "menu_stats": f"📊 STATS\n{load_quota().get(get_today_key(chat_id), {'text':0,'media':0})}",
                    "admin_stats": f"📊 GLOBAL\n{str(load_quota())[:900]}",
                    "menu_rules": "📜 RULES\n1. No Spam\n2. No SARA\n3. No Doxxing",
                    "menu_help": "ℹ️ HELP\n/start untuk menu"
                }
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":texts.get(cb_data,"Menu"),"reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"menu_main"}]]}})
                return "ok",200

            elif cb_data in ["profil","menu_threads","toggle_threads"]:
                if cb_data == "toggle_threads":
                    set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                q = load_quota().get(get_today_key(chat_id), {"text":0,"media":0})
                on = is_threads_enabled(chat_id)
                txt = f"👤 PROFILE\nID: {chat_id}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}\nThreads: {'ON ✅' if on else 'OFF ❌'}"
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"🔙 Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg and msg["text"].startswith(("/start","/menu","/admin")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)
        if is_media and quotas[key]["media"] >= LIMIT_MEDIA: return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT: return "ok",200
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark_fast(fb)
            files = {"photo": ("menfess.jpg", fb, "image/jpeg")}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30)
        else:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)
    except Exception as e:
        print(e)
    return "ok",200
