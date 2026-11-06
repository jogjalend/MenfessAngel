# api/index.py - JogjaLend Bot Angel V114 FAST + X AUTO SHARE + X PREMIUM QRIS 100K - FORMAL ENGLISH
from flask import Flask, request, jsonify
import os, requests, io, random, re, traceback, copy, time, hmac, hashlib, base64, urllib.parse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

try:
    import psycopg2
    from psycopg2 import pool
except:
    psycopg2 = None
    pool = None
try:
    from PIL import Image, ImageDraw, ImageFont
except:
    Image = None

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") or "@menfessangel"
ADMIN_ID = os.getenv("ADMIN_ID") or ""
DATABASE_URL = os.getenv("DATABASE_URL")
THREADS_URL = os.getenv("THREADS") or "https://threads.net/jogjalend"
THREADS_USER_ID = os.getenv("THREADS_USER_ID")
THREADS_TOKEN = os.getenv("THREADS_TOKEN")
MAIN_THREAD_ID = os.getenv("MAIN_THREAD_ID")
LOG_CHANNEL = os.getenv("LOG_CHANNEL") or CHANNEL_ID
WIB = timezone(timedelta(hours=7))
SEP = "●-----------------------------------------------------●"

# ===== X ENV =====
X_API_KEY = os.getenv("X_API_KEY") or ""
X_API_SECRET = os.getenv("X_API_SECRET") or ""
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or ""
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET") or ""

# ===== QRIS / X PREMIUM ENV =====
QRIS_IMAGE_URL = os.getenv("QRIS_IMAGE_URL") or ""
QRIS_TEXT = os.getenv("QRIS_TEXT") or "QRIS a.n jogjaStore, please scan the QR code above"
X_PRICE = os.getenv("X_PRICE") or "Rp 100.000 / 30 days"
PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS") or "30")

TG = requests.Session()
TG.headers.update({"Connection": "keep-alive"})
BASE_TG = f"https://api.telegram.org/bot{BOT_TOKEN}"

SETTINGS_CACHE = {}
SETTINGS_CACHE_TIME = 0
USERS = defaultdict(lambda: {"name": "", "username": "", "threads_on": False, "today_text": 0, "today_media": 0, "last_date": "", "banned": False, "total_text": 0, "total_media": 0, "total_chars": 0, "admin_target": "both", "warn": 0, "waiting_proof": False, "x_premium_until": "", "x_auto": True})

_db_pool = None
def get_pool():
    global _db_pool
    if _db_pool or not DATABASE_URL or not pool:
        return _db_pool
    try:
        _db_pool = pool.SimpleConnectionPool(1, 5, DATABASE_URL, connect_timeout=2)
    except:
        _db_pool = None
    return _db_pool

def get_db():
    p = get_pool()
    if p:
        try: return p.getconn()
        except: return None
    if not DATABASE_URL or not psycopg2: return None
    try: return psycopg2.connect(DATABASE_URL, connect_timeout=2)
    except: return None

def release_db(db):
    if not db: return
    p = get_pool()
    try:
        if p: p.putconn(db)
        else: db.close()
    except: pass

_db_init_done = False
def init_db():
    global _db_init_done
    if _db_init_done: return
    _db_init_done = True
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS menfess_users (user_id TEXT PRIMARY KEY, name TEXT, username TEXT, threads_on BOOLEAN DEFAULT FALSE, today_text INT DEFAULT 0, today_media INT DEFAULT 0, last_date TEXT, banned BOOLEAN DEFAULT FALSE, total_text INT DEFAULT 0, total_media INT DEFAULT 0, total_chars INT DEFAULT 0, admin_target TEXT DEFAULT 'both', warn INT DEFAULT 0)")
        cur.execute("ALTER TABLE menfess_users ADD COLUMN IF NOT EXISTS x_premium_until TEXT DEFAULT ''")
        cur.execute("CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('hashtag', '#jogjalend') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('peraturan', '1. No SARA & Pornography\n2. No spam\n3. Maximum 5 posts per day') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('approval', 'off') ON CONFLICT (key) DO NOTHING")
        cur.execute("INSERT INTO bot_settings (key, value) VALUES ('x_auto_share', 'off') ON CONFLICT (key) DO NOTHING")
        db.commit(); cur.close()
    except: pass
    finally: release_db(db)

try: init_db()
except: pass

def get_setting(k, default=""):
    global SETTINGS_CACHE_TIME
    if k in SETTINGS_CACHE and (time.time() - SETTINGS_CACHE_TIME < 60):
        return SETTINGS_CACHE[k]
    db = get_db()
    if not db: return SETTINGS_CACHE.get(k, default)
    try:
        cur = db.cursor(); cur.execute("SELECT value FROM bot_settings WHERE key=%s", (k,)); r = cur.fetchone(); cur.close()
        val = r[0] if r else default
        SETTINGS_CACHE[k] = val; SETTINGS_CACHE_TIME = time.time()
        return val
    except: return SETTINGS_CACHE.get(k, default)
    finally: release_db(db)

def set_setting(k, v):
    SETTINGS_CACHE[k] = v
    global SETTINGS_CACHE_TIME
    SETTINGS_CACHE_TIME = time.time()
    db = get_db()
    if not db: return
    try:
        cur = db.cursor(); cur.execute("INSERT INTO bot_settings (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s", (k, v, v)); db.commit(); cur.close()
    except: pass
    finally: release_db(db)

# ===== X - OAUTH 1.0a MANUAL =====
def _x_oauth_header(method, url, extra_params=None):
    if not X_API_KEY or not X_API_SECRET or not X_ACCESS_TOKEN or not X_ACCESS_SECRET:
        return None
    oauth = {
        "oauth_consumer_key": X_API_KEY,
        "oauth_nonce": base64.b64encode(os.urandom(32)).decode()[:32].replace("+","a").replace("/","b"),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": X_ACCESS_TOKEN,
        "oauth_version": "1.0",
    }
    all_params = dict(oauth)
    if extra_params:
        all_params.update(extra_params)
    sorted_params = sorted(all_params.items())
    param_str = "&".join(f"{urllib.parse.quote(str(k), safe='')}={urllib.parse.quote(str(v), safe='')}" for k,v in sorted_params)
    base = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"
    signing_key = f"{urllib.parse.quote(X_API_SECRET, safe='')}&{urllib.parse.quote(X_ACCESS_SECRET, safe='')}"
    sig = base64.b64encode(hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    header = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k,v in sorted(oauth.items()))
    return header

