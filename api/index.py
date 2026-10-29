from flask import Flask, request
import os, requests, io, psycopg2
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
THREADS_URL = os.getenv("THREADS") or os.getenv("THREADS_URL") or "https://www.threads.net/@jogjalend"
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
WIB = timezone(timedelta(hours=7))
SEP = "--------------------------"
HASHTAG = "#jogjalend"

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0})

def get_db():
    if not DATABASE_URL: return None
    try: return psycopg2.connect(DATABASE_URL, connect_timeout=5)
    except: return None

def init_db():
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0)")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS total_text INT DEFAULT 0")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS total_media INT DEFAULT 0")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS total_chars INT DEFAULT 0")
        db.commit(); cur.close(); db.close()
    except Exception as e: print(f"db init {e}")

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    try:
        cur = db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars FROM menfess_users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close(); db.close()
        if row: return {"name":row[0] or "", "username":row[1] or "", "threads_on":row[2] or False, "today_text":row[3] or 0, "today_media":row[4] or 0, "last_date":row[5] or "", "banned":row[6] or False, "total_text":row[7] or 0, "total_media":row[8] or 0, "total_chars":row[9] or 0}
    except: return None
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s",
                    (uid, user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars",0),
                     user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars",0)))
        db.commit(); cur.close(); db.close()
    except Exception as e: print(f"save {e}")

def get_user(uid):
    u = USERS[uid]
    if u["last_date"] == "" and DATABASE_URL:
        d = load_user_from_db(uid)
        if d: USERS[uid]=d; u=USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today: u["today_text"]=0; u["today_media"]=0; u["last_date"]=today; save_user_to_db(uid, u)
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except Exception as e: print(f"send {e}")

def welcome_text(user): return f"Hi {user['name']}!\n{SEP}\nPublish to @menfessangel\nTap Post!\n\nKuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5"

def back_kb(): return {"inline_keyboard": [[{"text": "<< Back", "callback_data": "back_home"}]]}
def main_kb(is_ad=False):
    kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb

def find_logo():
    for p in ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]:
        if os.path.exists(p): return p
    return None

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=5).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=8).content
    except: return None

def add_watermark(photo_bytes):
    try:
        lp = find_logo()
        if not lp: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(lp).convert("RGBA")
        w,h = base.size; sz = int(w*0.13); logo = logo.resize((sz,sz), Image.LANCZOS)
        overlay = Image.new("RGBA", base.size, (0,0,0,0)); overlay.paste(logo, (12, 12), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=92); bio.seek(0); return bio
    except: return None

# CHART SIMPLE ANTI GAGAL DI VERCEL
def make_personal_stats_chart(user):
    try:
        W,H = 1000, 500
        img = Image.new('RGB', (W,H), '#0D0D0F')
        draw = ImageDraw.Draw(img)
        f_big = ImageFont.load_default()
        f_mid = ImageFont.load_default()

        draw.rectangle([0,0,W,80], fill='#18181B')
        draw.text((20, 15), f"STATS - {user['name'][:25]}", fill='white', font=f_big)
        draw.text((20, 45), f"Chars: {user.get('total_chars',0)}", fill='white', font=f_mid)

        x_gap=20; box_w=230; y1=110; y2=260
        datas=[
            (f"TODAY TEXT\n{user['today_text']}/5", '#3B82F6'),
            (f"TODAY MEDIA\n{user['today_media']}/5", '#10B981'),
            (f"TOTAL TEXT\n{user['total_text']}", '#8B5CF6'),
            (f"TOTAL MEDIA\n{user['total_media']}", '#F59E0B'),
        ]
        x=20
        for txt,color in datas:
            draw.rectangle([x, y1, x+box_w, y2], fill='#1F1F23', outline=color, width=2)
            draw.text((x+15, y1+20), txt, fill='white', font=f_mid)
            x+=box_w+20

        used = user['today_text'] + user['today_media']
        draw.rectangle([20, 300, W-20, 380], fill='#18181B')
        draw.text((30, 310), f"Daily {used}/10 used - sisa {10-used}", fill='white', font=f_mid)
        draw.rectangle([30, 340, W-30, 355], fill='#27272A')
        if used>0:
            prog = int((W-60)*used/10)
            draw.rectangle([30, 340, 30+prog, 355], fill='white')

        bio = io.BytesIO()
        img.save(bio, format='JPEG', quality=85)
        bio.seek(0)
        print(f"Chart OK {bio.getbuffer().nbytes} bytes")
        return bio
    except Exception as e:
        print(f"chart error {e}")
        import traceback; traceback.print_exc()
        return None

