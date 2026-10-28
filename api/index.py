from flask import Flask, request
import os, requests, io, json, time
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
WIB = timezone(timedelta(hours=7))
SEP = "────────────────────────"
HASHTAG = "#jogjalend"

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_user": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "await_threads": False})

# CACHE biar gak pending
CACHE = {"channel_photo": None, "members": 0, "title": "menfessangel", "ts": 0}

def get_user(uid):
    u = USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today:
        u["today_text"]=0; u["today_media"]=0; u["last_date"]=today
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=3)
    except: pass

def find_logo():
    for p in ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]:
        if os.path.exists(p): return p
    return None

def get_channel_info_fast():
    # cache 5 menit, biar stats gak pending
    if time.time() - CACHE["ts"] < 300 and CACHE["channel_photo"]:
        return CACHE["channel_photo"], CACHE["members"], CACHE["title"]
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat", params={"chat_id": CHANNEL_ID}, timeout=3).json()
        chat = r.get("result", {})
        CACHE["channel_photo"] = chat.get("photo", {}).get("big_file_id")
        CACHE["title"] = chat.get("title", "menfessangel")
        try:
            rc = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount", params={"chat_id": CHANNEL_ID}, timeout=3).json()
            CACHE["members"] = rc.get("result", 0)
        except: pass
        CACHE["ts"] = time.time()
    except: pass
    return CACHE["channel_photo"], CACHE["members"], CACHE["title"]

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}, timeout=3).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=5).content
    except: return None

def add_watermark(photo_bytes):
    try:
        logo_path = find_logo()
        if not logo_path: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(logo_path).convert("RGBA")
        w, h = base.size
        # V85 - KIRI ATAS JELAS 13%
        logo_size = int(w * 0.13)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        # KIRI ATAS 12px padding
        overlay.paste(logo, (12, 12), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO()
        combined.save(bio, "JPEG", quality=92)
        bio.seek(0)
        return bio
    except:
        return None

def back_kb(): return {"inline_keyboard": [[{"text": "« Back", "callback_data": "back_home"}]]}

def send_success(chat_id, user, ch_msg_id):
    reply=f"""Menfess sent!
{SEP}
Remaining:
Text {user['today_text']}/5
Media {user['today_media']}/5"""
    channel_url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    kb=[[{"text": "See on channel", "url": channel_url}]]
    if user["threads_on"] and user["threads_user"]:
        kb.append([{"text": "See on Threads", "url": f"https://www.threads.net/@{user['threads_user'].replace('@','')}"}])
    kb.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
    kb.append([{"text": "« Back", "callback_data": "back_home"}])
    send(chat_id, reply, {"inline_keyboard": kb})

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "V85 KIRI ATAS JELAS + FAST LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
            user["username"]=msg["from"].get("username","")

        if text.startswith("/start"):
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name']}!\n\n{SEP}\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\n\nTap Post to start!", kb)

        elif not user["banned"]:
            if user.get("await_threads") and text and not text.startswith("/"):
                if text.strip()=="-": user["threads_user"]=""; user["threads_on"]=False; user["await_threads"]=False; send(chat_id, f"Threads OFF\n{SEP}\nRemoved", back_kb())
                elif text.startswith("@"): user["threads_user"]=text.strip(); user["threads_on"]=True; user["await_threads"]=False; send(chat_id, f"Threads ON {text}\n{SEP}\nActive", back_kb())
            elif text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    clean = text.strip()
                    if HASHTAG.lower() not in clean.lower(): clean = f"{clean} {HASHTAG}"
                    if user["threads_on"] and user["threads_user"]: clean+=f"\n🧵 {user['threads_user']}"
                    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=5).json()
                    ch_id=r.get("result",{}).get("message_id")
                    user["today_text"]+=1; user["total_text"]+=1
                    send_success(chat_id, user, ch_id)
            if "photo" in msg or "video" in msg:
                if user["today_media"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                    is_photo = "photo" in msg
                    base_cap = caption.strip() if caption else HASHTAG
                    if HASHTAG.lower() not in base_cap.lower(): base_cap = f"{base_cap} {HASHTAG}"
                    if user["threads_on"] and user["threads_user"]: base_cap+=f"\n🧵 {user['threads_user']}"
                    ch_id=None
                    if is_photo:
                        raw = download_file(fid)
                        wm = add_watermark(raw) if raw else None
                        if wm:
                            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": wm}, timeout=8).json()
                            ch_id=r.get("result",{}).get("message_id")
                        else:
                            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json()
                            ch_id=r.get("result",{}).get("message_id")
                    else:
                        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=8).json()
                        ch_id=r.get("result",{}).get("message_id")
                    user["today_media"]+=1; user["total_media"]+=1
                    send_success(chat_id, user, ch_id)

    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        # jawab cepet biar gak muter
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
        except: pass

        if cdata=="my_profile":
            # gak usah download foto profil biar cepet
            send(chat_id, f"My Profile\n{SEP}\nName: {user['name']}\nID: {uid}\nUsername: @{user['username'] or '-'}\nText: {user['today_text']}/5\nMedia: {user['today_media']}/5\nThreads: {'ON' if user['threads_on'] else 'OFF'}", back_kb())
        elif cdata in ["rules", "verification"]: 
            send(chat_id, f"📋 Verification\n{SEP}\nContact: @jogja_lend", back_kb())
        elif cdata=="post": send(chat_id, f"Post Menfess\n{SEP}\nKirim text/foto/video\nAuto watermark kiri atas + {HASHTAG}", back_kb())
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads Setting\n{SEP}\nStatus: {'ON' if user['threads_on'] else 'OFF'}\nUsername: {user['threads_user'] or '-'}", kb)
        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, f"Threads: ON\n{SEP}\nEnabled", back_kb())
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, f"Threads: OFF\n{SEP}\nDisabled", back_kb())
        elif cdata=="threads_set": user["await_threads"]=True; send(chat_id, f"Send @username\n{SEP}\nEx: @jogjalend or -", back_kb())
        elif cdata=="stats":
            _, members, title = get_channel_info_fast()
            total_t = sum(u["today_text"] for u in USERS.values())
            total_m = sum(u["today_media"] for u in USERS.values())
            all_t = sum(u["total_text"] for u in USERS.values())
            all_m = sum(u["total_media"] for u in USERS.values())
            send(chat_id, f"Stats - {title}\n\nMembers: {members}+\nToday: {total_t}T {total_m}M\nTotal: {all_t}T {all_m}M\n\nYour: {user['today_text']}/5 T, {user['today_media']}/5 M", back_kb())
        elif cdata=="help": send(chat_id, f"Help\n{SEP}\nChannel: @menfessangel\nAdmin: @jogjalend", back_kb())
        elif cdata=="back_home":
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name']}!\n\n{SEP}\nPublish to Channel @menfessangel\nTap Post to start!", kb)
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=3)
                except: pass
            send(chat_id, f"Deleted\n{SEP}\nRemoved", back_kb())
    return "ok",200
