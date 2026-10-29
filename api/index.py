from flask import Flask, request
import os, requests, io, json, psycopg2
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image, ImageDraw

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
WIB = timezone(timedelta(hours=7))
SEP = "────────────────────────"
HASHTAG = "#jogjalend"

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "await_bc": False})

def get_db():
    if not DATABASE_URL: return None
    return psycopg2.connect(DATABASE_URL)

def init_db():
    db = get_db()
    if not db: return
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS menfess_users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            username TEXT,
            threads_on BOOLEAN DEFAULT FALSE,
            today_text INT DEFAULT 0,
            today_media INT DEFAULT 0,
            last_date TEXT,
            banned BOOLEAN DEFAULT FALSE,
            total_text INT DEFAULT 0,
            total_media INT DEFAULT 0
        )
    """)
    db.commit(); cur.close(); db.close()

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    cur = db.cursor()
    cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media FROM menfess_users WHERE user_id=%s", (uid,))
    row = cur.fetchone()
    cur.close(); db.close()
    if row:
        return {"name":row[0], "username":row[1], "threads_on":row[2], "today_text":row[3], "today_media":row[4], "last_date":row[5], "banned":row[6], "total_text":row[7], "total_media":row[8], "await_bc": False}
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    cur = db.cursor()
    cur.execute("""
        INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s
    """, (uid, user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"],
          user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"]))
    db.commit(); cur.close(); db.close()

def get_user(uid):
    u = USERS[uid]
    # load dari DB kalo belum ada di memory
    if u["last_date"] == "" and DATABASE_URL:
        db_user = load_user_from_db(uid)
        if db_user:
            USERS[uid] = db_user
            u = USERS[uid]
    
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today:
        u["today_text"]=0; u["today_media"]=0; u["last_date"]=today
        if DATABASE_URL: save_user_to_db(uid, u)
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False
def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=4)
    except: pass

def welcome_text(user):
    return f"""Hi {user['name']}!
{SEP}
Publish to @menfessangel
Tap Post!

