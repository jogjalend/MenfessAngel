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
USERS_FILE = "/tmp/users.json"
BANNED_FILE = "/tmp/banned.json"
PENDING_FILE = "/tmp/admin_pending.json"

LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()

# === SUPER ADMIN - CUMA LU ===
ADMIN_USERNAMES = ["jogja_lend"]
ADMIN_IDS = [8584319568] 

BAD_WORDS = ["kontol","memek","ngentot","anjing","babi","tolol","goblok"]
LOGO_CACHE = None
for p in ["logo.png","api/logo.png"]:
    if os.path.exists(p):
        try: LOGO_CACHE = Image.open(p).convert("RGBA"); break
        except: pass

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path,"r") as f: return json.load(f)
    except: pass
    return default
def save_json(path, data):
    try:
        with open(path,"w") as f: json.dump(data,f)
    except: pass

def load_quota(): return load_json(QUOTA_FILE, {})
def save_quota(d): save_json(QUOTA_FILE, d)
def load_settings(): return load_json(SETTINGS_FILE, {})
def save_settings(d): save_json(SETTINGS_FILE, d)
def load_users(): return load_json(USERS_FILE, {})
def save_users(d): save_json(USERS_FILE, d)
def load_banned(): return load_json(BANNED_FILE, [])
def save_banned(d): save_json(BANNED_FILE, d)
def load_pending(): return load_json(PENDING_FILE, {})
def save_pending(d): save_json(PENDING_FILE, d)

def is_admin(chat_id, username):
    uname = (username or "").lower().replace("@","")
    if uname in ADMIN_USERNAMES: return True
    try:
        if int(chat_id) in ADMIN_IDS: return True
    except: pass
    if str(chat_id) in [str(x) for x in ADMIN_IDS]: return True
    return False

def save_user_info(chat_id, username, first_name):
    users = load_users()
    users[str(chat_id)] = {"username": username or "", "first_name": first_name or "", "last_seen": datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}
    save_users(users)

def is_banned(chat_id): return str(chat_id) in load_banned()
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
    for w in BAD_WORDS: c = re.sub(re.escape(w), "***", c, flags=re.IGNORECASE)
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
        if any(w in text.lower() for w in BAD_WORDS): text = censor_text(text)
        r1 = SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data={"media_type":"TEXT","text":text,"access_token":THREADS_TOKEN}, timeout=15)
        if not r1.ok: return None
        cid = r1.json().get("id")
        for i in range(6):
            time.sleep(5)
            rs = SESSION.get(f"https://graph.threads.net/v1.0/{cid}", params={"fields":"status","access_token":THREADS_TOKEN}, timeout=15)
            if rs.ok and rs.json().get("status") == "FINISHED": break
        r2 = SESSION.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish", data={"creation_id":cid,"access_token":THREADS_TOKEN}, timeout=15)
        if r2.ok: return r2.json().get("id")
    except: pass
    return None

def get_start_menu(chat_id=0, username=""):
    kb = [
        [{"text":"📋 Menu","callback_data":"menu_main"}],
        [{"text":"👤 Profile","callback_data":"profil"}, {"text":"🧵 Threads","callback_data":"menu_threads"}],
        [{"text":"📜 Rules","callback_data":"menu_rules"}]
    ]
    if is_admin(chat_id, username):
        kb.append([{"text":"⚙️ Admin Panel","callback_data":"menu_admin"}])
    return {"inline_keyboard": kb}

def get_main_menu(chat_id=0, username=""):
    kb = [
        [{"text":"📝 Post Menfess","callback_data":"menu_post"}],
        [{"text":"👤 Profile","callback_data":"profil"}, {"text":"🧵 Threads","callback_data":"menu_threads"}],
        [{"text":"📊 Stats","callback_data":"menu_stats"}],
        [{"text":"📜 Rules","callback_data":"menu_rules"}, {"text":"ℹ️ Help","callback_data":"menu_help"}],
        [{"text":"📢 Channel","url":"https://t.me/menfessangel"}],
        [{"text":"🔙 Back","callback_data":"back_to_start"}]
    ]
    if is_admin(chat_id, username):
        kb.insert(0, [{"text":"⚙️ Admin Panel - Boss","callback_data":"menu_admin"}])
    return {"inline_keyboard": kb}