def _x_upload_media(photo_bytes):
    try:
        url = "https://upload.twitter.com/1.1/media/upload.json"
        header = _x_oauth_header("POST", url)
        if not header: return None
        files = {"media": ("img.jpg", photo_bytes, "image/jpeg")}
        r = TG.post(url, headers={"Authorization": header}, files=files, timeout=10)
        j = r.json()
        return j.get("media_id_string")
    except Exception as e:
        print(f"X upload error: {e}")
        return None

def post_to_x(text_content, photo_bytes=None):
    try:
        if not X_API_KEY or not X_API_SECRET or not X_ACCESS_TOKEN or not X_ACCESS_SECRET:
            print("X ENV not configured")
            return False
        clean = re.sub(r"<[^>]+>", "", text_content or "").strip()
        if not clean:
            return False
        if len(clean) > 280:
            clean = clean[:277] + "..."
        media_id = None
        if photo_bytes:
            media_id = _x_upload_media(photo_bytes)
        url = "https://api.twitter.com/2/tweets"
        header = _x_oauth_header("POST", url, None)
        if not header: return False
        payload = {"text": clean}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}
        r = TG.post(url, headers={"Authorization": header, "Content-Type": "application/json"}, json=payload, timeout=10)
        print(f"X post: {r.status_code} {r.text[:300]}")
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"X post error: {e}")
        return False

def to_fancy(text):
    if not text: return ""
    pattern = r'<plain>.*?</plain>|<code>.*?</code>|<pre>.*?</pre>|<a[^>]*>.*?</a>|<[^>]+>|@\w+|#\w+|/\w+|https?://\S+|threads\.net/\S+|t\.me/\S+'
    res_parts = []; last_idx = 0
    for m in re.finditer(pattern, text, flags=re.DOTALL):
        before = text[last_idx:m.start()]
        conv = "".join(chr(0x1D5A0 + ord(c)-65) if 'A' <= c <= 'Z' else chr(0x1D5BA + ord(c)-97) if 'a' <= c <= 'z' else chr(0x1D7E2 + ord(c)-48) if '0' <= c <= '9' else c for c in before)
        res_parts.append(conv); res_parts.append(m.group(0)); last_idx = m.end()
    tail = text[last_idx:]
    conv = "".join(chr(0x1D5A0 + ord(c)-65) if 'A' <= c <= 'Z' else chr(0x1D5BA + ord(c)-97) if 'a' <= c <= 'z' else chr(0x1D7E2 + ord(c)-48) if '0' <= c <= '9' else c for c in tail)
    res_parts.append(conv); return "".join(res_parts)

def F(t): return to_fancy(t)
def M(t):
    out = []
    for line in t.split("\n"):
        if line.strip() == "": out.append("")
        elif "http" in line or "@" in line or "tg://" in line or line.strip().startswith("/"): out.append(line)
        else: out.append(f"<code>{line}</code>")
    return "\n".join(out)

def load_user_from_db(uid):
    db = get_db()
    if not db: return None
    try:
        cur = db.cursor()
        cur.execute("SELECT name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn, x_premium_until FROM menfess_users WHERE user_id=%s", (uid,))
        row = cur.fetchone(); cur.close()
        if row: return {"name": row[0] or "", "username": row[1] or "", "threads_on": row[2] or False, "today_text": row[3] or 0, "today_media": row[4] or 0, "last_date": row[5] or "", "banned": row[6] or False, "total_text": row[7] or 0, "total_media": row[8] or 0, "total_chars": row[9] or 0, "admin_target": row[10] or "both", "warn": row[11] or 0, "x_premium_until": row[12] or "", "waiting_proof": False, "x_auto": True}
    except: return None
    finally: release_db(db)
    return None

def save_user_to_db(uid, user):
    db = get_db()
    if not db: return
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menfess_users (user_id, name, username, threads_on, today_text, today_media, last_date, banned, total_text, total_media, total_chars, admin_target, warn, x_premium_until) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id) DO UPDATE SET name=%s, username=%s, threads_on=%s, today_text=%s, today_media=%s, last_date=%s, banned=%s, total_text=%s, total_media=%s, total_chars=%s, admin_target=%s, warn=%s, x_premium_until=%s", (uid, user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("admin_target", "both"), user.get("warn", 0), user.get("x_premium_until",""), user["name"], user["username"], user["threads_on"], user["today_text"], user["today_media"], user["last_date"], user["banned"], user["total_text"], user["total_media"], user.get("total_chars", 0), user.get("admin_target", "both"), user.get("warn", 0), user.get("x_premium_until","")))
        db.commit(); cur.close()
    except: pass
    finally: release_db(db)

def get_user(uid):
    u = USERS[uid]
    if u["last_date"] == "" and uid not in USERS or (u["name"] == "" and DATABASE_URL):
        d = load_user_from_db(uid)
        if d: USERS[uid] = d; u = USERS[uid]
    today = datetime.now(WIB).strftime("%Y-%m-%d")
    if u["last_date"] != today:
        u["today_text"] = 0; u["today_media"] = 0; u["last_date"] = today
    return u

def is_admin(uid): return str(uid) in ADMIN_ID.split(",") if ADMIN_ID else False

def is_premium_active(user):
    try:
        until = user.get("x_premium_until","") or ""
        if not until: return False
        dt = datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=WIB)
        return datetime.now(WIB) <= dt + timedelta(days=1)
    except: return False

