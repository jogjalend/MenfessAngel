import os, io, json, requests
from flask import Flask, request
from PIL import Image
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
CHANNEL_USERNAME = "menfessangel"
HASHTAG = "\n\n#jogjalend"
QUOTA_FILE = "/tmp/quota.json"
SETTINGS_FILE = "/tmp/settings.json"
BLOCKED_FILE = "/tmp/blocked.json"
MEMBERS_FILE = "/tmp/members.json"
LIMIT_TEXT = 5
LIMIT_MEDIA = 5
WIB = timezone(timedelta(hours=7))
SESSION = requests.Session()
ADMIN_IDS = [8584319568]

LOGO_CACHE = None
for p in ["logo.png","api/logo.png"]:
    if os.path.exists(p):
        try: LOGO_CACHE = Image.open(p).convert("RGBA"); break
        except: pass

def load_json(path):
    try:
        if os.path.exists(path):
            with open(path,"r") as f: return json.load(f)
    except: pass
    return {}
def save_json(path, d):
    try:
        with open(path,"w") as f: json.dump(d,f)
    except: pass

def load_quota(): return load_json(QUOTA_FILE)
def save_quota(d): save_json(QUOTA_FILE, d)
def load_settings(): return load_json(SETTINGS_FILE)
def save_settings(d): save_json(SETTINGS_FILE, d)
def load_blocked(): return load_json(BLOCKED_FILE)
def save_blocked(d): save_json(BLOCKED_FILE, d)
def load_members(): return load_json(MEMBERS_FILE)
def save_members(d): save_json(MEMBERS_FILE, d)

def is_admin(chat_id): return int(chat_id) in ADMIN_IDS
def is_blocked(chat_id): return str(chat_id) in load_blocked()
def is_threads_enabled(chat_id): return load_settings().get(str(chat_id),{}).get("threads", False)
def set_threads_enabled(chat_id, v):
    s = load_settings()
    if str(chat_id) not in s: s[str(chat_id)] = {}
    s[str(chat_id)]["threads"] = v
    save_settings(s)
def get_today_key(chat_id): return f"{chat_id}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
def add_hashtag(text):
    if not text: return HASHTAG.strip()
    if "#jogjalend" in text.lower(): return text
    return text.strip() + HASHTAG

def add_watermark_fast(b):
    if not LOGO_CACHE: return b
    try:
        base = Image.open(io.BytesIO(b)).convert("RGBA")
        w,h = base.size
        logo = LOGO_CACHE.copy()
        logo.thumbnail((int(w*0.20), int(w*0.20)), Image.LANCZOS)
        pad = int(w*0.03)
        base.paste(logo, (w-logo.width-pad, h-logo.height-pad), logo)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
        return out.getvalue()
    except: return b

def get_start_text(chat_id):
    on = is_threads_enabled(chat_id)
    mode = "ON ✅" if on else "OFF ❌"
    title = "𝗠𝗲𝗻𝗳𝗲𝘀𝘀 𝗔𝗻𝗴𝗲𝗹 • 𝗼 𝗳 𝗳 𝗶 𝗰 𝗶 𝗮 𝗹"
    return f"{title}\n\nYour post will be published to:\n\n  Channel → @menfessangel\n  Threads → @jogjalend [optional]\n  X → @jogjalendpm [maintenance]\n\nThreads mode: {mode}\nDaily reset: 00:00 WIB\nLimit: 5 texts & 5 media"

def get_main_menu(chat_id):
    if is_admin(chat_id):
        return {"inline_keyboard": [
            [{"text":"👤 Profile","callback_data":"profil"}],
            [{"text":"📜 Rules","callback_data":"menu_rules"}, {"text":"📝 Post Menfess","callback_data":"menu_post"}],
            [{"text":"🧵 Threads Setting","callback_data":"menu_threads"}],
            [{"text":"👑 Admin","callback_data":"admin_panel"}, {"text":"ℹ️ Help","callback_data":"menu_help"}]
        ]}
    else:
        return {"inline_keyboard": [
            [{"text":"👤 Profile","callback_data":"profil"}],
            [{"text":"📜 Rules","callback_data":"menu_rules"}, {"text":"📝 Post Menfess","callback_data":"menu_post"}],
            [{"text":"🧵 Threads Setting","callback_data":"menu_threads"}],
            [{"text":"📊 Stats","callback_data":"menu_stats"}, {"text":"ℹ️ Help","callback_data":"menu_help"}]
        ]}

