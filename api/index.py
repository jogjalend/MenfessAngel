from flask import Flask, request
import os, requests, io
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
WIB = timezone(timedelta(hours=7))

USERS = defaultdict(lambda: {"name": "", "username": "", "threads_user": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "await_threads": False})
HASHTAG = "#jogjalend"

def get_user(uid):
    u = USERS[uid]
    if u["last_date"] != datetime.now(WIB).strftime("%Y-%m-%d"):
        u["today_text"]=0; u["today_media"]=0; u["last_date"]=datetime.now(WIB).strftime("%Y-%m-%d")
    return u
def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    return requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload).json()

def find_logo():
    paths = ["logo.png", "../logo.png", "/vercel/path0/logo.png", os.path.join(os.path.dirname(__file__), "../logo.png"), os.path.join(os.path.dirname(__file__), "logo.png")]
    for p in paths:
        if os.path.exists(p): return p
    return None

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}).json()
        fp = info["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}"
        return requests.get(url).content
    except: return None

def add_watermark(photo_bytes):
    try:
        logo_path = find_logo()
        if not logo_path: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(logo_path).convert("RGBA")
        w, h = base.size
        logo_size = int(w * 0.16)  # 16% biar pas di kanan
        logo = logo.resize((logo_size, logo_size))
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        margin = 15
        # UJUNG KANAN BAWAH
        overlay.paste(logo, (w - logo_size - margin, h - logo_size - margin), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO()
        combined.save(bio, "JPEG", quality=92)
        bio.seek(0)
        return bio
    except Exception as e:
        print(e)
        return None

def back_kb(): return {"inline_keyboard": [[{"text": "« Back", "callback_data": "back_home"}]]}

def send_success(chat_id, user, ch_msg_id):
    reply=f"""Menfess sent!
Remaining quota:
Text : {user['today_text']}/5
Media : {user['today_media']}/5
Successfully posted to {'Telegram + Threads' if user['threads_on'] else 'Telegram only'} (Threads {'ON' if user['threads_on'] else 'OFF'})
Join Channel : {CHANNEL_ID}"""
    channel_url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    kb=[]
    kb.append([{"text": "See on channel", "url": channel_url}])
    if user["threads_on"] and user["threads_user"]:
        kb.append([{"text": "See on Threads", "url": f"https://www.threads.net/@{user['threads_user'].replace('@','')}"}])
    kb.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
    kb.append([{"text": "« Back to Menu", "callback_data": "back_home"}])
    send(chat_id, reply, {"inline_keyboard": kb})

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "V65 LOGO KANAN + #jogjalend UJUNG KALIMAT LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip()
            user["username"]=msg["from"].get("username","")
        if text.startswith("/start"):
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name'] or 'there'}!\nPromote your account here!\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend\n\nTap Post to start!", kb)
        elif not user["banned"]:
            if user.get("await_threads") and text and not text.startswith("/"):
                if text.strip()=="-": user["threads_user"]=""; user["threads_on"]=False; user["await_threads"]=False; send(chat_id, "Threads OFF", back_kb())
                elif text.startswith("@"): user["threads_user"]=text.strip(); user["threads_on"]=True; user["await_threads"]=False; send(chat_id, f"Threads ON {text}", back_kb())
            elif text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5: send(chat_id, "Limit 5/5 text", back_kb())
                else:
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    # PAKSA DI UJUNG KALIMAT
                    clean_text = text.strip()
                    if not clean_text.lower().endswith(HASHTAG.lower()):
                        clean_text = f"{clean_text} {HASHTAG}"
                    final=f"{clean_text}\n\n—\n<i>{tgl}</i>"
                    if user["threads_on"] and user["threads_user"]: final+=f"\n🧵 {user['threads_user']}"
                    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": final, "parse_mode": "HTML"}).json()
                    ch_id=r.get("result",{}).get("message_id")
                    user["today_text"]+=1; user["total_text"]+=1
                    send_success(chat_id, user, ch_id)
            if "photo" in msg or "video" in msg:
                if user["today_media"]>=5: send(chat_id, "Limit 5/5 media", back_kb())
                else:
                    fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                    is_photo = "photo" in msg
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    
                    # PAKSA DI UJUNG KALIMAT CAPTION
                    base_cap = caption.strip() if caption else ""
                    if base_cap and not base_cap.lower().endswith(HASHTAG.lower()):
                        base_cap = f"{base_cap} {HASHTAG}"
                    elif not base_cap:
                        base_cap = HASHTAG
                    
                    cap=f"{base_cap}\n\n—\n<i>{tgl}</i>"
                    if user["threads_on"] and user["threads_user"]: cap+=f"\n🧵 {user['threads_user']}"
                    
                    ch_id=None
                    if is_photo:
                        raw = download_file(fid)
                        wm = add_watermark(raw) if raw else None
                        if wm:
                            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                            files = {"photo": wm}
                            data = {"chat_id": CHANNEL_ID, "caption": cap, "parse_mode": "HTML"}
                            r = requests.post(url, data=data, files=files).json()
                            ch_id=r.get("result",{}).get("message_id")
                        else:
                            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": cap, "parse_mode": "HTML"}).json()
                            ch_id=r.get("result",{}).get("message_id")
                    else:
                        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": cap, "parse_mode": "HTML"}).json()
                        ch_id=r.get("result",{}).get("message_id")
                    
                    user["today_media"]+=1; user["total_media"]+=1
                    send_success(chat_id, user, ch_id)

    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
        except: pass
        if cdata=="my_profile": send(chat_id, f"My Profile\n@{user['username']}\nText {user['today_text']}/5 Media {user['today_media']}/5", back_kb())
        elif cdata=="rules": send(chat_id, "Rules: No SARA/porn Limit 5/hari", back_kb())
        elif cdata=="post": send(chat_id, f"📝 Kirim text/foto/video. Auto watermark logo + {HASHTAG} di ujung kalimat", back_kb())
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads: {'ON' if user['threads_on'] else 'OFF'}", kb)
        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, "ON", back_kb())
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, "OFF", back_kb())
        elif cdata=="threads_set": user["await_threads"]=True; send(chat_id, "Kirim @username atau -", back_kb())
        elif cdata=="stats": send(chat_id, f"Stats Text {user['today_text']}/5 Media {user['today_media']}/5", back_kb())
        elif cdata=="help": send(chat_id, "Help @jogjalend", back_kb())
        elif cdata=="back_home":
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name'] or 'there'}!", kb)
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit(): requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)})
            send(chat_id, "🗑️ Deleted", back_kb())
    return "ok",200
