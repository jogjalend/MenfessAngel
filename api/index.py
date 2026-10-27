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

def get_start_text(chat_id):
    on = is_threads_enabled(chat_id)
    mode = "𝖮𝖭" if on else "𝖮𝖥"
    return (
        "𝗠𝗘𝗡𝗙𝗘𝗦𝗦 𝗔𝗡𝗚𝗘𝗟 𝗕𝗢𝗧\n"
        "----------------\n\n"
        "𝖧𝗂! 𝖲𝖾𝗇𝖽 𝗒𝗈𝗎𝗋 𝗌𝖾𝖼𝗋𝖾𝗍 𝖺𝗇𝗈𝗇𝗒𝗆𝗈𝗎𝗌𝗅𝗒\n\n"
        "𝖯𝗎𝖻𝗅𝗂𝗌𝗁 𝗍𝗈:\n"
        "- 𝖢𝗁𝖺𝗇𝗇𝖾𝗅: @menfessangel\n"
        "- 𝖳𝗁𝗋𝖾𝖺𝖽𝗌: @jogjalend\n"
        "- 𝖷: @jogjalendpm\n\n"
        "𝖲𝗍𝖺𝗍𝗎𝗌:\n"
        f"- 𝖳𝗁𝗋𝖾𝖺𝖽𝗌: {mode}\n"
        "- 𝖱𝖾𝗌𝖾𝗍: 00:00 𝖶𝖨𝖡\n"
        "- 𝖫𝗂𝗆𝗂𝗍: 5 𝗍𝖾𝗑𝗍𝗌 & 5 𝗆𝖾𝖽𝗂𝖺 / 𝖽𝖺𝗒\n\n"
        "𝖳𝖺𝗉 𝖯𝗈𝗌𝗍 𝗍𝗈 𝗌𝗍𝖺𝗋𝗍!"
    )

def get_main_menu(chat_id):
    if is_admin(chat_id):
        return {"inline_keyboard": [
            [{"text":"𝖬𝗒 𝖯𝗋𝗈𝖿𝗂𝗅𝖾","callback_data":"profil"}],
            [{"text":"𝖱𝗎𝗅𝖾𝗌","callback_data":"menu_rules"}, {"text":"𝖯𝗈𝗌𝗍","callback_data":"menu_post"}],
            [{"text":"𝖳𝗁𝗋𝖾𝖺𝖽𝗌","callback_data":"menu_threads"}],
            [{"text":"𝖠𝖽𝗆𝗂𝗇","callback_data":"admin_panel"}],
            [{"text":"𝖲𝗍𝖺𝗍𝗌","callback_data":"menu_stats"}, {"text":"𝖧𝖾𝗅𝗉","callback_data":"menu_help"}]
        ]}
    else:
        return {"inline_keyboard": [
            [{"text":"𝖬𝗒 𝖯𝗋𝗈𝖿𝗂𝗅𝖾","callback_data":"profil"}],
            [{"text":"𝖱𝗎𝗅𝖾𝗌","callback_data":"menu_rules"}, {"text":"𝖯𝗈𝗌𝗍","callback_data":"menu_post"}],
            [{"text":"𝖳𝗁𝗋𝖾𝖺𝖽𝗌","callback_data":"menu_threads"}],
            [{"text":"𝖲𝗍𝖺𝗍𝗌","callback_data":"menu_stats"}, {"text":"𝖧𝖾𝗅𝗉","callback_data":"menu_help"}]
        ]}

def get_admin_menu():
    return {"inline_keyboard": [
        [{"text":"𝖡𝗅𝗈𝖼𝗄","callback_data":"admin_block"}, {"text":"𝖴𝗇𝖻𝗅𝗈𝖼𝗄","callback_data":"admin_unblock"}],
        [{"text":"𝖬𝖾𝗆𝖻𝖾𝗋𝗌","callback_data":"admin_members"}, {"text":"𝖡𝗅𝗈𝖼𝗄𝖾𝖽","callback_data":"admin_blocked"}],
        [{"text":"𝖣𝖾𝗅 𝖬𝖾𝗆𝖻𝖾𝗋","callback_data":"admin_del_member"}, {"text":"𝖱𝖾𝗌𝖾𝗍","callback_data":"admin_reset"}],
        [{"text":"𝖡𝗋𝗈𝖺𝖽𝖼𝖺𝗌𝗍","callback_data":"admin_broadcast"}, {"text":"𝖦𝗅𝗈𝖻𝖺𝗅","callback_data":"admin_stats"}],
        [{"text":"𝖡𝖺𝖼𝗄","callback_data":"menu_main"}]
    ]}

