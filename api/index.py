from flask import Flask, request
import os, requests, io, psycopg2, random
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
THREADS_URL = os.getenv("THREADS") or "https://threads.net/jogjalend"
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
WIB = timezone(timedelta(hours=7))
SEP = "-------------------------------------------"
HASHTAG = "#jogjalend"

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0, "admin_target": "both"})

def get_db():
    if not DATABASE_URL: return None
    try: return psycopg2.connect(DATABASE_URL, connect_timeout=5)
    except: return None

def init_db():
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0, admin_target TEXT DEFAULT 'both')")
        try: cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS admin_target TEXT DEFAULT 'both'")
        except: pass
        db.commit(); cur.close(); db.close()
    except: pass

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    try:
        cur = db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target FROM menfess_users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close(); db.close()
        if row: return {"name":row[0] or "", "username":row[1] or "", "threads_on":row[2] or False, "today_text":row[3] or 0, "today_media":row[4] or 0, "last_date":row[5] or "", "banned":row[6] or False, "total_text":row[7] or 0, "total_media":row[8] or 0, "total_chars":row[9] or 0, "admin_target":row[10] or "both"}
    except: return None
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s, admin_target=%s",
                    (uid,user["name"],user["username"],user["threads_on"],user["today_text"],user["today_media"],user["last_date"],user["banned"],user["total_text"],user["total_media"],user.get("total_chars",0),user.get("admin_target","both"),
                     user["name"],user["username"],user["threads_on"],user["today_text"],user["today_media"],user["last_date"],user["banned"],user["total_text"],user["total_media"],user.get("total_chars",0),user.get("admin_target","both")))
        db.commit(); cur.close(); db.close()
    except: pass

def get_user(uid):
    u = USERS[uid]
    if u["last_date"] == "" and DATABASE_URL:
        d = load_user_from_db(uid)
        if d: USERS[uid] = d; u = USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today: u["today_text"]=0; u["today_media"]=0; u["last_date"]=today; save_user_to_db(uid,u)
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send_message(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if keyboard: payload["reply_markup"] = keyboard
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except: pass

def get_welcome_text(user): return f"Hi {user['name']}!\n{SEP}\nPublish to @menfessangel\nTap Post!\n\nKuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5"
def get_back_keyboard(): return {"inline_keyboard": [[{"text": "<< Back", "callback_data": "back_home"}]]}
def get_main_keyboard(is_admin_user=False):
    kb = {"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
    if is_admin_user: kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb
def get_admin_keyboard(user):
    target = user.get("admin_target","both")
    return {"inline_keyboard": [[{"text": f"Target: {target.upper()}", "callback_data": "admin_noop"}], [{"text": "✅ Channel Only" if target=="channel" else "Channel Only", "callback_data": "admin_set_channel"}], [{"text": "✅ Threads Only" if target=="threads" else "Threads Only", "callback_data": "admin_set_threads"}], [{"text": "✅ Both (Channel+Threads)" if target=="both" else "Both", "callback_data": "admin_set_both"}], [{"text": "<< Back", "callback_data": "back_home"}]]}

# ... watermark, chart, threads functions same as V106 (english) ...

def post_to_threads(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        r = requests.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data={"media_type":"TEXT","text":text_content,"access_token":THREADS_TOKEN}, timeout=10).json()
        cid = r.get("id")
        if not cid: return False
        r2 = requests.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish", data={"creation_id":cid,"access_token":THREADS_TOKEN}, timeout=10).json()
        return "id" in r2
    except: return False

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def main_handler():
    try:
        init_db()
        if request.method=="GET": return "V106.1 FULL ENGLISH OK",200
        data=request.get_json(force=True,silent=True) or {}
        # ... message handling same as V106, using send_message ...
        if "callback_query" in data:
            cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",json={"callback_query_id":cq["id"]},timeout=2)
            except: pass

            if cdata=="help":
                send_message(chat_id, f"""Help - @menfessangel Bot

📝 CARA POST:
• Ketik langsung text lu disini
• Atau kirim foto/video + caption
• Auto ke-tag #jogjalend
• Auto publish ke channel

📊 KUOTA:
• 5 Text + 5 Media per hari
• Reset tiap 00:00 WIB
• /stats buat cek chart

🔗 THREADS:
• Setting di Threads Setting
• ON = auto ke threads.net/jogjalend juga
• OFF = cuma ke channel

📌 COMMAND:
/start - Menu utama
/stats - Lihat TODAY 1D & WEEKLY 7D

Bot V106.1
Author : @jogja_lend""", get_back_keyboard())
            # ... other callbacks ...
        return "ok",200
    except Exception as e:
        print(f"ERROR {e}"); return "ok",200