Kuota Post
Media : {user['today_media']}/5
Text : {user['today_text']}/5
Threads : {'ON ✅' if user['threads_on'] else 'OFF ❌'}"""

def find_logo():
    for p in ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]:
        if os.path.exists(p): return p
    return None
def get_profile_photo_id(user_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos", params={"user_id": user_id, "limit": 1}, timeout=4).json()
        if r.get("result", {}).get("total_count", 0) > 0:
            return r["result"]["photos"][0][-1]["file_id"]
    except: pass
    return None
def get_channel_info():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat", params={"chat_id": CHANNEL_ID}, timeout=4).json()
        chat = r.get("result", {}); title = chat.get("title", "menfessangel")
        try:
            rc = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount", params={"chat_id": CHANNEL_ID}, timeout=4).json(); members = rc.get("result", 0)
        except: members = 0
        return members, title
    except: return 0, "menfessangel"
def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=4).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=6).content
    except: return None
def add_watermark(photo_bytes):
    try:
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
def create_stats_chart(members, today_text, today_media, total_text, total_media):
    W,H = 800, 450; img = Image.new("RGB", (W,H), "#0f0f0f"); draw = ImageDraw.Draw(img)
    data = [("Today text", today_text), ("Today media", today_media), ("Total text", total_text), ("Total media", total_media), ("Members", members)]
    max_val = max([v for _,v in data] + [1]); bar_w = 110; gap = 30; start_x = 50; base_y = 350
    colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#f9ca24", "#6c5ce7"]
    for i, (label, val) in enumerate(data):
        h = int((val / max_val) * 250) if max_val>0 else 0
        x = start_x + i*(bar_w+gap); y = base_y - h
        draw.rectangle([x, y, x+bar_w, base_y], fill=colors[i])
        draw.text((x+10, base_y+10), label, fill="white"); draw.text((x+10, y-25), str(val), fill="white")
    draw.text((30, 20), f"STATS REALTIME - {datetime.now(WIB).strftime('%H:%M WIB')}", fill="white")
    bio = io.BytesIO(); img.save(bio, "PNG"); bio.seek(0); return bio

def back_kb(): return {"inline_keyboard": [[{"text": "« Back", "callback_data": "back_home"}]]}
def admin_back_kb(): return {"inline_keyboard": [[{"text": "« Back to Admin", "callback_data": "admin_panel"}]]}
def main_kb(is_admin_user=False):
    kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
    if is_admin_user: kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb

# === FIX UTAMA DI SINI ===
def send_success(chat_id, user, ch_msg_id):
    url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    buttons=[]
    if user.get("threads_on"):
        buttons.append([{"text": "See on Threads 🧵", "url": url}])
    buttons.append([{"text": "See on channel", "url": url}])
    buttons.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
    buttons.append([{"text": "« Back", "callback_data": "back_home"}])
    send(chat_id, f"Menfess sent!\n{SEP}\nRemaining\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nThreads : {'ON ✅' if user['threads_on'] else 'OFF ❌'}", {"inline_keyboard": buttons})

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": 
        init_db()
        return "V89 THREADS FIX + DB",200
    init_db()
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
            user["username"]=msg["from"].get("username","")

        if user.get("await_bc") and is_admin(chat_id) and text and not text.startswith("/"):
            user["await_bc"]=False
            sent=0
            for u_id in list(USERS.keys()):
                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": int(u_id), "text": f"📢 Broadcast\n{SEP}\n{text}", "parse_mode": "HTML"}, timeout=2)
                    sent+=1
                except: pass
            send(chat_id, f"Broadcast sent to {sent} users\n{SEP}\n{text}", admin_back_kb())
        elif text.startswith("/start"):
            send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        elif not user["banned"]:
            if text and not text.startswith("/") and len(text)>=3 and not user.get("await_bc"):
                if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    clean=text.strip()
                    if HASHTAG.lower() not in clean.lower(): clean=f"{clean} {HASHTAG}"
                    r=requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=5).json()
                    ch_id=r.get("result",{}).get("message_id"); user["today_text"]+=1; user["total_text"]+=1; save_user_to_db(uid, user); send_success(chat_id, user, ch_id)
            if "photo" in msg or "video" in msg:
                if user["today_media"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
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
                    user["today_media"]+=1; user["total_media"]+=1; save_user_to_db(uid, user); send_success(chat_id, user, ch_id)

    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
        except: pass

        if cdata=="my_profile":
            photo_id=get_profile_photo_id(chat_id)
            txt=f"My Profile\n{SEP}\nName: {user['name']}\nID: {uid}\nUsername: @{user['username'] or '-'}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nThreads: {'ON ✅' if user['threads_on'] else 'OFF ❌'}"
            if photo_id:
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": chat_id, "photo": photo_id, "caption": txt, "parse_mode": "HTML", "reply_markup": back_kb()}, timeout=5)
                except: send(chat_id, txt, back_kb())
            else: send(chat_id, txt, back_kb())
        elif cdata=="stats":
            members, title = get_channel_info()
            today_text = sum(u["today_text"] for u in USERS.values()); today_media = sum(u["today_media"] for u in USERS.values())
            all_text = sum(u["total_text"] for u in USERS.values()); all_media = sum(u["total_media"] for u in USERS.values())
            chart = create_stats_chart(members, today_text, today_media, all_text, all_media)
            caption_txt = f"Stats - {title}\n\nMembers: {members}+\nToday: {today_text} text {today_media} media\nTotal: {all_text} text {all_media} media\nYour: {user['today_text']}/5 text, {user['today_media']}/5 media"
            try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption_txt, "parse_mode": "HTML", "reply_markup": json.dumps(back_kb())}, files={"photo": chart}, timeout=8)
            except: send(chat_id, caption_txt, back_kb())
        elif cdata=="back_home":
            send(chat_id, welcome_text(user), main_kb(is_admin(chat_id)))
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads Setting\n{SEP}\nStatus: {'ON' if user['threads_on'] else 'OFF'}\n\nKalo ON, tiap menfess kekirim bakal ada tombol See on Threads", kb)
        elif cdata=="threads_on": 
            user["threads_on"]=True; save_user_to_db(uid, user)
            send(chat_id, f"Threads: ON ✅\n{SEP}\nEnabled - Sekarang setiap post ada tombol See on Threads", back_kb())
        elif cdata=="threads_off": 
            user["threads_on"]=False; save_user_to_db(uid, user)
            send(chat_id, f"Threads: OFF ❌\n{SEP}\nDisabled", back_kb())
        elif cdata in ["verification", "rules"]: send(chat_id, f"Verification\n{SEP}\nContact @jogja_lend", back_kb())
        elif cdata=="post": send(chat_id, f"Post Menfess\n{SEP}\nKirim text/foto/video\nWatermark kiri atas + {HASHTAG}", back_kb())
        elif cdata=="help": send(chat_id, f"Help\n{SEP}\nChannel: @menfessangel", back_kb())
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=3)
                except: pass
            send(chat_id, f"Deleted\n{SEP}\nRemoved", back_kb())

        elif cdata=="admin_panel" and is_admin(chat_id):
            members, _ = get_channel_info()
            today_text=sum(u["today_text"] for u in USERS.values()); today_media=sum(u["today_media"] for u in USERS.values())
            banned=len([u for u in USERS.values() if u["banned"]])
            kb={"inline_keyboard": [
                [{"text": f"👥 {len(USERS)} Users", "callback_data": "admin_users"}, {"text": f"📈 {today_text} text {today_media} media", "callback_data": "admin_chart"}],
                [{"text": "📢 Broadcast", "callback_data": "admin_bc"}, {"text": "📋 List User", "callback_data": "admin_list"}],
                [{"text": f"🚫 Banned {banned}", "callback_data": "admin_banlist"}, {"text": "🔍 Search", "callback_data": "admin_search"}],
                [{"text": "🔄 Reset All Limits", "callback_data": "admin_reset"}, {"text": "📊 Detail", "callback_data": "admin_detail"}],
                [{"text": "« Back", "callback_data": "back_home"}]
            ]}
            send(chat_id, f"🔐 ADMIN PANEL FULL\n{SEP}\nUsers: {len(USERS)}\nToday: {today_text} text {today_media} media\nMembers CH: {members}\nBanned: {banned}\n{SEP}\nPilih menu:", kb)

        elif cdata.startswith("admin_") and is_admin(chat_id):
            members, title = get_channel_info()
            today_text=sum(u["today_text"] for u in USERS.values()); today_media=sum(u["today_media"] for u in USERS.values())
            all_text=sum(u["total_text"] for u in USERS.values()); all_media=sum(u["total_media"] for u in USERS.values())

            if cdata=="admin_reset":
                for u in USERS.values(): u["today_text"]=0; u["today_media"]=0
                send(chat_id, f"✅ Reset done\n{SEP}\nSemua limit jadi 0/5", admin_back_kb())
            elif cdata=="admin_users" or cdata=="admin_list":
                txt=f"List User ({len(USERS)})\n{SEP}\n"
                for i,(uid2,u2) in enumerate(list(USERS.items())[:30]):
                    txt+=f"{i+1}. {u2['name'][:15]} | {u2['today_text']} text {u2['today_media']} media {'🚫' if u2['banned'] else ''} Threads:{'ON' if u2['threads_on'] else 'OFF'}\nID:{uid2}\n"
                send(chat_id, txt, admin_back_kb())
            elif cdata=="admin_chart":
                chart = create_stats_chart(members, today_text, today_media, all_text, all_media)
                cap=f"Admin Chart - {title}\nMembers:{members} Users:{len(USERS)}\nToday:{today_text} text {today_media} media\nTotal:{all_text} text {all_media} media"
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": cap, "parse_mode": "HTML", "reply_markup": json.dumps(admin_back_kb())}, files={"photo": chart}, timeout=8)
                except: send(chat_id, cap, admin_back_kb())
            elif cdata=="admin_detail":
                send(chat_id, f"Detail Stats\n{SEP}\nChannel: {title}\nMembers: {members}\nTotal Users: {len(USERS)}\nToday Text: {today_text}\nToday Media: {today_media}\nAll Time Text: {all_text}\nAll Time Media: {all_media}\nBanned: {len([u for u in USERS.values() if u['banned']])}", admin_back_kb())
            elif cdata=="admin_bc":
                user["await_bc"]=True
                send(chat_id, f"📢 BROADCAST\n{SEP}\nKirim text broadcast lu sekarang\nNanti kekirim ke {len(USERS)} user", admin_back_kb())
            elif cdata=="admin_banlist":
                banned_users=[(uid2,u2) for uid2,u2 in USERS.items() if u2["banned"]]
                if not banned_users: send(chat_id, f"No banned users", admin_back_kb())
                else:
                    txt=f"Banned {len(banned_users)}\n{SEP}\n"
                    for uid2,u2 in banned_users[:20]: txt+=f"{u2['name']} - {uid2}\n"
                    kb={"inline_keyboard": [[{"text": "Unban All", "callback_data": "admin_unbanall"}], [{"text": "« Back to Admin", "callback_data": "admin_panel"}]]}
                    send(chat_id, txt, kb)
            elif cdata=="admin_unbanall":
                for u in USERS.values(): u["banned"]=False
                send(chat_id, f"✅ All unbanned", admin_back_kb())
            elif cdata=="admin_search":
                send(chat_id, f"Search\n{SEP}\nKirim ID user yang mau dicari\nFormat: /ban ID atau /unban ID\nContoh: /ban 123456", admin_back_kb())
            else:
                send(chat_id, f"Coming soon {cdata}", admin_back_kb())
    return "ok",200