@app.route("/", methods=['GET'])
def home(): return "Bot Active - Admin 8584319568",200

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
            username = cq["from"].get("username") or ""
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})

            if cb_data == "menu_admin":
                if not is_admin(chat_id, username): return "ok",200
                txt = "⚙️ ADMIN PANEL\n\nBoss @jogja_lend (8584319568)\n\nSelect action:"
                kb = {"inline_keyboard": [[{"text":"👥 List Users","callback_data":"admin_list_users"}],[{"text":"🚫 Banned Users","callback_data":"admin_list_banned"}],[{"text":"🗑️ Delete Post by ID","callback_data":"admin_ask_delete"}],[{"text":"🔙 Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            elif cb_data == "admin_list_users":
                users = load_users()
                txt = f"👥 TOTAL USERS: {len(users)}\n\nLatest 20 users:\n" if users else "No users yet"
                if users:
                    for uid, info in list(users.items())[-20:]:
                        txt += f"{uid} | @{info['username']} | {info['first_name']}\n"
                kb2 = []
                for uid in list(users.keys())[-10:]:
                    kb2.append([{"text":f"ID {uid} - @{users[uid]['username']}","callback_data":f"admin_view_{uid}"}])
                kb2.append([{"text":"🔙 Back","callback_data":"menu_admin"}])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":kb2}})
                return "ok",200
            elif cb_data.startswith("admin_view_"):
                uid = cb_data.replace("admin_view_","")
                info = load_users().get(uid, {})
                is_b = uid in load_banned()
                txt = f"👤 USER DETAIL\nID: {uid}\nUsername: @{info.get('username')}\nName: {info.get('first_name')}\nLast Seen: {info.get('last_seen')}\nStatus: {'BANNED 🚫' if is_b else 'Active ✅'}"
                kb = {"inline_keyboard": [[{"text":"🚫 Ban" if not is_b else "✅ Unban","callback_data":f"admin_ban_{uid}" if not is_b else f"admin_unban_{uid}"}],[{"text":"🔙 Back","callback_data":"admin_list_users"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            elif cb_data.startswith("admin_ban_"):
                uid = cb_data.replace("admin_ban_","")
                banned = load_banned()
                if uid not in banned: banned.append(uid)
                save_banned(banned)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"User {uid} BANNED 🚫","reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"admin_list_users"}]]}})
                return "ok",200
            elif cb_data.startswith("admin_unban_"):
                uid = cb_data.replace("admin_unban_","")
                save_banned([b for b in load_banned() if str(b) != str(uid)])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"User {uid} UNBANNED ✅","reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"admin_list_users"}]]}})
                return "ok",200
            elif cb_data == "admin_list_banned":
                banned = load_banned()
                txt = f"🚫 BANNED: {len(banned)}\n\n" + "\n".join(banned) if banned else "No banned users"
                kb = {"inline_keyboard": [[{"text":f"Unban {uid}","callback_data":f"admin_unban_{uid}"}] for uid in banned[:10]] + [[{"text":"🔙 Back","callback_data":"menu_admin"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            elif cb_data == "admin_ask_delete":
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"🗑️ DELETE POST\nSend: /del <message_id>","reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"menu_admin"}]]}})
                return "ok",200
            elif cb_data.startswith("admin_post_"):
                choice = cb_data.replace("admin_post_","")
                p = load_pending().get(str(chat_id))
                if not p: return "ok",200
                caption = p["caption"]
                fb_content = None
                if p.get("is_media") and p.get("file_id"):
                    try:
                        r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={p['file_id']}").json()
                        fp = r["result"]["file_path"]
                        fb_content = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
                        fb_content = add_watermark_fast(fb_content)
                    except: pass
                tg_mid = None
                th_id = None
                if choice in ["telegram","both"]:
                    if p.get("is_media") and fb_content:
                        res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":("a.jpg", fb_content, "image/jpeg")})
                    else:
                        res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
                    if res.ok: tg_mid = res.json()["result"]["message_id"]
                if choice in ["threads","both"]:
                    th_id = post_to_threads(caption)
                pending = load_pending(); pending.pop(str(chat_id), None); save_pending(pending)
                txt = f"✅ Posted to {choice.upper()}\n"
                if tg_mid: txt += f"Telegram: https://t.me/{CHANNEL_USERNAME}/{tg_mid}\n"
                if th_id: txt += "Threads: Success ✅"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt})
                return "ok",200

            if cb_data == "menu_main":
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"📋 MAIN MENU\nWelcome, @{username}","reply_markup":get_main_menu(chat_id, username)})
                return "ok",200
            elif cb_data == "back_to_start":
                on = is_threads_enabled(chat_id)
                cap = f"🚀 Welcome, @{username}!\nYour post will be published to @{CHANNEL_USERNAME}\nThreads: {'ON ✅' if on else 'OFF ❌ (Default: Telegram only)'}\n\nDaily Limit: 5 texts & 5 media. Reset at 00:00 WIB."
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":cap,"reply_markup":get_start_menu(chat_id, username)})
                return "ok",200
            elif cb_data in ["menu_post","menu_stats","menu_rules","menu_help"]:
                texts = {"menu_post": "📝 POST MENFESS\nSend text or photo directly.","menu_stats": f"📊 STATS: {load_quota().get(get_today_key(chat_id), {'text':0,'media':0})}","menu_rules": "📜 RULES\n1. No Spam\n2. No SARA\n3. No Doxxing\n4. Stay Professional","menu_help": "ℹ️ HELP\n/start - menu"}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":texts[cb_data],"reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"menu_main"}]]}})
                return "ok",200
            elif cb_data in ["profil","menu_threads","toggle_threads"]:
                if cb_data == "toggle_threads":
                    set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                q = load_quota().get(get_today_key(chat_id), {"text":0,"media":0})
                on = is_threads_enabled(chat_id)
                txt = f"👤 PROFILE - @{username}\nID: {chat_id}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}\nThreads: {'ON ✅' if on else 'OFF ❌'}"
                kb = {"inline_keyboard": [[{"text": f"🧵 Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"🔙 Back to Menu","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            elif cb_data.startswith("delete|"):
                _, ch_msg_id = cb_data.split("|")
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":ch_msg_id})
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Deleted! 🗑️"})
                return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        username = msg["from"].get("username") or ""
        first_name = msg["from"].get("first_name") or ""
        tag = f"@{username}" if username else first_name
        save_user_info(chat_id, username, first_name)

        if is_banned(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"⛔ You are banned."})
            return "ok",200

        if "text" in msg and msg["text"].startswith("/del"):
            if not is_admin(chat_id, username): return "ok",200
            try:
                mid = msg["text"].split()[1]
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":mid})
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Post {mid} deleted ✅"})
            except: pass
            return "ok",200

        if "text" in msg and msg["text"].startswith(("/start","/menu")):
            on = is_threads_enabled(chat_id)
            caption = f"🚀 Welcome, {tag}!\nYour submission will be published to @{CHANNEL_USERNAME}\nThreads: {'ON ✅' if on else 'OFF ❌ (Default: Telegram only)'}\n\nDaily Limit: 5 texts & 5 media. Reset at 00:00 WIB."
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":get_start_menu(chat_id, username)})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)

        if not is_admin(chat_id, username):
            if is_media and quotas[key]["media"] >= LIMIT_MEDIA: return "ok",200
            if not is_media and quotas[key]["text"] >= LIMIT_TEXT: return "ok",200

        if is_admin(chat_id, username):
            pending = load_pending()
            pending[str(chat_id)] = {"caption": caption, "is_media": is_media, "file_id": msg["photo"][-1]["file_id"] if is_media else None}
            save_pending(pending)
            txt = f"⚙️ ADMIN POST - Where to post?\n\n{caption[:300]}"
            kb = {"inline_keyboard": [[{"text":"📢 Telegram Only","callback_data":"admin_post_telegram"}],[{"text":"🧵 Threads Only","callback_data":"admin_post_threads"}],[{"text":"📢+🧵 Both","callback_data":"admin_post_both"}],[{"text":"❌ Cancel","callback_data":"menu_main"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt,"reply_markup":kb})
            return "ok",200

        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark_fast(fb)
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":("a.jpg", fb, "image/jpeg")})
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption})
        cmid = res.json()["result"]["message_id"] if res.ok else "0"
        curl = f"https://t.me/{CHANNEL_USERNAME}/{cmid}"
        th_id = post_to_threads(caption) if is_threads_enabled(chat_id) else None
        if is_media: quotas[key]["media"] += 1
        else: quotas[key]["text"] += 1
        save_quota(quotas)
        buttons = [[{"text":"➡️ View Post","url":curl}]]
        if th_id: buttons.append([{"text":"🧵 View on Threads","url":f"https://www.threads.net/@{CHANNEL_USERNAME}"}])
        buttons.append([{"text":"📋 Menu","callback_data":"menu_main"}, {"text":"🗑️ Delete","callback_data":f"delete|{cmid}"}])
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Posted! Quota: {quotas[key]}","reply_markup":{"inline_keyboard":buttons}})
    except Exception as e:
        print(e)
    return "ok",200
