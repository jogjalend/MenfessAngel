from flask import Flask, request
import os, requests
from datetime import datetime, timezone, timedelta
from collections import defaultdict

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
WIB = timezone(timedelta(hours=7))

USERS = defaultdict(lambda: {
    "name": "", "username": "", "threads_user": "",
    "threads_on": False, "today_text": 0, "today_media": 0,
    "last_date": "", "banned": False, "total_text": 0, "total_media": 0,
    "await_threads": False
})

def get_user(uid):
    u = USERS[uid]
    if u["last_date"] != datetime.now(WIB).strftime("%Y-%m-%d"):
        u["today_text"]=0; u["today_media"]=0; u["last_date"]=datetime.now(WIB).strftime("%Y-%m-%d")
    return u
def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    return requests.post(url, json=payload).json()

def send_photo(chat_id, photo, caption, kb=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo, "caption": caption, "parse_mode": "HTML"}
    if kb: payload["reply_markup"]=kb
    return requests.post(url, json=payload).json()

def send_channel(text, media=None):
    try:
        if media:
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": media, "caption": text, "parse_mode": "HTML"}).json()
        else:
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}).json()
        return r.get("result",{}).get("message_id")
    except: return None

def get_profile_photo(chat_id):
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUserProfilePhotos", params={"user_id": chat_id, "limit": 1}).json()
        if r.get("result",{}).get("total_count",0)>0:
            return r["result"]["photos"][0][-1]["file_id"]
    except: pass
    return None

def back_kb():
    return {"inline_keyboard": [[{"text": "« Back", "callback_data": "back_home"}]]}

