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
    "threads_user": "", "threads_on": False,
    "today_text": 0, "today_media": 0, "last_date": "", 
    "banned": False, "total_text": 0, "total_media": 0,
    "await_threads": False, "username": ""
})

def get_today(): return datetime.now(WIB).strftime("%Y-%m-%d")
def get_user(uid):
    u = USERS[uid]
    today = get_today()
    if u["last_date"] != today:
        u["today_text"]=0; u["today_media"]=0; u["last_date"]=today
    return u
def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False
def send(chat_id, text, kb=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb: payload["reply_markup"]=kb
    requests.post(url, json=payload)
def send_channel(text, media=None):
    try:
        if media:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": media, "caption": text, "parse_mode": "HTML"})
        else:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"})
    except: pass

@app.route("/", methods=["GET"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET":
        return "V58 KEEP DESIGN + SUPER ADMIN - LIVE",200
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        msg=data["message"]; chat_id=msg["chat"]["id"]; uid=str(chat_id)
        user=get_user(uid); text=msg.get("text",""); caption=msg.get("caption","")
        if "from" in msg: user["username"] = msg["from"].get("username","")

        # COMMANDS
        if text.startswith("/start"):
            threads_status = "OFF ❌" # default OFF kayak screenshot lu
            if user["threads_on"]: threads_status="ON ✅"
            start_text = f"""Menfess Angel • o f f i c i a l

Your post will be published to:

Channel → @menfessangel
Threads → @jogjalend [optional]
X → @jogjalendpm [maintenance]

Threads mode: {threads_status}
Daily reset: 00:00 WIB
Limit: 5 texts & 5 media"""
            kb = {"inline_keyboard": [
                [{"text": "👤 Profile", "callback_data": "profil"}],
                [{"text": "📜 Rules", "callback_data": "rules"}, {"text": "📝 Post Menfess", "callback_data": "post"}],
                [{"text": "🧵 Threads Setting", "callback_data": "threads"}],
                [{"text": "📊 Stats", "callback_data": "stats"}, {"text": "ℹ️ Help", "callback_data": "help"}]
            ]}
            if is_admin(chat_id):
                kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL - BANYAK FITUR", "callback_data": "admin_panel"}])
            send(chat_id, start_text, kb)

        elif text.startswith("/admin") and is_admin(chat_id):
            # trigger admin panel
            data["callback_query"]={"message":{"chat":{"id":chat_id}},"data":"admin_panel","id":"0"}
        
        elif text.startswith("/broadcast ") and is_admin(chat_id):
            bc_text=text.replace("/broadcast ","")
            cnt=0
            for u_id in list(USERS.keys()):
                try: send(u_id, f"📢 <b>Broadcast Admin @menfessangel</b>\n\n{bc_text}"); cnt+=1
                except: pass
            send(chat_id, f"✅ Broadcast ke {cnt} user selesai")

        elif text.startswith("/ban ") and is_admin(chat_id):
            target=text.split(" ")[1]
            if target in USERS: USERS[target]["banned"]=True; send(chat_id, f"🚫 {target} dibanned")
            else: send(chat_id, "ID tidak ditemukan")

        elif text.startswith("/unban ") and is_admin(chat_id):
            target=text.split(" ")[1]
            if target in USERS: USERS[target]["banned"]=False; send(chat_id, f"✅ {target} diunban")
            else: send(chat_id, "ID tidak ditemukan")

        elif user["banned"]:
            send(chat_id, "🚫 Lu kebanned. Hubungi @jogjalend")
        else:
            # SET THREADS USERNAME
            if user.get("await_threads") and text:
                if text.strip()=="-":
                    user["threads_user"]=""; user["await_threads"]=False
                    send(chat_id, "✅ Threads username dihapus, mode jadi OFF ❌")
                elif text.startswith("@") and len(text)>=3:
                    user["threads_user"]=text.strip(); user["await_threads"]=False; user["threads_on"]=True
                    send(chat_id, f"✅ Threads set: {text} (ON ✅)\n/start untuk lihat")
                elif not text.startswith("/"):
                    send(chat_id, "⚠️ Kirim format @username atau -")
            # MENFESS TEXT
            elif text and not text.startswith("/") and len(text)>=3:
                if len(text)<5:
                    send(chat_id, "⚠️ Minimal 5 karakter su")
                elif user["today_text"]>=5:
                    send(chat_id, "⚠️ Limit text hari ini 5/5 habis. Reset 00:00 WIB")
                else:
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    final=f"{text}\n\n—\n<i>{tgl} • via Menfess Angel</i>"
                    if user["threads_on"] and user["threads_user"]: final+=f"\n🧵 {user['threads_user']}"
                    send_channel(final); user["today_text"]+=1; user["total_text"]+=1
                    send(chat_id, f"✅ Menfess terkirim! ({user['today_text']}/5)\nCek: {CHANNEL_ID}")

            # MENFESS MEDIA
            if "photo" in msg or "video" in msg or "animation" in msg:
                if user["today_media"]>=5:
                    send(chat_id, "⚠️ Limit media 5/5 habis")
                else:
                    fid=msg["photo"][-1]["file_id"] if "photo" in msg else (msg.get("video",{}).get("file_id") or msg.get("animation",{}).get("file_id"))
                    tgl=datetime.now(WIB).strftime("%d %b %H:%M WIB")
                    cap_text = f"{caption}\n\n—\n<i>{tgl} • via Menfess Angel</i>" if caption else f"<i>{tgl} • via Menfess Angel</i>"
                    if user["threads_on"] and user["threads_user"]: cap_text+=f"\n🧵 {user['threads_user']}"
                    send_channel(cap_text, media=fid); user["today_media"]+=1; user["total_media"]+=1
                    send(chat_id, f"✅ Media terkirim! ({user['today_media']}/5)")

    if "callback_query" in data:
        cq=data["callback_query"]; chat_id=cq["message"]["chat"]["id"]; uid=str(chat_id); user=get_user(uid); cdata=cq["data"]
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cq["id"]})
        except: pass

        # USER MENU (TETAP KAYAK SCREENSHOT)
        if cdata=="profil":
            send(chat_id, f"👤 <b>Profile</b>\n\nID: <code>{chat_id}</code>\nUsername: @{user['username'] or '-'}\nThreads: {user['threads_user'] or '-'} ({'ON ✅' if user['threads_on'] else 'OFF ❌'})\n\nHari ini:\nText: {user['today_text']}/5\nMedia: {user['today_media']}/5\n\nTotal: {user['total_text']} text, {user['total_media']} media\n\n3. No doxxing")
        elif cdata=="rules":
            send(chat_id, "📜 <b>Rules</b>\n\n1. No SARA, porn, spam\n2. No doxxing / sebar data pribadi\n3. Limit 5/hari\n4. Bahasa sopan\n5. Admin berhak reject\n\nMelanggar = banned")
        elif cdata=="post":
            send(chat_id, "📝 <b>Post Menfess</b>\n\nLangsung kirim text / foto / video / gif.\n\nAkan auto ke @menfessangel\n\nKetik /cancel buat batal")
        elif cdata=="threads":
            kb={"inline_keyboard": [[{"text": "ON ✅", "callback_data": "threads_on"}, {"text": "OFF ❌", "callback_data": "threads_off"}], [{"text": "Set @Username", "callback_data": "threads_set"}], [{"text": "« Back", "callback_data": "back_home"}]]}
            send(chat_id, f"🧵 <b>Threads Setting</b>\n\nStatus: {'ON ✅' if user['threads_on'] else 'OFF ❌'}\nUsername: {user['threads_user'] or '-'}\n\nKalau ON, username muncul di bawah menfess", kb)
        elif cdata=="threads_on": user["threads_on"]=True; send(chat_id, "🧵 Threads: ON ✅")
        elif cdata=="threads_off": user["threads_on"]=False; send(chat_id, "🧵 Threads: OFF ❌")
        elif cdata=="threads_set": user["await_threads"]=True; send(chat_id, "🧵 Kirim @username Threads lu\n\nContoh: @jogjalend\nKirim - untuk hapus")
        elif cdata=="stats": send(chat_id, f"📊 <b>Stats</b>\n\nToday: {user['today_text']}/5 text, {user['today_media']}/5 media\nTotal: {user['total_text']} text, {user['total_media']} media")
        elif cdata=="help": send(chat_id, "ℹ️ <b>Help</b>\n\nChannel: @menfessangel\nAdmin: @jogjalend\n\n/start - menu utama")
        elif cdata=="back_home":
            threads_status="OFF ❌" if not user["threads_on"] else "ON ✅"
            start_text = f"""Menfess Angel • o f f i c i a l

Your post will be published to:

Channel → @menfessangel
Threads → @jogjalend [optional]
X → @jogjalendpm [maintenance]

Threads mode: {threads_status}
Daily reset: 00:00 WIB
Limit: 5 texts & 5 media"""
            kb = {"inline_keyboard": [
                [{"text": "👤 Profile", "callback_data": "profil"}],
                [{"text": "📜 Rules", "callback_data": "rules"}, {"text": "📝 Post Menfess", "callback_data": "post"}],
                [{"text": "🧵 Threads Setting", "callback_data": "threads"}],
                [{"text": "📊 Stats", "callback_data": "stats"}, {"text": "ℹ️ Help", "callback_data": "help"}]
            ]}
            if is_admin(chat_id): kb["inline_keyboard"].append([{"text": "🔐 ADMIN PANEL - BANYAK FITUR", "callback_data": "admin_panel"}])
            send(chat_id, start_text, kb)

        # SUPER ADMIN PANEL
        if is_admin(chat_id) and cdata.startswith("admin_"):
            if cdata=="admin_panel":
                total_t=sum(u["today_text"] for u in USERS.values()); total_m=sum(u["today_media"] for u in USERS.values()); banned=len([u for u in USERS.values() if u["banned"]])
                kb={"inline_keyboard": [
                    [{"text": f"👥 Users: {len(USERS)}", "callback_data": "admin_users"}, {"text": f"📈 Today: {total_t}T {total_m}M", "callback_data": "admin_stats"}],
                    [{"text": "📢 Broadcast", "callback_data": "admin_bc"}, {"text": f"🚫 Banned: {banned}", "callback_data": "admin_banlist"}],
                    [{"text": "🔄 Reset All Limit", "callback_data": "admin_reset"}, {"text": "📋 List User 20", "callback_data": "admin_list"}],
                    [{"text": "🗑️ Clear DB", "callback_data": "admin_clear"}, {"text": "« Back Home", "callback_data": "back_home"}]
                ]}
                send(chat_id, f"🔐 <b>SUPER ADMIN PANEL</b>\n\nBot: Menfess Angel\nChannel: {CHANNEL_ID}\n\nTotal User: {len(USERS)}\nToday: {total_t} text, {total_m} media\nBanned: {banned}\n\n<b>Commands:</b>\n/broadcast PESAN\n/ban USER_ID\n/unban USER_ID\n\nKlik menu di bawah:", kb)
            elif cdata=="admin_users" or cdata=="admin_stats":
                total_t=sum(u["today_text"] for u in USERS.values()); total_m=sum(u["today_media"] for u in USERS.values()); total_all_t=sum(u["total_text"] for u in USERS.values()); total_all_m=sum(u["total_media"] for u in USERS.values())
                send(chat_id, f"📊 <b>Stats Detail</b>\n\nDate: {get_today()}\nUsers: {len(USERS)}\n\nToday:\n• Text: {total_t}\n• Media: {total_m}\n\nAll time:\n• Text: {total_all_t}\n• Media: {total_all_m}")
            elif cdata=="admin_bc":
                send(chat_id, "📢 <b>Broadcast</b>\n\nKetik:\n<code>/broadcast Halo guys, bot update fitur baru!</code>\n\nAkan kirim ke semua user")
            elif cdata=="admin_banlist":
                banned=[f"{k} (@{v['username']})" if v['username'] else k for k,v in USERS.items() if v["banned"]]
                txt="🚫 <b>Banned List:</b>\n\n" + ("\n".join(banned) if banned else "Kosong, belum ada yang kebanned") + "\n\n/unban ID untuk unban\n/ban ID untuk ban"
                send(chat_id, txt)
            elif cdata=="admin_list":
                lst=list(USERS.items())[:25]
                txt="📋 <b>25 User Terbaru:</b>\n\n"
                for uid,u in lst:
                    txt+=f"<code>{uid}</code> @{u['username'] or '-'} | {u['today_text']}T {u['today_media']}M {'🚫' if u['banned'] else ''}\n"
                send(chat_id, txt)
            elif cdata=="admin_reset":
                for u in USERS.values(): u["today_text"]=0; u["today_media"]=0
                send(chat_id, "✅ Semua limit user direset jadi 0/5")
            elif cdata=="admin_clear":
                kb={"inline_keyboard": [[{"text": "✅ YA HAPUS SEMUA", "callback_data": "admin_clear_yes"}, {"text": "❌ BATAL", "callback_data": "admin_panel"}]]}
                send(chat_id, "⚠️ Yakin hapus semua data user? Tidak bisa undo!", kb)
            elif cdata=="admin_clear_yes":
                USERS.clear(); send(chat_id, "🗑️ Database dikosongkan")

    return "ok",200
