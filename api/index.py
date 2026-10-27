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
        logo.thumbnail((int(w*0.18), int(w*0.18)), Image.LANCZOS)
        pad = int(w*0.035)
        base.paste(logo, (w-logo.width-pad, h-logo.height-pad), logo)
        out = io.BytesIO()
        base.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
        return out.getvalue()
    except: return b

def get_real_channel_count():
    try:
        r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id={CHANNEL_ID}", timeout=10).json()
        if r.get("ok"): return r["result"]
        r2 = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount?chat_id=@{CHANNEL_USERNAME}", timeout=10).json()
        if r2.get("ok"): return r2["result"]
    except: pass
    return 0

def make_stats_image():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        members = load_members()
        quota = load_quota()
        real_channel = get_real_channel_count()
        total_text = sum(v.get("text",0) for v in quota.values())
        total_media = sum(v.get("media",0) for v in quota.values())
        total_post = total_text + total_media
        today_str = datetime.now(WIB).strftime('%Y-%m-%d')
        today_post = sum(v.get("text",0)+v.get("media",0) for k,v in quota.items() if today_str in k)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,5))
        fig.patch.set_facecolor('#ffffff')
        labels = ['Text', 'Media']
        vals = [total_text if total_text>0 else 1, total_media if total_media>0 else 1]
        ax1.pie(vals, labels=labels, autopct='%1.0f%%', colors=['#1d9bf0','#ffad1f'])
        ax1.set_title('Post Type', fontweight='bold')
        cats = ['Channel', 'Bot Users', 'Today', 'Total']
        nums = [real_channel, len(members), today_post, total_post]
        ax2.bar(cats, nums, color=['#1d9bf0','#7856ff','#00ba7c','#ffad1f'])
        ax2.set_title(f'@{CHANNEL_USERNAME} - {today_str}', fontweight='bold')
        for i, v in enumerate(nums): ax2.text(i, v+0.2, str(v), ha='center', fontweight='bold')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close()
        buf.seek(0)
        return buf.getvalue(), real_channel
    except Exception as e:
        print(f"stats error {e}")
        return None, get_real_channel_count()

def get_start_text(chat_id, first_name="Jogja Lend"):
    name = first_name if first_name else "there"
    return (
        f"Hi {name}!\n"
        "Promote your account here!\n"
        "______________________________________\n\n"
        "Publish to:\n"
        "• Channel → @menfessangel\n"
        "• Threads → @jogjalend [optional]\n"
        "• X → @jogjalendpm [maintenance]\n\n"
        "Tap Post to start!"
    )

def get_main_menu(chat_id):
    if is_admin(chat_id):
        return {"inline_keyboard": [
            [{"text":"My Profile","callback_data":"profil"}],
            [{"text":"Rules","callback_data":"menu_rules"}, {"text":"Post","callback_data":"menu_post"}],
            [{"text":"Threads Setting","callback_data":"menu_threads"}],
            [{"text":"Admin Panel 👑","callback_data":"admin_panel"}],
            [{"text":"Stats","callback_data":"menu_stats"}, {"text":"Help","callback_data":"menu_help"}]
        ]}
    else:
        return {"inline_keyboard": [
            [{"text":"My Profile","callback_data":"profil"}],
            [{"text":"Rules","callback_data":"menu_rules"}, {"text":"Post","callback_data":"menu_post"}],
            [{"text":"Threads Setting","callback_data":"menu_threads"}],
            [{"text":"Stats","callback_data":"menu_stats"}, {"text":"Help","callback_data":"menu_help"}]
        ]}

def get_admin_menu():
    return {"inline_keyboard": [
        [{"text":"📢 Real Count","callback_data":"admin_real_count"}, {"text":"👥 All Users","callback_data":"admin_members"}],
        [{"text":"🚫 Blocked List","callback_data":"admin_blocked"}, {"text":"🔍 Search User","callback_data":"admin_search"}],
        [{"text":"🚷 Blok User","callback_data":"admin_block"}, {"text":"✅ Unblok User","callback_data":"admin_unblock"}],
        [{"text":"🗑️ Hapus User","callback_data":"admin_del_member"}, {"text":"🔄 Reset Quota","callback_data":"admin_reset"}],
        [{"text":"⬅️ Back","callback_data":"menu_main"}]
    ]}

