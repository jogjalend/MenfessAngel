import os, io, json, requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta
app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"
QUOTA_FILE = "/tmp/quota.json"
SETTINGS_FILE = "/tmp/settings.json"
BLOCKED_FILE = "/tmp/blocked.json"
MEMBERS_FILE = "/tmp/members.json"
GLOBAL_FILE = "/tmp/global.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
ADMIN_IDS = [8584319568]

def load_json(path, default=None):
    try:
        if os.path.exists(path):
            with open(path,"r") as f: return json.load(f)
    except: pass
    return default if default is not None else {}
def save_json(path, d):
    try:
        with open(path,"w") as f: json.dump(d,f)
    except: pass
def load_quota(): return load_json(QUOTA_FILE, {})
def save_quota(d): save_json(QUOTA_FILE, d)
def load_settings(): return load_json(SETTINGS_FILE, {})
def save_settings(d): save_json(SETTINGS_FILE, d)
def load_blocked(): return load_json(BLOCKED_FILE, {})
def save_blocked(d): save_json(BLOCKED_FILE, d)
def load_members(): return load_json(MEMBERS_FILE, {})
def save_members(d): save_json(MEMBERS_FILE, d)
def load_global():
    g = load_json(GLOBAL_FILE, {})
    if not g: g = {"hashtag":"\n\n#jogjalend","limit_text":5,"limit_media":5}
    return g
def save_global(d): save_json(GLOBAL_FILE, d)

def is_admin(chat_id): return int(chat_id) in ADMIN_IDS
def is_blocked(chat_id): return str(chat_id) in load_blocked()
def is_threads_enabled(chat_id): return load_settings().get(str(chat_id),{}).get("threads", False)
def set_threads_enabled(chat_id, v):
    s = load_settings()
    if str(chat_id) not in s: s[str(chat_id)] = {}
    s[str(chat_id)]["threads"] = v
    save_settings(s)
def get_today_key(chat_id): return f"{chat_id}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(text):
    g = load_global()
    ht = g.get("hashtag","")
    if not text: return ht.strip()
    if "jogjalend" in text.lower(): return text
    return text.strip() + ht

def get_real_channel_count():
    try:
        r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}", timeout=10).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 0

def get_start_text(first_name="Jogja Lend"):
    return f"Hi {first_name}!\nPromote your account here!\n______________________________________\n\nPublish to:\n• Channel → @menfessangel\n• Threads → @jogjalend [optional]\n• X → @jogjalendpm [maintenance]\n\nTap Post to start!"

def get_main_menu(chat_id):
    if is_admin(chat_id):
        return {"inline_keyboard": [
            [{"text":"My Profile","callback_data":"profil"}],
            [{"text":"Rules","callback_data":"menu_rules"}, {"text":"Post","callback_data":"menu_post"}],
            [{"text":"Threads Setting","callback_data":"menu_threads"}],
            [{"text":"Admin Panel","callback_data":"admin_panel"}],
            [{"text":"Stats","callback_data":"menu_stats"}, {"text":"Help","callback_data":"menu_help"}]
        ]}
    else:
        return {"inline_keyboard": [
            [{"text":"My Profile","callback_data":"profil"}],
            [{"text":"Rules","callback_data":"menu_rules"}, {"text":"Post","callback_data":"menu_post"}],
            [{"text":"Threads Setting","callback_data":"menu_threads"}],
            [{"text":"Stats","callback_data":"menu_stats"}, {"text":"Help","callback_data":"menu_help"}]
        ]}

def delete_and_send_menu(chat_id, msg_id, first_name):
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id}, timeout=5)
    except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(first_name),"reply_markup":get_main_menu(chat_id)})

def make_avatar_bytes(name):
    try:
        initial = (name or "J")[0].upper()
        img = Image.new('RGB', (800, 800), color=(29, 155, 240))
        draw = ImageDraw.Draw(img)
        # bulat putih tengah
        draw.ellipse((100, 100, 700, 700), fill=(255,255,255))
        # huruf
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 350)
        except:
            font = ImageFont.load_default()
        # center text
        bbox = draw.textbbox((0,0), initial, font=font)
        w = bbox[2]-bbox[0]
        h = bbox[3]-bbox[1]
        draw.text(((800-w)/2, (800-h)/2 - 20), initial, fill=(29,155,240), font=font)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=90)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        print(f"avatar err {e}")
        return None

