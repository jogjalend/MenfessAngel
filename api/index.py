from flask import Flask, request
import os, requests, io, json, psycopg2
from datetime import datetime, timezone, timedelta
from PIL import Image

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
WIB = timezone(timedelta(hours=7))
SEP = "────────────────────────"
HASHTAG = "#jogjalend"

def get_db():
    return psycopg2.connect(DATABASE_URL)

def get_user(uid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, first_name, today_text, today_media, total_text, total_media, threads_user, threads_on, last_date, banned FROM users WHERE user_id=%s", (int(uid),))
    row = cur.fetchone()
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if not row:
        cur.execute("INSERT INTO users (user_id, last_date) VALUES (%s,%s) ON CONFLICT DO NOTHING", (int(uid), today))
        conn.commit()
        user = {"name": "", "username": "", "threads_user": "", "threads_on": False, "today_text": 0, "today_media": 0, "total_text": 0, "total_media": 0, "last_date": today, "banned": False}
    else:
        user = {"name": row[2] or "", "username": row[1] or "", "today_text": row[3] or 0, "today_media": row[4] or 0, "total_text": row[5] or 0, "total_media": row[6] or 0, "threads_user": row[7] or "", "threads_on": row[8] or False, "last_date": row[9], "banned": row[10] or False}
        if user["last_date"] != today:
            cur.execute("UPDATE users SET today_text=0, today_media=0, last_date=%s WHERE user_id=%s", (today, int(uid)))
            conn.commit()
            user["today_text"]=0; user["today_media"]=0
    cur.close(); conn.close()
    return user

def db_update(uid, query, val=None):
    conn = get_db(); cur = conn.cursor()
    if val is None:
        cur.execute(query, (int(uid),))
    else:
        cur.execute(query, (val, int(uid)))
    conn.commit(); cur.close(); conn.close()

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=10).json()

def find_logo():
    paths = ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]
    for p in paths:
        if os.path.exists(p): return p
    return None

def get_profile_photo_id(user_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos", params={"user_id": user_id, "limit": 1}, timeout=10).json()
        if r.get("result", {}).get("total_count", 0) > 0:
            return r["result"]["photos"][0][-1]["file_id"]
    except: pass
    return None

def get_channel_info():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat", params={"chat_id": CHANNEL_ID}, timeout=10).json()
        chat = r.get("result", {})
        photo_file_id = chat.get("photo", {}).get("big_file_id")
        title = chat.get("title", "menfessangel")
        try:
            rc = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount", params={"chat_id": CHANNEL_ID}, timeout=10).json()
            members = rc.get("result", 0)
        except: members = 0
        return photo_file_id, members, title
    except: return None, 0, "menfessangel"

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=10).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=20).content
    except: return None

