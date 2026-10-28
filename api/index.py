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
        logo_size = int(w * 0.16)
        logo = logo.resize((logo_size, logo_size))
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        margin = 15
        overlay.paste(logo, (w - logo_size - margin, h - logo_size - margin), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO()
        combined.save(bio, "JPEG", quality=92)
        bio.seek(0)
        return bio
    except: return None

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
    if request.method=="GET": return "V66 ADMIN FIX + LOGO KANAN + #jogjalend LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip()
            user["username"]=msg["from"].get("username","")
        if text.startswith("/start"):
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "⚙️ ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name'] or 'there'}!\nPromote your account here!\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend\n\nTap Post to start!", kb)
        elif text.startswith("/broadcast ") and is_admin(chat_id):
            bc=text.replace("/broadcast ","")
            cnt=0
            for uid2 in list(USERS.keys()):
                try: send(uid2, f"📢 <b>Broadcast</b>\n\n{bc}"); cnt+=1
                except: pass
            send(chat_id, f"✅ Broadcast ke {cnt} user", back_kb())
        elif text.startswith("/ban ") and is_admin(chat_id):
            try: USERS[text.split()[1]]["banned"]=True; send(chat_id, "🚫 Banned", back_kb())
            except: send(chat_id, "Format /ban ID", back_kb())
        elif text.startswith("/unban ") and is_admin(chat_id):
            try: USERS[text.split()[1]]["banned"]=False; send(chat_id, "✅ Unbanned", back_kb())
            except: send(chat_id, "Format /unban ID", back_kb())
        elif not user["banned"]:
            if user.get("await_threads") and text and not text.startswith("/"):
                if text.strip()=="-": user["threads_user"]=""; user["threads_on"]=False; user["await_threads"]=False; send(chat_id, "Threads OFF", back_kb())
                elif text.startswith("@"): user["threads_user"]=text.strip(); user["threads_on"]=True; user["await_threads"]=False; send(chat_id, f"Threads ON {text}", back_kb())
            elif text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5: send(chat_id, "Limit 5/5 text", back_kb())
                else:
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    clean_text = text.strip()
                    if HASHTAG.lower() not in clean_text.lower():
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
                    base_cap = caption.strip() if caption else ""
                    if base_cap and HASHTAG.lower() not in base_cap.lower():
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
                            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": cap, "parse_mode": "HTML"}, files={"photo": wm}).json()
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

        if cdata=="my_profile":
            send(chat_id, f"My Profile\nName: {user['name']}\n@{user['username'] or '-'}\nText {user['today_text']}/5 Media {user['today_media']}/5\nThreads {user['threads_user'] or '-'}", back_kb())
        elif cdata=="rules": send(chat_id, "📜 Rules\n1. No SARA/porn/spam\n2. No doxxing\n3. Limit 5/hari\n4. Sopan", back_kb())
        elif cdata=="post": send(chat_id, f"📝 Kirim text/foto/video. Auto watermark logo + {HASHTAG} di ujung kalimat", back_kb())
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"🧵 Threads Setting\nStatus: {'ON' if user['threads_on'] else 'OFF'}\nUsername: {user['threads_user'] or '-'}", kb)
        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, "✅ Threads ON", back_kb())
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, "✅ Threads OFF", back_kb())
        elif cdata=="threads_set": user["await_threads"]=True; send(chat_id, "Kirim @username Threads (ex @jogjalend) atau kirim - untuk hapus", back_kb())
        elif cdata=="stats": send(chat_id, f"📊 Stats\nToday: Text {user['today_text']}/5 Media {user['today_media']}/5\nTotal: {user['total_text']}T {user['total_media']}M", back_kb())
        elif cdata=="help": send(chat_id, "ℹ️ Help\nChannel: @menfessangel\nAdmin: @jogjalend\n/start for menu", back_kb())
        elif cdata=="back_home":
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "⚙️ ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name'] or 'there'}!\nPromote your account here!\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend\n\nTap Post to start!", kb)
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)})
                except: pass
            send(chat_id, "🗑️ Deleted from channel", back_kb())

        # === ADMIN PANEL FIX - INI YANG BIKIN BISA DI TAB ===
        if cdata=="admin_panel" and is_admin(chat_id):
            total_t=sum(u["today_text"] for u in USERS.values())
            total_m=sum(u["today_media"] for u in USERS.values())
            kb={"inline_keyboard": [
                [{"text": f"👥 {len(USERS)} Users", "callback_data": "admin_users"}, {"text": f"📈 {total_t}T {total_m}M", "callback_data": "admin_stats"}],
                [{"text": "📢 Broadcast", "callback_data": "admin_bc"}, {"text": "📋 List 20", "callback_data": "admin_list"}],
                [{"text": "🔄 Reset All", "callback_data": "admin_reset"}, {"text": "🚫 Banned List", "callback_data": "admin_banlist"}],
                [{"text": "« Back", "callback_data": "back_home"}]
            ]}
            send(chat_id, f"🔐 ADMIN PANEL\n\nUsers: {len(USERS)}\nToday: {total_t} text {total_m} media\n\nCommands:\n/broadcast text\n/ban id\n/unban id\n\nLogo: {'✅ Found' if find_logo() else '❌ Not found'}\nHashtag: {HASHTAG}", kb)

        elif cdata.startswith("admin_") and is_admin(chat_id):
            if cdata=="admin_list":
                txt="📋 20 users:\n\n"
                for k,v in list(USERS.items())[:20]: txt+=f"<code>{k}</code> @{v['username'] or '-'} T{v['today_text']} M{v['today_media']}\n"
                send(chat_id, txt, back_kb())
            elif cdata=="admin_banlist":
                banned=[f"<code>{k}</code> @{v['username']}" for k,v in USERS.items() if v["banned"]]
                send(chat_id, "🚫 Banned:\n"+("\n".join(banned) if banned else "None"), back_kb())
            elif cdata=="admin_reset":
                for u in USERS.values(): u["today_text"]=0; u["today_media"]=0
                send(chat_id, "✅ All limits reset", back_kb())
            elif cdata=="admin_bc": send(chat_id, "Ketik: /broadcast pesan lu\nContoh: /broadcast maintenance 1 jam", back_kb())
            elif cdata=="admin_users": send(chat_id, f"Total users: {len(USERS)}", back_kb())
            elif cdata=="admin_stats":
                total_t=sum(u["total_text"] for u in USERS.values()); total_m=sum(u["total_media"] for u in USERS.values())
                send(chat_id, f"📊 Total: {total_t} text {total_m} media\nToday: {sum(u['today_text'] for u in USERS.values())}T", back_kb())

    return "ok",200
