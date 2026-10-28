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
    "await_threads": False, "last_msg_id": None
})

def get_user(uid):
    u = USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today:
        u["today_text"]=0; u["today_media"]=0; u["last_date"]=today
    return u

def is_admin(uid):
    return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def send(chat_id, text, kb=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb:
        payload["reply_markup"]=kb
    return requests.post(url, json=payload).json()

def send_channel(text, media=None):
    try:
        if media:
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                json={"chat_id": CHANNEL_ID, "photo": media, "caption": text, "parse_mode": "HTML"}).json()
        else:
            r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}).json()
        return r.get("result", {}).get("message_id")
    except:
        return None

def send_success_reply(chat_id, user, ch_msg_id):
    threads_st = "ON" if user["threads_on"] else "OFF"
    posted_to = "Telegram + Threads" if user["threads_on"] else "Telegram only"
    
    # BALASAN PERSIS FOTO LU
    reply = f"""Menfess sent!
Remaining quota:
Text : {user['today_text']}/5
Media : {user['today_media']}/5
Successfully posted to {posted_to} (Threads {threads_st})
Join Channel : {CHANNEL_ID}"""

    # TOMBOL DINAMIS
    channel_url = f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
    
    inline_kb = []
    inline_kb.append([{"text": "See on channel", "url": channel_url}])
    
    # KALAU THREADS ON, MUNCUL SEE ON THREADS
    if user["threads_on"] and user["threads_user"]:
        t_user = user["threads_user"].replace("@","")
        inline_kb.append([{"text": "See on Threads", "url": f"https://www.threads.net/@{t_user}"}])
    
    inline_kb.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}" if ch_msg_id else "del_none"}])
    
    kb = {"inline_keyboard": inline_kb}
    send(chat_id, reply, kb)

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET":
        return "V61 FINAL FIX - SEE ON THREADS - LIVE",200

    data = request.get_json(force=True, silent=True) or {}
    
    # MESSAGE HANDLER
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id)
        user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg:
            user["name"]=msg["from"].get("first_name","")
            if msg["from"].get("last_name"):
                user["name"] += " " + msg["from"].get("last_name")
            user["username"]=msg["from"].get("username","")

        # COMMANDS
        if text.startswith("/start"):
            kb={"inline_keyboard": [
                [{"text": "My Profile", "callback_data": "my_profile"}],
                [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}],
                [{"text": "Threads Setting", "callback_data": "threads"}],
                [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]
            ]}
            if is_admin(chat_id):
                kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"""Hi {user['name'] or 'there'}!
Promote your account here!

____________________

Publish to:
- Channel -> @menfessangel
- Threads -> @jogjalend [optional]
- X -> @jogjalendpm [maintenance]

Tap Post to start!""", kb)

        elif text.startswith("/broadcast ") and is_admin(chat_id):
            bc=text.replace("/broadcast ","")
            cnt=0
            for uid2 in list(USERS.keys()):
                try: send(uid2, f"📢 <b>Broadcast</b>\n\n{bc}"); cnt+=1
                except: pass
            send(chat_id, f"✅ Broadcast ke {cnt} user")

        elif text.startswith("/ban ") and is_admin(chat_id):
            try: USERS[text.split()[1]]["banned"]=True; send(chat_id, "🚫 Banned")
            except: send(chat_id, "Format: /ban USER_ID")
        elif text.startswith("/unban ") and is_admin(chat_id):
            try: USERS[text.split()[1]]["banned"]=False; send(chat_id, "✅ Unbanned")
            except: send(chat_id, "Format: /unban USER_ID")

        elif user["banned"]:
            send(chat_id, "🚫 You are banned. Contact @jogjalend")

        else:
            # SET THREADS USERNAME
            if user.get("await_threads") and text and not text.startswith("/"):
                if text.strip()=="-":
                    user["threads_user"]=""; user["threads_on"]=False; user["await_threads"]=False
                    send(chat_id, "✅ Threads removed. Now OFF")
                elif text.startswith("@") and len(text)>=3:
                    user["threads_user"]=text.strip(); user["threads_on"]=True; user["await_threads"]=False
                    send(chat_id, f"✅ Threads set to {text} (ON)")
                else:
                    send(chat_id, "⚠️ Send @username or - to remove")

            # TEXT MENFESS
            elif text and not text.startswith("/") and len(text)>=3:
                if user["today_text"]>=5:
                    send(chat_id, "⚠️ Text limit 5/5 reached. Reset 00:00 WIB")
                else:
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    final = f"{text}\n\n—\n<i>{tgl}</i>"
                    if user["threads_on"] and user["threads_user"]:
                        final += f"\n🧵 {user['threads_user']}"
                    ch_id = send_channel(final)
                    user["today_text"]+=1; user["total_text"]+=1
                    send_success_reply(chat_id, user, ch_id)

            # MEDIA MENFESS
            if "photo" in msg or "video" in msg or "animation" in msg:
                if user["today_media"]>=5:
                    send(chat_id, "⚠️ Media limit 5/5 reached")
                else:
                    fid=None
                    if "photo" in msg: fid=msg["photo"][-1]["file_id"]
                    elif "video" in msg: fid=msg["video"]["file_id"]
                    elif "animation" in msg: fid=msg["animation"]["file_id"]
                    
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    cap = f"{caption}\n\n—\n<i>{tgl}</i>" if caption else f"<i>{tgl}</i>"
                    if user["threads_on"] and user["threads_user"]:
                        cap+=f"\n🧵 {user['threads_user']}"
                    
                    ch_id = send_channel(cap, media=fid)
                    user["today_media"]+=1; user["total_media"]+=1
                    send_success_reply(chat_id, user, ch_id)

    # CALLBACK HANDLER
    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
        except: pass

        if cdata=="my_profile":
            threads_st="ON" if user["threads_on"] else "OFF"
            send(chat_id, f"""My Profile
____________________

Name: {user['name']}
ID: {uid}
Username: @{user['username'] or '-'}

Text: {user['today_text']}/5
Media: {user['today_media']}/5
Threads: {threads_st}""")
        
        elif cdata=="rules":
            send(chat_id, "📜 Rules\n\n1. No SARA, porn, spam\n2. No doxxing\n3. Limit 5 text & 5 media / day\n4. Be polite\n5. Admin can reject/ban")

        elif cdata=="post":
            send(chat_id, "📝 Send your menfess now (text/photo/video). It will auto post to @menfessangel")

        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set @Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"🧵 Threads Setting\n\nStatus: {'ON' if user['threads_on'] else 'OFF'}\nUsername: {user['threads_user'] or '-'}", kb)

        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, "✅ Threads: ON")
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, "✅ Threads: OFF")
        elif cdata=="threads_set": user["await_threads"]=True; send(chat_id, "Send @threads username (ex: @jogjalend) or send - to remove")

        elif cdata=="stats":
            send(chat_id, f"📊 Stats\n\nToday: Text {user['today_text']}/5 Media {user['today_media']}/5\nTotal: {user['total_text']} text {user['total_media']} media")

        elif cdata=="help":
            send(chat_id, "ℹ️ Help\n\nChannel: @menfessangel\nAdmin: @jogjalend\n/start for menu")

        elif cdata=="back_home":
            kb={"inline_keyboard": [[{"text": "My Profile", "callback_data": "my_profile"}], [{"text": "Rules", "callback_data": "rules"}, {"text": "Post", "callback_data": "post"}], [{"text": "Threads Setting", "callback_data": "threads"}], [{"text": "Stats", "callback_data": "stats"}, {"text": "Help", "callback_data": "help"}]]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL", "callback_data": "admin_panel"}])
            send(chat_id, f"Hi {user['name'] or 'there'}!\nPromote your account here!\n\nPublish to:\n- Channel -> @menfessangel\n- Threads -> @jogjalend", kb)

        # DELETE FEATURE
        elif cdata.startswith("del_"):
            mid = cdata.replace("del_","")
            if mid=="none" or not mid.isdigit():
                send(chat_id, "❌ Cannot delete")
            else:
                try:
                    resp = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}).json()
                    if resp.get("ok"):
                        send(chat_id, "🗑️ Deleted from channel")
                    else:
                        send(chat_id, f"❌ Failed delete: {resp.get('description')}")
                except Exception as e:
                    send(chat_id, f"❌ Error: {e}")
            # remove buttons from original success message
            try:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup", json={"chat_id": chat_id, "message_id": cq["message"]["message_id"], "reply_markup": {"inline_keyboard": []}})
            except: pass

        # ADMIN PANEL BANYAK FITUR
        if is_admin(chat_id) and cdata.startswith("admin_"):
            if cdata=="admin_panel":
                total_t=sum(u["today_text"] for u in USERS.values()); total_m=sum(u["today_media"] for u in USERS.values())
                kb={"inline_keyboard": [
                    [{"text": f"👥 {len(USERS)} Users", "callback_data": "admin_users"}, {"text": f"📈 {total_t}T {total_m}M Today", "callback_data": "admin_stats"}],
                    [{"text": "📢 Broadcast", "callback_data": "admin_bc"}, {"text": "📋 List 20", "callback_data": "admin_list"}],
                    [{"text": "🔄 Reset All", "callback_data": "admin_reset"}, {"text": "🚫 Banned List", "callback_data": "admin_banlist"}],
                    [{"text": "« Back", "callback_data": "back_home"}]
                ]}
                send(chat_id, f"🔐 ADMIN PANEL\n\nUsers: {len(USERS)}\nToday: {total_t} text {total_m} media\n\nCommands:\n/broadcast text\n/ban id\n/unban id", kb)
            elif cdata=="admin_list":
                txt="📋 20 users:\n\n"
                for k,v in list(USERS.items())[:20]: txt+=f"<code>{k}</code> @{v['username'] or '-'} T{v['today_text']} M{v['today_media']}\n"
                send(chat_id, txt)
            elif cdata=="admin_banlist":
                banned=[f"<code>{k}</code>" for k,v in USERS.items() if v["banned"]]
                send(chat_id, "🚫 Banned:\n" + ("\n".join(banned) if banned else "None"))
            elif cdata=="admin_reset":
                for u in USERS.values(): u["today_text"]=0; u["today_media"]=0
                send(chat_id, "✅ All limits reset")
            elif cdata=="admin_bc": send(chat_id, "Use: /broadcast your message")
            elif cdata=="admin_users": send(chat_id, f"Total users: {len(USERS)}")
            elif cdata=="admin_stats": send(chat_id, f"Total: {len(USERS)} users\nToday OK")

    return "ok",200