def add_watermark(photo_bytes):
    try:
        logo_path = find_logo()
        if not logo_path: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(logo_path).convert("RGBA")
        w, h = base.size
        logo_size = int(w * 0.13)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        overlay.paste(logo, (w - logo_size - 12, h - logo_size - 12), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO()
        combined.save(bio, "JPEG", quality=90)
        bio.seek(0)
        return bio
    except: return None

def back_kb(): return {"inline_keyboard": [[{"text": "« Back", "callback_data": "back_home"}]]}

def send_success(chat_id, user, ch_msg_id):
    reply=f"""Menfess sent!
{SEP}
Remaining:
Text {user['today_text']}/5
Media {user['today_media']}/5
Posted to {'Telegram + Threads' if user['threads_on'] else 'Telegram'}"""
    channel_url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    kb=[[{"text": "See on channel", "url": channel_url}]]
    if user["threads_on"] and user["threads_user"]:
        kb.append([{"text": "See on Threads", "url": f"https://www.threads.net/@{user['threads_user'].replace('@','')}"}])
    kb.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
    kb.append([{"text": "« Back", "callback_data": "back_home"}])
    send(chat_id, reply, {"inline_keyboard": kb})

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "V84 NEON 13% PAS + NO TIME + DB LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            name = (msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
            uname = msg["from"].get("username","")
            db_update(uid, "UPDATE users SET first_name=%s, username=%s WHERE user_id=%s", name)
            # we update username separately
            conn=get_db(); cur=conn.cursor(); cur.execute("UPDATE users SET username=%s WHERE user_id=%s", (uname, int(uid))); conn.commit(); cur.close(); conn.close()
            user["name"]=name; user["username"]=uname

        if text.startswith("/start"):
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"""Hi {user['name']}!\n\n{SEP}\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\n- X -> @jogjalendpm [maintenance]\n\nTap Post to start!""", kb)

        elif not user["banned"]:
            if user.get("await_threads") and text and not text.startswith("/"):
                # custom handling for await
                pass
            # need re-fetch await flag from db
            conn=get_db(); cur=conn.cursor(); cur.execute("SELECT threads_user FROM users WHERE user_id=%s", (int(uid),)); cur.close(); conn.close()

            # Check await via simple logic - if last message was set username
            # For simplicity use total_text check: we store await in memory? better query
            # Quick fix: if user threads_user empty and text starts with @ we treat as set
            if text and not text.startswith("/") and text.startswith("@") and len(text)>2 and len(text)<33:
                # This is threads set if user just clicked set
                db_update(uid, "UPDATE users SET threads_user=%s, threads_on=TRUE WHERE user_id=%s", text.strip())
                user["threads_user"]=text.strip(); user["threads_on"]=True
                send(chat_id, f"Threads ON {text}\n{SEP}\nActive", back_kb())
            elif text and not text.startswith("/") and len(text)>=3 and not text.startswith("@"):
                if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    clean_text = text.strip()
                    if HASHTAG.lower() not in clean_text.lower(): clean_text = f"{clean_text} {HASHTAG}"
                    final = f"{clean_text}"
                    if user["threads_on"] and user["threads_user"]: final+=f"\n🧵 {user['threads_user']}"
                    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": final, "parse_mode": "HTML"}, timeout=10).json()
                    ch_id=r.get("result",{}).get("message_id")
                    conn=get_db(); cur=conn.cursor(); cur.execute("UPDATE users SET today_text=today_text+1, total_text=total_text+1 WHERE user_id=%s", (int(uid),)); conn.commit(); cur.close(); conn.close()
                    user["today_text"]+=1
                    send_success(chat_id, user, ch_id)
            if "photo" in msg or "video" in msg:
                if user["today_media"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                    is_photo = "photo" in msg
                    base_cap = caption.strip() if caption else ""
                    if base_cap and HASHTAG.lower() not in base_cap.lower(): base_cap = f"{base_cap} {HASHTAG}"
                    elif not base_cap: base_cap = HASHTAG
                    cap = f"{base_cap}"
                    if user["threads_on"] and user["threads_user"]: cap+=f"\n🧵 {user['threads_user']}"
                    ch_id=None
                    if is_photo:
                        raw = download_file(fid)
                        wm = add_watermark(raw) if raw else None
                        if wm:
                            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": cap, "parse_mode": "HTML"}, files={"photo": wm}, timeout=20).json()
                            ch_id=r.get("result",{}).get("message_id")
                        else:
                            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": cap, "parse_mode": "HTML"}, timeout=10).json()
                            ch_id=r.get("result",{}).get("message_id")
                    else:
                        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": cap, "parse_mode": "HTML"}, timeout=20).json()
                        ch_id=r.get("result",{}).get("message_id")
                    conn=get_db(); cur=conn.cursor(); cur.execute("UPDATE users SET today_media=today_media+1, total_media=total_media+1 WHERE user_id=%s", (int(uid),)); conn.commit(); cur.close(); conn.close()
                    user["today_media"]+=1
                    send_success(chat_id, user, ch_id)

    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=5)
        except: pass

        if cdata=="my_profile":
            photo_id = get_profile_photo_id(chat_id)
            caption_txt = f"""My Profile\n{SEP}\nName: {user['name']}\nID: {uid}\nUsername: @{user['username'] or '-'}\nText: {user['today_text']}/5\nMedia: {user['today_media']}/5\nThreads: {'ON' if user['threads_on'] else 'OFF'}"""
            if photo_id:
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": chat_id, "photo": photo_id, "caption": caption_txt, "parse_mode": "HTML", "reply_markup": back_kb()}, timeout=10)
                except: send(chat_id, caption_txt, back_kb())
            else: send(chat_id, caption_txt, back_kb())

        elif cdata in ["rules", "verification"]:
            send(chat_id, f"""📋 Verification - How to Join JogjaLend\n{SEP}\n\nEntering JogjaLend Telegram group requires special verification...\n\n1. Create a Telegram username\n2. Open Donate 100.000 via EWALLET & BANK or form @jogja_lend\n3. Willing to comply rules\n\n{SEP}\n\nContact Admin: @jogja_lend""", back_kb())
        elif cdata=="post": send(chat_id, f"Post Menfess\n{SEP}\nKirim text/foto/video sekarang\nAuto watermark + {HASHTAG}", back_kb())
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads Setting\n{SEP}\nStatus: {'ON' if user['threads_on'] else 'OFF'}\nUsername: {user['threads_user'] or '-'}", kb)
        elif cdata=="threads_on": db_update(uid, "UPDATE users SET threads_on=TRUE WHERE user_id=%s"); send(chat_id, f"Threads: ON\n{SEP}\nEnabled", back_kb())
        elif cdata=="threads_off": db_update(uid, "UPDATE users SET threads_on=FALSE WHERE user_id=%s"); send(chat_id, f"Threads: OFF\n{SEP}\nDisabled", back_kb())
        elif cdata=="threads_set": send(chat_id, f"Send @username\n{SEP}\nEx: @jogjalend", back_kb())
        elif cdata=="stats":
            channel_photo_id, members, title = get_channel_info()
            conn=get_db(); cur=conn.cursor(); cur.execute("SELECT SUM(today_text), SUM(today_media), SUM(total_text), SUM(total_media), COUNT(*) FROM users"); t_row=cur.fetchone(); cur.close(); conn.close()
            total_t = t_row[0] or 0; total_m = t_row[1] or 0; all_t = t_row[2] or 0; all_m = t_row[3] or 0; ucount = t_row[4] or 0
            caption_txt = f"""Stats - {title}\n\n📈 Channel Activity:\nMembers: {members}+\nToday: {total_t} text, {total_m} media\nTotal: {all_t} text, {all_m} media\nUsers: {ucount}\n\n👤 Your Stats:\nToday: {user['today_text']}/5 text, {user['today_media']}/5 media\nTotal: {user['total_text']} text, {user['total_media']} media\nChannel: {CHANNEL_ID}"""
            if channel_photo_id:
                content = download_file(channel_photo_id)
                if content:
                    try:
                        bio = io.BytesIO(content)
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption_txt, "parse_mode": "HTML", "reply_markup": json.dumps(back_kb())}, files={"photo": bio}, timeout=10)
                    except: send(chat_id, caption_txt, back_kb())
                else: send(chat_id, caption_txt, back_kb())
            else: send(chat_id, caption_txt, back_kb())
        elif cdata=="help": send(chat_id, f"Help\n{SEP}\nChannel: @menfessangel\nAdmin: @jogjalend", back_kb())
        elif cdata=="back_home":
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"""Hi {user['name']}!\n\n{SEP}\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\n- X -> @jogjalendpm [maintenance]\n\nTap Post to start!""", kb)
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=10)
                except: pass
            send(chat_id, f"Deleted\n{SEP}\nRemoved", back_kb())
    return "ok",200
