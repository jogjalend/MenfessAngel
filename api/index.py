from flask import Flask, request
import os, requests, io, json
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from PIL import Image

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
WIB = timezone(timedelta(hours=7))
SEP = "────────────────────────"
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
    paths = ["logo.png", "../logo.png", os.path.join(os.path.dirname(__file__), "../logo.png")]
    for p in paths:
        if os.path.exists(p): return p
    return None

def get_profile_photo_id(user_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos", params={"user_id": user_id, "limit": 1}).json()
        if r.get("result", {}).get("total_count", 0) > 0:
            return r["result"]["photos"][0][-1]["file_id"]
    except: pass
    return None

def get_channel_info():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChat", params={"chat_id": CHANNEL_ID}).json()
        chat = r.get("result", {})
        photo_file_id = chat.get("photo", {}).get("big_file_id")
        title = chat.get("title", "menfessangel")
        try:
            rc = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount", params={"chat_id": CHANNEL_ID}).json()
            members = rc.get("result", 0)
        except: members = 0
        return photo_file_id, members, title
    except: return None, 0, "menfessangel"

def download_file(file_id):
    try:
        info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile", params={"file_id": file_id}).json()
        fp = info["result"]["file_path"]
        return requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
    except: return None

def add_watermark(photo_bytes):
    try:
        logo_path = find_logo()
        if not logo_path: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = Image.open(logo_path).convert("RGBA")
        w, h = base.size
        # V82 - PILIHAN C 13% PAS
        logo_size = int(w * 0.13)
        logo = logo.resize((logo_size, logo_size))
        # transparan dikit biar elegan
        logo.putalpha(200)
        overlay = Image.new("RGBA", base.size, (0,0,0,0))
        overlay.paste(logo, (w - logo_size - 12, h - logo_size - 12), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=90); bio.seek(0)
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
    if request.method=="GET": return "V82 LOGO 13% PAS + NO TIME LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id); user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]=(msg["from"].get("first_name","")+" "+(msg["from"].get("last_name","") or "")).strip() or "-"
            user["username"]=msg["from"].get("username","")

        if text.startswith("/start"):
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            caption_txt = f"""Hi {user['name']}!

{SEP}

Publish to:
- Channel -> @menfessangel
- Threads -> @jogjalend [optional]
- X -> @jogjalendpm [maintenance]

Tap Post to start!"""
            send(chat_id, caption_txt, kb)

        elif not user["banned"]:
            if user.get("await_threads") and text and not text.startswith("/"):
                if text.strip()=="-": user["threads_user"]=""; user["threads_on"]=False; user["await_threads"]=False; send(chat_id, f"Threads OFF\n{SEP}\nRemoved", back_kb())
                elif text.startswith("@"): user["threads_user"]=text.strip(); user["threads_on"]=True; user["await_threads"]=False; send(chat_id, f"Threads ON {text}\n{SEP}\nActive", back_kb())
            elif text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5: send(chat_id, f"Limit 5/5\n{SEP}\nReset 00:00 WIB", back_kb())
                else:
                    clean_text = text.strip()
                    if HASHTAG.lower() not in clean_text.lower(): clean_text = f"{clean_text} {HASHTAG}"
                    final = f"{clean_text}"
                    if user["threads_on"] and user["threads_user"]: final+=f"\n🧵 {user['threads_user']}"
                    r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": final, "parse_mode": "HTML"}).json()
                    ch_id=r.get("result",{}).get("message_id")
                    user["today_text"]+=1; user["total_text"]+=1
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
            photo_id = get_profile_photo_id(chat_id)
            caption_txt = f"""My Profile
{SEP}
Name: {user['name']}
ID: {uid}
Username: @{user['username'] or '-'}
Text: {user['today_text']}/5
Media: {user['today_media']}/5
Threads: {'ON' if user['threads_on'] else 'OFF'}"""
            if photo_id:
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": chat_id, "photo": photo_id, "caption": caption_txt, "parse_mode": "HTML", "reply_markup": back_kb()})
                except: send(chat_id, caption_txt, back_kb())
            else:
                send(chat_id, caption_txt, back_kb())

        elif cdata in ["rules", "verification"]: 
            rules_text = f"""📋 Verification - How to Join JogjaLend
{SEP}

Entering JogjaLend Telegram group requires special verification to ensure seriousness in joining JogjaLend group.
To avoid joining and leaving the group as you please.

𝙍𝙚𝙦𝙪𝙞𝙧𝙚𝙢𝙚𝙣𝙩𝙨 𝙩𝙤 𝙅𝙤𝙞𝙣 JogjaLend:

1. Create a Telegram username
(How to create can be searched on Google)

2. As a guarantee of seriousness to join JogjaLend forum, please choose ONE of the following verification methods:

   - Open Donate 100.000 and for donate method can be via EWALLET & BANK.

   - Complete the registration form from @jogja_lend

3. Willing to comply with all rules in JogjaLend

{SEP}

Contact Admin: @jogja_lend"""
            send(chat_id, rules_text, back_kb())

        elif cdata=="post": send(chat_id, f"Post Menfess\n{SEP}\nKirim text/foto/video sekarang\nAuto watermark + {HASHTAG}", back_kb())
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Threads Setting\n{SEP}\nStatus: {'ON' if user['threads_on'] else 'OFF'}\nUsername: {user['threads_user'] or '-'}", kb)
        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, f"Threads: ON\n{SEP}\nEnabled", back_kb())
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, f"Threads: OFF\n{SEP}\nDisabled", back_kb())
        elif cdata=="threads_set": user["await_threads"]=True; send(chat_id, f"Send @username\n{SEP}\nEx: @jogjalend or -", back_kb())
        elif cdata=="stats":
            channel_photo_id, members, title = get_channel_info()
            total_t = sum(u["today_text"] for u in USERS.values())
            total_m = sum(u["today_media"] for u in USERS.values())
            all_t = sum(u["total_text"] for u in USERS.values())
            all_m = sum(u["total_media"] for u in USERS.values())
            caption_txt = f"""Stats - {title}

📈 Channel Activity:
Members: {members}+
Today: {total_t} text, {total_m} media
Total: {all_t} text, {all_m} media

👤 Your Stats:
Today: {user['today_text']}/5 text, {user['today_media']}/5 media
Total: {user['total_text']} text, {user['total_media']} media
Channel: {CHANNEL_ID}"""
            if channel_photo_id:
                content = download_file(channel_photo_id)
                if content:
                    try:
                        bio = io.BytesIO(content)
                        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption_txt, "parse_mode": "HTML", "reply_markup": json.dumps(back_kb())}, files={"photo": bio})
                    except:
                        send(chat_id, caption_txt, back_kb())
                else:
                    send(chat_id, caption_txt, back_kb())
            else:
                logo_path = find_logo()
                if logo_path and os.path.exists(logo_path):
                    try:
                        with open(logo_path, 'rb') as f:
                            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption_txt, "parse_mode": "HTML", "reply_markup": json.dumps(back_kb())}, files={"photo": f})
                    except:
                        send(chat_id, caption_txt, back_kb())
                else:
                    send(chat_id, caption_txt, back_kb())
        elif cdata=="help": send(chat_id, f"Help\n{SEP}\nChannel: @menfessangel\nAdmin: @jogjalend", back_kb())
        elif cdata=="back_home":
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Verification", "callback_data": "verification"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            caption_txt = f"""Hi {user['name']}!

