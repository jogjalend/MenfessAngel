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
    g = load_global(); ht = g.get("hashtag","")
    if not text: return ht.strip()
    if "jogjalend" in text.lower(): return text
    return text.strip() + ht
def get_real_channel_count():
    try:
        r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}", timeout=10).json()
        if r.get("ok"): return r["result"]
    except: pass
    return 659

def get_start_text(chat_id=0):
    on = is_threads_enabled(chat_id) if chat_id else False
    mode = "ON ✅" if on else "OFF ❌"
    return f"""Menfess Angel • o f f i c i a l

Your post will be published to:

Channel → @menfessangel
Threads → @jogjalend [optional]
X → @jogjalendpm [maintenance]

Threads mode: {mode}
Daily reset: 00:00 WIB
Limit: 5 texts & 5 media"""

def get_main_menu(chat_id):
    base = [
        [{"text":"👤 Profile","callback_data":"profil"}],
        [{"text":"📜 Rules","callback_data":"menu_rules"}, {"text":"📝 Post Menfess","callback_data":"menu_post"}],
        [{"text":"🧵 Threads Setting","callback_data":"menu_threads"}],
        [{"text":"📊 Stats","callback_data":"menu_stats"}, {"text":"ℹ️ Help","callback_data":"menu_help"}]
    ]
    if is_admin(chat_id):
        base.insert(3, [{"text":"👑 ADMIN PANEL PRO","callback_data":"admin_panel"}])
    return {"inline_keyboard": base}

def safe_send(chat_id, msg_id, text, reply_markup):
    try:
        r = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":text,"reply_markup":reply_markup}, timeout=10).json()
        if r.get("ok"): return True
    except: pass
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id}, timeout=5)
    except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text,"reply_markup":reply_markup}, timeout=10)
    return True

def make_avatar_bytes(name):
    try:
        initial = "J"
        img = Image.new('RGB', (800, 800), color=(29, 155, 240))
        draw = ImageDraw.Draw(img); draw.ellipse((100, 100, 700, 700), fill=(255,255,255))
        try: font = ImageFont.truetype("DejaVuSans-Bold.ttf", 350)
        except: font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), initial, font=font); w = bbox[2]-bbox[0]; h = bbox[3]-bbox[1]
        draw.text(((800-w)/2, (800-h)/2 - 20), initial, fill=(29,155,240), font=font)
        buf = io.BytesIO(); img.save(buf, format='JPEG', quality=90); buf.seek(0); return buf.getvalue()
    except: return None