@app.route("/", methods=['GET'])
def home(): return "Bot V30 Font Menu",200
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
                    SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":"𝖯𝗈𝗌𝗍 𝖽𝖾𝗅𝖾𝗍𝖾𝖽"})
                except: pass
                return "ok",200
            if cb_data in ["menu_main", "back_to_start"]:
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)})
                return "ok",200
            elif cb_data == "admin_panel":
                if not is_admin(chat_id): return "ok",200
                m = load_members(); b = load_blocked()
                txt = f"𝖠𝖣𝖬𝖨𝖭 𝖯𝖠𝖭𝖤𝖫\n\n𝖬𝖾𝗆𝖻𝖾𝗋𝗌: {len(m)}\n𝖡𝗅𝗈𝖼𝗄𝖾𝖽: {len(b)}"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":get_admin_menu()})
                return "ok",200
            elif cb_data in ["profil","menu_threads","toggle_threads"]:
                if cb_data == "toggle_threads": set_threads_enabled(chat_id, not is_threads_enabled(chat_id))
                q = load_quota().get(get_today_key(chat_id), {"text":0,"media":0})
                on = is_threads_enabled(chat_id)
                txt = f"𝖬𝗒 𝖯𝗋𝗈𝖿𝗂𝗅𝖾\n\n𝖨𝖣: {chat_id}\n𝖳𝖾𝗑𝗍: {q['text']}/{LIMIT_TEXT}\n𝖬𝖾𝖽𝗂𝖺: {q['media']}/{LIMIT_MEDIA}\n𝖳𝗁𝗋𝖾𝖺𝖽𝗌: {'𝖮𝖭' if on else '𝖮𝖥𝖥'}"
                kb = {"inline_keyboard": [[{"text": f"𝖳𝗁𝗋𝖾𝖺𝖽𝗌: {'𝖮𝖭' if on else '𝖮𝖥𝖥'}","callback_data":"toggle_threads"}],[{"text":"𝖡𝖺𝖼𝗄","callback_data":"menu_main"}]]}
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":kb})
                return "ok",200
            else:
                txts = {"menu_post":"𝖯𝗈𝗌𝗍 𝖬𝖾𝗇𝖿𝖾𝗌𝗌\n𝖩𝗎𝗌𝗍 𝗌𝖾𝗇𝖽 𝗍𝖾𝗑𝗍 𝗈𝗋 𝗉𝗁𝗈𝗍𝗈!","menu_rules":"𝖱𝗎𝗅𝖾𝗌:\n1. 𝖭𝗈 𝖲𝗉𝖺𝗆\n2. 𝖭𝗈 𝖲𝖠𝖱𝖠\n3. 𝖭𝗈 𝖣𝗈𝗑𝗑𝗂𝗇𝗀","menu_help":"𝖧𝖾𝗅𝗉:\n/start - 𝖬𝖺𝗂𝗇 𝗆𝖾𝗇𝗎"}
                txt = txts.get(cb_data, "𝖲𝗍𝖺𝗍𝗌")
                if cb_data == "admin_reset": save_quota({}); txt="𝖰𝗎𝗈𝗍𝖺 𝗋𝖾𝗌𝖾𝗍!"
                SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={"chat_id":chat_id,"message_id":msg_id,"text":txt,"reply_markup":{"inline_keyboard":[[{"text":"𝖡𝖺𝖼𝗄","callback_data":"menu_main"}]]}})
                return "ok",200
        if "message" not in data: return "ok",200
        msg = data["message"]; chat_id = msg["chat"]["id"]; text = msg.get("text","")
        members = load_members()
        if str(chat_id) not in members:
            members[str(chat_id)] = {"username": msg["from"].get("username","-"), "name": msg["from"].get("first_name","-"), "joined": datetime.now(WIB).strftime("%Y-%m-%d %H:%M")}
            save_members(members)
        if is_blocked(chat_id) and not is_admin(chat_id):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":"𝖸𝗈𝗎 𝖺𝗋𝖾 𝖻𝗅𝗈𝖼𝗄𝖾𝖽"}); return "ok",200
        if is_admin(chat_id) and text.startswith("/block "): 
            t=text.split()[1]; b=load_blocked(); b[t]=f"blocked"; save_blocked(b)
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"{t} 𝖻𝗅𝗈𝖼𝗄𝖾𝖽"}); return "ok",200
        if text.startswith(("/start","/menu")):
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":get_start_text(chat_id),"reply_markup":get_main_menu(chat_id)})
            return "ok",200
        raw_caption = msg.get("caption") or msg.get("text") or ""
        if not raw_caption and "photo" not in msg: return "ok",200
        quotas = load_quota(); key = get_today_key(chat_id)
        if key not in quotas: quotas[key] = {"text":0,"media":0}
        is_media = "photo" in msg
        caption = add_hashtag(raw_caption)
        if is_media and quotas[key]["media"] >= LIMIT_MEDIA: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"𝖫𝗂𝗆𝗂𝗍 𝗋𝖾𝖺𝖼𝗁𝖾𝖽\n𝖳𝖾𝗑𝗍: {quotas[key]['text']}/{LIMIT_TEXT}\n𝖬𝖾𝖽𝗂𝖺: {quotas[key]['media']}/{LIMIT_MEDIA}"}); return "ok",200
        if not is_media and quotas[key]["text"] >= LIMIT_TEXT: SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":f"𝖫𝗂𝗆𝗂𝗍 𝗋𝖾𝖺𝖼𝗁𝖾𝖽\n𝖳𝖾𝗑𝗍: {quotas[key]['text']}/{LIMIT_TEXT}\n𝖬𝖾𝖽𝗂𝖺: {quotas[key]['media']}/{LIMIT_MEDIA}"}); return "ok",200
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
            keterangan = f"𝖲𝗎𝖼𝖼𝖾𝗌𝖿𝗎𝗅𝗅𝗒 𝗉𝗈𝗌𝗍𝖾𝖽 𝗍𝗈 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗆 & 𝖳𝗁𝗋𝖾𝖺𝖽𝗌 (𝖳𝗁𝗋𝖾𝖺𝖽𝗌 𝖮𝖭)" if on else f"𝖲𝗎𝖼𝖼𝖾𝗌𝗌𝖿𝗎𝗅𝗅𝗒 𝗉𝗈𝗌𝗍𝖾𝖽 𝗍𝗈 𝖳𝖾𝗅𝖾𝗀𝗋𝖺𝗆 𝗈𝗇𝗅𝗒 (𝖳𝗁𝗋𝖾𝖺𝖽𝗌 𝖮𝖥𝖥)"
            success_text = f"𝖬𝖾𝗇𝖿𝖾𝗌𝗌 𝗌𝖾𝗇𝗍!\n𝖱𝖾𝗆𝖺𝗂𝗇𝗂𝗇𝗀 𝗊𝗎𝗈𝗍𝖺:\n𝖳𝖾𝗑𝗍: {quotas[key]['text']}/{LIMIT_TEXT}\n𝖬𝖾𝖽𝗂𝖺: {quotas[key]['media']}/{LIMIT_MEDIA}\n{keterangan}\n𝖩𝗈𝗂𝗇: @{CHANNEL_USERNAME}"
            tl = f"https://t.me/{CHANNEL_USERNAME}/{pid}"
            th = f"https://www.threads.net/@jogjalend"
            btn = {"inline_keyboard": [[{"text":"𝖲𝖾𝖾 𝗈𝗇 𝖼𝗁𝖺𝗇𝗇𝖾𝗅","url":tl}, {"text":"𝖲𝖾𝖾 𝗈𝗇 𝖳𝗁𝗋𝖾𝖺𝖽𝗌","url":th}],[{"text":"𝖣𝖾𝗅𝖾𝗍𝖾","callback_data":f"delete_post_{pid}"}]]} if on else {"inline_keyboard": [[{"text":"𝖲𝖾𝖾 𝗈𝗇 𝖼𝗁𝖺𝗇𝗇𝖾𝗅","url":tl}],[{"text":"𝖣𝖾𝗅𝖾𝗍𝖾","callback_data":f"delete_post_{pid}"}]]}
            SESSION.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":success_text,"reply_markup":btn})
    except Exception as e: print(e)
    return "ok",200