{SEP}

Publish to:
- Channel -> @menfessangel
- Threads -> @jogjalend [optional]
- X -> @jogjalendpm [maintenance]

Tap Post to start!"""
            send(chat_id, caption_txt, kb)
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)})
                except: pass
            send(chat_id, f"Deleted\n{SEP}\nRemoved", back_kb())
        if cdata=="admin_panel" and is_admin(chat_id):
            total_t=sum(u["today_text"] for u in USERS.values()); total_m=sum(u["today_media"] for u in USERS.values())
            kb={"inline_keyboard": [[{"text": f"👥 {len(USERS)} Users", "callback_data": "admin_users"}, {"text": f"📈 {total_t}T {total_m}M", "callback_data": "admin_stats"}], [{"text": "📢 Broadcast", "callback_data": "admin_bc"}, {"text": "📋 List", "callback_data": "admin_list"}], [{"text": "🔄 Reset", "callback_data": "admin_reset"}, {"text": "🚫 Banned", "callback_data": "admin_banlist"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"Admin Panel\n{SEP}\nUsers: {len(USERS)}\nToday: {total_t}T {total_m}M", kb)
        elif cdata.startswith("admin_") and is_admin(chat_id):
            if cdata=="admin_reset":
                for u in USERS.values(): u["today_text"]=0; u["today_media"]=0
                send(chat_id, f"Reset done\n{SEP}\nAll limits 0", back_kb())
            else: send(chat_id, f"Admin\n{SEP}\nDone", back_kb())
    return "ok",200