# HELPER FIX BACK
def delete_and_send_menu(chat_id, msg_id, first_name):
    try:
        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id}, timeout=5)
    except: pass
    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id, first_name),"reply_markup":get_main_menu(chat_id)})

@app.route("/", methods=['GET'])
def home(): return "Bot V43 Fix Back",200
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
            user_first = cq["from"].get("first_name","Jogja Lend")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id":cq["id"]})

            if cb_data.startswith("delete_post_"):
                try:
                    target_id = int(cb_data.replace("delete_post_",""))
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":CHANNEL_ID,"message_id":target_id})
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"✅ Post deleted from channel"})
                except: 
                    try:
                        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
                        SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"✅ Post deleted from channel"})
                    except: pass
                return "ok",200

            if cb_data.startswith("admin_view_"):
                if not is_admin(chat_id): return "ok",200
                target = cb_data.replace("admin_view_","")
                members = load_members(); blocked = load_blocked(); quota = load_quota(); settings = load_settings()
                info = members.get(target, {})
                user_posts = sum(v.get("text",0)+v.get("media",0) for k,v in quota.items() if k.startswith(target+"_"))
                today_key = f"{target}_{datetime.now(WIB).strftime('%Y-%m-%d')}"
                today_q = quota.get(today_key, {"text":0,"media":0})
                is_b = "YES 🚫" if target in blocked else "NO ✅"
                th = "ON" if settings.get(target,{}).get("threads") else "OFF"
                txt = (
                    f"👤 USER DETAIL\n"
                    f"______________________________________\n\n"
                    f"ID: {target}\n"
                    f"Name: {info.get('name','-')}\n"
                    f"Username: @{info.get('username','-')}\n"
                    f"Joined: {info.get('joined','-')}\n\n"
                    f"Blocked: {is_b}\n"
                    f"Threads: {th}\n"
                    f"Today: {today_q['text']} text, {today_q['media']} media\n"
                    f"Total Posts: {user_posts}\n"
                )
                kb = {"inline_keyboard": [
                    [{"text":"🚷 Blok","callback_data":f"admin_block_{target}"}, {"text":"✅ Unblok","callback_data":f"admin_unblock_{target}"}],
                    [{"text":"🗑️ Hapus Data","callback_data":f"admin_del_{target}"}, {"text":"🔄 Reset Quota","callback_data":f"admin_reset_{target}"}],
                    [{"text":"⬅️ Back","callback_data":"admin_members"}]
                ]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200

            if cb_data.startswith("admin_block_"):
                if not is_admin(chat_id): return "ok",200
                target = cb_data.replace("admin_block_","")
                b = load_blocked(); b[target] = "blocked by admin"; save_blocked(b)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"✅ User {target} berhasil di-BLOK","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_members"}]]}})
                return "ok",200

            if cb_data.startswith("admin_unblock_"):
                if not is_admin(chat_id): return "ok",200
                target = cb_data.replace("admin_unblock_","")
                b = load_blocked()
                if target in b: del b[target]; save_blocked(b)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"✅ User {target} berhasil di-UNBLOK","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_blocked"}]]}})
                return "ok",200

            if cb_data.startswith("admin_del_"):
                if not is_admin(chat_id): return "ok",200
                target = cb_data.replace("admin_del_","")
                m = load_members()
                if target in m: del m[target]; save_members(m)
                q = load_quota()
                for k in list(q.keys()):
                    if k.startswith(target+"_"): del q[k]
                save_quota(q)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"🗑️ Data user {target} berhasil dihapus","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_members"}]]}})
                return "ok",200

            if cb_data.startswith("admin_reset_"):
                if not is_admin(chat_id): return "ok",200
                target = cb_data.replace("admin_reset_","")
                q = load_quota()
                for k in list(q.keys()):
                    if k.startswith(target+"_"): del q[k]
                save_quota(q)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"🔄 Quota user {target} direset","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":f"admin_view_{target}"}]]}})
                return "ok",200

            # FIX UTAMA BACK - WORK UNTUK FOTO & TEXT
            if cb_data in ["menu_main", "back_to_start"]:
                delete_and_send_menu(chat_id, msg_id, user_first)
                return "ok",200

            elif cb_data == "menu_stats":
                img_bytes, real_count = make_stats_image()
                members = load_members(); blocked = load_blocked(); quota = load_quota()
                total_post = sum(v.get("text",0)+v.get("media",0) for v in quota.values())
                caption = f"MENFESS ANGEL - STATS\n______________________________________\n\nChannel Subs: {real_count}\nBot Users: {len(members)}\nBlocked: {len(blocked)}\nTotal Posts: {total_post}\nDate: {datetime.now(WIB).strftime('%Y-%m-%d')}"
                # Hapus menu sebelumnya biar gak numpuk
                try: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", json={"chat_id":chat_id,"message_id":msg_id})
                except: pass
                if img_bytes:
                    files = {"photo": ("stats.png", img_bytes, "image/png")}
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":chat_id,"caption":caption,"reply_markup":json.dumps({"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]})}, files=files)
                else:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":{"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}})
                return "ok",200

            elif cb_data == "admin_panel":
                if not is_admin(chat_id): return "ok",200
                real = get_real_channel_count()
                m = load_members(); b = load_blocked(); q = load_quota()
                total = sum(v.get("text",0)+v.get("media",0) for v in q.values())
                txt = f"👑 ADMIN PANEL - KHUSUS LU\n______________________________________\n\n📢 Channel Subs: {real}\n👥 Bot Users: {len(m)}\n🚫 Blocked: {len(b)}\n📊 Total Posts: {total}\n\nID Admin: {chat_id}\nAkses Full!"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":get_admin_menu()})
                return "ok",200
            elif cb_data == "admin_real_count":
                if not is_admin(chat_id): return "ok",200
                real = get_real_channel_count()
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"📢 REAL CHANNEL COUNT\n\n@{CHANNEL_USERNAME}: {real} subs\nUpdate: {datetime.now(WIB).strftime('%Y-%m-%d %H:%M')} WIB","reply_markup":{"inline_keyboard":[[{"text":"Refresh","callback_data":"admin_real_count"}],[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            elif cb_data == "admin_members":
                if not is_admin(chat_id): return "ok",200
                members = load_members()
                if not members:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Belum ada user","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                    return "ok",200
                items = list(members.items())[-15:][::-1]
                kb = []
                txt = f"👥 ALL USERS ({len(members)} total)\n______________________________________\nPencet untuk liat detail:\n\n"
                for uid, info in items:
                    name = info.get('name','-')[:15]
                    txt += f"• {name} - {uid}\n"
                    kb.append([{"text":f"{name} ({uid})","callback_data":f"admin_view_{uid}"}])
                kb.append([{"text":"⬅️ Back","callback_data":"admin_panel"}])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":kb}})
                return "ok",200
            elif cb_data == "admin_blocked":
                if not is_admin(chat_id): return "ok",200
                blocked = load_blocked()
                if not blocked:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Gak ada user diblokir","reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                    return "ok",200
                kb = []
                for uid in list(blocked.keys())[:15]:
                    kb.append([{"text":f"Unblok {uid}","callback_data":f"admin_unblock_{uid}"}])
                kb.append([{"text":"⬅️ Back","callback_data":"admin_panel"}])
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":f"🚫 BLOCKED LIST ({len(blocked)})","reply_markup":{"inline_keyboard":kb}})
                return "ok",200
            elif cb_data in ["admin_block","admin_unblock","admin_search","admin_del_member"]:
                if not is_admin(chat_id): return "ok",200
                instr = {
                    "admin_block": "Kirim: /block USER_ID\nContoh: /block 123456789",
                    "admin_unblock": "Kirim: /unblock USER_ID\nContoh: /unblock 123456789",
                    "admin_search": "Kirim: /search USER_ID\nContoh: /search 123456789",
                    "admin_del_member": "Kirim: /deluser USER_ID\nContoh: /deluser 123456789"
                }
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":instr[cb_data],"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"admin_panel"}]]}})
                return "ok",200
            elif cb_data in ["profil","menu_threads","toggle_threads"]:
                if cb_data == "toggle_threads": set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                q = load_quota().get(get_today_key(chat_id), {"text":0,"media":0})
                on = is_threads_enabled(chat_id)
                txt = f"My Profile\n\nID: {chat_id}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}\nThreads: {'ON' if on else 'OFF'}"
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"⬅️ Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            else:
                txts = {"menu_post":"Post Menfess\nJust send text or photo!","menu_rules":"Rules:\n1. No Spam\n2. No SARA\n3. No Doxxing","menu_help":"Help:\n/start - Main menu","admin_reset":"Quota global direset!"}
                txt = txts.get(cb_data, "Menu")
                if cb_data == "admin_reset": save_quota({}); txt="✅ Semua quota direset!"
                # coba edit, kalau gagal (karena foto) delete+send
                try:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"⬅️ Back","callback_data":"menu_main"}]]}})
                except:
                    delete_and_send_menu(chat_id, msg_id, user_first)
                return "ok",200

        if "message" not in data: return "ok",200
        msg = data["message"]; chat_id = msg["chat"]["id"]; text = msg.get("text","")
        members = load_members()
        if str(chat_id) not in members:
            members[str(chat_id)] = {"username": msg["from"].get("username","-"), "name": msg["from"].get("first_name","-"), "joined": datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}
            save_members(members)
        if is_blocked(chat_id) and not is_admin(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"🚫 You are blocked by admin"}); return "ok",200
        if is_admin(chat_id):
            if text.startswith("/block "):
                target=text.split()[1]; b=load_blocked(); b[target]="blocked"; save_blocked(b)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"✅ {target} diblokir"}); return "ok",200
            if text.startswith("/unblock "):
                target=text.split()[1]; b=load_blocked()
                if target in b: del b[target]; save_blocked(b)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"✅ {target} di-unblok"}); return "ok",200
            if text.startswith("/search "):
                target=text.split()[1]; m=load_members(); info=m.get(target)
                if info:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Found: {info}\nID: {target}","reply_markup":{"inline_keyboard":[[{"text":"Lihat Detail","callback_data":f"admin_view_{target}"}]]}})
                else:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"User {target} gak ketemu"})
                return "ok",200
            if text.startswith("/deluser "):
                target=text.split()[1]; m=load_members()
                if target in m: del m[target]; save_members(m)
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"🗑️ User {target} dihapus"}); return "ok",200
        if text.startswith(("/start","/menu")):
            user_first = msg["from"].get("first_name","Jogja Lend")
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id, user_first),"reply_markup":get_main_menu(chat_id)})
            return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota(); key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)
        if is_media and quotas[key]["media"] >= LIMIT_MEDIA:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached\nText: {quotas[key]['text']}/{LIMIT_TEXT}\nMedia: {quotas[key]['media']}/{LIMIT_MEDIA}"}); return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT:
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached\nText: {quotas[key]['text']}/{LIMIT_TEXT}\nMedia: {quotas[key]['media']}/{LIMIT_MEDIA}"}); return "ok",200
        if is_media:
            fid = msg["photo"][-1]["file_id"]
            r = SESSION.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}").json()
            fb = SESSION.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{r['result']['file_path']}").content
            fb = add_watermark_fast(fb)
            files = {"photo": ("menfess.jpg", fb, "image/jpeg")}
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":CHANNEL_ID,"caption":caption}, files=files, timeout=30).json()
        else:
            res = SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":CHANNEL_ID,"text":caption}).json()
        if res.get("ok"):
            pid = res["result"]["message_id"]
            if is_media: quotas[key]["media"]+=1
            else: quotas[key]["text"]+=1
            save_quota(quotas)
            on = is_threads_enabled(chat_id)
            success_text = f"Menfess sent!\nQuota: Text {quotas[key]['text']}/{LIMIT_TEXT} Media {quotas[key]['media']}/{LIMIT_MEDIA}\nJoin: @{CHANNEL_USERNAME}"
            tl = f"https://t.me/{CHANNEL_USERNAME}/{pid}"
            btn = {"inline_keyboard": [[{"text":"See on channel","url":tl}],[{"text":"Delete","callback_data":f"delete_post_{pid}"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":success_text,"reply_markup":btn})
    except Exception as e: print(e)
    return "ok",200