def send_success(chat_id, user, ch_msg_id):
    threads_st="ON" if user["threads_on"] else "OFF"
    posted_to="Telegram + Threads" if user["threads_on"] else "Telegram only"
    reply=f"""Menfess sent!
Remaining quota:
Text : {user['today_text']}/5
Media : {user['today_media']}/5
Successfully posted to {posted_to} (Threads {threads_st})
Join Channel : {CHANNEL_ID}"""
    channel_url=f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    inline_kb=[]
    inline_kb.append([{"text": "See on channel", "url": channel_url}])
    if user["threads_on"] and user["threads_user"]:
        inline_kb.append([{"text": "See on Threads", "url": f"https://www.threads.net/@{user['threads_user'].replace('@','')}"}])
    inline_kb.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
    inline_kb.append([{"text": "« Back to Menu", "callback_data": "back_home"}])
    send(chat_id, reply, {"inline_keyboard": inline_kb})

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "V62 FINAL - ALL BACK + PHOTO PROFILE - LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id)
        user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]= (msg["from"].get("first_name","")+" "+msg["from"].get("last_name","")).strip()
            user["username"]=msg["from"].get("username","")

        if text.startswith("/start"):
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name'] or 'there'}!\nPromote your account here!\n\n____________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend [optional]\n- X -> @jogjalendpm [maintenance]\n\nTap Post to start!", kb)

        elif text.startswith("/broadcast ") and is_admin(chat_id):
            bc=text.replace("/broadcast ","")
            for u_id in USERS.keys():
                try: send(u_id, f"📢 Broadcast\n\n{bc}")
                except: pass
            send(chat_id, "✅ Broadcast done", back_kb())

        elif not user["banned"]:
            if user.get("await_threads") and text and not text.startswith("/"):
                if text.strip()=="-": user["threads_user"]=""; user["threads_on"]=False; user["await_threads"]=False; send(chat_id, "Threads OFF", back_kb())
                elif text.startswith("@"): user["threads_user"]=text.strip(); user["threads_on"]=True; user["await_threads"]=False; send(chat_id, f"Threads ON {text}", back_kb())
            elif text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5: send(chat_id, "Limit 5/5 text", back_kb())
                else:
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    final=f"{text}\n\n—\n<i>{tgl}</i>"
                    if user["threads_on"] and user["threads_user"]: final+=f"\n🧵 {user['threads_user']}"
                    ch_id=send_channel(final); user["today_text"]+=1; user["total_text"]+=1
                    send_success(chat_id, user, ch_id)
            if "photo" in msg or "video" in msg:
                if user["today_media"]>=5: send(chat_id, "Limit 5/5 media", back_kb())
                else:
                    fid=msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video",{}).get("file_id")
                    cap=f"{caption}\n\n—\n<i>{datetime.now(WIB).strftime('%d %b %H:%M WIB')}</i>" if caption else f"<i>{datetime.now(WIB).strftime('%d %b %H:%M WIB')}</i>"
                    if user["threads_on"] and user["threads_user"]: cap+=f"\n🧵 {user['threads_user']}"
                    ch_id=send_channel(cap, media=fid); user["today_media"]+=1; user["total_media"]+=1
                    send_success(chat_id, user, ch_id)

    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
        except: pass

        # MY PROFILE WITH PHOTO
        if cdata=="my_profile":
            threads_st="ON" if user["threads_on"] else "OFF"
            profile_caption=f"""My Profile
____________________

Name: {user['name']}
ID: {uid}
Username: @{user['username'] or '-'}

Text: {user['today_text']}/5
Media: {user['today_media']}/5
Threads: {threads_st}
Username: {user['threads_user'] or '-'}"""
            photo_id=get_profile_photo(chat_id)
            kb={"inline_keyboard": [[{"text": f"Threads: {threads_st}", "callback_data": "threads"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            if photo_id:
                send_photo(chat_id, photo_id, profile_caption, kb)
            else:
                send(chat_id, profile_caption, kb)

        elif cdata=="rules":
            send(chat_id, "📜 Rules\n\n1. No SARA/porn/spam\n2. No doxxing\n3. Limit 5/hari\n4. Sopan\n5. Admin berhak ban", back_kb())
        elif cdata=="post":
            send(chat_id, "📝 Kirim text/foto/video sekarang. Auto post ke @menfessangel", back_kb())
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"🧵 Threads Setting\nStatus: {'ON' if user['threads_on'] else 'OFF'}\nUsername: {user['threads_user'] or '-'}", kb)
        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, "Threads ON ✅", back_kb())
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, "Threads OFF ❌", back_kb())
        elif cdata=="threads_set": user["await_threads"]=True; send(chat_id, "Kirim @username Threads (ex @jogjalend) atau - untuk hapus", back_kb())
        elif cdata=="stats":
            send(chat_id, f"📊 Stats\n\nToday: Text {user['today_text']}/5 Media {user['today_media']}/5\nTotal: {user['total_text']}T {user['total_media']}M", back_kb())
        elif cdata=="help":
            send(chat_id, "ℹ️ Help\n\nChannel @menfessangel\nAdmin @jogjalend\n/start menu", back_kb())
        elif cdata=="back_home":
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name'] or 'there'}!\nPromote your account here!\n\n____________________\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend\n- X -> @jogjalendpm\n\nTap Post to start!", kb)
        elif cdata.startswith("del_"):
            mid=cdata.replace("del_","")
            if mid.isdigit():
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)})
                send(chat_id, "🗑️ Deleted from channel", back_kb())
        # ADMIN
        if is_admin(chat_id) and cdata.startswith("admin_"):
            if cdata=="admin_panel":
                total_t=sum(u["today_text"] for u in USERS.values())
                kb={"inline_keyboard": [[{"text": f"👥 {len(USERS)} Users", "callback_data": "admin_users"}, {"text": f"📈 {total_t} Today", "callback_data": "admin_stats"}], [{"text": "📢 Broadcast", "callback_data": "admin_bc"}, {"text": "📋 List", "callback_data": "admin_list"}], [{"text": "🔄 Reset", "callback_data": "admin_reset"}], [{"text": "« Back", "callback_data": "back_home"}]]}
                send(chat_id, f"🔐 ADMIN PANEL\nUsers: {len(USERS)}\nToday: {total_t}", kb)
            elif cdata=="admin_list": send(chat_id, "\n".join([f"{k} {v['today_text']}/5" for k,v in list(USERS.items())[:20]]), back_kb())
            elif cdata=="admin_reset":
                for u in USERS.values(): u["today_text"]=0; u["today_media"]=0
                send(chat_id, "Reset done", back_kb())
            elif cdata=="admin_bc": send(chat_id, "Ketik /broadcast pesan", back_kb())
            elif cdata=="admin_users": send(chat_id, f"Total {len(USERS)}", back_kb())
            elif cdata=="admin_stats": send(chat_id, f"Total users {len(USERS)}", back_kb())

    return "ok",200
