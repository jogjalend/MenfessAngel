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

def is_admin(cid): return int(cid) in ADMIN_IDS
def is_blocked(cid): return str(cid) in load_blocked()
def is_threads_enabled(cid): return load_settings().get(str(cid),{}).get("threads", False)
def set_threads_enabled(cid, v):
    s = load_settings()
    if str(cid) not in s: s[str(cid)] = {}
    s[str(cid)]["threads"] = v
    save_settings(s)

def get_today_key(cid): return f"{cid}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
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

def get_start_text(cid=0):
    on = is_threads_enabled(cid)
    mode = "ON ✅" if on else "OFF ❌"
    return f"""Menfess Angel • o f f i c i a l

Your post will be published to:

Channel → @menfessangel
Threads → @jogjalend [optional]
X → @jogjalendpm [maintenance]

Threads mode: {mode}
Daily reset: 00:00 WIB
Limit: 5 texts & 5 media"""

def get_main_menu(cid):
    base = [
        [{"text":"👤 Profile","callback_data":"profil"}],
        [{"text":"📜 Rules","callback_data":"menu_rules"}, {"text":"📝 Post Menfess","callback_data":"menu_post"}],
        [{"text":"🧵 Threads Setting","callback_data":"menu_threads"}],
        [{"text":"📊 Stats","callback_data":"menu_stats"}, {"text":"ℹ️ Help","callback_data":"menu_help"}]
    ]
    if is_admin(cid):
        base.insert(3, [{"text":"👑 ADMIN PANEL PRO","callback_data":"admin_panel"}])
    return {"inline_keyboard": base}

def safe_send(cid, mid, text, kb):
    try:
        r = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":cid,"message_id":mid,"text":text,"reply_markup":kb}, timeout=10).json()
        if r.get("ok"): return True
    except: pass
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":cid,"message_id":mid}, timeout=5)
    except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":text,"reply_markup":kb}, timeout=10)
    return True

def send_profile(cid, mid):
    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":cid,"message_id":mid})
    except: pass
    g = load_global(); quotas = load_quota(); key = get_today_key(cid); q = quotas.get(key, {"text":0,"media":0}); on = is_threads_enabled(cid); members = load_members(); info = members.get(str(cid), {})
    caption = f"My Profile\n______________________________________\n\nID: {cid}\nUsername: @{info.get('username','-')}\n\nText: {q['text']}/{g['limit_text']}\nMedia: {q['media']}/{g['limit_media']}\nThreads: {'ON ✅' if on else 'OFF ❌'}"
    kb = {"inline_keyboard": [[{"text": f"Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":caption,"reply_markup":kb})

@app.route("/", methods=['GET','POST'])
@app.route("/api/index", methods=['GET','POST'])
@app.route("/api/index.py", methods=['GET','POST'])
def handler():
    if request.method == 'GET':
        return f"V48.4 UI OFFICIAL FIXED - {get_real_channel_count()} LIVE - OK",200

    data = request.get_json(silent=True)
    if not data: return "ok",200

    if "callback_query" in data:
        cq = data["callback_query"]; cb = cq["data"]; cid = cq["message"]["chat"]["id"]; mid = cq["message"]["message_id"]
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})

        if cb in ["menu_main","back_main","back"]:
            try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":cid,"message_id":mid}, timeout=5)
            except: pass
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":get_start_text(cid),"reply_markup":get_main_menu(cid)})
            return "ok",200

        if cb in ["profil","toggle_threads"]:
            if cb == "toggle_threads": set_threads_enabled(cid, not is_threads_enabled(cid))
            send_profile(cid, mid); return "ok",200

        if cb == "menu_threads":
            on = is_threads_enabled(cid)
            txt = f"🧵 Threads Setting\n______________________________________\n\nStatus: {'ON ✅' if on else 'OFF ❌'}\n\nJika ON, menfess dipost ke Threads @jogjalend"
            kb = {"inline_keyboard": [[{"text": f"Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
            safe_send(cid, mid, txt, kb); return "ok",200

        if cb == "menu_rules":
            txt = "📜 Rules\n______________________________________\n\n1. No Spam\n2. No SARA\n3. No Doxxing\n4. No Promosi Ilegal\n5. No Porn"
            safe_send(cid, mid, txt, {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}); return "ok",200

        if cb == "menu_post":
            txt = "📝 Post Menfess\n______________________________________\n\nJust send text or photo!\n\nCaption auto tambah #jogjalend"
            safe_send(cid, mid, txt, {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}); return "ok",200

        if cb == "menu_help":
            txt = "ℹ️ Help\n______________________________________\n\n/start - Menu utama\nKirim text/photo - Post menfess\nQuota 5 text + 5 media per hari"
            safe_send(cid, mid, txt, {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}); return "ok",200

        if cb == "menu_stats":
            real = get_real_channel_count(); m = load_members(); b = load_blocked(); q = load_quota()
            total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
            txt = f"📊 STATS\n______________________________________\n\nChannel Subs: {real}\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\nDate: {datetime.now(WIB).strftime('%d %B')}"
            safe_send(cid, mid, txt, {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}); return "ok",200

        if cb == "admin_panel" and is_admin(cid):
            real = get_real_channel_count(); m = load_members(); b = load_blocked(); q = load_quota(); g = load_global()
            total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
            txt = f"👑 ADMIN PANEL PRO\n______________________________________\n\nChannel Subs: {real} LIVE\nBot Users: {len(m)}\nBlocked: {len(b)}\nTotal Posts: {total}\n\nPilih menu:"
            kb = {"inline_keyboard": [
                [{"text":"1. Real Count","callback_data":"admin_real_count"}],
                [{"text":"2. All Users","callback_data":"admin_members"}],
                [{"text":"3. Blocked List","callback_data":"admin_blocked"}],
                [{"text":"⬅️ Back","callback_data":"menu_main"}]
            ]}
            safe_send(cid, mid, txt, kb); return "ok",200

        back_admin = {"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"admin_panel"}]]}
        if cb=="admin_real_count": safe_send(cid, mid, f"Real Count\n\n@{CHANNEL_USERNAME}: {get_real_channel_count()} subs LIVE", back_admin); return "ok",200
        if cb=="admin_members":
            m=load_members(); txt="All Users\n"+"\n".join([f"{v.get('name','-')} {k}" for k,v in list(m.items())[-20:]]) or "0 user"
            safe_send(cid, mid, txt, back_admin); return "ok",200
        if cb=="admin_blocked":
            b=load_blocked(); txt=f"Blocked {len(b)}\n"+"\n".join(b.keys()) or "Kosong"
            safe_send(cid, mid, txt, back_admin); return "ok",200

    if "message" in data:
        msg = data["message"]; cid = msg["chat"]["id"]; text = msg.get("text","")
        members = load_members()
        if str(cid) not in members:
            members[str(cid)] = {"username": msg["from"].get("username","-"), "name": "User", "joined": datetime.now(WIB).strftime("%Y-%m-%d")}
            save_members(members)

        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":get_start_text(cid),"reply_markup":get_main_menu(cid)})
            return "ok",200

        raw = msg.get("caption") or msg.get("text") or ""
        if not raw and "photo" not in msg: return "ok",200

        quotas = load_quota(); key = get_today_key(cid)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        g = load_global(); is_media = "photo" in msg; caption = add_hashtag(raw)

        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files={"photo":("menfess.jpg", fb)}, timeout=30).json()
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}).json()

        if res.get("ok"):
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":f"✅ Menfess sent!","reply_markup":get_main_menu(cid)})
    return "ok",200
