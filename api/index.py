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

def make_stats_image():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        members = load_members()
        blocked = load_blocked()
        quota = load_quota()
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
        cats = ['Members', 'Blocked', 'Today', 'Total']
        nums = [len(members), len(blocked), today_post, total_post]
        ax2.bar(cats, nums, color=['#1d9bf0','#f4212e','#00ba7c','#7856ff'])
        ax2.set_title(f'@menfessangel - {today_str}', fontweight='bold')
        for i, v in enumerate(nums):
            ax2.text(i, v+0.2, str(v), ha='center', fontweight='bold')
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        print(e)
        return None

# === PAKAI VERSI LU ===
def get_start_text(chat_id, first_name="Jogja Lend"):
    name = first_name if first_name else "there"
    return (
        "MENFESS ANGEL BOT\n"
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
            [{"text":"Admin Panel","callback_data":"admin_panel"}],
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
        [{"text":"Block","callback_data":"admin_block"}, {"text":"Unblock","callback_data":"admin_unblock"}],
        [{"text":"Members","callback_data":"admin_members"}, {"text":"Blocked","callback_data":"admin_blocked"}],
        [{"text":"Del Member","callback_data":"admin_del_member"}, {"text":"Reset","callback_data":"admin_reset"}],
        [{"text":"Broadcast","callback_data":"admin_broadcast"}, {"text":"Global","callback_data":"admin_stats"}],
        [{"text":"Back","callback_data":"menu_main"}]
    ]}

@app.route("/", methods=['GET'])
def home(): return "Bot V38 Clean Final",200
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
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"Post deleted"})
                except: pass
                return "ok",200
            if cb_data in ["menu_main", "back_to_start"]:
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":get_start_text(chat_id, user_first),"reply_markup":get_main_menu(chat_id)})
                return "ok",200
            elif cb_data == "menu_stats":
                img_bytes = make_stats_image()
                members = load_members()
                blocked = load_blocked()
                quota = load_quota()
                total_post = sum(v.get("text",0)+v.get("media",0) for v in quota.values())
                caption = f"MENFESS ANGEL - CHANNEL STATS\n━━━━━━━━━━━━━━━\n\nMembers: {len(members)}\nBlocked: {len(blocked)}\nTotal Posts: {total_post}\nDate: {datetime.now(WIB).strftime('%Y-%m-%d')}"
                if img_bytes:
                    files = {"photo": ("stats.png", img_bytes, "image/png")}
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id":chat_id,"caption":caption,"reply_markup":json.dumps({"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]})}, files=files)
                else:
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":caption,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}})
                return "ok",200
            elif cb_data == "admin_panel":
                if not is_admin(chat_id): return "ok",200
                m = load_members(); b = load_blocked()
                txt = f"ADMIN PANEL\n\nMembers: {len(m)}\nBlocked: {len(b)}"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":get_admin_menu()})
                return "ok",200
            elif cb_data in ["profil","menu_threads","toggle_threads"]:
                if cb_data == "toggle_threads": set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                q = load_quota().get(get_today_key(chat_id), {"text":0,"media":0})
                on = is_threads_enabled(chat_id)
                txt = f"My Profile\n\nID: {chat_id}\nText: {q['text']}/{LIMIT_TEXT}\nMedia: {q['media']}/{LIMIT_MEDIA}\nThreads: {'ON' if on else 'OFF'}"
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if on else 'OFF'}","callback_data":"toggle_threads"}],[{"text":"Back","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            else:
                txts = {"menu_post":"Post Menfess\nJust send text or photo!","menu_rules":"Rules:\n1. No Spam\n2. No SARA\n3. No Doxxing","menu_help":"Help:\n/start - Main menu"}
                txt = txts.get(cb_data, "Stats")
                if cb_data == "admin_reset": save_quota({}); txt="Quota reset!"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"Back","callback_data":"menu_main"}]]}})
                return "ok",200
        if "message" not in data: return "ok",200
        msg = data["message"]; chat_id = msg["chat"]["id"]; text = msg.get("text","")
        members = load_members()
        if str(chat_id) not in members:
            members[str(chat_id)] = {"username": msg["from"].get("username","-"), "name": msg["from"].get("first_name","-"), "joined": datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}
            save_members(members)
        if is_blocked(chat_id) and not is_admin(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"You are blocked"}); return "ok",200
        if is_admin(chat_id) and text.startswith("/block "): 
            t=text.split()[1]; b=load_blocked(); b[t]=f"blocked"; save_blocked(b)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"{t} blocked"}); return "ok",200
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
        if is_media and quotas[key]["media"] >= LIMIT_MEDIA: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached\nText: {quotas[key]['text']}/{LIMIT_TEXT}\nMedia: {quotas[key]['media']}/{LIMIT_MEDIA}"}); return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"Limit reached\nText: {quotas[key]['text']}/{LIMIT_TEXT}\nMedia: {quotas[key]['media']}/{LIMIT_MEDIA}"}); return "ok",200
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
            keterangan = f"Successfully posted to Telegram & Threads (Threads ON)" if on else f"Successfully posted to Telegram only (Threads OFF)"
            success_text = f"Menfess sent!\nRemaining quota:\nText: {quotas[key]['text']}/{LIMIT_TEXT}\nMedia: {quotas[key]['media']}/{LIMIT_MEDIA}\n{keterangan}\nJoin: @{CHANNEL_USERNAME}"
            tl = f"https://t.me/{CHANNEL_USERNAME}/{pid}"
            th = f"https://www.threads.net/@jogjalend"
            btn = {"inline_keyboard": [[{"text":"See on channel","url":tl}, {"text":"See on Threads","url":th}],[{"text":"Delete","callback_data":f"delete_post_{pid}"}]]} if on else {"inline_keyboard": [[{"text":"See on channel","url":tl}],[{"text":"Delete","callback_data":f"delete_post_{pid}"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":success_text,"reply_markup":btn})
    except Exception as e: print(e)
    return "ok",200