def send_profile_with_photo(chat_id, msg_id, user_first):
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
    except: pass
    g = load_global()
    quotas = load_quota()
    key = get_today_key(chat_id)
    q = quotas.get(key, {"text":0,"media":0})
    on = is_threads_enabled(chat_id)
    members = load_members()
    info = members.get(str(chat_id), {})
    real = get_real_channel_count()
    caption = f"My Profile\n______________________________________\n\nName: {info.get('name', user_first)}\nID: {chat_id}\nUsername: @{info.get('username','-')}\n\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}\nThreads: {'ON' if on else 'OFF'}"
    kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}
    
    photo_bytes = None
    # 1. coba foto asli Telegram
    try:
        r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos?user_id={chat_id}&limit=1", timeout=10).json()
        if r.get("ok") and r["result"]["total_count"] > 0:
            file_id = r["result"]["photos"][0][-1]["file_id"]
            rf = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            if rf.get("ok"):
                photo_bytes = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{rf['result']['file_path']}", timeout=15).content
    except Exception as e:
        print(f"get photo fail {e}")

    # 2. fallback avatar
    if not photo_bytes:
        photo_bytes = make_avatar_bytes(user_first or info.get('name','J'))

    if photo_bytes:
        files = {"photo": ("profile.jpg", photo_bytes, "image/jpeg")}
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":chat_id,"caption":caption,"reply_markup":json.dumps(kb)}, files=files, timeout=20)
    else:
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":kb})

@app.route("/", methods=['GET'])
def home(): return "Bot V48.1 Profile Photo Fix",200
@app.route("/", methods=['POST'])
@app.route("/api/index.py", methods=['POST'])
def handler():
    try:
        data = request.get_json()
        if not data: return "ok",200
        if "callback_query" in data:
            cq = data["callback_query"]; cb_data = cq["data"]; chat_id = cq["message"]["chat"]["id"]; msg_id = cq["message"]["message_id"]; user_first = cq["from"].get("first_name","Jogja Lend")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
            if cb_data in ["menu_main"]:
                delete_and_send_menu(chat_id, msg_id, user_first); return "ok",200
            if cb_data in ["profil","toggle_threads","menu_threads"]:
                if cb_data == "toggle_threads": set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                send_profile_with_photo(chat_id, msg_id, user_first); return "ok",200
            if cb_data == "menu_stats":
                real = get_real_channel_count(); m = load_members(); b = load_blocked(); q = load_quota()
                total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt = f"STATS\n______________________________________\n\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\nDate: {datetime.now(WIB).strftime('%Y-%m-%d')}"
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}})
                return "ok",200
            if cb_data == "admin_panel":
                if not is_admin(chat_id): return "ok",200
                real = get_real_channel_count(); m = load_members(); b = load_blocked(); q = load_quota(); g = load_global()
                total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt = f"ADMIN PANEL\n______________________________________\n\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\nQuota: {g['limit_text']}/{g['limit_media']}\nHashtag: {g['hashtag'].strip()}"
                kb = {"inline_keyboard": [[{"text":"Real Count","callback_data":"admin_real_count"}, {"text":"All Users","callback_data":"admin_members"}],[{"text":"Blocked List","callback_data":"admin_blocked"}],[{"text":"Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb}); return "ok",200
            txts = {"menu_post":"Post Menfess\nJust send text or photo!","menu_rules":"Rules:\n1. No Spam\n2. No SARA\n3. No Doxxing","menu_help":"Help: /start","admin_real_count":f"Channel @{CHANNEL_USERNAME}: {get_real_channel_count()} subs","admin_members":"All Users - use /search ID","admin_blocked":"Blocked List - use /search"}
            txt = txts.get(cb_data, "Menu")
            try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}})
            except: delete_and_send_menu(chat_id, msg_id, user_first)
            return "ok",200
        if "message" not in data: return "ok",200
        msg = data["message"]; chat_id = msg["chat"]["id"]; text = msg.get("text","")
        members = load_members()
        if str(chat_id) not in members:
            members[str(chat_id)] = {"username": msg["from"].get("username","-"), "name": msg["from"].get("first_name","-"), "joined": datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}
            save_members(members)
        if is_blocked(chat_id) and not is_admin(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"You are blocked"}); return "ok",200
        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(msg["from"].get("first_name","Jogja Lend")),"reply_markup":get_main_menu(chat_id)}); return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota(); key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        g = load_global()
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)
        if is_media and quotas[key]["media"] >= g["limit_media"]:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached","reply_markup":{"inline_keyboard":[[{"text":"Back to Menu","callback_data":"menu_main"}]]}}); return "ok",200
        if not is_media and quotas[key]["text"] >= g["limit_text"]:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached","reply_markup":{"inline_keyboard":[[{"text":"Back to Menu","callback_data":"menu_main"}]]}}); return "ok",200
        if is_media:
            fid = msg["photo"][-1]["file_id"]; r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
            files = {"photo": ("menfess.jpg", fb, "image/jpeg")}
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30).json()
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}).json()
        if res.get("ok"):
            pid = res["result"]["message_id"]
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas)
            tl = f"https://t.me/{CHANNEL_USERNAME}/{pid}"
            btn = {"inline_keyboard": [[{"text":"See on channel","url":tl}],[{"text":"Delete","callback_data":f"delete_post_{pid}"}],[{"text":"Back to Menu","callback_data":"menu_main"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Menfess sent! Quota {quotas[key]['text']}/{g['limit_text']} {quotas[key]['media']}/{g['limit_media']}","reply_markup":btn})
    except Exception as e: print(e)
    return "ok",200