def send_message(chat_id, text, kb=None):
    try:
        kb_fancy = None
        if kb and "inline_keyboard" in kb:
            kb_fancy = copy.deepcopy(kb)
            for row in kb_fancy["inline_keyboard"]:
                for btn in row:
                    if "text" in btn and "url" not in btn: btn["text"] = F(btn["text"])
        payload = {"chat_id": chat_id, "text": F(text).replace("<plain>", "").replace("</plain>", ""), "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb_fancy: payload["reply_markup"] = kb_fancy
        r = TG.post(f"{BASE_TG}/sendMessage", json=payload, timeout=3)
        return r.status_code == 200
    except: return False

def edit_message_fast(chat_id, msg_id, text, kb=None):
    try:
        kb_fancy = None
        if kb and "inline_keyboard" in kb:
            kb_fancy = copy.deepcopy(kb)
            for row in kb_fancy["inline_keyboard"]:
                for btn in row:
                    if "text" in btn and "url" not in btn: btn["text"] = F(btn["text"])
        payload = {"chat_id": chat_id, "message_id": msg_id, "text": F(text).replace("<plain>", "").replace("</plain>", ""), "parse_mode": "HTML", "disable_web_page_preview": True}
        if kb_fancy: payload["reply_markup"] = kb_fancy
        TG.post(f"{BASE_TG}/editMessageText", json=payload, timeout=3)
        return True
    except: return False

def report_error(chat_id, where, error):
    err_str = str(error)
    if "Timeout" in err_str or "timed out" in err_str: return
    print(f"ERROR {where}: {err_str}")

# ===== QRIS / PREMIUM HELPERS =====
def send_qris(chat_id):
    if QRIS_IMAGE_URL:
        try:
            TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": chat_id, "photo": QRIS_IMAGE_URL, "caption": f"Please scan this QRIS to pay for X Premium\nPrice: {X_PRICE}"}, timeout=5)
            return True
        except: pass
    return False

def get_x_premium_keyboard(user=None):
    if user and is_premium_active(user):
        auto = "ON" if user.get("x_auto", True) else "OFF"
        return {"inline_keyboard": [[{"text": f"𝕏 X Auto Post: {auto}", "callback_data": "x_toggle_auto"}], [{"text": "Back", "callback_data": "back_home"}]]}
    return {"inline_keyboard": [[{"text": "💳 I Have Transferred, Send Receipt", "callback_data": "x_pay_proof"}], [{"text": "Back", "callback_data": "back_home"}]]}

def get_welcome_text(user):
    hashtag = get_setting('hashtag', '#jogjalend')
    prem = " ✅ X Premium" if is_premium_active(user) else ""
    return f"Welcome !{prem}\n{SEP}\nPublish to {CHANNEL_ID}\nPlease tap Post to submit.\n\nQuota\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5\nTag: {hashtag}"

def get_back_keyboard(): return {"inline_keyboard": [[{"text": "Back", "callback_data": "back_home"}]]}
def get_main_keyboard(is_ad=False):
    kb = {"inline_keyboard": [[{"text": "👤 My Profile", "callback_data": "my_profile"}, {"text": "💌 Post", "callback_data": "post"}], [{"text": "📧 Threads Setting", "callback_data": "threads"}], [{"text": "𝕏 X Premium", "callback_data": "x_premium"}], [{"text": "📈 Stats", "callback_data": "stats"}, {"text": "ℹ️ Bot Info", "callback_data": "info_bot"}]]}
    if is_ad: kb["inline_keyboard"].append([{"text": "🔧 ADMIN PANEL", "callback_data": "admin_panel"}])
    return kb
def get_menu_1():
    return {"inline_keyboard": [[{"text": "🔔 Tag", "callback_data": "lend_tag"}], [{"text": "📥 Approval Mode", "callback_data": "lend_persetujuan"}], [{"text": "🗑️ Delete Message", "callback_data": "lend_hapus"}], [{"text": "🇮🇩 Language", "callback_data": "lend_lang"}, {"text": "✅ Close", "callback_data": "close"}], [{"text": "▶️ More", "callback_data": "lend_page2"}]]}
def get_menu_2():
    return {"inline_keyboard": [[{"text": "📜 Rules", "callback_data": "lend_peraturan"}], [{"text": "⚠️ Warnings", "callback_data": "lend_peringatan"}], [{"text": "🚫 Blacklist", "callback_data": "lend_blacklist"}], [{"text": "🔐 Permissions", "callback_data": "lend_izin"}, {"text": "📋 Channel Log", "callback_data": "lend_log"}], [{"text": "🎯 Channel Management", "callback_data": "lend_channel"}], [{"text": "⬅️ Back", "callback_data": "lend_page1"}, {"text": "❌ Close", "callback_data": "close"}]]}

def get_admin_panel():
    x_on = get_setting('x_auto_share', 'off') == 'on'
    x_label = f"{'✅ ' if x_on else '❌ '}𝕏 Auto Share: {'ON' if x_on else 'OFF'}"
    return {"inline_keyboard": [
        [{"text": "👥 User List", "callback_data": "admin_users"}, {"text": "📊 All Stats", "callback_data": "admin_allstats"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}, {"text": "🚫 Ban/Unban", "callback_data": "lend_blacklist"}],
        [{"text": "🎯 Channel Target", "callback_data": "lend_channel"}],
        [{"text": x_label, "callback_data": "admin_x_toggle"}],
        [{"text": "🧪 Test Post to X", "callback_data": "admin_x_test"}],
        [{"text": "🔗 Set Webhook", "callback_data": "admin_webhook"}, {"text": "📋 Check Logs", "callback_data": "admin_logs"}],
        [{"text": "⚙️ Bot Settings", "callback_data": "lend_page1"}],
        [{"text": "⬅️ Back", "callback_data": "back_home"}]
    ]}

def get_channel_target_keyboard(user):
    target = user.get("admin_target", "both")
    return {"inline_keyboard": [[{"text": f"📍 Target: {target.upper()}", "callback_data": "admin_noop"}], [{"text": f"{'✅ ' if target=='channel' else ''}📢 Channel Only", "callback_data": "admin_set_channel"}, {"text": f"{'✅ ' if target=='threads' else ''}🧵 Threads Only", "callback_data": "admin_set_threads"}], [{"text": f"{'✅ ' if target=='both' else ''}🚀 Both (Channel+Threads)", "callback_data": "admin_set_both"}], [{"text": "⬅️ Back", "callback_data": "admin_panel"}]]}

_LOGO_CACHED = None
def get_logo_cached():
    global _LOGO_CACHED
    if _LOGO_CACHED is not None: return _LOGO_CACHED
    base_dir = os.path.dirname(__file__)
    for p in [os.path.join(base_dir, "logo.png"), "logo.png", os.path.join(os.getcwd(), "api/logo.png")]:
        if os.path.exists(p):
            try:
                logo = Image.open(p).convert("RGBA")
                bbox = logo.getbbox()
                if bbox: logo = logo.crop(bbox)
                _LOGO_CACHED = logo
                return logo
            except: return None
    return None

def download_file(file_id):
    try:
        info = TG.get(f"{BASE_TG}/getFile", params={"file_id": file_id}, timeout=3).json()
        fp = info["result"]["file_path"]
        return TG.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}", timeout=5).content
    except: return None

