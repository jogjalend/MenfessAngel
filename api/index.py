from flask import Flask, request
import os, requests, io, json, psycopg2
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
SEP = "────────────────────────"
HASHTAG = "#jogjalend"

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0})

def get_db():
    if not DATABASE_URL: return None
    return psycopg2.connect(DATABASE_URL)

def init_db():
    db = get_db()
    if not db: return
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0)")
    db.commit(); cur.close(); db.close()

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    cur = db.cursor()
    cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars FROM menfess_users WHERE user_id=%s", (uid,))
    row = cur.fetchone(); cur.close(); db.close()
    if row: return {"name":row[0], "username":row[1], "threads_on":row[2], "today_text":row[3], "today_media":row[4], "last_date":row[5], "banned":row[6], "total_text":row[7], "total_media":row[8], "total_chars":row[9] or 0}
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    cur = db.cursor()
    cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s",
                (uid, user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars",0),
                 user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars",0)))
    db.commit(); cur.close(); db.close()

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
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=4)
    except: pass

def welcome_text(user): return f"Hi {user['name']}!\n{SEP}\nPublish to @menfessangel\nTap Post!\n\nKuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nThreads : {'ON ✅' if user['threads_on'] else 'OFF ❌'}"
def back_kb(): return {"inline_keyboard": [[{"text": "« Back", "callback_data": "back_home"}]]}
def admin_back_kb(): return {"inline_keyboard": [[{"text": "« Back to Admin", "callback_data": "admin_panel"}]]}
def main_kb(is_admin_user=False):
    kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
    if is_admin_user: kb["inline_keyboard"].append([{"text": "🛠 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb

def find_logo():
    for p in ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]:
        if os.path.exists(p): return p
    return None
def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=4).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=6).content
    except: return None
def add_watermark(photo_bytes):
    try:
        from PIL import Image
        lp = find_logo()
        if not lp: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(lp).convert("RGBA")
        w,h = base.size; sz = int(w*0.13)
        logo = logo.resize((sz,sz), Image.LANCZOS)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        overlay.paste(logo, (12, 12), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=92); bio.seek(0)
        return bio
    except: return None

# === STATS V1 DASHBOARD JOURNEY - PIL ANTI BUG GARIS PUTIH ===
def make_personal_stats_chart(user):
    try:
        W,H = 1000, 600
        img = Image.new('RGB', (W,H), '#0D0D0F')
        draw = ImageDraw.Draw(img, 'RGBA')
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 26)
            font_sub = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 15)
            font_big = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 42)
            font_mid = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font_title = ImageFont.load_default(); font_sub=font_title; font_big=font_title; font_mid=font_title

        total_chars = user.get('total_chars',0)
        today_text = user['today_text']; today_media = user['today_media']
        total_text = user['total_text']; total_media = user['total_media']

        # header
        draw.rounded_rectangle([30,30, W-30, 115], radius=18, fill='#18181B')
        draw.text((60, 48), f"Your Menfess Journey ✨ {user['name'][:20]}", fill='white', font=font_title)
        draw.text((60, 82), f"{today_text} text • {today_media} media today • {total_chars} karakter", fill='#A1A1AA', font=font_sub)

        # 4 cards
        cards = [
            {'label':'TODAY TEXT','val':today_text,'sub':f'{today_text}/5 today','color':'#3B82F6','pos':(30,145)},
            {'label':'TODAY MEDIA','val':today_media,'sub':f'{today_media}/5 today','color':'#10B981','pos':(270,145)},
            {'label':'TOTAL TEXT','val':total_text,'sub':f'{total_chars} chars','color':'#8B5CF6','pos':(510,145)},
            {'label':'TOTAL MEDIA','val':total_media,'sub':'all time','color':'#F59E0B','pos':(750,145)},
        ]
        max_v = max(5, total_text, total_media, 1)
        for c in cards:
            x,y = c['pos']
            draw.rounded_rectangle([x, y, x+220, y+175], radius=22, fill='#18181B', outline=c['color'], width=1)
            draw.ellipse([x+18, y+18, x+28, y+28], fill=c['color'])
            draw.text((x+42, y+16), c['label'], fill='#71717A', font=font_sub)
            draw.text((x+18, y+48), str(c['val']), fill='white', font=font_big)
            draw.text((x+18, y+108), c['sub'], fill=c['color'], font=font_mid)
            # mini bar
            bw = int(c['val']/max_v*150) if max_v>0 else 0
            bw = max(8, bw) if c['val']>0 else 0
            draw.rounded_rectangle([x+18, y+140, x+18+150, y+148], radius=4, fill='#27272A')
            if bw>0:
                draw.rounded_rectangle([x+18, y+140, x+18+bw, y+148], radius=4, fill=c['color'])

        # bottom limit
        used = today_text + today_media
        draw.rounded_rectangle([30, 350, W-30, 480], radius=18, fill='#18181B')
        draw.text((60, 370), "Daily Limit", fill='white', font=font_mid)
        draw.text((60, 400), f"{used} / 10 kuota kepake hari ini • sisa {10-used}", fill='#A1A1AA', font=font_sub)
        draw.rounded_rectangle([60, 435, W-60, 453], radius=10, fill='#27272A')
        prog = int(used/10*(W-120))
        if prog>0:
            draw.rounded_rectangle([60, 435, 60+prog, 453], radius=10, fill='#FFFFFF')

        bio = io.BytesIO()
        img.save(bio, format='JPEG', quality=92)
        bio.seek(0)
        return bio
    except Exception as e:
        print(f"chart error: {e}")
        return None