def send_profile_with_photo(chat_id, msg_id, user_first):
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
    except: pass
    g = load_global(); quotas = load_quota(); key = get_today_key(chat_id); q = quotas.get(key, {"text":0,"media":0}); on = is_threads_enabled(chat_id); members = load_members(); info = members.get(str(chat_id), {})
    caption = f"My Profile\n______________________________________\n\nName: {info.get('name', 'Kamu')}\nID: {chat_id}\nUsername: @{info.get('username','-')}\n\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}\nThreads: {'ON ✅' if on else 'OFF ❌'}"
    kb = {"inline_keyboard": [[{"text": f"Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
    photo_bytes = make_avatar_bytes("J")
    if photo_bytes:
        files = {"photo": ("profile.jpg", photo_bytes, "image/jpeg")}
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":chat_id,"caption":caption,"reply_markup":json.dumps(kb)}, files=files, timeout=20)
    else: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":kb})

@app.route("/", methods=['GET','POST'])
@app.route("/api/index", methods=['GET','POST'])
@app.route("/api/index.py", methods=['GET','POST'])
def handler():
    if request.method == 'GET':
        return f"Bot V48.4 UI Official Fixed - {get_real_channel_count()} LIVE - OK",200
    try:
        data = request.get_json()
        if not data: return "ok",200
        if "callback_query" in data:
            cq = data["callback_query"]; cb_data = cq["data"]; chat_id = cq["message"]["chat"]["id"]; msg_id = cq["message"]["message_id"]
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})
            if cb_data in ["menu_main", "back_main", "back"]:
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id}, timeout=5)
                except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)})
                return "ok",200
            if cb_data in ["profil","toggle_threads"]:
                if cb_data == "toggle_threads": set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                send_profile_with_photo(chat_id, msg_id, "Kamu"); return "ok",200
            if cb_data == "menu_threads":
                on = is_threads_enabled(chat_id)
                txt = f"🧵 Threads Setting\n______________________________________\n\nStatus: {'ON ✅' if on else 'OFF ❌'}\n\nJika ON, menfess juga dipost ke Threads (optional)"
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
                safe_send(chat_id, msg_id, txt, kb); return "ok",200
            if cb_data == "menu_rules":
                txt = "📜 Rules\n______________________________________\n\n1. No Spam\n2. No SARA\n3. No Doxxing\n4. No Promosi Ilegal\n5. No Porn"
                kb = {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
                safe_send(chat_id, msg_id, txt, kb); return "ok",200
            if cb_data == "menu_post":
                txt = "📝 Post Menfess\n______________________________________\n\nJust send text or photo!\n\nCaption auto tambah #jogjalend"
                kb = {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
                safe_send(chat_id, msg_id, txt, kb); return "ok",200
            if cb_data == "menu_help":
                txt = "ℹ️ Help\n______________________________________\n\n/start - Menu utama\nKirim text/photo - Post menfess\nQuota 5 text + 5 media per hari"
                kb = {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
                safe_send(chat_id, msg_id, txt, kb); return "ok",200
            if cb_data == "menu_stats":
                real = get_real_channel_count(); m = load_members(); b = load_blocked(); q = load_quota()
                total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt = f"📊 STATS\n______________________________________\n\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\nDate: {datetime.now(WIB).strftime('%d %B')}"
                kb = {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
                safe_send(chat_id, msg_id, txt, kb); return "ok",200
            if cb_data == "admin_panel":
                if not is_admin(chat_id): return "ok",200
                real = get_real_channel_count(); m = load_members(); b = load_blocked(); q = load_quota(); g = load_global()
                total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt = f"👑 ADMIN PANEL PRO\n______________________________________\n\nChannel Subs: {real} LIVE\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\n\nPilih menu:"
                kb = {"inline_keyboard": [
                    [{"text":"1. Real Count","callback_data":"admin_real_count"}],
                    [{"text":"2. All Users","callback_data":"admin_members"}],
                    [{"text":"3. Blocked List","callback_data":"admin_blocked"}],
                    [{"text":"4. Search User","callback_data":"admin_search"}],
                    [{"text":"5. Set Quota","callback_data":"admin_setquota"}],
                    [{"text":"6. Blok Username","callback_data":"admin_blockuser"}],
                    [{"text":"7. Broadcast","callback_data":"admin_broadcast"}],
                    [{"text":"8. Setting Welcome","callback_data":"admin_welcome"}],
                    [{"text":"⬅️ Back to Main","callback_data":"menu_main"}]
                ]}
                safe_send(chat_id, msg_id, txt, kb); return "ok",200
            g=load_global(); real=get_real_channel_count()
            back_admin = {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"admin_panel"}]]}
            if cb_data=="admin_real_count": txt=f"Real Count\n\n@{CHANNEL_USERNAME}: {real} subs LIVE"; safe_send(chat_id, msg_id, txt, back_admin); return "ok",200
            elif cb_data=="admin_members": m=load_members(); txt="All Users\n"+"\n".join([f"{v.get('name','-')} {k}" for k,v in list(m.items())[-20:]]) or "0 user"; safe_send(chat_id, msg_id, txt, back_admin); return "ok",200
            elif cb_data=="admin_blocked": b=load_blocked(); txt=f"Blocked {len(b)}\n"+"\n".join(b.keys()) or "Kosong"; safe_send(chat_id, msg_id, txt, back_admin); return "ok",200
            else: txt="Menu admin"; safe_send(chat_id, msg_id, txt, back_admin); return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]; chat_id = msg["chat"]["id"]; text = msg.get("text","")
        members = load_members()
        if str(chat_id) not in members:
            members[str(chat_id)] = {"username": msg["from"].get("username","-"), "name": "User", "joined": datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}
            save_members(members)
        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)}); return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota(); key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        g = load_global(); is_media = "photo" in msg; caption = add_hashtag(raw_caption)
        if is_media and quotas[key]["media"] >= g["limit_media"]:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached","reply_markup":{"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}}); return "ok",200
        if not is_media and quotas[key]["text"] >= g["limit_text"]:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached","reply_markup":{"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}}); return "ok",200
        if is_media:
            fid = msg["photo"][-1]["file_id"]; r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
            files = {"photo": ("menfess.jpg", fb, "image/jpeg")}
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30).json()
        else: res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}).json()
        if res.get("ok"):
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"✅ Menfess sent!","reply_markup":get_main_menu(chat_id)})
    except Exception as e: print(e)
    return "ok",200