def send_stats(chat_id, user):
    try:
        chart = make_personal_stats_chart(user)
        caption = f"Stats {user['name']}\nToday {user['today_text']} text {user['today_media']} media\nTotal {user['total_text']} text {user['total_media']} media"
        if chart:
            chart.seek(0)
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption}, files={"photo": ("stats.jpg", chart, "image/jpeg")}, timeout=20).json()
            print(f"sendPhoto {r}")
            if r.get("ok"): return
        send(chat_id, caption, back_kb())
    except Exception as e:
        print(f"send_stats {e}")
        send(chat_id, "Stats error", back_kb())

def post_to_threads_auto(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        url_create = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
        r = requests.post(url_create, data={"media_type": "TEXT", "text": text_content, "access_token": THREADS_TOKEN}, timeout=10).json()
        creation_id = r.get("id")
        if not creation_id: return False
        url_pub = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
        r2 = requests.post(url_pub, data={"creation_id": creation_id, "access_token": THREADS_TOKEN}, timeout=10).json()
        return "id" in r2
    except: return False

def send_success(chat_id, user, ch_msg_id):
    try:
        url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
        buttons=[]
        if user.get("threads_on"): buttons.append([{"text": "See on Threads", "url": THREADS_URL}])
        buttons.append([{"text": "See on channel", "url": url}])
        buttons.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
        buttons.append([{"text": "Back", "callback_data": "back_home"}])
        send(chat_id, f"Menfess sent!\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5", {"inline_keyboard": buttons})
    except: pass

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    try:
        init_db()
        if request.method=="GET": return f"V102 CHART FIX OK - {THREADS_URL}",200
        data = request.get_json(force=True, silent=True) or {}
        if "message" in data:
            msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
            if "from" in msg:
                raw = (msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
                user["name"] = raw.encode('ascii','ignore').decode('ascii') or "User"
                user["username"]=msg["from"].get("username","")
            if text.startswith("/start"): send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
            elif text.lower().startswith("/stats"): send_stats(chat_id, user)
            elif text.lower().startswith("/profile") or text.lower().startswith("/me"): send(chat_id, f"My Profile\n{SEP}\nName: {user['name']}\nMedia: {user['today_media']}/5\nText: {user['today_text']}/5", back_kb())
            elif not user["banned"]:
                if text and not text.startswith("/") and len(text)>=3:
                    if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                    else:
                        clean=text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean=f"{clean} {HASHTAG}"
                        try:
                            r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=5).json()
                            ch_id=r.get("result",{}).get("message_id")
                            if user.get("threads_on"): post_to_threads_auto(clean)
                            user["today_text"]+=1; user["total_text"]+=1; user["total_chars"]=user.get("total_chars",0)+len(text)
                            save_user_to_db(uid, user); send_success(chat_id, user, ch_id)
                        except Exception as e: print(e)
                if "photo" in msg or "video" in msg:
                    if user["today_media"]>=5: send(chat_id, f"Limit 5/5", back_kb())
                    else:
                        try:
                            fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                            is_photo="photo" in msg
                            base_cap=caption.strip() if caption else HASHTAG
                            if HASHTAG.lower() not in base_cap.lower(): base_cap=f"{base_cap} {HASHTAG}"
                            ch_id=None
                            if is_photo:
                                raw=download_file(fid); wm=add_watermark(raw) if raw else None
                                if wm: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": ("wm.jpg", wm, "image/jpeg")}, timeout=15).json(); ch_id=r.get("result",{}).get("message_id")
                                else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id=r.get("result",{}).get("message_id")
                            else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=8).json(); ch_id=r.get("result",{}).get("message_id")
                            if user.get("threads_on"): post_to_threads_auto(base_cap)
                            user["today_media"]+=1; user["total_media"]+=1
                            save_user_to_db(uid, user); send_success(chat_id, user, ch_id)
                        except Exception as e: print(e)
        if "callback_query" in data:
            cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
            except: pass
            if cdata=="stats": send_stats(chat_id, user)
            elif cdata=="back_home": send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
            elif cdata.startswith("del_"):
                mid=cdata.replace("del_","")
                if mid.isdigit():
                    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=3)
                    except: pass
                send(chat_id, "Deleted", back_kb())
            elif cdata in ["my_profile","post","threads","help"]:
                send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        return "ok",200
    except Exception as e:
        print(f"GLOBAL {e}"); import traceback; traceback.print_exc(); return "ok",200