def get_admin_menu():
    return {"inline_keyboard": [
        [{"text":"🚫 Blokir User","callback_data":"admin_block"}, {"text":"✅ Unblock","callback_data":"admin_unblock"}],
        [{"text":"👥 Cek Anggota","callback_data":"admin_members"}, {"text":"📋 Cek Blokir","callback_data":"admin_blocked"}],
        [{"text":"🗑️ Hapus Anggota","callback_data":"admin_del_member"}, {"text":"🔄 Reset Quota","callback_data":"admin_reset"}],
        [{"text":"📢 Broadcast","callback_data":"admin_broadcast"}, {"text":"📊 Global Stats","callback_data":"admin_stats"}],
        [{"text":"🔙 Back","callback_data":"menu_main"}]
    ]}

@app.route("/", methods=['GET'])
def home(): return "Bot V23 Full",200

@app.route("/", methods=['POST'])
@app.route("/api/index.py", methods=['POST'])
def handler():
    try:
        data = request.get_json()
        if not data: return "ok",200
        
        if "callback_query" in data:
            cq = data["callback_query"]
            cb_data = cq["data"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})

            if cb_data.startswith("delete_post_"):
                try:
                    target_id = int(cb_data.replace("delete_post_",""))
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":target_id})
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"🗑️ Post berhasil dihapus"})
                except Exception as e:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Gagal hapus: {e}"})
                return "ok",200

            if cb_data in ["menu_main", "back_to_start"]:
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)})
                return "ok",200
            elif cb_data == "admin_panel":
                if not is_admin(chat_id): return "ok",200
                members = load_members(); blocked = load_blocked()
                txt = f"👑 ADMIN PANEL\n👥 Anggota: {len(members)}\n🚫 Blokir: {len(blocked)}\n\n/block 123\n/unblock 123\n/del_member 123"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":get_admin_menu()})
                return "ok",200
            elif cb_data == "admin_members" and is_admin(chat_id):
                members = load_members()
                txt = "👥 Anggota (20 terbaru):\n\n" + "\n".join([f"ID: {k} | @{v.get('username','-')} | {v.get('name','-')}" for k,v in list(members.items())[-20:]]) if members else "Belum ada anggota"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt[:4000],"reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            elif cb_data == "admin_blocked" and is_admin(chat_id):
                blocked = load_blocked()
                txt = "📋 LIST BLOKIR:\n\n" + "\n".join([f"ID: {k} | {v}" for k,v in blocked.items()]) if blocked else "Tidak ada blokir"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt[:4000],"reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            elif cb_data in ["admin_block","admin_unblock","admin_del_member","admin_reset","menu_post","menu_stats","menu_rules","menu_help","admin_stats","admin_broadcast"]:
                if cb_data == "admin_reset": save_quota({}); txt="✅ Quota reset!"
                elif cb_data == "admin_stats": txt=f"📊 GLOBAL\nQuota: {len(load_quota())}\nMembers: {len(load_members())}\nBlocked: {len(load_blocked())}"
                elif cb_data == "admin_broadcast": txt="📢 Kirim: /broadcast pesan"
                elif cb_data == "menu_stats": txt=f"📊 STATS\n{load_quota().get(get_today_key(chat_id), {'text':0,'media':0})}"
                elif cb_data == "menu_post": txt="📝 Kirim text/foto langsung untuk post"
                elif cb_data == "menu_rules": txt="📜 RULES\n1. No Spam\n2. No SARA\n3. No Doxxing"
                else: txt="ℹ️ HELP\n/start untuk menu"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"🔙 Back","callback_data":"admin_panel" if 'admin' in cb_data else "menu_main"}]]}})
                return "ok",200
            elif cb_data in ["profil","menu_threads","toggle_threads"]:
                if cb_data == "toggle_threads": set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                q = load_quota().get(get_today_key(chat_id), {"text":0,"media":0})
                on = is_threads_enabled(chat_id)
                txt = f"👤 PROFILE\nID: {chat_id}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}\nThreads: {'ON ✅' if on else 'OFF ❌'}"
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON ✅' if on else 'OFF ❌'}","callback_data":"toggle_threads"}],[{"text":"🔙 Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text","")

        members = load_members()
        if str(chat_id) not in members:
            members[str(chat_id)] = {"username": msg["from"].get("username","-"), "name": msg["from"].get("first_name","-"), "joined": datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}
            save_members(members)

        if is_blocked(chat_id) and not is_admin(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"🚫 Lu diblokir admin @jogja_lend"})
            return "ok",200

        if is_admin(chat_id) and text.startswith("/"):
            if text.startswith("/block "):
                target = text.split()[1]; b=load_blocked(); b[target]=f"blocked {datetime.now(WIB)}"; save_blocked(b)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"✅ {target} diblokir"}); return "ok",200
            elif text.startswith("/unblock "):
                target = text.split()[1]; b=load_blocked(); b.pop(target,None); save_blocked(b)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"✅ {target} di unblock"}); return "ok",200
            elif text.startswith("/del_member "):
                target = text.split()[1]; m=load_members(); q=load_quota()
                if target in m: del m[target]
                for k in list(q.keys()):
                    if k.startswith(target+"_"): del q[k]
                save_members(m); save_quota(q)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"🗑️ {target} dihapus"}); return "ok",200
            elif text.startswith("/broadcast "):
                pesan = text.replace("/broadcast ",""); m=load_members(); c=0
                for mid in m:
                    try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":mid,"text":f"📢 BROADCAST:\n\n{pesan}"}); c+=1
                    except: pass
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"✅ Broadcast ke {c}"}); return "ok",200

        if text.startswith(("/start","/menu","/admin")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)})
            return "ok",200

        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        
        quotas = load_quota()
        key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)

        if is_media and quotas[key]["media"] >= LIMIT_MEDIA:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Limit media habis\nSisa kuota :\nText : {quotas[key]['text']}/{LIMIT_TEXT}\nMedia : {quotas[key]['media']}/{LIMIT_MEDIA}"})
            return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Limit text habis\nSisa kuota :\nText : {quotas[key]['text']}/{LIMIT_TEXT}\nMedia : {quotas[key]['media']}/{LIMIT_MEDIA}"})
            return "ok",200

        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fp = r["result"]["file_path"]
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}").content
            fb = add_watermark_fast(fb)
            files = {"photo": ("menfess.jpg", fb, "image/jpeg")}
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30).json()
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}).json()

        if res.get("ok"):
            posted_msg_id = res["result"]["message_id"]
            if is_media: quotas[key]["media"] += 1
            else: quotas[key]["text"] += 1
            save_quota(quotas)
            
            used_text = quotas[key]["text"]
            used_media = quotas[key]["media"]
            threads_on = is_threads_enabled(chat_id)

            if threads_on:
                keterangan = f"Berhasil posting ke Telegram & Threads (Threads ON)\nJoin Channel : @{CHANNEL_USERNAME}\nThreads : @jogjalend"
            else:
                keterangan = f"Berhasil posting ke Telegram only (Threads OFF)\nJoin Channel : @{CHANNEL_USERNAME}"

            success_text = (
                f"Menfess terkirim!\n"
                f"Sisa kuota :\n"
                f"Text : {used_text}/{LIMIT_TEXT}\n"
                f"Media : {used_media}/{LIMIT_MEDIA}\n"
                f"{keterangan}"
            )

            telegram_link = f"https://t.me/{CHANNEL_USERNAME}/{posted_msg_id}"
            threads_link = f"https://www.threads.net/@jogjalend"

            if threads_on:
                buttons = {
                    "inline_keyboard": [
                        [{"text":"See on channel","url": telegram_link}, {"text":"See on Threads","url": threads_link}],
                        [{"text":"Delete","callback_data": f"delete_post_{posted_msg_id}"}]
                    ]
                }
            else:
                buttons = {
                    "inline_keyboard": [
                        [{"text":"See on channel","url": telegram_link}],
                        [{"text":"Delete","callback_data": f"delete_post_{posted_msg_id}"}]
                    ]
                }

            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":success_text,"reply_markup":buttons})
        else:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"❌ Gagal: {res.get('description')}"})

    except Exception as e:
        print(f"ERR {e}")
    return "ok",200