def send_stats(chat_id, user):
    chart = make_personal_stats_chart(user)
    caption = f"Stats - {user['name']}\nToday: {user['today_text']} text, {user['today_media']} media\nTotal: {user['total_text']} text, {user['total_media']} media\nChars: {user.get('total_chars',0)}"
    if chart:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption}, files={"photo": chart}, timeout=12)
            return
        except: pass
    send(chat_id, caption, back_kb())

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
    url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    buttons=[]
    if user.get("threads_on"): buttons.append([{"text": "📧See on Threads", "url": THREADS_URL}])
    buttons.append([{"text": "✉️See on channel", "url": url}])
    buttons.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
    buttons.append([{"text": "« Back", "callback_data": "back_home"}])
    send(chat_id, f"Menfess sent!\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nThreads : {'ON ✅' if user['threads_on'] else 'OFF ❌'}\n{'Auto posted to Threads!' if user.get('threads_on') else ''}", {"inline_keyboard": buttons})

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": 
        init_db()
        try:
            cmds=[
                {"command":"start","description":"Buka menu utama"},
                {"command":"newpost","description":"create a new post"},
                {"command":"profile","description":"My profile & kuota"},
                {"command":"threads","description":"ON/OFF auto post Threads"},
                {"command":"stats","description":"check your stats"},
                {"command":"help","description":"answers to basic questions"}
            ]
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands", json={"commands": cmds}, timeout=3)
        except: pass
        return f"V97 STATS V1 DASHBOARD - {THREADS_URL}",200

    init_db()
    data = request.get_json(force=True, silent=True) or {}
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg: user["name"]=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"; user["username"]=msg["from"].get("username","")
        if text.startswith("/start"): send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        elif text.lower().startswith("/help"): send(chat_id, f"/start - Buka menu utama + cek kuota\n/help - daftar command\n/profile /me - cek profile\n/post /newpost - Buat menfess baru. Auto watermark + {HASHTAG}\n/threads - Setting auto post ke Threads ON/OFF. Kalo ON ✅ = tiap menfess auto ke Threads\n/stats - Liat stats pribadi\n/limit - Cek sisa kuota\n\nThreads: {'ON' if user['threads_on'] else 'OFF'}\nhttps://www.threads.net/@jogjalend", back_kb())
        elif text.lower().startswith("/profile") or text.lower().startswith("/me"): send(chat_id, f"My Profile\n{SEP}\nName: {user['name']}\nMedia: {user['today_media']}/5\nText: {user['today_text']}/5\nThreads: {'ON ✅' if user['threads_on'] else 'OFF ❌'}\n{THREADS_URL}", back_kb())
        elif text.lower().startswith("/post") or text.lower().startswith("/newpost"): send(chat_id, f"Post\n{SEP}\nKirim teks/foto/video langsung. Auto watermark + {HASHTAG}", back_kb())
        elif text.lower().startswith("/threads"):
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads Setting\n{SEP}\nStatus: {'ON ✅' if user['threads_on'] else 'OFF ❌'}\nLink: {THREADS_URL}\n\nKalo ON = auto post ke Threads juga", kb)
        elif text.lower().startswith("/stats"): send_stats(chat_id, user)
        elif text.lower().startswith("/limit"): send(chat_id, f"Sisa Kuota\n{SEP}\nText {5-user['today_text']} Media {5-user['today_media']}\nReset 00:00 WIB", back_kb())
        elif not user["banned"]:
            if text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    clean=text.strip()
                    if HASHTAG.lower() not in clean.lower(): clean=f"{clean} {HASHTAG}"
                    r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=5).json()
                    ch_id=r.get("result",{}).get("message_id")
                    if user.get("threads_on"): post_to_threads_auto(clean)
                    user["today_text"]+=1; user["total_text"]+=1; user["total_chars"]=user.get("total_chars",0)+len(text); save_user_to_db(uid, user); send_success(chat_id, user, ch_id)
            if "photo" in msg or "video" in msg:
                if user["today_media"]>=5: send(chat_id, f"Limit 5/5", back_kb())
                else:
                    fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                    is_photo="photo" in msg
                    base_cap=caption.strip() if caption else HASHTAG
                    if HASHTAG.lower() not in base_cap.lower(): base_cap=f"{base_cap} {HASHTAG}"
                    ch_id=None
                    if is_photo:
                        raw=download_file(fid); wm=add_watermark(raw) if raw else None
                        if wm: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": wm}, timeout=8).json(); ch_id=r.get("result",{}).get("message_id")
                        else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id=r.get("result",{}).get("message_id")
                    else: r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=8).json(); ch_id=r.get("result",{}).get("message_id")
                    if user.get("threads_on"): post_to_threads_auto(base_cap)
                    user["today_media"]+=1; user["total_media"]+=1; 
                    if caption: user["total_chars"]=user.get("total_chars",0)+len(caption)
                    save_user_to_db(uid, user); send_success(chat_id, user, ch_id)
    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
        except: pass
        if cdata=="my_profile": send(chat_id, f"My Profile\n{SEP}\nThreads: {'ON ✅' if user['threads_on'] else 'OFF ❌'}\n{THREADS_URL}", back_kb())
        elif cdata=="back_home": send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads Setting\n{SEP}\nStatus: {'ON ✅' if user['threads_on'] else 'OFF ❌'}\nLink: {THREADS_URL}\nKalo ON auto post ke Threads", kb)
        elif cdata=="threads_on": user["threads_on"]=True; save_user_to_db(uid, user); send(chat_id, f"Threads: ON ✅\n{SEP}\nAuto post ENABLED\n{THREADS_URL}", back_kb())
        elif cdata=="threads_off": user["threads_on"]=False; save_user_to_db(uid, user); send(chat_id, f"Threads: OFF ❌\n{SEP}\nAuto post DISABLED", back_kb())
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=3)
                except: pass
            send(chat_id, "Deleted", back_kb())
        elif cdata=="stats": send_stats(chat_id, user)
        elif cdata in ["verification","post","help","admin_panel"]:
            if cdata=="verification": send(chat_id, f"Verification\n{SEP}\nHubungi @jogja_lend", back_kb())
            elif cdata=="post": send(chat_id, f"Post\n{SEP}\nKirim langsung", back_kb())
            elif cdata=="help": send(chat_id, f"/start - Buka menu utama + cek kuota\n/help - daftar command\n/profile /me - cek profile\n/post /newpost - Buat menfess baru. Auto watermark + {HASHTAG}\n/threads - Setting auto post ke Threads ON/OFF. Kalo ON ✅ = tiap menfess auto ke Threads\n/stats - Liat stats pribadi\n/limit - Cek sisa kuota\n\nThreads: {'ON' if user['threads_on'] else 'OFF'}\nhttps://www.threads.net/@jogjalend", back_kb())
            elif cdata=="admin_panel": send(chat_id, f"Admin\n{SEP}\n/reset /ban /unban", admin_back_kb())
    return "ok",200