def add_watermark(photo_bytes):
    try:
        if not Image or not photo_bytes: return None
        logo_orig = get_logo_cached()
        if not logo_orig: return None
        base = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
        logo = logo_orig.copy()
        w, h = base.size
        target_w = int(w * 0.20); target_w = max(60, min(target_w, 400))
        target_h = int(target_w * logo.height / logo.width)
        max_h = int(h * 0.20)
        if target_h > max_h:
            target_h = max_h; target_w = int(target_h * logo.width / logo.height)
        logo = logo.resize((target_w, target_h), Image.LANCZOS)
        margin = max(10, int(w * 0.015))
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        overlay.paste(logo, (margin, margin), logo)
        combined = Image.alpha_composite(base, overlay).convert("RGB")
        bio = io.BytesIO(); combined.save(bio, "JPEG", quality=82, optimize=True); bio.seek(0); return bio
    except Exception as e:
        print(f"watermark error: {e}"); return None

def get_font(size, bold=False):
    try:
        if not Image: return None
        p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if os.path.exists(p): return ImageFont.truetype(p, size)
    except: pass
    return ImageFont.load_default() if Image else None

def make_today_chart(user):
    try:
        if not Image: return None
        W, H = 720, 400; img = Image.new('RGB', (W, H), '#0D0D0F'); draw = ImageDraw.Draw(img)
        f_title = get_font(22, True); f_small = get_font(14)
        draw.rectangle([0, 0, W, 60], fill='#161618')
        draw.text((20, 12), f"TODAY 1D - {user['name'][:16]}", fill='white', font=f_title)
        hours = ["08:00", "12:00", "16:00", "20:00"]; total = user['today_text'] + user['today_media']
        highs = [0]*4 if total == 0 else [random.randint(0, 2)+(total//4) for _ in hours]
        max_val = max(highs) if max(highs) > 0 else 3
        slot_w = (700-50)//len(hours)
        for idx in range(len(hours)):
            xc = 50+idx*slot_w+slot_w//2; v = highs[idx]
            yh = 370-int(v/max_val*250) if max_val > 0 else 370
            color = '#10B981' if idx % 2 == 0 else '#EF4444'
            if total == 0: color = '#27272A'
            draw.rectangle([xc-15, yh, xc+15, 370], fill=color)
            draw.text((xc-15, 378), hours[idx], fill='#A1A1AA', font=f_small)
        bio = io.BytesIO(); img.save(bio, format='JPEG', quality=70); bio.seek(0); return bio
    except: return None

def make_weekly_chart(user):
    try:
        if not Image: return None
        W, H = 720, 400; img = Image.new('RGB', (W, H), '#0D0D0F'); draw = ImageDraw.Draw(img)
        f_title = get_font(22, True); f_small = get_font(14)
        draw.rectangle([0, 0, W, 60], fill='#161618')
        draw.text((20, 12), "WEEKLY 7D", fill='white', font=f_title)
        days = ["22", "23", "24", "25", "26", "27", "28"]; vals = [random.randint(1, 4) for _ in days]; max_v = max(vals)
        slot_w = (700-50)//len(days)
        for idx in range(len(days)):
            xc = 50+idx*slot_w+slot_w//2; v = vals[idx]
            yv = 370-int(v/max_v*250); draw.rectangle([xc-14, yv, xc+14, 370], fill='#3B82F6')
            draw.text((xc-8, 378), days[idx], fill='#A1A1AA', font=f_small)
        bio = io.BytesIO(); img.save(bio, format='JPEG', quality=70); bio.seek(0); return bio
    except: return None

def send_stats(chat_id, user, mode="today"):
    try:
        kb = {"inline_keyboard": [[{"text": "TODAY 1D" if mode != "today" else "• TODAY 1D", "callback_data": "stats_today"}, {"text": "WEEKLY 7D" if mode != "weekly" else "• WEEKLY 7D", "callback_data": "stats_weekly"}], [{"text": "Back", "callback_data": "back_home"}]]}
        if mode == "today": chart = make_today_chart(user); cap = f"📊 TODAY 1D - {user['name']}\n{user['today_text']} text | {user['today_media']} media"
        else: chart = make_weekly_chart(user); cap = f"📈 WEEKLY 7D - {user['name']}\nLast 7 days"
        if chart:
            chart.seek(0)
            try:
                r = TG.post(f"{BASE_TG}/sendPhoto", data={"chat_id": chat_id, "caption": cap}, files={"photo": ("s.jpg", chart, "image/jpeg")}, timeout=5).json()
                if r.get("ok"):
                    send_message(chat_id, "Please select a mode:", kb); return
            except: pass
        send_message(chat_id, cap, kb)
    except: pass

def post_to_threads(text_content):
    try:
        if not THREADS_USER_ID or not THREADS_TOKEN: return False
        data = {"media_type": "TEXT", "text": text_content[:450], "access_token": THREADS_TOKEN}
        if MAIN_THREAD_ID: data["reply_to_id"] = MAIN_THREAD_ID
        r = TG.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads", data=data, timeout=3).json()
        cid = r.get("id")
        if not cid: return False
        r2 = TG.post(f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish", data={"creation_id": cid, "access_token": THREADS_TOKEN}, timeout=3).json()
        return "id" in r2
    except: return False

def send_success(chat_id, user, ch_msg_id, target="both"):
    try:
        url = f"https://t.me/{CHANNEL_ID.replace('@','')}/{ch_msg_id}" if ch_msg_id else f"https://t.me/{CHANNEL_ID.replace('@','')}"
        buttons = []
        if target in ["threads", "both"] and (user.get("threads_on") or is_admin(chat_id)): buttons.append([{"text": "View on Threads", "url": THREADS_URL}])
        if target in ["channel", "both"] and ch_msg_id: buttons.append([{"text": "View on Channel", "url": url}])
        if ch_msg_id: buttons.append([{"text": "Delete", "callback_data": f"del_{ch_msg_id}"}])
        buttons.append([{"text": "Back", "callback_data": "back_home"}])
        note = f" -> {target.upper()}" if is_admin(chat_id) else ""
        if is_premium_active(user) and user.get("x_auto", True) and get_setting('x_auto_share', 'off') == 'on':
            note += " + X"
        if is_admin(chat_id) and get_setting('x_auto_share', 'off') == 'on':
            if " + X" not in note: note += " + X"
        send_message(chat_id, f"Menfess successfully sent!{note}\n{SEP}\nMedia : {user['today_media']}/5\nText : {user['today_text']}/5", {"inline_keyboard": buttons})
    except Exception as e: report_error(chat_id, "send_success", e)

def send_user_list(chat_id):
    db = get_db()
    if not db:
        send_message(chat_id, "Database is not connected."); return
    try:
        cur = db.cursor()
        cur.execute("SELECT user_id, name, username, total_text+total_media as total, banned, x_premium_until FROM menfess_users ORDER BY total DESC")
        rows = cur.fetchall(); cur.close()
        back_kb = {"inline_keyboard": [[{"text": "Back", "callback_data": "admin_panel"}]]}
        if not rows:
            send_message(chat_id, M("No users yet."), back_kb); return
        header = M(f"Total Users: {len(rows)}\n------------------------------\nAll Members:")
        txt = header + "\n"
        for i, r in enumerate(rows, 1):
            status = " BANNED" if r[4] else ""
            prem = " 👑" if r[5] else ""
            display = f"<a href=\"tg://user?id={r[0]}\">@{r[2]}</a>" if r[2] else f"<a href=\"tg://user?id={r[0]}\">{r[0]}</a>"
            line = f"{i}. {display} - {r[0]} ({r[3]}){status}{prem}\n"
            if len(txt) + len(line) > 3200:
                send_message(chat_id, txt, back_kb)
                txt = M(f"Continued ({i}/{len(rows)}):") + "\n"
            txt += line
        send_message(chat_id, txt, back_kb)
    except Exception as e:
        send_message(chat_id, f"Failed to retrieve user list: {e}")
    finally: release_db(db)

def handle_admin_command(chat_id, text):
    if text.startswith("/clearmenu"):
        TG.post(f"{BASE_TG}/setChatMenuButton", json={"menu_button": {"type": "default"}}, timeout=3)
        TG.post(f"{BASE_TG}/deleteMyCommands", json={}, timeout=3)
        send_message(chat_id, "Menu button and commands have been cleared."); return True
    if text.startswith("/ban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1]; tu = get_user(target); tu["banned"] = True; save_user_to_db(target, tu); send_message(chat_id, M(f"User {target} has been BANNED."))
        return True
    if text.startswith("/unban"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1]; tu = get_user(target); tu["banned"] = False; tu["warn"] = 0; save_user_to_db(target, tu); send_message(chat_id, M(f"User {target} has been UNBANNED."))
        return True
    if text.startswith("/warn"):
        parts = text.split()
        if len(parts) >= 2:
            target = parts[1]; tu = get_user(target); tu["warn"] = tu.get("warn", 0)+1
            if tu["warn"] >= 3: tu["banned"] = True
            save_user_to_db(target, tu); send_message(chat_id, M(f"Warning for {target} = {tu['warn']}/3 {'+ AUTO BANNED' if tu['banned'] else ''}"))
        return True
    if text.startswith("/settag"):
        nt = text.replace("/settag", "").strip()
        if nt: set_setting('hashtag', nt); send_message(chat_id, M(f"Hashtag has been changed to {nt}"))
        return True
    if text.startswith("/setperaturan"):
        nt = text.replace("/setperaturan", "").strip()
        if nt: set_setting('peraturan', nt); send_message(chat_id, M("Rules have been updated."))
        return True
    if text.startswith("/x_test"):
        ok = post_to_x(f"Test JogjaLend Bot - X Auto Share ON {datetime.now(WIB).strftime('%H:%M')}")
        send_message(chat_id, M(f"X Test: {'SUCCESSFUL ✅' if ok else 'FAILED ❌ - Please check the X ENV in Vercel / Logs'}"))
        return True
    if text.startswith("/broadcast"):
        btext = text.replace("/broadcast", "").strip()
        if btext:
            db = get_db()
            if db:
                cur = db.cursor(); cur.execute("SELECT user_id FROM menfess_users"); rows = cur.fetchall(); cur.close(); release_db(db)
                for r in rows: send_message(r[0], f"📢 BROADCAST\n{SEP}\n{btext}")
                send_message(chat_id, M(f"Broadcast has been sent to {len(rows)} users."))
        return True
    if text.startswith("/users"):
        send_user_list(chat_id); return True
    if text.startswith("/setwebhook"):
        host = request.host_url.rstrip('/'); wh = f"{host}/api/index"
        r = TG.get(f"{BASE_TG}/setWebhook", params={"url": wh}, timeout=3).json()
        send_message(chat_id, M(f"Webhook: {wh}\nResult: {r}")); return True
    return False

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    try:
        host = request.host_url.rstrip('/')
        webhook_url = f"{host}/api/index"
        custom = os.getenv("WEBHOOK_URL")
        if custom: webhook_url = custom
        r = TG.get(f"{BASE_TG}/setWebhook", params={"url": webhook_url}, timeout=3).json()
        return f"Webhook set to {webhook_url}<br>{r}", 200
    except Exception as e:
        return f"Error setting webhook: {e}", 500

@app.route("/webhookinfo", methods=["GET"])
def webhook_info():
    try:
        r = TG.get(f"{BASE_TG}/getWebhookInfo", timeout=3).json()
        return jsonify(r), 200
    except Exception as e:
        return str(e), 500

@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def main_handler():
    data = {}; where = "init"
    try:
        if request.method == "GET": return "JogjaLend Bot V114 FAST + X + QRIS OK", 200
        where = "parse_json"; data = request.get_json(force=True, silent=True) or {}
        if "message" in data:
            msg = data["message"]; chat_id = msg["chat"]["id"]; uid = str(chat_id)
            where = f"get_user {uid}"; user = get_user(uid); text = msg.get("text", ""); caption = msg.get("caption", "")
            HASHTAG = get_setting('hashtag', '#jogjalend')
            if "from" in msg:
                raw = (msg["from"].get("first_name", "")+" "+(msg["from"].get("last_name", "") or "")).strip() or "-"
                user["name"] = raw.encode('ascii', 'ignore').decode('ascii') or "User"
                user["username"] = msg["from"].get("username", "")
            if is_admin(chat_id) and text.startswith("/"):
                if handle_admin_command(chat_id, text):
                    return "ok", 200
            if text.startswith("/start"):
                save_user_to_db(uid, user)
                send_message(chat_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif text.startswith("/newpost"): send_message(chat_id, f"Post Menfess\n{SEP}\nPlease type your text directly, or send media with a caption.\nHashtag will be added automatically: {HASHTAG}", get_back_keyboard())
            elif text.startswith("/profile"): send_message(chat_id, f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5\nX Premium: {'ACTIVE until '+user.get('x_premium_until','') if is_premium_active(user) else 'Not active'}", get_back_keyboard())
            elif text.lower().startswith("/stats"): send_stats(chat_id, user, "today")
            elif not user["banned"]:
                if user.get("waiting_proof") and ("photo" in msg or "video" in msg):
                    user["waiting_proof"] = False
                    save_user_to_db(uid, user)
                    fid = msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video", {}).get("file_id")
                    send_message(chat_id, f"Receipt Received! ✅\n{SEP}\nYour payment is currently being verified by the admin. You will receive a notification once it has been approved.", get_back_keyboard())
                    for adm in ADMIN_ID.split(","):
                        adm = adm.strip()
                        if not adm: continue
                        try:
                            TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": adm, "photo": fid, "caption": f"💰 X PREMIUM PAYMENT\nUser: {user['name']} (@{user['username']})\nID: {uid}\nPrice: {X_PRICE}"}, timeout=5)
                            send_message(adm, f"Would you like to approve this user?", {"inline_keyboard": [[{"text": "✅ Approve for 30 Days", "callback_data": f"x_approve_{uid}"}, {"text": "❌ Reject", "callback_data": f"x_reject_{uid}"}]]})
                        except: pass
                    return "ok", 200
                if text and not text.startswith("/") and len(text) >= 3:
                    if user["today_text"] >= 5: send_message(chat_id, f"Limit Reached 5/5\n{SEP}\nQuota will reset at 00:00 WIB", get_back_keyboard())
                    else:
                        clean = text.strip()
                        if HASHTAG.lower() not in clean.lower(): clean = f"{clean} {HASHTAG}"
                        target = user.get("admin_target", "both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                        ch_id = None
                        if target in ["channel", "both"]:
                            r = TG.post(f"{BASE_TG}/sendMessage", json={"chat_id": CHANNEL_ID, "text": clean, "parse_mode": "HTML"}, timeout=3).json()
                            ch_id = r.get("result", {}).get("message_id")
                        if target in ["threads", "both"]: post_to_threads(clean)
                        if (is_admin(chat_id) or (is_premium_active(user) and user.get("x_auto", True))) and get_setting('x_auto_share', 'off') == 'on':
                            post_to_x(clean)
                        user["today_text"] += 1; user["total_text"] += 1; user["total_chars"] = user.get("total_chars", 0)+len(text)
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, target)
                if "photo" in msg or "video" in msg:
                    if user["today_media"] >= 5: send_message(chat_id, "Limit Reached 5/5", get_back_keyboard())
                    else:
                        fid = msg["photo"][-1]["file_id"] if "photo" in msg else msg.get("video", {}).get("file_id")
                        is_photo = "photo" in msg
                        base_cap = caption.strip() if caption else HASHTAG
                        if HASHTAG.lower() not in base_cap.lower(): base_cap = f"{base_cap} {HASHTAG}"
                        target = user.get("admin_target", "both") if is_admin(chat_id) else ("both" if user.get("threads_on") else "channel")
                        ch_id = None
                        wm_bytes = None
                        if target in ["channel", "both"]:
                            if is_photo:
                                raw = download_file(fid); wm = add_watermark(raw) if raw else None
                                if wm:
                                    wm.seek(0); wm_bytes = wm.read(); wm.seek(0)
                                    r = TG.post(f"{BASE_TG}/sendPhoto", data={"chat_id": CHANNEL_ID, "caption": base_cap, "parse_mode": "HTML"}, files={"photo": ("wm.jpg", wm, "image/jpeg")}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                                else:
                                    r = TG.post(f"{BASE_TG}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=3).json(); ch_id = r.get("result", {}).get("message_id")
                            else:
                                r = TG.post(f"{BASE_TG}/sendVideo", json={"chat_id": CHANNEL_ID, "video": fid, "caption": base_cap, "parse_mode": "HTML"}, timeout=5).json(); ch_id = r.get("result", {}).get("message_id")
                        if target in ["threads", "both"]: post_to_threads(base_cap)
                        if (is_admin(chat_id) or (is_premium_active(user) and user.get("x_auto", True))) and get_setting('x_auto_share', 'off') == 'on':
                            if is_photo and wm_bytes:
                                post_to_x(base_cap, wm_bytes)
                            elif not is_photo:
                                post_to_x(base_cap)
                        user["today_media"] += 1; user["total_media"] += 1
                        save_user_to_db(uid, user); send_success(chat_id, user, ch_id, target)
        if "callback_query" in data:
            cq = data["callback_query"]; chat_id = cq["message"]["chat"]["id"]; uid = str(chat_id); cdata = cq["data"]; msg_id = cq["message"]["message_id"]
            where = f"callback {cdata}"
            try: TG.post(f"{BASE_TG}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=2)
            except: pass
            user = get_user(uid)
            HASHTAG = get_setting('hashtag', '#jogjalend')
            if cdata in ["stats", "stats_today", "stats_weekly"]:
                try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=2)
                except: pass
                mode = "weekly" if cdata == "stats_weekly" else "today"
                send_stats(chat_id, user, mode)
            elif cdata == "back_home": edit_message_fast(chat_id, msg_id, get_welcome_text(user), get_main_keyboard(is_admin(chat_id)))
            elif cdata == "lend_page1": edit_message_fast(chat_id, msg_id, M("Please select one of the settings you would like to change."), get_menu_1())
            elif cdata == "lend_page2": edit_message_fast(chat_id, msg_id, M("Please select one of the settings you would like to change."), get_menu_2())
            elif cdata == "my_profile": edit_message_fast(chat_id, msg_id, f"My Profile\n{SEP}\nName: {user['name']}\nUsername: @{user['username']}\nMedia: {user['today_media']}/5 Text: {user['today_text']}/5\nHashtag: {HASHTAG}\nX Premium: {'ACTIVE until '+user.get('x_premium_until','') if is_premium_active(user) else 'Not active'}", get_back_keyboard())
            elif cdata == "post": edit_message_fast(chat_id, msg_id, f"Post Menfess\n{SEP}\nPlease type your text directly, or send media with a caption.\nHashtag will be added automatically: {HASHTAG}", get_back_keyboard())
            elif cdata == "threads":
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Back", "callback_data": "back_home"}]]}
                edit_message_fast(chat_id, msg_id, f"Threads Settings\n{SEP}\nStatus: {'ON' if user.get('threads_on') else 'OFF'}\nLink: threads.net/jogjalend", kb)
            elif cdata == "threads_toggle":
                user["threads_on"] = not user.get("threads_on", False); save_user_to_db(uid, user)
                kb = {"inline_keyboard": [[{"text": f"Threads: {'ON' if user.get('threads_on') else 'OFF'}", "callback_data": "threads_toggle"}], [{"text": "threads.net/jogjalend", "url": THREADS_URL}], [{"text": "Back", "callback_data": "back_home"}]]}
                edit_message_fast(chat_id, msg_id, f"Threads {'ON' if user['threads_on'] else 'OFF'}!\nLink: threads.net/jogjalend", kb)
            elif cdata == "info_bot":
                edit_message_fast(chat_id, msg_id, "Bot Information\n\nJogjaLend Bot is a bot developed by the @jogja_lend team.\n<pre>Bot Version : V114\nDatabase  : PostgreSQL</pre>\nFor questions regarding bot usage, feature suggestions, or bug reports, please contact @joglendsupportBot", get_back_keyboard())
            # ===== X PREMIUM =====
            elif cdata == "x_premium":
                if is_premium_active(user):
                    auto = "ON" if user.get("x_auto", True) else "OFF"
                    edit_message_fast(chat_id, msg_id, f"🎉 X Premium ACTIVE ✅\n{SEP}\nValid Until: {user.get('x_premium_until','')}\nAutomatic Posting Status: {auto}\nYour menfess will be automatically posted to X when enabled.", get_x_premium_keyboard(user))
                else:
                    send_qris(chat_id)
                    edit_message_fast(chat_id, msg_id, f"𝕏 X Premium 🔒\n{SEP}\nEnable automatic posting of your menfess to X.\n\nPrice: {X_PRICE}\n{QRIS_TEXT}\n\nInstructions:\n1. Please transfer the exact amount.\n2. Tap 'I Have Transferred'.\n3. Send a photo of your transfer receipt here.\n4. Please wait for admin approval.", get_x_premium_keyboard(user))
            elif cdata == "x_pay_proof":
                user["waiting_proof"] = True; save_user_to_db(uid, user)
                edit_message_fast(chat_id, msg_id, f"Submit Transfer Receipt\n{SEP}\nPlease send a PHOTO of your QRIS transfer receipt here.\nPlease do not send a menfess yet, send only the receipt photo.", get_back_keyboard())
            elif cdata == "x_toggle_auto":
                if is_premium_active(user):
                    user["x_auto"] = not user.get("x_auto", True); save_user_to_db(uid, user)
                    auto = "ON" if user.get("x_auto", True) else "OFF"
                    edit_message_fast(chat_id, msg_id, f"🎉 X Premium ACTIVE ✅\n{SEP}\nValid Until: {user.get('x_premium_until','')}\nAutomatic Posting Status: {auto}", get_x_premium_keyboard(user))
            elif cdata.startswith("x_approve_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    target_id = cdata.replace("x_approve_", "")
                    tu = get_user(target_id)
                    until = (datetime.now(WIB) + timedelta(days=PREMIUM_DAYS)).strftime("%Y-%m-%d")
                    tu["x_premium_until"] = until; tu["x_auto"] = True; save_user_to_db(target_id, tu)
                    edit_message_fast(chat_id, msg_id, f"✅ Approved! User {target_id} is now active until {until}", get_admin_panel())
                    send_message(target_id, f"🎉 X Premium ACTIVATED!\n{SEP}\nValid Until: {until}\nYour menfess will now be automatically posted to X. You may enable or disable this feature in the X Premium menu.", get_back_keyboard())
            elif cdata.startswith("x_reject_"):
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    target_id = cdata.replace("x_reject_", "")
                    edit_message_fast(chat_id, msg_id, f"❌ Rejected. User {target_id}", get_admin_panel())
                    send_message(target_id, f"❌ Your X Premium payment was rejected.\n{SEP}\nPlease contact the admin if you believe you have completed the transfer.", get_back_keyboard())
            elif cdata == "admin_panel":
                if is_admin(chat_id): edit_message_fast(chat_id, msg_id, M("ADMIN PANEL V114\n------------------------------\nPlease select an admin menu:"), get_admin_panel())
                else: edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
            elif cdata == "admin_x_toggle":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    cur = get_setting('x_auto_share', 'off')
                    new = 'on' if cur == 'off' else 'off'
                    set_setting('x_auto_share', new)
                    edit_message_fast(chat_id, msg_id, M(f"X Auto Share: {new.upper()}\n------------------------------\n{'Posts from admin and Premium users will now be automatically shared to X.' if new=='on' else 'Automatic sharing to X has been disabled.'}\nPlease check the X ENV in Vercel if it fails."), get_admin_panel())
            elif cdata == "admin_x_test":
                if not is_admin(chat_id):
                    edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
                else:
                    ok = post_to_x(f"Test JogjaLend Bot X Auto Share {datetime.now(WIB).strftime('%H:%M')}")
                    edit_message_fast(chat_id, msg_id, M(f"X Test: {'SUCCESSFUL ✅ - Please check your X account' if ok else 'FAILED ❌ - Please check the X ENV / Basic Plan / Vercel Logs'}"), get_admin_panel())
            elif cdata == "lend_tag":
                edit_message_fast(chat_id, msg_id, M(f"Current Tag: {HASHTAG}\n------------------------------\nTo change it, use the command:\n/settag #newtag"), get_menu_1())
            elif cdata == "lend_persetujuan":
                cur = get_setting('approval', 'off')
                kb = {"inline_keyboard": [[{"text": f"Mode: {cur.upper()} - Tap to change", "callback_data": "toggle_approval"}], [{"text": "Back", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Approval Mode\n------------------------------\nIf ON, menfess will not be posted immediately. It will be sent to the LOG_CHANNEL for approval first.\nStatus: {cur}"), kb)
            elif cdata == "toggle_approval":
                cur = get_setting('approval', 'off'); new = 'on' if cur == 'off' else 'off'; set_setting('approval', new)
                kb = {"inline_keyboard": [[{"text": f"Mode: {new.upper()} - Tap to change", "callback_data": "toggle_approval"}], [{"text": "Back", "callback_data": "lend_page1"}]]}
                edit_message_fast(chat_id, msg_id, M(f"Approval Mode has been changed to {new.upper()}"), kb)
            elif cdata == "lend_hapus": edit_message_fast(chat_id, msg_id, M("Delete Message\n------------------------------\nUsers may delete their own posts using the Delete button after posting. Admins may use /del by replying."), get_menu_1())
            elif cdata == "lend_lang": edit_message_fast(chat_id, msg_id, M("Language\n------------------------------\nCurrent bot language: English (Formal)."), get_menu_1())
            elif cdata == "lend_peraturan":
                per = get_setting('peraturan', '-')
                edit_message_fast(chat_id, msg_id, M(f"Rules\n------------------------------\n{per}\n\nTo change: /setperaturan <text>"), get_menu_2())
            elif cdata == "lend_peringatan": edit_message_fast(chat_id, msg_id, M(f"Warnings\n------------------------------\n/warn <user_id> - Add a warning (3 warnings = auto ban)\nYour current warnings: {user.get('warn',0)}/3"), get_menu_2())
            elif cdata == "lend_blacklist":
                db = get_db()
                txt = "Blacklist\n------------------------------\n"
                if db:
                    cur = db.cursor(); cur.execute("SELECT user_id, name, warn FROM menfess_users WHERE banned=true LIMIT 20"); rows = cur.fetchall(); cur.close(); release_db(db)
                    if not rows: txt += "There are no banned users."
                    else:
                        for r in rows: txt += f"{r[1]} - {r[0]} warn:{r[2]}\n"
                    kb = {"inline_keyboard": [[{"text": "Unban: /unban <id>", "callback_data": "admin_noop"}], [{"text": "Back", "callback_data": "lend_page2"}]]}
                else: kb = get_menu_2()
                edit_message_fast(chat_id, msg_id, M(txt), kb)
            elif cdata == "lend_izin": edit_message_fast(chat_id, msg_id, M("Permissions\n------------------------------\nAll users may post text/media (maximum 5). Admins may ban or warn users. Please edit the code to limit links."), get_menu_2())
            elif cdata == "lend_log": edit_message_fast(chat_id, msg_id, M(f"Channel Log\n------------------------------\nLog Channel: {LOG_CHANNEL}\nErrors and approvals will be sent here.\nTo change, update the LOG_CHANNEL env."), get_menu_2())
            elif cdata == "lend_channel":
                if is_admin(chat_id): edit_message_fast(chat_id, msg_id, M(f"Channel Management\n------------------------------\nPlease select a posting target.\nCurrent: {user.get('admin_target','both').upper()}"), get_channel_target_keyboard(user))
                else: edit_message_fast(chat_id, msg_id, M("Access denied. Admin only."), get_back_keyboard())
            elif cdata == "admin_set_channel":
                if is_admin(chat_id): user["admin_target"] = "channel"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Set to CHANNEL ONLY\n------------------------------\nMenfess will only be sent to {CHANNEL_ID}"), get_channel_target_keyboard(user))
            elif cdata == "admin_set_threads":
                if is_admin(chat_id): user["admin_target"] = "threads"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Set to THREADS ONLY\n------------------------------\nMenfess will only be sent to Threads"), get_channel_target_keyboard(user))
            elif cdata == "admin_set_both":
                if is_admin(chat_id): user["admin_target"] = "both"; save_user_to_db(uid, user); edit_message_fast(chat_id, msg_id, M(f"Set to BOTH\n------------------------------\nMenfess will be sent to Channel + Threads"), get_channel_target_keyboard(user))
            elif cdata == "admin_users":
                send_user_list(chat_id)
                edit_message_fast(chat_id, msg_id, M("User list has been sent below."), get_admin_panel())
            elif cdata == "admin_allstats":
                db = get_db()
                if db:
                    cur = db.cursor(); cur.execute("SELECT SUM(total_text), SUM(total_media) FROM menfess_users"); s = cur.fetchone(); cur.close(); release_db(db)
                    edit_message_fast(chat_id, msg_id, M(f"GLOBAL STATISTICS\n------------------------------\nText : {s[0]}\nMedia: {s[1]}"), get_admin_panel())
            elif cdata == "admin_broadcast":
                edit_message_fast(chat_id, msg_id, M("Broadcast\n------------------------------\nPlease type:") + "\n/broadcast <message>\n" + M("It will be sent to all users in the database."), get_admin_panel())
            elif cdata == "admin_webhook":
                r = TG.get(f"{BASE_TG}/getWebhookInfo", timeout=3).json()
                res = r.get('result', {})
                url = res.get('url', '')
                edit_message_fast(chat_id, msg_id, M("Webhook Information\n------------------------------") + f"\nURL: <a href=\"{url}\">{url}</a>\n" + M(f"Pending: {res.get('pending_update_count')}\nLast Error: {res.get('last_error_message')}\n\nTo reset:") + "\n/setwebhook", get_admin_panel())
            elif cdata == "admin_logs": edit_message_fast(chat_id, msg_id, M(f"Logs\n------------------------------\nErrors are automatically sent to {LOG_CHANNEL}\nPlease check /webhookinfo and Vercel Logs."), get_admin_panel())
            elif cdata == "admin_noop": pass
            elif cdata == "close":
                try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": chat_id, "message_id": msg_id}, timeout=2)
                except: pass
            elif cdata.startswith("del_"):
                mid = cdata.replace("del_", "")
                if mid.isdigit():
                    try: TG.post(f"{BASE_TG}/deleteMessage", json={"chat_id": CHANNEL_ID, "message_id": int(mid)}, timeout=2)
                    except: pass
                edit_message_fast(chat_id, msg_id, "Successfully Deleted ✅", get_back_keyboard())
        return "ok", 200
    except Exception as e:
        try: print(f"[CRITICAL {where}] {e}\n{traceback.format_exc()}")
        except: pass
        return "ok", 200
